"""
LLM adapter — vendor-neutral abstraction over OpenAI/Anthropic/Gemini/Ollama
using the open-source `litellm` library.

Free-first philosophy: every provider in this file costs $0.
  - LM Studio — local inference via OpenAI-compatible API (localhost:1234)
                 runs any GGUF model; highest priority when running locally
  - Ollama    — local inference (set OLLAMA_BASE_URL; runs Llama, Gemma, Qwen,
                 DeepSeek, Mistral, Phi locally at zero cost)
  - Gemini    — Google free tier: ~1 500 req/day on gemini-2.5-flash (set GEMINI_API_KEY)
  - OpenAI    — paid, but accepts OpenRouter key for free-tier routing
  - Pollinations — keyless; always available as the final fallback (no config needed)

Mock mode: if `LLM_MOCK_MODE=true` is set OR the configured key starts with
`sk-mock-`, the adapter returns deterministic canned responses instead of
hitting the real provider API. This lets the test suite + smoke runs work
end-to-end without spending money on real LLM calls.

LM Studio quick-start (Windows/Mac/Linux):
  1. Install from https://lmstudio.ai  (or: irm https://lmstudio.ai/install.ps1 | iex)
  2. Download a model in the LM Studio UI (Llama, Gemma, Mistral, DeepSeek, etc.)
  3. Start the local server (default port 1234)
  4. Set in backend/.env:
       LM_STUDIO_BASE_URL=http://localhost:1234/v1   # optional, this is the default
       LM_STUDIO_MODEL=llama-3.2-3b-instruct         # match what you loaded
  LM Studio auto-detected when the port is reachable — no key required.

Ollama quick-start (on a machine with >=4 GB RAM):
  curl -fsSL https://ollama.ai/install.sh | sh
  ollama pull llama3.2:3b        # 2.0 GB, fast
  ollama pull gemma2:2b          # 1.6 GB, very fast
  ollama pull qwen2.5:3b         # 2.3 GB, multilingual
  ollama pull deepseek-r1:1.5b   # 1.1 GB, reasoning
  # then set in backend/.env:
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=llama3.2:3b
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
    # LM Studio: local OpenAI-compatible server at localhost:1234, no key needed
    "lmstudio": {
        "model_template": "openai/{model}",
        "env_keys": [],
    },
    # Ollama: local inference, no key needed — uses OLLAMA_BASE_URL
    "ollama": {
        "model_template": "ollama/{model}",
        "env_keys": [],
    },
    # OpenRouter: free-tier routing to Llama/Gemma/Qwen/DeepSeek community models
    "openrouter": {
        "model_template": "openrouter/{model}",
        "env_keys": ["OPENROUTER_API_KEY"],
    },
    # Groq: free tier, fastest cloud inference
    "groq": {
        "model_template": "groq/{model}",
        "env_keys": ["GROQ_API_KEY"],
    },
    # DeepSeek: very capable, free tier available
    "deepseek": {
        "model_template": "deepseek/{model}",
        "env_keys": ["DEEPSEEK_API_KEY"],
    },
    # Qwen (Alibaba): multilingual, free tier
    "qwen": {
        "model_template": "qwen/{model}",
        "env_keys": ["QWEN_API_KEY"],
    },
    # Mistral: free tier available
    "mistral": {
        "model_template": "mistral/{model}",
        "env_keys": ["MISTRAL_API_KEY"],
    },
}


class LLMProviderError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# LM Studio helpers  (OpenAI-compatible local server, highest priority)
# ---------------------------------------------------------------------------

def _lmstudio_base_url() -> str:
    """Base URL for the LM Studio local server (OpenAI-compatible)."""
    return os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1").rstrip("/")


def _lmstudio_enabled() -> bool:
    """True when LM Studio is explicitly opted-in or the base URL is configured."""
    if os.environ.get("LM_STUDIO_BASE_URL"):
        return True
    return os.environ.get("LM_STUDIO_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _lmstudio_models() -> list[str]:
    """Ordered list of LM Studio models to try."""
    raw = os.environ.get("LM_STUDIO_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    default_model = os.environ.get("LM_STUDIO_MODEL", "").strip()
    # Generic names that work with most GGUF models loaded in LM Studio
    fallbacks = [
        "local-model",          # LM Studio default model identifier
        "llama-3.2-3b-instruct",
        "gemma-2-2b-it",
        "mistral-7b-instruct-v0.3",
        "deepseek-r1-distill-qwen-7b",
    ]
    if default_model and default_model not in fallbacks:
        return [default_model] + fallbacks
    if default_model:
        return [default_model] + [m for m in fallbacks if m != default_model]
    return fallbacks


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------

def _ollama_base_url() -> str:
    """Base URL for the local (or remote) Ollama server."""
    return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")


def _ollama_enabled() -> bool:
    """True when Ollama is explicitly opted-in via env or OLLAMA_BASE_URL is set."""
    if os.environ.get("OLLAMA_BASE_URL"):
        return True
    return os.environ.get("OLLAMA_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def _ollama_models() -> list[str]:
    """Ordered list of Ollama models to try (smallest/fastest first for the OCI server)."""
    raw = os.environ.get("OLLAMA_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    # Default preference order — override with OLLAMA_MODELS env
    default_model = os.environ.get("OLLAMA_MODEL", "").strip()
    fallbacks = [
        "llama3.2:3b",   # 2.0 GB, solid all-rounder
        "gemma2:2b",     # 1.6 GB, very fast, good quality
        "qwen2.5:3b",    # 2.3 GB, multilingual
        "deepseek-r1:1.5b",  # 1.1 GB, reasoning-focused
        "llama3.2:1b",   # 0.7 GB, tiny fallback
    ]
    if default_model and default_model not in fallbacks:
        return [default_model] + fallbacks
    if default_model:
        return [default_model] + [m for m in fallbacks if m != default_model]
    return fallbacks


# ---------------------------------------------------------------------------
# Mock mode
# ---------------------------------------------------------------------------

def _mock_mode_active() -> bool:
    """True when we should short-circuit real LLM calls."""
    flag = (os.environ.get("LLM_MOCK_MODE", "") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    # Fallback: any of the known placeholder keys
    for env in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
                "GOOGLE_API_KEY", "LLM_API_KEY", "EMERGENT_LLM_KEY"):
        v = os.environ.get(env, "") or ""
        if v.startswith(("sk-mock-", "sk-emergent-")):
            return True
    return False


def _mock_response(system_msg: str, prompt: str) -> str:
    """Deterministic canned response good enough for tests + smoke runs."""
    p = (prompt or "")[:600].lower()
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
    if "chapter" in p:
        return ("Chapter body generated in mock mode. " * 60).strip()
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
    return (
        f"[mock-mode-response:{h}] — set LM_STUDIO_BASE_URL (local free), "
        "OLLAMA_BASE_URL (local free), GROQ_API_KEY (free), GEMINI_API_KEY (free), "
        "or OPENROUTER_API_KEY (free) in backend/.env to get real AI output."
    )


# ---------------------------------------------------------------------------
# Key / config helpers
# ---------------------------------------------------------------------------

def resolve_api_key(provider: str) -> str | None:
    """Return the API key for provider, or None if not configured.

    Ollama, LM Studio, and Pollinations never need a key.
    """
    p = provider.lower()
    if p in ("ollama", "lmstudio", "pollinations"):
        return None  # keyless — uses api_base
    cfg = _PROVIDER_CONFIG.get(p)
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
# Free-tier Gemini fallback cascade
# ---------------------------------------------------------------------------
_DEFAULT_GEMINI_FALLBACKS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
]


def _quota_exhausted(err_msg: str) -> bool:
    m = err_msg.lower()
    return (
        "429" in m or "resource_exhausted" in m or "exceeded your current quota" in m
        or ("rate" in m and "limit" in m)
    )


def _model_unavailable(err_msg: str) -> bool:
    m = err_msg.lower()
    return (
        "404" in m and ("not_found" in m or "is not found" in m or "not found" in m)
    ) or "is not supported for generatecontent" in m


def _gemini_fallbacks() -> list[str]:
    raw = os.environ.get("LLM_GEMINI_FALLBACK_MODELS", "").strip()
    if raw:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return list(_DEFAULT_GEMINI_FALLBACKS)


# ---------------------------------------------------------------------------
# Core completion — litellm-backed, handles LM Studio + Ollama + cloud providers
# ---------------------------------------------------------------------------

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
    """Send a one-shot completion via litellm. Returns the response text.

    Supports: LM Studio (local), Ollama (local), Gemini, OpenAI, Anthropic,
              Groq, DeepSeek, Qwen, Mistral, OpenRouter, Pollinations.

    Resilience:
      1. LM Studio: tries all configured models sequentially on failure.
      2. Ollama: tries all configured models sequentially on failure.
      3. Gemini: cascades through free-tier model buckets on 429.
      4. All providers: exponential backoff on transient 503/connection errors.
      5. Final fallback: Pollinations keyless text API (always available).
    """
    import asyncio

    if _mock_mode_active():
        return _mock_response(system_msg, prompt)

    p = provider.lower()
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt},
    ]

    # ── LM Studio (local OpenAI-compatible, highest priority, keyless) ────────
    if p == "lmstudio":
        base_url = _lmstudio_base_url()
        models_to_try = [model] if model else _lmstudio_models()
        last_lms_err: Exception | None = None
        for lm in models_to_try:
            # LM Studio uses OpenAI-compatible API: model prefix "openai/"
            full = f"openai/{lm}"
            kwargs: dict[str, Any] = {
                "model": full,
                "messages": messages,
                "api_base": base_url,
                "api_key": "lm-studio",   # arbitrary non-empty string required by litellm
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            logger.debug("llm_adapter (lmstudio): %s @ %s", full, base_url)
            for attempt in range(2):
                try:
                    resp = await litellm.acompletion(**kwargs)
                    return resp["choices"][0]["message"]["content"] or ""
                except Exception as e:
                    last_lms_err = e
                    msg = str(e).lower()
                    if "connection" in msg or "refused" in msg or "timeout" in msg:
                        if attempt == 0:
                            await asyncio.sleep(1)
                            continue
                    logger.warning("lmstudio model=%s failed: %s", lm, str(e)[:120])
                    break  # try next model
        raise LLMProviderError(
            f"LM Studio at {base_url} could not complete the request. "
            f"Last error: {last_lms_err}. "
            f"Make sure LM Studio is running with a model loaded and the server started."
        )

    # ── Ollama (local/private, keyless) ──────────────────────────────────────
    if p == "ollama":
        base_url = _ollama_base_url()
        models_to_try = [model] if model else _ollama_models()
        last_ollama_err: Exception | None = None
        for om in models_to_try:
            full = f"ollama/{om}"
            kwargs: dict[str, Any] = {
                "model": full,
                "messages": messages,
                "api_base": base_url,
                "temperature": temperature,
            }
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            logger.debug("llm_adapter (ollama): %s @ %s", full, base_url)
            for attempt in range(2):
                try:
                    resp = await litellm.acompletion(**kwargs)
                    return resp["choices"][0]["message"]["content"] or ""
                except Exception as e:
                    last_ollama_err = e
                    msg = str(e).lower()
                    if "connection" in msg or "refused" in msg or "timeout" in msg:
                        if attempt == 0:
                            await asyncio.sleep(1)
                            continue
                    logger.warning("ollama model=%s failed: %s", om, str(e)[:120])
                    break  # try next model
        raise LLMProviderError(
            f"Ollama at {base_url} could not complete the request. "
            f"Last error: {last_ollama_err}. "
            f"Make sure Ollama is running and at least one model is pulled."
        )

    # ── Pollinations (keyless, always free) ──────────────────────────────────
    if p == "pollinations":
        from services.free_apis import pollinations as _poll
        out = await _poll.generate_text(prompt, model=model or "openai", system=system_msg)
        if out:
            return out
        raise LLMProviderError("Pollinations text generation returned empty response")

    # ── Cloud providers (all via litellm, need a key) ────────────────────────
    api_key = resolve_api_key(provider)
    if not api_key:
        cfg = _PROVIDER_CONFIG.get(p)
        env_hint = (", ".join(cfg["env_keys"]) if cfg else "LLM_API_KEY")
        raise LLMProviderError(
            f"No API key configured for provider='{provider}'. Set one of: {env_hint}"
        )

    is_gemini = p in ("gemini", "google")
    chain: list[str] = [model]
    if is_gemini:
        for fb in _gemini_fallbacks():
            if fb != model and fb not in chain:
                chain.append(fb)

    last_err: Exception | None = None
    for chain_idx, current_model in enumerate(chain):
        full_model = model_id(provider, current_model)
        kwargs = {
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
                "llm_adapter: quota hit, falling back to %s (%d/%d)",
                full_model, chain_idx + 1, len(chain),
            )
        else:
            logger.debug("llm_adapter: %s session=%s", full_model, session_id)

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
                if quota or unavailable:
                    reason = "quota exhausted" if quota else "model deprecated/404"
                    logger.warning("llm_adapter: %s %s: %s", full_model, reason, msg[:140])
                    break
                if transient and attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "llm transient error attempt %d on %s, retrying in %ds: %s",
                        attempt + 1, full_model, wait, msg[:120],
                    )
                    await asyncio.sleep(wait)
                    continue
                raise

    # All cloud fallbacks exhausted — try Pollinations as the final $0 backstop
    if (
        last_err is not None
        and os.environ.get("LLM_POLLINATIONS_FALLBACK", "true").lower() not in {"false", "0", "off"}
    ):
        try:
            from services.free_apis import pollinations
            logger.warning(
                "llm_adapter: all %s buckets exhausted, falling back to Pollinations (keyless)",
                provider,
            )
            out = await pollinations.generate_text(prompt, model="openai", system=system_msg)
            if out:
                return out
        except Exception as fe:
            logger.warning("pollinations fallback failed: %s", str(fe)[:200])

    raise last_err or RuntimeError("llm_completion exhausted all fallback models")


# ---------------------------------------------------------------------------
# Utility — key / provider detection
# ---------------------------------------------------------------------------

def any_key_configured() -> bool:
    """True when at least one real LLM provider is available.

    'Available' includes:
    - LM Studio running locally (LM_STUDIO_BASE_URL set or LM_STUDIO_ENABLED=true)
    - A configured API key for any cloud provider
    - Ollama running locally (OLLAMA_BASE_URL set or OLLAMA_ENABLED=true)
    - Pollinations (always free, no key needed) unless explicitly disabled
    - Mock mode (for tests)
    """
    if _mock_mode_active():
        return True
    # LM Studio: no key, just a running server
    if _lmstudio_enabled():
        return True
    # Ollama: no key, just a running server
    if _ollama_enabled():
        return True
    # Pollinations: always available unless explicitly disabled
    if os.environ.get("LLM_POLLINATIONS_FALLBACK", "true").lower() not in {"false", "0", "off"}:
        return True
    # Cloud provider keys
    keys = (
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
        "GOOGLE_API_KEY", "LLM_API_KEY", "EMERGENT_LLM_KEY",
        "GROQ_API_KEY", "DEEPSEEK_API_KEY", "QWEN_API_KEY",
        "MISTRAL_API_KEY", "OPENROUTER_API_KEY",
    )
    return any(os.environ.get(k) for k in keys)


def configured_providers() -> list[str]:
    """List of active provider names for the /system/status display."""
    if _mock_mode_active():
        return ["mock"]
    out: list[str] = []
    # Local inference — highest priority
    if _lmstudio_enabled():
        out.append("lmstudio")
    if _ollama_enabled():
        out.append("ollama")
    # Cloud keys
    if os.environ.get("GROQ_API_KEY"):
        out.append("groq")
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        out.append("gemini")
    if os.environ.get("DEEPSEEK_API_KEY"):
        out.append("deepseek")
    if os.environ.get("QWEN_API_KEY"):
        out.append("qwen")
    if os.environ.get("MISTRAL_API_KEY"):
        out.append("mistral")
    if os.environ.get("OPENROUTER_API_KEY"):
        out.append("openrouter")
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY"):
        out.append("openai")
    if os.environ.get("ANTHROPIC_API_KEY"):
        out.append("anthropic")
    if os.environ.get("EMERGENT_LLM_KEY") and not out:
        out = ["openai", "anthropic", "gemini"]
    # Pollinations is always available
    if "pollinations" not in out:
        out.append("pollinations")
    return out
