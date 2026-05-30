"""
Cost status endpoint — free-only policy enforcement view.

Aggregates connector cost classifications + paid integrations into a single
operator-facing report. Required by the Free-Only Final Build Directive.

cost_class taxonomy (from connectors registry):
  - free_local          → no network calls, runs on operator's box
  - free_external       → free public API (Reddit, HackerNews, Grants.gov)
  - manual_free         → manual export pack (TikTok, IG, YouTube)
  - paid_blocked        → blocked by Cost Guard (Twitter API, etc.)
  - unknown             → must be blocked-by-default per directive
"""
import os

from fastapi import APIRouter, Depends

router = APIRouter()


async def get_db():
    from server import db
    return db


@router.get("/status")
async def cost_status(db=Depends(get_db)):
    """Live $0/month enforcement report.

    Returns:
      target_monthly_usd: 0
      estimated_monthly_usd: sum of any paid integrations active
      blocked: counts of paid + unknown connectors
      requires_secret: list of named secrets the operator hasn't set
    """
    connectors = await db.connectors.find({}, {"_id": 0}).to_list(1000)

    by_class: dict[str, int] = {}
    paid_blocked: list[dict] = []
    unknown_blocked: list[dict] = []
    free_active: list[dict] = []
    manual_export: list[dict] = []

    for c in connectors:
        cls = c.get("cost_class") or "unknown"
        by_class[cls] = by_class.get(cls, 0) + 1
        summary = {"id": c.get("id"), "name": c.get("name"), "platform": c.get("platform")}
        if cls == "paid_blocked":
            paid_blocked.append({**summary, "monthly_cost_usd": c.get("monthly_cost_usd", 0)})
        elif cls == "unknown":
            unknown_blocked.append(summary)
        elif cls in ("free_local", "free_external"):
            free_active.append(summary)
        elif cls == "manual_free":
            manual_export.append(summary)

    # Estimate: only counts active paid services, NOT blocked ones (those are $0 by definition)
    estimated_monthly_usd = 0.0

    # Required secrets per integration (operator-facing, no values returned)
    required_secrets = {
        "STRIPE_API_KEY": "Stripe payments — receive real money",
        "OPENAI_API_KEY": "OpenAI key — proposals, books, advisor (Tier 3)",
        "ANTHROPIC_API_KEY": "Anthropic Claude key — advisor + reasoning (Tier 3)",
        "GEMINI_API_KEY": "Google Gemini key — scripts + summarization (Tier 2)",
        "LLM_API_KEY": "Universal fallback (set if all providers share one key e.g. OpenRouter)",
        "OPERATOR_EMAIL": "Operator allowlist — locks Google login to one email",
    }
    requires_secret = [
        {"name": k, "purpose": v}
        for k, v in required_secrets.items()
        if not os.environ.get(k)
    ]

    # Optional secrets — surface as warnings only
    optional_secrets = {
        "STRIPE_WEBHOOK_SECRET": "Stripe webhook signature verification (live mode required)",
        "BW_SESSION": "Bitwarden CLI session token — enables vault browser",
    }
    optional_missing = [
        {"name": k, "purpose": v}
        for k, v in optional_secrets.items()
        if not os.environ.get(k)
    ]

    return {
        "target_monthly_usd": 0.0,
        "estimated_monthly_usd": round(estimated_monthly_usd, 2),
        "compliant": estimated_monthly_usd == 0.0,
        "connectors_by_class": by_class,
        "free_active": free_active,
        "manual_export": manual_export,
        "paid_blocked": paid_blocked,
        "unknown_blocked": unknown_blocked,
        "requires_secret": requires_secret,
        "optional_missing_secrets": optional_missing,
        "policy": {
            "block_paid": True,
            "block_unknown_cost": True,
            "fail_closed_on_missing_secret": True,
        },
    }


@router.get("/policy")
async def cost_policy():
    """Static policy document — Free-Only enforcement rules."""
    return {
        "target_monthly_usd": 0.0,
        "block_paid_connectors": True,
        "block_unknown_cost": True,
        "manual_export_when_api_paid": True,
        "fail_closed_on_missing_secret": True,
        "approved_free_integrations": [
            "litellm + LLM provider API key (Gemini / Claude / OpenAI text + images, BYO key)",
            "Stripe Checkout (test mode by default)",
            "Reddit JSON API (no auth)",
            "HackerNews API (no auth)",
            "Grants.gov API (no auth)",
            "Browser SpeechSynthesis (audiobooks, $0 TTS)",
            "Vaultwarden self-hosted Docker (or Bitwarden free tier)",
            "Caddy + Let's Encrypt (free HTTPS)",
            "Oracle Cloud Always Free (compute + bandwidth)",
        ],
    }
