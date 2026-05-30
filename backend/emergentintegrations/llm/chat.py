"""
Cash AI — Unified LLM shim for emergentintegrations.llm.chat.

Supported providers (all OpenAI-compatible except gemini/anthropic):
  groq        — api.groq.com          (free tier, 30 req/min)
  gemini      — Google Gemini          (free tier, via google-generativeai)
  deepseek    — api.deepseek.com       (paid, cheap; $0.14/M tokens)
  openrouter  — openrouter.ai          (BYOK OpenAI/Claude; or free models)
  mistral     — api.mistral.ai         (mistral-small free tier)
  codestral   — codestral.mistral.ai   (code-optimised, free tier)
  qwen        — dashscope.aliyuncs.com (Alibaba Qwen, free tier)
  ollama      — localhost:11434        (local, OpenAI-compat; OLLAMA_BASE_URL)
  koboldcpp   — localhost:5001         (local, OpenAI-compat; KOBOLD_BASE_URL)
  anthropic   — Anthropic Claude       (paid)

Public API (matches original emergentintegrations signature):
    LlmChat(api_key, session_id, system_message)
    LlmChat.with_model(provider, model)  -> self
    await LlmChat.send_message(UserMessage) -> str
    UserMessage(text)
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("emergentintegrations.llm.chat")

# OpenAI-compatible base URLs for each provider
_PROVIDER_BASE_URLS: dict[str, str] = {
    "groq":       "https://api.groq.com/openai/v1",
    "deepseek":   "https://api.deepseek.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "codestral":  "https://codestral.mistral.ai/v1",
    "qwen":       "https://dashscope.aliyuncs.com/compatible-mode/v1",
    # local — override with env var
    "ollama":     os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    "koboldcpp":  os.environ.get("KOBOLD_BASE_URL", "http://localhost:5001/v1"),
}

_PROVIDER_EXTRA_HEADERS: dict[str, dict] = {
    "openrouter": {
        "HTTP-Referer": "https://app.alreadyherellc.com",
        "X-Title": "Already Here Command OS",
    },
}

# Providers that use empty string as the API key (local, no auth)
_NO_AUTH_PROVIDERS = {"ollama", "koboldcpp"}


@dataclass
class UserMessage:
    text: str


class LlmChat:
    """Unified LLM chat client — routes to correct backend by provider name."""

    def __init__(self, api_key: str, session_id: str = "", system_message: str = ""):
        self._api_key = api_key
        self._session_id = session_id
        self._system_message = system_message
        self._provider: str = "gemini"
        self._model: str = "gemini-2.5-flash"

    def with_model(self, provider: str, model: str) -> LlmChat:
        self._provider = provider.lower()
        self._model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        provider = self._provider
        if provider in ("gemini",):
            return await self._call_gemini(message.text)
        elif provider in ("anthropic", "claude"):
            return await self._call_anthropic(message.text)
        elif provider in _PROVIDER_BASE_URLS:
            return await self._call_openai_compat(message.text, provider)
        else:
            logger.warning("Unknown provider %r — falling back to Gemini", provider)
            return await self._call_gemini(message.text)

    # ── OpenAI-compatible (Groq / DeepSeek / OpenRouter / Mistral / Qwen / Ollama / KoboldCpp) ──

    async def _call_openai_compat(self, prompt: str, provider: str) -> str:
        import httpx

        base_url = _PROVIDER_BASE_URLS[provider]
        extra_headers = _PROVIDER_EXTRA_HEADERS.get(provider, {})
        api_key = self._api_key if provider not in _NO_AUTH_PROVIDERS else "nokey"

        messages: list[dict] = []
        if self._system_message:
            messages.append({"role": "system", "content": self._system_message})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            **extra_headers,
        }

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json={"model": self._model, "messages": messages, "max_tokens": 4096},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    # ── Gemini ────────────────────────────────────────────────────────────────

    async def _call_gemini(self, prompt: str) -> str:
        try:
            import google.generativeai as genai  # type: ignore
        except ImportError as e:
            raise RuntimeError("google-generativeai not installed") from e

        genai.configure(api_key=self._api_key)
        model_name = self._model.removeprefix("gemini/")
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._system_message or None,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        return response.text.strip()

    # ── Anthropic ─────────────────────────────────────────────────────────────

    async def _call_anthropic(self, prompt: str) -> str:
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("anthropic not installed") from e

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        msg = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self._system_message or "You are a helpful assistant.",
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
