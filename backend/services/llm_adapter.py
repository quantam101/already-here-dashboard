"""
LLM adapter — vendor-neutral abstraction over OpenAI/Anthropic/Gemini using
the open-source `litellm` library. Operators bring their own provider key.

Mock mode: if `LLM_MOCK_MODE=true` is set OR the configured key starts with
`sk-mock-`, the adapter returns deterministic canned responses instead of
hitting the real provider API. This lets buyers run the test suite + smoke-
test the dashboard end-to-end without spending money on real LLM calls.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any

import litellm

logger = logging.getLogger("llm_adapter")

litellm.suppress_debug_info = True  # type: ignore[attr-defined]


_PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
    "openai": {
        "model_template": "{model}",
        "env_keys": ["OPENAI_API_KEY", "LLM_API_KEY"],
    },
    "anthropic": {
        "model_template": "anthropic/{model}",
        "env_keys": ["ANTHROPIC_API_KEY", "LLM_API_KEY"],
    },
    "gemini": {
        "model_template": "gemini/{model}",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "LLM_API_KEY"],
    },
    "google": {
        "model_template": "gemini/{model}",
        "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "LLM_API_KEY"],
    },
}


class LLMProviderError(RuntimeError):
    pass


def _mock_mode_active() -> bool:
    """True when we should short-circuit real LLM calls."""
    flag = (os.environ.get("LLM_MOCK_MODE", "") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    # Fallback: any of the known placeholder keys
    for env in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                "GOOGLE_API_KEY", "LLM_API_KEY", "EMERGENT_LLM_KEY"):
        v = os.environ.get(env, "") or ""
        if v.startswith("sk-mock-") or v.startswith("sk-emergent-"):
            return True
    return False


def _mock_response(system_msg: str, prompt: str) -> str:
    """Deterministic canned response good enough for tests + smoke runs.

    We tailor the output based on coarse signals in the prompt so downstream
    parsers (script-format, proposal sections, book chapters) still succeed.
    """
    p = (prompt or "")[:600].lower()
    # Script generator expects HOOK:/SCRIPT:/CTA:/SHOTS:
    if "hook" in p and "shot" in p:
        return (
            "HOOK: 3-second pattern interrupt that demos the outcome\n"
            "SCRIPT: This is a mock-mode script body that proves end-to-end "
            "wiring works without a real LLM provider key. Real buyers swap "
            "the placeholder key for an OpenAI / Anthropic / Gemini key.\n"
            "CTA: Sign up free at alreadyherellc.com\n"
            "SHOTS: opening montage, talking head, screen capture, "
            "result reveal, before/after split, CTA card"
        )
    # Proposal generator expects long-form prose with sections (>500 chars).
    if "proposal" in p or "grant" in p or "capability statement" in p:
        return (
            "## Executive Summary\n"
            "This mock-mode response demonstrates the proposal pipeline is wired "
            "end-to-end without requiring a real LLM provider key. Replace the "
            "placeholder credentials with OPENAI_API_KEY, ANTHROPIC_API_KEY, or "
            "GEMINI_API_KEY in backend/.env to produce real generated content. "
            "The downstream parser, persistence layer, audit log, and distillation "
            "cache are all exercised by this stub identically to the real path.\n\n"
            "## Approach\n"
            "Tier-aware LLM routing through the vendor-neutral `litellm` adapter, "
            "with semantic compression on every prompt and a 30-day cache fingerprint "
            "keyed on (model, system_msg, distilled_prompt). Real production runs "
            "will see typical 30-50% token savings on repeat regenerations.\n\n"
            "## Budget\n"
            "$0.00 — mock mode does not invoke any external API.\n\n"
            "## Outcomes\n"
            "A functional, commerce-ready dashboard with governance, telemetry, "
            "cost guard, and audit trail wired end-to-end. Operator can flip to "
            "any real LLM provider with a single env-var change."
        )
    # Advisor expects JSON with headline/next_action/rationale/confidence
    if ("json" in p and ("next action" in p or "snapshot" in p)) or "advisor" in p:
        return (
            '{"headline":"Publish one share-link campaign to one channel today",'
            '"next_action":"Generate a UTM-tagged share link from /pricing and post '
            'it to one Reddit thread or LinkedIn post in your niche. Track impressions '
            'in /api/analytics/utm-attribution; aim for 100 clicks within 48h.",'
            '"rationale":"Q_D (qualified demand) is the limiter — every other lever '
            'multiplies a near-zero base. One concrete channel-acquisition action '
            'unblocks downstream variables.",'
            '"confidence":"medium",'
            '"owner_agent":"sales_execution"}'
        )
    # Book chapter generator expects ~500 words of prose
    if "chapter" in p:
        return (
            "Chapter body generated in mock mode. " * 60
        ).strip()
    # Generic fallback — short summary keyed by prompt hash for determinism
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    return f"[mock-mode-response:{h}] (set OPENAI_API_KEY / ANTHROPIC_API_KEY / GEMINI_API_KEY to get real output)"


def resolve_api_key(provider: str) -> str | None:
    cfg = _PROVIDER_CONFIG.get(provider.lower())
    if not cfg:
        return os.environ.get("LLM_API_KEY") or os.environ.get("EMERGENT_LLM_KEY")
    for env_name in cfg["env_keys"]:
        v = os.environ.get(env_name)
        if v:
            return v
    return os.environ.get("EMERGENT_LLM_KEY")  # legacy fallback


def model_id(provider: str, model: str) -> str:
    cfg = _PROVIDER_CONFIG.get(provider.lower())
    if not cfg:
        return f"{provider}/{model}" if "/" not in model else model
    return cfg["model_template"].format(model=model)


# ---------------------------------------------------------------------------
# Free-tier fallback chain
# ---------------------------------------------------------------------------
# Each Gemini model has its OWN per-day free-tier quota bucket. When the
# primary model (gemini-3-flash-preview = 20/day free) returns 429, cascade
# through the cheaper-but-still-capable siblings before failing. Each
# additional bucket buys ~250-1500 free requests/day at $0 cost.
#
# Order is intentional: best-quality first, then a chain of progressively
# more generous free-tier buckets. Order can be overridden via
# LLM_GEMINI_FALLBACK_MODELS env (comma-separated).
_DEFAULT_GEMINI_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]


def _quota_exhausted(err_msg: str) -> bool:
    """True when the upstream error is a hard daily quota / rate-limit hit."""
    m = err_msg.lower()
    return (
        "429" in m or "resource_exhausted" in m or "exceeded your current quota" in m
        or ("rate" in m and "limit" in m)
    )


def _model_unavailable(err_msg: str) -> bool:
    """True when the model is deprecated / unrecognised by upstream (404).

    We treat this exactly like a quota hit: skip to the next fallback so
    operators aren't blocked by Google deprecating a model in our chain.
    """
    m = err_msg.lower()
    return (
        "404" in m and ("not_found" in m or "is not found" in m or "not found" in m)
    ) or "is not supported for generatecontent" in m


def _gemini_fallbacks() -> list[str]:
    raw = os.environ.get("LLM_GEMINI_FALLBACK_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(_DEFAULT_GEMINI_FALLBACKS)


async def llm_completion(
    *,
    provider: str,
    model: str,
    system_msg: str,
    prompt: str,
    session_id: str = "",
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """Send a one-shot completion. Returns the response text.

    Resilience strategy (all free):
      1. Retry transient upstream errors (503, connection resets) with
         exponential backoff on the SAME model.
      2. On a 429/quota error from a Gemini model, automatically cascade
         through the free-tier fallback chain (each model = its own
         daily bucket).
      3. Permanent errors (auth, 4xx other than 429) bubble immediately.
    """
    import asyncio
    if _mock_mode_active():
        return _mock_response(system_msg, prompt)

    api_key = resolve_api_key(provider)
    if not api_key:
        raise LLMProviderError(
            f"No API key configured for provider='{provider}'. "
            f"Set one of: " + ", ".join(_PROVIDER_CONFIG[provider]["env_keys"])
        )

    # Build the model chain. Only Gemini gets the multi-model cascade — the
    # other providers don't expose multiple free-tier buckets.
    is_gemini = provider.lower() in ("gemini", "google")
    chain: list[str] = [model]
    if is_gemini:
        for fb in _gemini_fallbacks():
            if fb != model and fb not in chain:
                chain.append(fb)

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]
    last_err: Exception | None = None

    for chain_idx, current_model in enumerate(chain):
        full_model = model_id(provider, current_model)
        kwargs: dict[str, Any] = {
            "model": full_model,
            "messages": messages,
            "api_key": api_key,
            "temperature": temperature,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        if session_id:
            kwargs["metadata"] = {"session_id": session_id}

        if chain_idx > 0:
            logger.warning(
                "llm_adapter: primary quota hit, falling back to %s (chain %d/%d)",
                full_model, chain_idx + 1, len(chain),
            )
        else:
            logger.debug("llm_adapter call: %s session=%s", full_model, session_id)

        for attempt in range(3):
            try:
                resp = await litellm.acompletion(**kwargs)
                return resp["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError) as e:
                raise RuntimeError(f"Unexpected litellm response shape: {e}") from e
            except Exception as e:
                last_err = e
                msg = str(e)
                quota = _quota_exhausted(msg)
                unavailable = _model_unavailable(msg)
                transient = (
                    "503" in msg.lower() or "unavailable" in msg.lower()
                    or "overloaded" in msg.lower() or "timeout" in msg.lower()
                    or "connection" in msg.lower()
                )
                # Quota OR deprecated model → break to try next fallback model.
                if quota or unavailable:
                    reason = "quota exhausted" if quota else "model deprecated/404"
                    logger.warning(
                        "llm_adapter: model=%s %s: %s",
                        full_model, reason, msg[:140],
                    )
                    break
                # Transient → retry same model (1s, 2s).
                if transient and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "llm transient error attempt %d on %s, retrying in %ds: %s",
                        attempt + 1, full_model, wait, msg[:120],
                    )
                    await asyncio.sleep(wait)
                    continue
                # Permanent error → bubble.
                raise

    # All fallbacks exhausted. Caller will catch the quota error and may
    # apply its own deterministic template fallback (see llm_runner.py).
    raise last_err or RuntimeError("llm_completion exhausted all fallback models")


def any_key_configured() -> bool:
    keys = (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "GOOGLE_API_KEY", "LLM_API_KEY", "EMERGENT_LLM_KEY",
    )
    return any(os.environ.get(k) for k in keys) or _mock_mode_active()


def configured_providers() -> list[str]:
    if _mock_mode_active():
        return ["mock"]
    out = []
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"):
        out.append("openai")
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_API_KEY"):
        out.append("anthropic")
    if (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("LLM_API_KEY")
    ):
        out.append("gemini")
    if os.environ.get("EMERGENT_LLM_KEY") and not out:
        out = ["openai", "anthropic", "gemini"]
    return out
