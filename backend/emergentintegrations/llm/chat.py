"""
Compatibility shim for emergentintegrations.llm.chat.
Replaces the private package with direct calls to google-generativeai, anthropic, and httpx.

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
from typing import Optional

logger = logging.getLogger("emergentintegrations.llm.chat")


@dataclass
class UserMessage:
    text: str


class LlmChat:
    """Unified LLM chat interface — Gemini primary, Anthropic and Groq fallbacks."""

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
        elif provider in ("groq",):
            return await self._call_groq(message.text)
        else:
            # Fallback: try Gemini with the key we have
            logger.warning("Unknown provider %r — falling back to Gemini", provider)
            return await self._call_gemini(message.text)

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

    # ── Groq ──────────────────────────────────────────────────────────────────

    async def _call_groq(self, prompt: str) -> str:
        import httpx

        messages = []
        if self._system_message:
            messages.append({"role": "system", "content": self._system_message})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"model": self._model, "messages": messages, "max_tokens": 4096},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
