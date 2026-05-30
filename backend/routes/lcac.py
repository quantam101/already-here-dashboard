"""
Lifelong Catch and Correct (LCAC) — audit-trail anomaly side panel.

Read-only view that scans the last N audit events + ledger entries + cost
status for issues that need operator attention. Returns a structured report
the dashboard renders as a side panel.

Compliant with the Free-Only Build Directive: zero paid API calls, deterministic
code, fail-closed on missing data.
"""
import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

router = APIRouter()


async def get_db():
    from server import db
    return db


@router.get("/")
async def lifelong_catch_correct(db=Depends(get_db)):
    """Scan the system for actionable issues. Returns a flat list of findings.

    Each finding has: severity (high/medium/low), category, message, suggestion.
    """
    findings: list[dict] = []

    # ─── Free-only compliance ────────────────────────────────────────────────
    if not os.environ.get("OPERATOR_EMAIL"):
        findings.append({
            "severity": "medium",
            "category": "security",
            "message": "Operator allowlist not configured",
            "suggestion": "Set OPERATOR_EMAIL in backend/.env so only one Google account can log in",
        })
    if not os.environ.get("STRIPE_WEBHOOK_SECRET") and os.environ.get("STRIPE_API_KEY", "").startswith("sk_live_"):
        findings.append({
            "severity": "high",
            "category": "payments",
            "message": "Stripe in LIVE mode but no webhook secret configured",
            "suggestion": "Add STRIPE_WEBHOOK_SECRET to backend/.env so paid events are signature-verified",
        })
    from services.llm_adapter import any_key_configured
    if not any_key_configured():
        findings.append({
            "severity": "high",
            "category": "ai",
            "message": "No LLM provider key set — AI features (proposals, scout, advisor, books) will fail",
            "suggestion": (
                "Set at least one of OPENAI_API_KEY, ANTHROPIC_API_KEY, "
                "GEMINI_API_KEY, or LLM_API_KEY in backend/.env"
            ),
        })

    # ─── Ledger anomalies ────────────────────────────────────────────────────
    cutoff_iso = (datetime.now(UTC) - timedelta(days=30)).isoformat()
    recent = await db.revenue_ledger.find(
        {"occurred_on": {"$gte": cutoff_iso}}, {"_id": 0}
    ).to_list(1000)
    if not recent:
        findings.append({
            "severity": "low",
            "category": "revenue",
            "message": "No ledger entries in the last 30 days",
            "suggestion": "Record real earnings on /proof-of-work to populate the profit meter",
        })
    else:
        negatives = [e for e in recent if (e.get("net_amount") or 0) < 0]
        if negatives:
            findings.append({
                "severity": "medium",
                "category": "revenue",
                "message": f"{len(negatives)} ledger entries with negative net (refunds or losses)",
                "suggestion": "Review on /proof-of-work to confirm these are intentional",
            })

    # ─── Agent failure rate ──────────────────────────────────────────────────
    agents = await db.agents.find({}, {"_id": 0}).to_list(200)
    for a in agents:
        runs = (a.get("success_count") or 0) + (a.get("failure_count") or 0)
        if runs >= 10:
            fr = (a.get("failure_count") or 0) / runs
            if fr > 0.25:
                findings.append({
                    "severity": "medium",
                    "category": "agents",
                    "message": f"Agent '{a.get('name')}' has {int(fr*100)}% failure rate ({a.get('failure_count')}/{runs})",
                    "suggestion": "Inspect on /agents and review the audit log for last failure",
                })

    # ─── Stale builds ────────────────────────────────────────────────────────
    builds = await db.builds.find({}, {"_id": 0}).to_list(50)
    if not builds:
        findings.append({
            "severity": "low",
            "category": "builds",
            "message": "Build registry is empty",
            "suggestion": "Seed via `python backend/seed_data.py` on the host",
        })

    # ─── Audit gap detection ─────────────────────────────────────────────────
    last_audit = await db.audit_log.find({}, {"_id": 0}).sort("timestamp", -1).to_list(1)
    if last_audit:
        last_ts = last_audit[0].get("timestamp")
        if isinstance(last_ts, str):
            try:
                last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                age_hours = (datetime.now(UTC) - last_dt).total_seconds() / 3600
                if age_hours > 24:
                    findings.append({
                        "severity": "low",
                        "category": "audit",
                        "message": f"No audit events recorded in the last {int(age_hours)}h",
                        "suggestion": "Daily auto-cycle may not be firing — check scheduler logs",
                    })
            except (ValueError, TypeError):
                pass

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 9))

    return {
        "scanned_at": datetime.now(UTC).isoformat(),
        "findings_count": len(findings),
        "by_severity": {
            sev: sum(1 for f in findings if f["severity"] == sev)
            for sev in ("high", "medium", "low")
        },
        "findings": findings,
    }
