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
        Smart failover (all $0):
          LM Studio (local) → Ollama (local) → Groq (free API) → Gemini (free API) →
          DeepSeek (free API) → Qwen (free API) → Mistral (free API) →
          OpenRouter free models → Pollinations (always free, no key)
        Use this in all routes instead of run_cached(provider="gemini", …).
        Does NOT cache or track budget (stateless helper for agents/routes).

    await run_cached(
        db, provider, model, system_msg, prompt, *, session_id, tier=3
    ) -> str
        Low-level: specific provider + model. Use when you want caching/budget.

    await get_today_usage(db) -> dict
    await check_daily_budget(db, *, expected_tokens=0) -> None  (raises 429)

Free provider setup guide (all $0, no credit card):
  LM_STUDIO_BASE_URL → local LM Studio server (start server in LM Studio UI)
  LM_STUDIO_MODEL    → model name shown in LM Studio (e.g. llama-3.2-3b-instruct)
  OLLAMA_BASE_URL    → local Ollama server (run `ollama serve`)
  OLLAMA_MODEL       → e.g. llama3.2:3b, gemma2:2b, qwen2.5:3b, deepseek-r1:1.5b
  GROQ_API_KEY       → free at console.groq.com  (Llama 3.3 70B, 14 400 req/day)
  GEMINI_API_KEY     → free at ai.google.dev     (Gemini 2.5 Flash, 1 500 req/day)
  DEEPSEEK_API_KEY   → free tier at platform.deepseek.com
  QWEN_API_KEY       → free tier at dashscope.aliyuncs.com
  MISTRAL_API_KEY    → free tier at console.mistral.ai
  OPENROUTER_API_KEY → free at openrouter.ai     (Llama/Gemma/Qwen free models)
  Pollinations       → always available, zero config (gpt-4o-mini class, no key)
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from emergentintegrations.llm.chat import LlmChat, UserMessage
from fastapi import HTTPException

from services.distillation_service import (
    cache_lookup,
    cache_store,
    distill_text,
    estimate_tokens,
)
from services.llm_adapter import (
    LLMProviderError,
    any_key_configured,
    llm_completion,
)

logger = logging.getLogger("llm_runner")

BUDGET_COLLECTION = "llm_budget"


def _today_iso() -> str:
    return datetime.now(UTC).date().isoformat()


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
                "No LLM provider configured. Free options (no credit card): "
                "OLLAMA_BASE_URL (local), GROQ_API_KEY (console.groq.com), "
                "GEMINI_API_KEY (ai.google.dev), OPENROUTER_API_KEY (openrouter.ai). "
                "Pollinations keyless fallback is always available — check "
                "LLM_POLLINATIONS_FALLBACK is not set to 'false'."
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


# ── llm_complete — stateless failover helper ──────────────────────────────────
# Special sentinel values used in the provider tuple:
#   provider == "ollama"        → use llm_completion(provider="ollama", …)
#   provider == "pollinations"  → use llm_completion(provider="pollinations", …)
#   api_key  == "__ollama__"    → ditto (legacy compat)
_OLLAMA_SENTINEL = "__ollama__"
_POLLINATIONS_SENTINEL = "__pollinations__"


