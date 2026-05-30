"""Pollinations.ai — keyless free image / text / audio generation.

Docs: https://pollinations.ai/
Limits (May 2026): no documented hard rate limit; reasonable use only.
Output: PNG/JPEG, MP3, or plain text depending on endpoint.

All endpoints are simple HTTP GETs (or POSTs with JSON). No auth.
"""
from __future__ import annotations

import asyncio
import logging
import urllib.parse
from typing import Optional

import httpx

logger = logging.getLogger("free_apis.pollinations")

IMAGE_ENDPOINT = "https://image.pollinations.ai/prompt"
TEXT_ENDPOINT = "https://text.pollinations.ai"
AUDIO_ENDPOINT = "https://text.pollinations.ai"

# Reasonable defaults for vertical short-form
DEFAULT_W = 1080
DEFAULT_H = 1920

# Pollinations OpenAI-compatible audio voices
AUDIO_VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]


async def generate_image(
    prompt: str,
    *,
    width: int = DEFAULT_W,
    height: int = DEFAULT_H,
    model: str = "flux",
    seed: Optional[int] = None,
    nologo: bool = True,
    timeout: float = 60.0,
) -> bytes:
    """Returns raw image bytes (JPEG). Raises httpx.HTTPError on failure.

    Models available: `flux` (default, highest quality), `flux-realism`,
    `flux-anime`, `flux-3d`, `turbo` (fastest).
    """
    safe_prompt = urllib.parse.quote(prompt[:600], safe="")
    params = {
        "width": str(width),
        "height": str(height),
        "model": model,
        "nologo": "true" if nologo else "false",
    }
    if seed is not None:
        params["seed"] = str(int(seed))
    qs = "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    url = f"{IMAGE_ENDPOINT}/{safe_prompt}?{qs}"

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if not ct.startswith("image/"):
            raise httpx.HTTPError(f"unexpected content-type: {ct!r}")
        if len(r.content) < 1024:
            raise httpx.HTTPError(f"image too small ({len(r.content)} bytes)")
        return r.content


async def generate_text(
    prompt: str,
    *,
    model: str = "openai",
    system: str = "",
    timeout: float = 60.0,
) -> str:
    """Free keyless text generation via the Pollinations OpenAI-compatible
    chat-completion endpoint. Used as a last-resort fallback when every
    Gemini bucket is exhausted.

    Endpoint: POST https://text.pollinations.ai/{model}
    Body:     {messages: [{role, content}]}  (OpenAI Chat format)

    Models (community-hosted, no key): `openai`, `openai-fast`, `mistral`,
    `claude-hybridspace`, `llama`. Default `openai` (gpt-4o-mini class).

    Retries on 502/503 (Pollinations queue saturation) with exponential
    backoff. Raises on permanent failures.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system[:2000]})
    messages.append({"role": "user", "content": prompt[:6000]})
    url = f"{TEXT_ENDPOINT}/{urllib.parse.quote(model)}"

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                r = await client.post(url, json={"messages": messages})
                if r.status_code in (502, 503, 504):
                    raise httpx.HTTPError(f"pollinations transient {r.status_code}")
                r.raise_for_status()
                try:
                    data = r.json()
                    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
                except ValueError:
                    return r.text.strip()
        except Exception as e:
            last_err = e
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            raise
    raise last_err or RuntimeError("pollinations.generate_text exhausted retries")


def is_available() -> bool:
    """Pollinations is keyless and always available unless network blocks it."""
    return True


async def synthesize_speech(
    text: str,
    *,
    voice: str = "nova",
    timeout: float = 120.0,
) -> bytes:
    """OpenAI-compatible TTS via Pollinations — keyless free.

    Voices (Feb 2026): alloy, echo, fable, onyx, nova, shimmer.
    Returns MP3 bytes.
    """
    if voice not in AUDIO_VOICES:
        voice = "nova"
    safe = urllib.parse.quote(text[:1500], safe="")
    url = f"{AUDIO_ENDPOINT}/{safe}?model=openai-audio&voice={voice}"
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        ct = r.headers.get("content-type", "")
        if not ct.startswith("audio/"):
            raise httpx.HTTPError(f"unexpected content-type: {ct!r}, body[:200]={r.text[:200]!r}")
        if len(r.content) < 1024:
            raise httpx.HTTPError(f"audio too small ({len(r.content)} bytes)")
        return r.content


async def health_check(timeout: float = 5.0) -> bool:
    """Quick reachability probe — used in /api/free-providers/status."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{TEXT_ENDPOINT}/ping?model=openai")
            return r.status_code == 200
    except (httpx.HTTPError, asyncio.TimeoutError):
        return False
