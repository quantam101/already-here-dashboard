"""
Data Distillation API — operator-facing telemetry + cache controls.

  GET  /api/distillation/stats   → cache rows, hits, tokens-saved, $ saved
  GET  /api/distillation/config  → current TTL, cost-per-1k, compression on/off
  POST /api/distillation/preview → POST {text, payload?} → distilled text +
                                   YAML payload + before/after token counts
  POST /api/distillation/clear   → wipe cache (returns rows deleted)

No LLM is invoked here — these are pure telemetry/utility endpoints.
"""
import os
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services.distillation_service import (
    CACHE_TTL_SECONDS,
    cache_clear,
    cache_stats,
    distill_text,
    estimate_tokens,
    to_yaml_payload,
)
from services.llm_runner import daily_usage_history, get_today_usage

router = APIRouter()


async def get_db():
    from server import db
    return db


class PreviewRequest(BaseModel):
    text: str = ""
    payload: Any | None = None
    max_chars: int | None = None


@router.get("/stats")
async def stats(db=Depends(get_db)):
    return await cache_stats(db)


@router.get("/config")
async def config():
    return {
        "ttl_seconds": CACHE_TTL_SECONDS,
        "token_cost_per_1k_usd": float(os.environ.get("TOKEN_COST_PER_1K", "0.0001")),
        "compression_enabled": True,
        "yaml_payloads_enabled": True,
        "tiers": {
            "tier_1": "Local rule-based — no LLM (hashtags, formatting, slugs)",
            "tier_2": "Distill + cache lookup — LLM only on miss",
            "tier_3": "LLM call with compressed input + YAML payloads",
        },
    }


@router.post("/preview")
async def preview(body: PreviewRequest):
    """Show the operator exactly what distillation does to their text.

    Useful for tuning prompts and verifying the savings on a specific input.
    """
    distilled = distill_text(body.text, max_chars=body.max_chars)
    yaml_str = to_yaml_payload(body.payload) if body.payload is not None else ""
    json_alt = ""
    if body.payload is not None:
        import json
        json_alt = json.dumps(body.payload, separators=(",", ":"), default=str)

    return {
        "original": {
            "chars": len(body.text or ""),
            "tokens_est": estimate_tokens(body.text or ""),
        },
        "distilled": {
            "text": distilled,
            "chars": len(distilled),
            "tokens_est": estimate_tokens(distilled),
        },
        "savings": {
            "chars": max(0, len(body.text or "") - len(distilled)),
            "tokens_est": max(0, estimate_tokens(body.text or "") - estimate_tokens(distilled)),
            "percent": (
                round(100 * (1 - len(distilled) / max(1, len(body.text or ""))), 1)
                if body.text else 0.0
            ),
        },
        "yaml_payload": yaml_str,
        "json_payload": json_alt,
        "payload_savings_tokens_est": max(
            0, estimate_tokens(json_alt) - estimate_tokens(yaml_str)
        ),
    }


@router.post("/clear")
async def clear(db=Depends(get_db)):
    n = await cache_clear(db)
    return {"deleted": n}


@router.get("/budget")
async def budget(db=Depends(get_db)):
    """Today's LLM token usage and daily cap status (Cost Guard hard floor)."""
    return await get_today_usage(db)


@router.get("/budget/history")
async def budget_history(days: int = 14, db=Depends(get_db)):
    """Last N days of LLM token usage rows (newest first)."""
    days = max(1, min(int(days), 90))
    return await daily_usage_history(db, days=days)