def _failover_providers() -> list[tuple[str, str, str]]:
    """Build the ordered free-provider list from available env vars.

    Returns list of (provider_name, model_id, api_key_or_sentinel).

    Priority (all $0):
      1. LM Studio    — local OpenAI-compatible server, zero latency, completely offline
      2. Ollama       — local inference, zero latency, completely offline
      3. Groq         — fastest cloud, very generous free tier
      4. Gemini       — best quality free tier (1 500 req/day on flash)
      5. DeepSeek     — excellent reasoning, free tier
      6. Qwen         — great multilingual, free tier
      7. Mistral      — solid European option, free tier
      8. OpenRouter   — routes to Llama/Gemma/Qwen/DeepSeek free community models
      9. Pollinations — always available, zero config (gpt-4o-mini class, keyless)
    """
    from services.llm_adapter import (
        _lmstudio_base_url, _lmstudio_enabled, _lmstudio_models,
        _ollama_base_url, _ollama_enabled, _ollama_models,
    )

    providers: list[tuple[str, str, str]] = []

    # 1. LM Studio — local OpenAI-compatible server, keyless, highest priority
    if _lmstudio_enabled():
        lms_base = _lmstudio_base_url()
        for lm in _lmstudio_models():
            providers.append(("lmstudio", lm, lms_base))

    # 2. Ollama — local, keyless
    if _ollama_enabled():
        base = _ollama_base_url()
        for om in _ollama_models():
            providers.append(("ollama", om, base))

    # 3. Groq — free tier, fastest cloud inference
    gr = os.environ.get("GROQ_API_KEY", "").strip()
    if gr:
        providers.append(("groq", "llama-3.3-70b-versatile", gr))
        providers.append(("groq", "gemma2-9b-it",             gr))
        providers.append(("groq", "llama-3.1-8b-instant",     gr))

    # 4. Gemini — best free-tier quality (multiple free-quota buckets)
    gm = (
        os.environ.get("GEMINI_API_KEY", "")
        or os.environ.get("GOOGLE_API_KEY", "")
        or os.environ.get("EMERGENT_LLM_KEY", "")
    ).strip()
    if gm:
        providers.append(("gemini", "gemini-2.5-flash",      gm))
        providers.append(("gemini", "gemini-2.0-flash",      gm))
        providers.append(("gemini", "gemini-2.5-flash-lite", gm))
        providers.append(("gemini", "gemini-1.5-flash",      gm))

    # 5. DeepSeek — very capable, free tier
    ds = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if ds:
        providers.append(("deepseek", "deepseek-chat",    ds))
        providers.append(("deepseek", "deepseek-coder",   ds))

    # 6. Qwen (Alibaba) — multilingual, free tier
    qw = os.environ.get("QWEN_API_KEY", "").strip()
    if qw:
        providers.append(("qwen", "qwen-plus",  qw))
        providers.append(("qwen", "qwen-turbo", qw))

    # 7. Mistral — free tier
    ms = os.environ.get("MISTRAL_API_KEY", "").strip()
    if ms:
        providers.append(("mistral", "mistral-small-latest", ms))

    # 8. OpenRouter — free community models (Llama, Gemma, Qwen, DeepSeek)
    or_ = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if or_:
        free_models = [
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2.5-7b-instruct:free",
            "deepseek/deepseek-r1-distill-qwen-7b:free",
            "mistralai/mistral-7b-instruct:free",
        ]
        for fm in free_models:
            providers.append(("openrouter", fm, or_))

    # 9. Pollinations — always available, no key, no quota
    if os.environ.get("LLM_POLLINATIONS_FALLBACK", "true").lower() not in {"false", "0", "off"}:
        providers.append(("pollinations", "openai",      _POLLINATIONS_SENTINEL))
        providers.append(("pollinations", "openai-fast", _POLLINATIONS_SENTINEL))
        providers.append(("pollinations", "mistral",     _POLLINATIONS_SENTINEL))

    return providers


async def llm_complete(
    system: str,
    user: str,
    *,
    max_tokens: int = 1500,
    temperature: float = 0.7,
    session_id: str = "llm-complete",
) -> str:
    """Smart multi-provider LLM call with automatic failover (all $0 cost).

    Tries providers in priority order:
      Ollama (local) → Groq → Gemini → DeepSeek → Qwen → Mistral
      → OpenRouter free models → Pollinations (always available, keyless)

    Falls through to the next provider on any error (expired key, rate limit,
    connection error). Pollinations is always the final backstop — the function
    never returns 503 unless Pollinations is explicitly disabled.

    Use this in routes/agents instead of hardcoding run_cached(provider="gemini").
    Stateless: does NOT cache or track budget. Wrap with run_cached() for that.
    """
    from services.llm_adapter import llm_completion

    providers = _failover_providers()
    if not providers:
        raise HTTPException(
            status_code=503,
            detail=(
                "No LLM providers available. Set OLLAMA_BASE_URL, GROQ_API_KEY, "
                "GEMINI_API_KEY, or OPENROUTER_API_KEY in .env. "
                "Pollinations is always free — ensure LLM_POLLINATIONS_FALLBACK != false."
            ),
        )

    last_error: Exception | None = None
    for provider, model, api_key in providers:
        try:
            logger.debug("llm_complete: trying provider=%s model=%s", provider, model)

            # ── Local providers (LM Studio, Ollama) and Pollinations go through llm_adapter (litellm) ──
            if provider in ("lmstudio", "ollama", "pollinations"):
                result = await llm_completion(
                    provider=provider,
                    model=model,
                    system_msg=system,
                    prompt=user,
                    session_id=session_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                if result:
                    logger.info("llm_complete: success provider=%s model=%s", provider, model)
                    return result
                continue

            # ── Cloud providers — LlmChat (Emergent SDK) ──────────────────
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
