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

    await llm_complete(system, user, *, max_tokens, temperature) -> str
        Smart failover: Groq → Gemini → Mistral → DeepSeek → OpenRouter → …
        Use this in all routes instead of run_cached(provider="gemini", …).
        Does NOT cache or track budget (stateless helper for agents/routes).

    await run_cached(
        db, provider, model, system_msg, prompt, *, session_id, tier=3
    ) -> str
        Low-level: specific provider + model. Use when you want caching/budget.

    await get_today_usage(db) -> dict
    await check_daily_budget(db, *, expected_tokens=0) -> None  (raises 429)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from emergentintegrations.llm.chat import LlmChat, UserMessage

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
    api_key = os.environ.get("EMERGENT_LLM_KEY") or os.environ.get("GROQ_API_KEY") or ""
    if not api_key:
        raise HTTPException(status_code=503, detail="No LLM key configured (set EMERGENT_LLM_KEY or GROQ_API_KEY)")

    model_id = f"{provider}/{model}"
    distilled_prompt = distill_text(prompt)

    # 1) Cache lookup — free hits
    try:
        hit = await cache_lookup(db, model_id, system_msg, distilled_prompt)
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
    chat = LlmChat(api_key=api_key, session_id=session_id, system_message=system_msg)
    chat.with_model(provider, model)
    try:
        response = await chat.send_message(UserMessage(text=distilled_prompt))
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
        await cache_store(db, model_id, system_msg, distilled_prompt, response, tier=tier)
    except Exception:
        pass

    return response


async def daily_usage_history(db, days: int = 14) -> list[dict]:
    """Last N days of LLM budget rows, newest first."""
    rows = await db[BUDGET_COLLECTION].find({}, {"_id": 0}).sort("date", -1).to_list(days)
    return rows


# ── llm_complete — stateless failover helper ──────────────────────────────────

def _failover_providers() -> list[tuple[str, str, str]]:
    """
    Build the ordered provider list from available env vars.
    Returns list of (provider_name, model_id, api_key).
    Priority: Groq (fastest, free) → Gemini Flash → Mistral → DeepSeek → OpenRouter
    """
    providers: list[tuple[str, str, str]] = []
    gr = os.environ.get("GROQ_API_KEY", "").strip()
    lm = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    ms = os.environ.get("MISTRAL_API_KEY", "").strip()
    ds = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    qw = os.environ.get("QWEN_API_KEY", "").strip()
    or_ = os.environ.get("OPENROUTER_API_KEY", "").strip()

    if gr:
        providers.append(("groq",      "llama-3.3-70b-versatile", gr))
        providers.append(("groq",      "llama-3.1-8b-instant",    gr))
    if lm:
        providers.append(("gemini",    "gemini-2.5-flash",        lm))
    if ms:
        providers.append(("mistral",   "mistral-small-latest",    ms))
        providers.append(("codestral", "codestral-latest",        ms))
    if ds:
        providers.append(("deepseek",  "deepseek-chat",           ds))
    if qw:
        providers.append(("qwen",      "qwen-plus",               qw))
    if or_:
        providers.append(("openrouter", "openai/gpt-4o-mini",     or_))
    if lm:
        # Gemini 1.5 as last resort
        providers.append(("gemini",    "gemini-1.5-flash",        lm))
    return providers


async def llm_complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 1500,
    temperature: float = 0.7,
    session_id: str = "llm-complete",
) -> str:
    """
    Smart multi-provider LLM call with automatic failover.

    Tries providers in priority order (Groq first — fastest & free).
    Falls through to the next provider on any error (expired key, rate limit, 4xx/5xx).

    Use this in routes / agents instead of hardcoding run_cached(provider="gemini", …).
    Does NOT use the distillation cache or budget tracker — it is stateless.
    If you need caching, call run_cached() directly after this.

    Raises HTTPException(502) only when ALL configured providers fail.
    Raises HTTPException(503) when no providers are configured.
    """
    providers = _failover_providers()
    if not providers:
        raise HTTPException(
            status_code=503,
            detail="No LLM keys configured. Set GROQ_API_KEY or EMERGENT_LLM_KEY in .env.",
        )

    last_error: Exception | None = None
    for provider, model, api_key in providers:
        try:
            logger.debug("llm_complete: trying provider=%s model=%s", provider, model)
            import uuid as _uuid
            sid = f"{session_id}-{_uuid.uuid4().hex[:8]}"
            chat = LlmChat(api_key=api_key, session_id=sid, system_message=system)
            chat.with_model(provider, model)
            response = await chat.send_message(UserMessage(text=user))
            if response:
                logger.info("llm_complete: success provider=%s model=%s", provider, model)
                return response
        except Exception as exc:
            last_error = exc
            logger.warning(
                "llm_complete: provider=%s model=%s failed: %s — trying next",
                provider, model, str(exc)[:120],
            )
            continue

    raise HTTPException(
        status_code=502,
        detail=f"All LLM providers failed. Last error: {last_error}",
    )
