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

# Reasonable defaults for vertical short-form
DEFAULT_W = 1080
DEFAULT_H = 1920


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
    timeout: float = 30.0,
) -> str:
    """Free keyless text generation. Used as a last-resort fallback for hooks /
    scripts when Gemini buckets are exhausted AND the operator wants
    something better than the deterministic template.

    Models: `openai`, `mistral`, `llama`, `claude` (community-hosted, no key).
    """
    safe_prompt = urllib.parse.quote(prompt[:1500], safe="")
    url = f"{TEXT_ENDPOINT}/{safe_prompt}?model={urllib.parse.quote(model)}"
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.text.strip()


def is_available() -> bool:
    """Pollinations is keyless and always available unless network blocks it."""
    return True


async def health_check(timeout: float = 5.0) -> bool:
    """Quick reachability probe — used in /api/free-providers/status."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{TEXT_ENDPOINT}/ping?model=openai")
            return r.status_code == 200
    except (httpx.HTTPError, asyncio.TimeoutError):
        return False
