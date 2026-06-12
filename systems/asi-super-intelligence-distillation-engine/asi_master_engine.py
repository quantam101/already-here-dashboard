from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MINIMUM_DAILY_FIELD_REVENUE = 500.0
MINIMUM_DISPATCH_VALUE = 130.0
MINIMUM_EFFECTIVE_HOURLY = 65.0
PREFERRED_SMART_HANDS_FLAT = 200.0
RETAINER_FLOOR_MONTHLY = 1500.0
PREMIUM_SERVICE_TYPES = {
    "server_smart_hands",
    "data_center",
    "network_support",
    "ap_wireless",
    "pos_support",
    "access_control",
    "healthcare_equipment",
    "project_management",
    "field_project_lead",
    "retainer_coverage",
}
LOW_MARGIN_TERMS = ("helper", "labor only", "unknown pay", "commission only", "intern", "w2", "full-time", "employee")
LONG_TRAVEL_TERMS = ("flagstaff", "show low", "tucson", "yuma", "prescott")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def loads(value: str | None, default: Any = None) -> Any:
    return json.loads(value) if value else default


@dataclass(frozen=True)
class LeadDecision:
    grade: str
    expected_revenue: float
    target_rate: float
    effective_hourly: float | None
    stackability_score: int
    repeat_potential: int
    retainer_potential: int
    data_value_score: int
    risk_flags: tuple[str, ...]
    next_action: str


