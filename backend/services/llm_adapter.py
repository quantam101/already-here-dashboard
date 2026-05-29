"""
LLM adapter — vendor-neutral abstraction over OpenAI/Anthropic/Gemini using
the open-source `litellm` library. Replaces the previous `emergentintegrations`
dependency so the codebase can be shipped to any buyer without Emergent ties.

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

    In mock mode (see _mock_mode_active) returns a deterministic synthesized
    response instead of calling the real provider — lets the full test suite
    + dashboard work without a real API key.
    """
    if _mock_mode_active():
        return _mock_response(system_msg, prompt)

    api_key = resolve_api_key(provider)
    if not api_key:
        raise LLMProviderError(
            f"No API key configured for provider='{provider}'. "
            f"Set one of: " + ", ".join(_PROVIDER_CONFIG[provider]["env_keys"])
        )

    full_model = model_id(provider, model)
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]
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

    logger.debug("llm_adapter call: %s session=%s", full_model, session_id)
    resp = await litellm.acompletion(**kwargs)
    try:
        return resp["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected litellm response shape: {e}") from e


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
