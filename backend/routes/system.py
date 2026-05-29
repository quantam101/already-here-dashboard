"""
System status — operator-facing health/config check that powers the Quickstart Wizard.

No secrets are leaked; the endpoint only reports *whether* each piece of config is
set, not the values themselves.
"""
from fastapi import APIRouter, Depends
import os
from services.bitwarden_service import get_bitwarden_service

router = APIRouter()


async def get_db():
    from server import db
    return db


def _stripe_mode() -> str:
    key = os.environ.get("STRIPE_API_KEY", "") or ""
    if key.startswith("sk_live_"):
        return "live"
    if key.startswith("sk_test_"):
        return "test"
    if not key:
        return "missing"
    return "unknown"


@router.get("/status")
async def system_status(db=Depends(get_db)):
    """Operator dashboard status snapshot — drives the Quickstart Wizard.

    Returns a JSON-safe summary of what's configured. No secret values returned.
    """
    from services.llm_adapter import any_key_configured, configured_providers

    operator_email = os.environ.get("OPERATOR_EMAIL", "") or ""
    operator_token_set = bool(os.environ.get("OPERATOR_TOKEN"))
    llm_key_set = any_key_configured()
    stripe_webhook_secret_set = bool(os.environ.get("STRIPE_WEBHOOK_SECRET"))

    # Counts of seeded entities — used by wizard to know if seed_data ran
    counts = {
        "revenue_streams": await db.revenue_streams.count_documents({}),
        "agents": await db.agents.count_documents({}),
        "builds": await db.builds.count_documents({}),
        "connectors": await db.connectors.count_documents({}),
        "ledger_entries": await db.revenue_ledger.count_documents({}),
        "books": await db.books.count_documents({}),
        "payment_transactions": await db.payment_transactions.count_documents({}),
    }

    # Daily scheduler hour for the Run Cycle automation
    daily_cycle_hour = os.environ.get("DAILY_CYCLE_HOUR_UTC", "7")

    bw = await get_bitwarden_service().status()

    return {
        "operator_email_set": bool(operator_email),
        "operator_email_masked": (
            operator_email[0] + "***@" + operator_email.split("@", 1)[1]
            if operator_email and "@" in operator_email else None
        ),
        "operator_token_set": operator_token_set,
        "stripe_mode": _stripe_mode(),
        "stripe_webhook_secret_set": stripe_webhook_secret_set,
        "llm_key_set": llm_key_set,
        "llm_providers_configured": configured_providers(),
        "daily_cycle_hour_utc": daily_cycle_hour,
        "counts": counts,
        "is_seeded": counts["revenue_streams"] >= 3 and counts["agents"] >= 3,
        "system_mode": os.environ.get("SYSTEM_MODE", "production"),
        "bitwarden": {
            "installed": bw["installed"],
            "unlocked": bw["unlocked"],
            "server": bw["server"],
            "user_masked": (bw["user"][0] + "***@" + bw["user"].split("@", 1)[1]) if bw["user"] and "@" in bw["user"] else None,
        },
    }