class StateMesh:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks(
                    task_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 50,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    worker_id TEXT,
                    lease_until TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_agent_tasks_claim ON agent_tasks(status, priority, created_at);
                CREATE TABLE IF NOT EXISTS companies(
                    company_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(name)
                );
                CREATE TABLE IF NOT EXISTS opportunities(
                    opportunity_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    company_id TEXT,
                    title TEXT NOT NULL,
                    location TEXT,
                    service_type TEXT,
                    expected_revenue REAL,
                    target_rate REAL,
                    effective_hourly REAL,
                    grade TEXT NOT NULL,
                    stackability_score INTEGER,
                    repeat_potential INTEGER,
                    retainer_potential INTEGER,
                    data_value_score INTEGER,
                    risk_flags_json TEXT NOT NULL,
                    raw_payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS action_log(
                    action_id TEXT PRIMARY KEY,
                    opportunity_id TEXT,
                    action_type TEXT NOT NULL,
                    action_body TEXT NOT NULL,
                    approval_required INTEGER NOT NULL DEFAULT 1,
                    sent_at TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evaluation_metrics(
                    metric_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    source_engine TEXT NOT NULL,
                    scores_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sync_outbox(
                    outbox_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_log(
                    audit_id TEXT PRIMARY KEY,
                    actor TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def audit(self, actor: str, event_type: str, entity_type: str, entity_id: str, details: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO audit_log VALUES (?, ?, ?, ?, ?, ?, ?)", (uuid.uuid4().hex, actor, event_type, entity_type, entity_id, dumps(details), now()))

    def stage(self, task: dict[str, Any]) -> str:
        task_id = task.get("task_id") or f"TASK_{uuid.uuid4().hex[:12].upper()}"
        kind = task.get("kind", "revenue_lead")
        payload = task.get("payload", task)
        timestamp = now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO agent_tasks(task_id, kind, payload_json, status, priority, max_attempts, created_at, updated_at)
                VALUES (?, ?, ?, 'PENDING', ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET payload_json=excluded.payload_json, status='PENDING', updated_at=excluded.updated_at
                """,
                (task_id, kind, dumps(payload), int(task.get("priority", 50)), int(task.get("max_attempts", 3)), timestamp, timestamp),
            )
        self.audit("system", "TASK_STAGED", "agent_task", task_id, {"kind": kind})
        return task_id

    def claim(self, worker_id: str, limit: int = 8, lease_seconds: int = 300) -> list[dict[str, Any]]:
        lease_until = (datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)).isoformat()
        timestamp = now()
        claimed: list[dict[str, Any]] = []
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """
                SELECT * FROM agent_tasks
                WHERE (status='PENDING' OR (status='PROCESSING' AND lease_until < ?)) AND attempts < max_attempts
                ORDER BY priority ASC, created_at ASC
                LIMIT ?
                """,
                (timestamp, limit),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE agent_tasks SET status='PROCESSING', worker_id=?, lease_until=?, attempts=attempts+1, updated_at=? WHERE task_id=?",
                    (worker_id, lease_until, timestamp, row["task_id"]),
                )
                item = dict(row)
                item["payload"] = loads(item.pop("payload_json"), {})
                claimed.append(item)
            conn.execute("COMMIT")
        return claimed

    def complete(self, task_id: str, worker_id: str, status: str = "LOCAL_FALLBACK", error: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute("UPDATE agent_tasks SET status=?, worker_id=?, lease_until=NULL, error=?, updated_at=? WHERE task_id=?", (status, worker_id, error, now(), task_id))
        self.audit(worker_id, "TASK_TRANSITION", "agent_task", task_id, {"status": status, "error": error})

    def store_company(self, name: str | None, source: str) -> str | None:
        if not name:
            return None
        company_id = uuid.uuid5(uuid.NAMESPACE_DNS, name.lower()).hex
        timestamp = now()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO companies VALUES (?, ?, ?, ?, ?) ON CONFLICT(name) DO UPDATE SET source=excluded.source, updated_at=excluded.updated_at",
                (company_id, name, source, timestamp, timestamp),
            )
        return company_id

    def store_result(self, task: dict[str, Any], decision: LeadDecision, action_body: str) -> str:
        payload = task["payload"]
        source = str(payload.get("source", "unknown"))
        company_id = self.store_company(payload.get("company"), source)
        opportunity_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{source}|{payload.get('title')}|{payload.get('location')}").hex
        timestamp = now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO opportunities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(opportunity_id) DO UPDATE SET expected_revenue=excluded.expected_revenue, target_rate=excluded.target_rate,
                effective_hourly=excluded.effective_hourly, grade=excluded.grade, stackability_score=excluded.stackability_score,
                repeat_potential=excluded.repeat_potential, retainer_potential=excluded.retainer_potential, data_value_score=excluded.data_value_score,
                risk_flags_json=excluded.risk_flags_json, raw_payload_json=excluded.raw_payload_json, updated_at=excluded.updated_at
                """,
                (
                    opportunity_id,
                    source,
                    company_id,
                    str(payload.get("title", "Untitled opportunity")),
                    payload.get("location"),
                    payload.get("service_type"),
                    decision.expected_revenue,
                    decision.target_rate,
                    decision.effective_hourly,
                    decision.grade,
                    decision.stackability_score,
                    decision.repeat_potential,
                    decision.retainer_potential,
                    decision.data_value_score,
                    dumps(decision.risk_flags),
                    dumps(payload),
                    timestamp,
                    timestamp,
                ),
            )
            conn.execute("INSERT INTO action_log VALUES (?, ?, ?, ?, 1, NULL, ?)", (uuid.uuid4().hex, opportunity_id, "COUNTER_OR_REPLY", action_body, timestamp))
            conn.execute("INSERT INTO evaluation_metrics VALUES (?, ?, ?, ?, ?)", (uuid.uuid4().hex, task["task_id"], "LOCAL_DETERMINISTIC_REVENUE_SCORER", dumps(decision.__dict__), timestamp))
            conn.execute("INSERT INTO sync_outbox VALUES (?, ?, ?, 'PENDING', ?)", (uuid.uuid4().hex, "opportunity.upserted", dumps({"opportunity_id": opportunity_id}), timestamp))
        return opportunity_id

    def summary(self) -> dict[str, Any]:
        with self.connect() as conn:
            top = [dict(row) for row in conn.execute("SELECT title, source, location, expected_revenue, target_rate, grade, retainer_potential, data_value_score FROM opportunities ORDER BY expected_revenue DESC, data_value_score DESC LIMIT 10")]
            actions = [dict(row) for row in conn.execute("SELECT action_type, action_body, approval_required FROM action_log WHERE sent_at IS NULL ORDER BY created_at DESC LIMIT 10")]
            return {"top_opportunities": top, "pending_actions": actions}


def num(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).replace("$", "").replace(",", "")) if value not in (None, "") else default
    except ValueError:
        return default


def contains_any(text: str, terms: set[str] | tuple[str, ...]) -> bool:
    lower = text.lower()
    return any(term.lower() in lower for term in terms)


def score(payload: dict[str, Any]) -> LeadDecision:
    title = str(payload.get("title", ""))
    description = str(payload.get("description", ""))
    location = str(payload.get("location", ""))
    service_type = str(payload.get("service_type", payload.get("serviceType", ""))).lower()
    combined = " ".join([title, description, location, service_type])
    listed_rate = num(payload.get("listed_rate", payload.get("listedRate")))
    max_hours = num(payload.get("max_hours", payload.get("maxHours")), 2.0)
    fixed_pay = num(payload.get("fixed_pay", payload.get("fixedPay")))
    expected_revenue = fixed_pay or (listed_rate * max_hours if listed_rate else num(payload.get("expected_revenue", payload.get("expectedRevenue"))))
    travel_minutes = num(payload.get("estimated_travel_minutes", payload.get("estimatedTravelMinutes")))
    onsite_minutes = num(payload.get("estimated_onsite_minutes", payload.get("estimatedOnsiteMinutes")), max_hours * 60 if max_hours else 120)
    effective_hourly = expected_revenue / max((travel_minutes + onsite_minutes) / 60, 0.25) if expected_revenue else None
    premium = service_type in PREMIUM_SERVICE_TYPES or contains_any(combined, {"server", "data center", "hpe", "storage", "access control", "pos", "wireless", "project manager", "site lead", "field lead", "retainer"})
    risk_flags: list[str] = []
    if expected_revenue < MINIMUM_DISPATCH_VALUE:
        risk_flags.append("below_minimum_dispatch_value")
    if effective_hourly is not None and effective_hourly < MINIMUM_EFFECTIVE_HOURLY:
        risk_flags.append("below_effective_hourly_floor")
    if contains_any(combined, LOW_MARGIN_TERMS):
        risk_flags.append("employment_or_low_margin_language")
    if contains_any(location, LONG_TRAVEL_TERMS) or travel_minutes > 90:
        risk_flags.append("travel_burden")
    if not expected_revenue:
        risk_flags.append("pay_not_visible")
    repeat_potential = min((2 if payload.get("repeat_potential") else 0) + (3 if contains_any(combined, {"retainer", "recurring", "vendor", "multi-site", "rollout", "municipal", "procurement"}) else 0) + (1 if premium else 0), 5)
    retainer_potential = min((3 if payload.get("retainer_potential") else 0) + (2 if contains_any(combined, {"overflow", "coverage", "vendor list", "municipal", "procurement", "msp", "retainer", "recurring"}) else 0) + (2 if service_type in {"project_management", "field_project_lead", "retainer_coverage"} else 0), 5)
    stackability_score = max(0, min(5, 5 - (2 if travel_minutes > 45 else 0) - (1 if onsite_minutes > 180 else 0) + (1 if expected_revenue >= 250 else 0) + (2 if expected_revenue >= MINIMUM_DAILY_FIELD_REVENUE else 0)))
    data_value_score = min(10, 1 + repeat_potential + retainer_potential + (1 if payload.get("company") else 0) + (1 if premium else 0))
    if expected_revenue >= MINIMUM_DAILY_FIELD_REVENUE:
        grade = "A"
    elif expected_revenue >= 250 and stackability_score >= 3:
        grade = "B"
    elif expected_revenue >= 150 and stackability_score >= 4:
        grade = "C"
    elif retainer_potential >= 4 and data_value_score >= 7:
        grade = "B_STRATEGIC"
    else:
        grade = "AVOID"
    if "travel_burden" in risk_flags and expected_revenue < MINIMUM_DAILY_FIELD_REVENUE:
        grade = "AVOID"
    if "employment_or_low_margin_language" in risk_flags and retainer_potential < 4:
        grade = "AVOID"
    target_rate = max(expected_revenue, PREFERRED_SMART_HANDS_FLAT if premium else MINIMUM_DISPATCH_VALUE)
    if "travel_burden" in risk_flags:
        target_rate = max(target_rate, 450.0)
    next_action = {
        "A": "Pursue as a $500 daily field anchor or premium project/SOW.",
        "B": "Pursue only if it stacks locally or converts into project/retainer work.",
        "B_STRATEGIC": "Store as database intelligence and convert to retainer, procurement, vendor, or software workflow.",
        "C": "Use only as tightly clustered filler after premium work is secured.",
        "AVOID": "Pass unless the buyer approves a premium or travel-adjusted counter.",
    }[grade]
    return LeadDecision(grade, expected_revenue, target_rate, effective_hourly, stackability_score, repeat_potential, retainer_potential, data_value_score, tuple(risk_flags), next_action)


def action_draft(payload: dict[str, Any], decision: LeadDecision) -> str:
    company = payload.get("company") or "Team"
    title = payload.get("title") or "this assignment"
    location = payload.get("location") or "the listed site"
    return "\n".join([
        f"Hello {company},",
        "",
        f"Stephen Franklin with Already Here LLC. I can support {title} at {location} at a flat rate of ${decision.target_rate:,.0f}, including standard field tools, onsite work, closeout notes, required photos, and coordination with remote support as needed.",
        "",
        "Additional approved onsite work beyond the agreed scope is billed at $65/hr. Please confirm scope, site access, onsite contact, parts/equipment availability, and that no unpaid return trip is required.",
        "",
        "If this is recurring Phoenix metro coverage, Already Here LLC can also support a monthly retainer or priority-response arrangement.",
        "",
        "Stephen Franklin",
        "Already Here LLC",
        "602-882-2920",
        "dispatch@alreadyherellc@gmail.com",
    ])


def demo_tasks() -> list[dict[str, Any]]:
    return [
        {"kind": "revenue_lead", "priority": 5, "payload": {"source": "direct_vendor", "company": "Phoenix MSP Overflow Buyer", "title": "Same-Day Network Outage Smart Hands", "location": "Phoenix, AZ", "service_type": "server_smart_hands", "fixed_pay": 500, "estimated_travel_minutes": 25, "estimated_onsite_minutes": 150, "retainer_potential": True, "repeat_potential": True}},
        {"kind": "revenue_lead", "priority": 10, "payload": {"source": "workmarket", "company": "Concert Technologies", "title": "PIAB Mount and LTE Test", "location": "Flagstaff, AZ", "service_type": "network_support", "listed_rate": 65, "max_hours": 2, "estimated_travel_minutes": 240, "estimated_onsite_minutes": 90, "repeat_potential": True}},
        {"kind": "revenue_lead", "priority": 20, "payload": {"source": "municipal_procurement", "company": "City Procurement Path", "title": "Vendor Registration for IT Field Services and Project Management", "location": "Chandler, AZ", "service_type": "municipal_procurement", "expected_revenue": 0, "retainer_potential": True, "repeat_potential": True}},
    ]


def run_cycle(db_path: str, tasks: list[dict[str, Any]], limit: int = 8) -> dict[str, Any]:
    mesh = StateMesh(db_path)
    for task in tasks:
        mesh.stage(task)
    worker_id = f"AH_AGENT_{uuid.uuid4().hex[:8].upper()}"
    claimed = mesh.claim(worker_id, limit=limit)
    processed = 0
    for task in claimed:
        try:
            decision = score(task["payload"])
            mesh.store_result(task, decision, action_draft(task["payload"], decision))
            mesh.complete(task["task_id"], worker_id)
            processed += 1
        except Exception as exc:
            mesh.complete(task["task_id"], worker_id, status="FAILED", error=str(exc))
    return {"worker_id": worker_id, "claimed": len(claimed), "processed": processed, "summary": mesh.summary()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Already Here ASI Super-Intelligence Distillation Engine")
    parser.add_argument("--db", default="./state_mesh_wal.db")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--ingest-json")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    tasks: list[dict[str, Any]] = []
    if args.demo:
        tasks.extend(demo_tasks())
    if args.ingest_json:
        raw = json.loads(Path(args.ingest_json).read_text(encoding="utf-8"))
        tasks.extend(raw["tasks"] if isinstance(raw, dict) and "tasks" in raw else raw)
    result = run_cycle(args.db, tasks, args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
