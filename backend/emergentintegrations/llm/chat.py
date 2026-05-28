"""
Compatibility shim for emergentintegrations.llm.chat.
Replaces the private package with direct calls to google-generativeai, anthropic, httpx.

Supported providers:
  groq        — api.groq.com (free tier, fast)
  gemini      — Google Gemini via google-generativeai (free tier)
  deepseek    — api.deepseek.com (OpenAI-compatible, generous free tier)
  openrouter  — openrouter.ai (many free models, set OPENROUTER_API_KEY)
  anthropic   — Anthropic Claude (paid)

Public API (matches original):
    LlmChat(api_key, session_id, system_message)
    LlmChat.with_model(provider, model)         -> self
    await LlmChat.send_message(UserMessage) -> str

    UserMessage(text)
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger("emergentintegrations.llm.chat")


@dataclass
class UserMessage:
    text: str


class LlmChat:
    """Unified LLM chat interface — Groq / Gemini / DeepSeek / OpenRouter / Anthropic."""

    def __init__(self, api_key: str, session_id: str = "", system_message: str = ""):
        self._api_key = api_key
        self._session_id = session_id
        self._system_message = system_message
        self._provider: str = "gemini"
        self._model: str = "gemini-2.5-flash"

    def with_model(self, provider: str, model: str) -> "LlmChat":
        self._provider = provider.lower()
        self._model = model
        return self

    async def send_message(self, message: UserMessage) -> str:
        provider = self._provider
        if provider == "gemini":
            return await self._call_gemini(message.text)
        elif provider in ("anthropic", "claude"):
            return await self._call_anthropic(message.text)
        elif provider == "groq":
            return await self._call_openai_compat(
                message.text,
                base_url="https://api.groq.com/openai/v1",
            )
        elif provider == "deepseek":
            return await self._call_openai_compat(
                message.text,
                base_url="https://api.deepseek.com/v1",
            )
        elif provider == "openrouter":
            return await self._call_openai_compat(
                message.text,
                base_url="https://openrouter.ai/api/v1",
                extra_headers={
                    "HTTP-Referer": "https://app.alreadyherellc.com",
                    "X-Title": "Already Here Command OS",
                },
            )
        else:
            logger.warning("Unknown provider %r — falling back to Gemini", provider)
            return await self._call_gemini(message.text)

    # ── OpenAI-compatible (Groq / DeepSeek / OpenRouter) ──────────────────────

    async def _call_openai_compat(
        self,
        prompt: str,
        base_url: str,
        extra_headers: dict | None = None,
    ) -> str:
        import httpx

        messages = []
        if self._system_message:
            messages.append({"role": "system", "content": self._system_message})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

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
        model_name = self._model
        # Normalize model name (strip "gemini/" prefix if present)
        if model_name.startswith("gemini/"):
            model_name = model_name[len("gemini/"):]
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=self._system_message or None,
        )
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: model.generate_content(prompt),
        )
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
