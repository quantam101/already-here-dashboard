"""
Governance Service — declarative L0-L5 autonomy + HITL gate enforcement.

Loads `/app/governance.yaml` at startup, exposes:
  - current_level() -> str               ("L0".."L5")
  - level_numeric() -> int                (0..5)
  - gate(action_id) -> dict | None
  - require_approval(action_id, db) -> None  (raises HTTPException 403/202)
  - approval_queue collection helpers

Approval flow (matches blueprint §5 §9):
  1. Caller invokes a gated action (e.g. POST /api/payments/checkout).
  2. AutonomyGateway looks up the route in governance.yaml::route_gates.
  3. If the gate's min_level > current autonomy_level → block:
       a. If no pending approval row exists, INSERT one and return HTTP 202
          with the approval_id (operator UI shows it in /api/governance/queue).
       b. If an approval row exists with status='approved' → allow.
       c. If status='rejected' → return HTTP 403.
  4. Caller then re-invokes with header `X-Approval-Id: <id>`.

This is the single chokepoint for "Controlled Enterprise Autonomy."
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi import HTTPException, Request

logger = logging.getLogger("governance")

LEVEL_TO_INT = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
INT_TO_LEVEL = {v: k for k, v in LEVEL_TO_INT.items()}

DEFAULT_MANIFEST_PATH = os.environ.get(
    "GOVERNANCE_MANIFEST", "/app/governance.yaml"
)

APPROVAL_COLLECTION = "approval_queue"


# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

_MANIFEST_CACHE: dict | None = None


def load_manifest(path: str = DEFAULT_MANIFEST_PATH) -> dict:
    """Read governance.yaml. Cached; call reload_manifest() to refresh."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    p = Path(path)
    if not p.exists():
        # Fail-closed: missing manifest → most restrictive level (L0 / advisory).
        # An absent governance file is never a reason to grant more autonomy.
        logger.error(
            "governance manifest missing at %s — defaulting to L0 (most restrictive). "
            "Mount governance.yaml into the container or set GOVERNANCE_MANIFEST.", path
        )
        _MANIFEST_CACHE = {"system": {"autonomy_level": "L0"}, "hitl_gates": [], "route_gates": {}}
        return _MANIFEST_CACHE
    try:
        with p.open("r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("governance manifest parse failed: %s — defaulting to L0", e)
        data = {"system": {"autonomy_level": "L0"}, "hitl_gates": [], "route_gates": {}}
    _MANIFEST_CACHE = data
    return _MANIFEST_CACHE


def reload_manifest() -> dict:
    """Force re-read of governance.yaml (operator-triggered)."""
    global _MANIFEST_CACHE
    _MANIFEST_CACHE = None
    return load_manifest()


# ---------------------------------------------------------------------------
# Level helpers
# ---------------------------------------------------------------------------

def current_level() -> str:
    """Env var > manifest. Operators can override without editing the file."""
    env = os.environ.get("AUTONOMY_LEVEL", "").strip().upper()
    if env in LEVEL_TO_INT:
        return env
    return (load_manifest().get("system", {}) or {}).get("autonomy_level", "L3")


def level_numeric(level: str | None = None) -> int:
    return LEVEL_TO_INT.get((level or current_level()).upper(), 3)


def gate(action_id: str) -> dict | None:
    """Return the gate dict for an action id, or None if no gate is mapped."""
    for g in load_manifest().get("hitl_gates", []) or []:
        if g.get("id") == action_id:
            return g
    return None


def route_to_gate(method: str, path: str) -> str | None:
    """Map an inbound HTTP request to a gate id, if any."""
    key = f"{method.upper()} {path}"
    return (load_manifest().get("route_gates", {}) or {}).get(key)


# ---------------------------------------------------------------------------
# Approval queue
# ---------------------------------------------------------------------------

async def create_approval_row(db, action_id: str, context: dict) -> dict:
    """Create a pending approval row.

    `required_decisions` is computed at creation time:
      - 2 if env `DUAL_ACTOR_APPROVAL=true` AND the gate's severity is "critical"
        (i.e. all L5 gates: capital_allocation, payment_modification,
        contract_execution, pii_access, security_modification,
        private_data_to_public_llm).
      - 1 otherwise.

    `decisions` is an append-only ledger; each entry has actor/note/decided_at.
    Status flips to "approved" only when len(decisions) >= required_decisions
    AND every decision is an `approve`.
    """
    g = gate(action_id) or {}
    dual = os.environ.get("DUAL_ACTOR_APPROVAL", "").strip().lower() in {"1", "true", "yes", "on"}
    required = 2 if (dual and g.get("severity") == "critical") else 1
    row = {
        "id": f"appr-{uuid.uuid4().hex[:12]}",
        "action_id": action_id,
        "context": context,
        "status": "pending",
        "requested_at": datetime.now(UTC).isoformat(),
        "decided_at": None,
        "decided_by": None,
        "decision_note": None,
        "required_decisions": required,
        "decisions": [],
    }
    await db[APPROVAL_COLLECTION].insert_one(row)
    return row


async def get_approval(db, approval_id: str) -> dict | None:
    return await db[APPROVAL_COLLECTION].find_one({"id": approval_id}, {"_id": 0})


async def list_approvals(db, status: str | None = None, limit: int = 50) -> list[dict]:
    q = {"status": status} if status else {}
    return await db[APPROVAL_COLLECTION].find(q, {"_id": 0}).sort("requested_at", -1).to_list(limit)


async def decide_approval(
    db, approval_id: str, *, approve: bool, note: str = "", actor: str = "operator"
) -> dict:
    """Apply one decision to an approval row. Two-person rule when enabled.

    - Reject by any single actor → status becomes "rejected" immediately.
    - Approve: append to `decisions` (deduped by actor). Status flips to
      "approved" once distinct approving actors >= required_decisions.
    - Same actor double-approving cannot satisfy the 2-of-2 rule (deduped).
    """
    row = await get_approval(db, approval_id)
    if not row:
        return {}
    if row.get("status") in {"approved", "rejected"}:
        return row  # final — no further decisions accepted

    now_iso = datetime.now(UTC).isoformat()
    decision_entry = {
        "actor": actor,
        "approve": approve,
        "note": note,
        "decided_at": now_iso,
    }

    if not approve:
        rejected_decisions = list(row.get("decisions") or []) + [decision_entry]
        await db[APPROVAL_COLLECTION].update_one(
            {"id": approval_id},
            {"$set": {
                "status": "rejected",
                "decided_at": now_iso,
                "decided_by": actor,
                "decision_note": note,
                "decisions": rejected_decisions,
            }},
        )
        return await get_approval(db, approval_id) or {}

    # Approve flow — append, then check threshold against distinct actors
    decisions = list(row.get("decisions") or [])
    # dedupe: if this actor already approved, skip the append (idempotent)
    if not any(d.get("actor") == actor and d.get("approve") for d in decisions):
        decisions.append(decision_entry)

    required = int(row.get("required_decisions") or 1)
    distinct_approvers = {d.get("actor") for d in decisions if d.get("approve")}
    final = len(distinct_approvers) >= required

    update = {
        "decisions": decisions,
        "decided_at": now_iso,
        "decided_by": actor,
        "decision_note": note,
    }
    if final:
        update["status"] = "approved"

    await db[APPROVAL_COLLECTION].update_one({"id": approval_id}, {"$set": update})
    return await get_approval(db, approval_id) or {}


# ---------------------------------------------------------------------------
# Single chokepoint — call this from any gated route
# ---------------------------------------------------------------------------

async def enforce(
    *,
    db,
    request: Request,
    action_id: str,
    context: dict | None = None,
) -> None:
    """Block the request unless the gate is cleared.

    Behavior:
      - No gate mapped → noop (allow).
      - Current autonomy_level >= gate.min_level → noop (allow).
      - X-Approval-Id header present + row approved → allow.
      - X-Approval-Id header present + row rejected → 403.
      - Otherwise → 202 with a fresh approval_id (operator must approve).
    """
    g = gate(action_id)
    if not g:
        return  # action not in the gate list

    required_level = LEVEL_TO_INT.get(g.get("min_level", "L5"), 5)
    if level_numeric() >= required_level:
        return  # autonomy bracket is high enough

    approval_id = request.headers.get("X-Approval-Id", "").strip()
    if approval_id:
        row = await get_approval(db, approval_id)
        if row and row.get("action_id") == action_id:
            if row.get("status") == "approved":
                return
            if row.get("status") == "rejected":
                raise HTTPException(
                    status_code=403,
                    detail=f"Approval {approval_id} was rejected: {row.get('decision_note', '')}",
                )

    # No usable approval — create a pending row and return 202.
    row = await create_approval_row(db, action_id, context or {})
    required = int(row.get("required_decisions") or 1)
    next_step = (
        f"Operator approves via POST /api/governance/approvals/{row['id']}/approve "
        f"(actor=<distinct_id>), then re-issue this request with header "
        f"`X-Approval-Id: {row['id']}`."
    )
    if required >= 2:
        next_step += (
            f" TWO-PERSON RULE active: this gate needs {required} distinct actors to "
            f"approve before the request will clear (set actor= in the approve body)."
        )
    raise HTTPException(
        status_code=202,
        detail={
            "action_id": action_id,
            "approval_id": row["id"],
            "severity": g.get("severity"),
            "description": g.get("description"),
            "current_autonomy_level": current_level(),
            "required_min_level": g.get("min_level"),
            "required_decisions": required,
            "next_step": next_step,
        },
    )
