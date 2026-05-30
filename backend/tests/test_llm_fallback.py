"""Tests for the LLM fallback chain + deterministic hook template fallback.

These exercise the multi-model cascade in llm_adapter.llm_completion and
the deterministic hook generator in routes.hooks._deterministic_hooks.
"""
from __future__ import annotations

import asyncio
import pytest

from routes.hooks import _deterministic_hooks
from services import llm_adapter


def test_deterministic_hooks_returns_requested_count():
    out = _deterministic_hooks("zero-cost video pipelines", "creator economy", 5)
    assert len(out) == 5
    assert all(v.hook and v.pattern for v in out)
    # No duplicates across patterns
    assert len({v.pattern for v in out}) == 5


def test_deterministic_hooks_handles_empty_topic():
    out = _deterministic_hooks("", "", 3)
    assert len(out) == 3
    assert all("this" in v.hook or "your niche" in v.hook for v in out)


def test_quota_exhausted_detection():
    f = llm_adapter._quota_exhausted
    assert f("litellm.RateLimitError: 429 You exceeded your quota")
    assert f("RESOURCE_EXHAUSTED: gemini-3-flash daily limit")
    assert f("Error code: 429 - rate limit reached")
    assert not f("connection reset by peer")
    assert not f("invalid api key")


def test_gemini_fallback_chain_default():
    chain = llm_adapter._gemini_fallbacks()
    # Default chain has multiple distinct free-tier buckets
    assert "gemini-2.5-flash" in chain
    assert "gemini-2.0-flash" in chain
    assert len(set(chain)) == len(chain)  # no dupes


@pytest.fixture
def reset_gemini_env(monkeypatch):
    """Mark a real gemini key as present and clear other providers."""
    monkeypatch.setenv("GEMINI_API_KEY", "real-looking-key-NOT-mock")
    monkeypatch.delenv("LLM_MOCK_MODE", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("EMERGENT_LLM_KEY", raising=False)


def test_llm_completion_cascades_through_models(monkeypatch, reset_gemini_env):
    """Simulate gemini-3-flash 429ing, gemini-2.5-flash succeeding."""
    calls: list[str] = []

    async def fake_acompletion(**kwargs):
        model = kwargs["model"]
        calls.append(model)
        if model == "gemini/gemini-3-flash-preview":
            raise Exception(
                'litellm.RateLimitError: VertexAIException - {"error":{"code":429,'
                '"message":"You exceeded your current quota","status":"RESOURCE_EXHAUSTED"}}'
            )
        return {"choices": [{"message": {"content": "OK from fallback model"}}]}

    monkeypatch.setattr(llm_adapter.litellm, "acompletion", fake_acompletion)

    out = asyncio.run(llm_adapter.llm_completion(
        provider="gemini",
        model="gemini-3-flash-preview",
        system_msg="sys",
        prompt="hi",
        session_id="test",
    ))
    assert out == "OK from fallback model"
    assert calls[0] == "gemini/gemini-3-flash-preview"
    assert calls[1] != "gemini/gemini-3-flash-preview"
    assert calls[1].startswith("gemini/gemini-")


def test_llm_completion_all_models_exhausted_raises(monkeypatch, reset_gemini_env):
    """When every model in the chain 429s AND Pollinations fallback is
    disabled, the original error bubbles."""
    monkeypatch.setenv("LLM_GEMINI_FALLBACK_MODELS", "gemini-2.5-flash")
    monkeypatch.setenv("LLM_POLLINATIONS_FALLBACK", "false")

    async def fake_acompletion(**_kwargs):
        raise Exception(
            'litellm.RateLimitError: VertexAIException - 429 quota exceeded'
        )

    monkeypatch.setattr(llm_adapter.litellm, "acompletion", fake_acompletion)

    with pytest.raises(Exception) as exc_info:
        asyncio.run(llm_adapter.llm_completion(
            provider="gemini",
            model="gemini-3-flash-preview",
            system_msg="sys",
            prompt="hi",
            session_id="test",
        ))
    assert "429" in str(exc_info.value) or "quota" in str(exc_info.value).lower()
