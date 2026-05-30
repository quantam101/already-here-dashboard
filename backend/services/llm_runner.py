"""
Unified LLM runner — every route that calls an LLM should go through this.

Responsibilities:
  1. Apply semantic compression to the prompt (free token savings).
  2. Check the distillation cache; serve cached response on hit.
  3. Enforce the daily token budget (LLM_DAILY_TOKEN_CAP env, 0 = unlimited).
  4. Make the LLM call only on a cache miss.
  5. Persist the response into the cache.
  6. Track tokens consumed in the daily `llm_budget` row so the dashboard can
     show "tokens used today" and the Cost Guard has a hard floor to enforce.

Public API:

    await run_cached(
        db, provider, model, system_msg, prompt, *, session_id, tier=3
    ) -> str

    await get_today_usage(db) -> dict
    await check_daily_budget(db, *, expected_tokens=0) -> None  (raises 429)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from services.llm_adapter import (
    LLMProviderError, any_key_configured, llm_completion,
)

from services.distillation_service import (
    cache_lookup, cache_store, distill_text, estimate_tokens,
)

logger = logging.getLogger("llm_runner")

BUDGET_COLLECTION = "llm_budget"


def _today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _daily_cap() -> int:
    """Daily token cap (in + out combined). 0 = unlimited."""
    try:
        return int(os.environ.get("LLM_DAILY_TOKEN_CAP", "0"))
    except ValueError:
        return 0


async def _get_today_row(db) -> dict:
    today = _today_iso()
    row = await db[BUDGET_COLLECTION].find_one({"date": today}, {"_id": 0})
    if not row:
        row = {
            "id": f"budget-{today}",
            "date": today,
            "tokens_in": 0,
            "tokens_out": 0,
            "calls": 0,
            "blocked": 0,
            "cache_hits": 0,
        }
        try:
            await db[BUDGET_COLLECTION].insert_one(row)
        except Exception:
            # Race: another worker inserted first. Re-read.
            row = await db[BUDGET_COLLECTION].find_one({"date": today}, {"_id": 0}) or row
    return row


async def get_today_usage(db) -> dict:
    """Operator-facing daily summary."""
    row = await _get_today_row(db)
    cap = _daily_cap()
    used = int(row.get("tokens_in", 0)) + int(row.get("tokens_out", 0))
    return {
        "date": row["date"],
        "tokens_in": int(row.get("tokens_in", 0)),
        "tokens_out": int(row.get("tokens_out", 0)),
        "tokens_total": used,
        "calls": int(row.get("calls", 0)),
        "cache_hits": int(row.get("cache_hits", 0)),
        "blocked": int(row.get("blocked", 0)),
        "daily_cap": cap,
        "remaining": (cap - used) if cap else None,
        "over_cap": bool(cap and used >= cap),
    }


async def _record_call(db, *, tokens_in: int, tokens_out: int, cache_hit: bool = False):
    """Best-effort: bump the daily counters. Never fail the calling request."""
    today = _today_iso()
    try:
        await _get_today_row(db)
        inc = {"calls": 1}
        if cache_hit:
            inc["cache_hits"] = 1
            inc["tokens_in"] = 0  # cache hit doesn't bill input tokens
            inc["tokens_out"] = 0
        else:
            inc["tokens_in"] = int(tokens_in)
            inc["tokens_out"] = int(tokens_out)
        await db[BUDGET_COLLECTION].update_one(
            {"date": today}, {"$inc": inc},
        )
    except Exception as e:
        logger.warning("llm budget bump failed: %s", e)


async def _record_blocked(db) -> None:
    today = _today_iso()
    try:
        await _get_today_row(db)
        await db[BUDGET_COLLECTION].update_one(
            {"date": today}, {"$inc": {"blocked": 1}},
        )
    except Exception:
        pass


async def check_daily_budget(db, *, expected_tokens: int = 0) -> None:
    """Raise HTTP 429 if today's usage + expected next call would exceed cap.

    Pass `expected_tokens` if you know the rough size of the prompt — this
    short-circuits BEFORE the LLM call, so you don't burn the call to discover
    the budget is gone.
    """
    cap = _daily_cap()
    if cap <= 0:
        return  # unlimited
    row = await _get_today_row(db)
    used = int(row.get("tokens_in", 0)) + int(row.get("tokens_out", 0))
    if used + expected_tokens >= cap:
        await _record_blocked(db)
        raise HTTPException(
            status_code=429,
            detail=(
                f"Daily LLM token cap reached ({used}/{cap}). "
                "Bump LLM_DAILY_TOKEN_CAP env or wait for UTC midnight."
            ),
        )


async def run_cached(
    db,
    provider: str,
    model: str,
    system_msg: str,
    prompt: str,
    *,
    session_id: str,
    tier: int = 3,
    parse_json: bool = False,
) -> str:
    """One-stop LLM call: distill → cache-lookup → budget-check → LLM → cache-store.

    Returns the raw LLM response string. Caller is responsible for parsing it.
    On cache hit, no LLM call is made and the budget is not charged.
    """
    api_key_present = any_key_configured()
    if not api_key_present:
        raise HTTPException(
            status_code=503,
            detail=(
                "No LLM provider key configured. Set one of: OPENAI_API_KEY, "
                "ANTHROPIC_API_KEY, GEMINI_API_KEY, or LLM_API_KEY."
            ),
        )

    model_id_str = f"{provider}/{model}"
    distilled_prompt = distill_text(prompt)

    # 1) Cache lookup — free hits
    try:
        hit = await cache_lookup(db, model_id_str, system_msg, distilled_prompt)
    except Exception:
        hit = None
    if hit and hit.get("response"):
        await _record_call(db, tokens_in=0, tokens_out=0, cache_hit=True)
        logger.info("llm_runner: cache HIT session=%s", session_id)
        return hit["response"]

    # 2) Budget pre-check (rough estimate from the distilled prompt)
    estimated = estimate_tokens(distilled_prompt) + estimate_tokens(system_msg)
    await check_daily_budget(db, expected_tokens=estimated)

    # 3) Make the call
    try:
        response = await llm_completion(
            provider=provider, model=model,
            system_msg=system_msg, prompt=distilled_prompt,
            session_id=session_id,
        )
    except LLMProviderError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e

    # 4) Record + cache (both best-effort)
    await _record_call(
        db,
        tokens_in=estimated,
        tokens_out=estimate_tokens(response),
        cache_hit=False,
    )
    try:
        await cache_store(db, model_id_str, system_msg, distilled_prompt, response, tier=tier)
    except Exception:
        pass

    return response


# ---------------------------------------------------------------------------
# Tier-aware routing (blueprint §3.5)
# ---------------------------------------------------------------------------

# Mapping of tier label → (provider, model). Operators can override via env.
TIER_LOW = "low"   # zero-LLM — caller MUST pass `local_fn`
TIER_MID = "mid"   # gemini-3-flash (fast, cheap)
TIER_HIGH = "high" # claude-sonnet (high reasoning)


def _tier_model(tier: str) -> tuple[str, str]:
    tier = (tier or TIER_MID).lower()
    if tier == TIER_HIGH:
        return (
            os.environ.get("LLM_TIER_HIGH_PROVIDER", "anthropic"),
            os.environ.get("LLM_TIER_HIGH_MODEL", "claude-sonnet-4-5"),
        )
    # default mid
    return (
        os.environ.get("LLM_TIER_MID_PROVIDER", "gemini"),
        os.environ.get("LLM_TIER_MID_MODEL", "gemini-2.5-flash"),
    )


async def run_tiered(
    db,
    tier: str,
    system_msg: str,
    prompt: str,
    *,
    session_id: str,
    local_fn=None,
):
    """Tier-aware wrapper around run_cached().

    Tier 1 (low):  skip the LLM entirely. `local_fn(prompt)` must be supplied
                   and is expected to be a pure Python deterministic transform.
                   Records a "tier_1_local" call in the budget counter for
                   visibility but never bills tokens.
    Tier 2 (mid):  Gemini 3 Flash via run_cached().
    Tier 3 (high): Claude Sonnet 4.5 via run_cached().
    """
    tier = (tier or TIER_MID).lower()

    if tier == TIER_LOW:
        if local_fn is None:
            raise HTTPException(
                status_code=500,
                detail="run_tiered(tier='low') requires a local_fn callable",
            )
        result = local_fn(prompt)
        try:
            await _record_call(db, tokens_in=0, tokens_out=0, cache_hit=False)
            # tag this as a tier-1 local routing event in the cache for stats
            await cache_store(
                db, "local/python", system_msg, distill_text(prompt),
                str(result), tier=1,
            )
        except Exception:
            pass
        return result

    provider, model = _tier_model(tier)
    tier_num = 3 if tier == TIER_HIGH else 2
    return await run_cached(
        db, provider, model, system_msg, prompt,
        session_id=session_id, tier=tier_num,
    )


async def daily_usage_history(db, days: int = 14) -> list[dict]:
    """Last N days of LLM budget rows, newest first."""
    rows = await db[BUDGET_COLLECTION].find({}, {"_id": 0}).sort("date", -1).to_list(days)
    return rows
