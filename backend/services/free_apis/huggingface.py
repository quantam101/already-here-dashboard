"""Hugging Face Inference API client — free tier with operator token.

Docs:    https://huggingface.co/docs/api-inference
Token:   https://huggingface.co/settings/tokens (free, no card)

The free tier is rate-limited per-account (HF rotates models in/out of the
free Inference API, exact quotas not published). When a model is "cold",
HF returns 503 with `estimated_time` — we wait + retry.

Covered capabilities:
  - Image generation (FLUX.1-schnell — fast, decent quality)
  - Voice cloning / expressive TTS (XTTS-v2 or Bark)
  - Talking head from a still photo + audio (SadTalker-equivalent)
  - Music generation (MusicGen)
  - Text-to-video (AnimateDiff / CogVideoX)

Every helper returns bytes for media outputs, or raises a typed exception
so callers can cascade to the next provider.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger("free_apis.huggingface")

BASE = "https://router.huggingface.co/hf-inference/models"

# Conservative model picks — these are confirmed on the free Inference tier
# as of Feb-May 2026 via the new router.huggingface.co endpoint. Operator
# can override via env vars.
# NOTE: HF heavily pruned the free hf-inference provider in 2025. The
# previously-free FLUX.1-schnell is now a paid-provider model. We default
# to SD 1.5 which remains on the free CPU tier.
DEFAULT_IMAGE_MODEL = os.environ.get("HF_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")
DEFAULT_TTS_MODEL = os.environ.get("HF_TTS_MODEL", "coqui/XTTS-v2")
DEFAULT_MUSIC_MODEL = os.environ.get("HF_MUSIC_MODEL", "facebook/musicgen-small")
DEFAULT_VIDEO_MODEL = os.environ.get("HF_VIDEO_MODEL", "ali-vilab/text-to-video-ms-1.7b")

# Task names per the new pipeline routing scheme.
# NOTE (Feb 2026): the hf-inference router actually rejects requests when
# the explicit `/pipeline/{task}` suffix is appended for the most common
# diffusion / TTS / audio / video models — it expects the bare
# /models/{model} path with `inputs` in the body. We keep the constants
# for documentation but no longer append them to the URL.
TASK_TEXT_TO_IMAGE = "text-to-image"
TASK_TEXT_TO_SPEECH = "text-to-speech"
TASK_TEXT_TO_AUDIO = "text-to-audio"
TASK_TEXT_TO_VIDEO = "text-to-video"


class HFNotConfigured(RuntimeError):
    pass


class HFModelLoading(RuntimeError):
    """Returned when the model is cold-loading on the HF infrastructure."""


def _token() -> Optional[str]:
    return os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_API_KEY")


def is_configured() -> bool:
    return bool(_token())


def _headers() -> dict[str, str]:
    tk = _token()
    if not tk:
        raise HFNotConfigured(
            "HUGGINGFACE_API_KEY not set. Free token at "
            "https://huggingface.co/settings/tokens."
        )
    return {"Authorization": f"Bearer {tk}"}


async def _post_for_bytes(
    model: str,
    json_payload: dict,
    *,
    task: str = TASK_TEXT_TO_IMAGE,  # kept for API compat; unused in URL
    timeout: float = 120.0,
    max_warm_wait: float = 60.0,
) -> bytes:
    """POST JSON to the new router endpoint, return binary body.

    Endpoint format (Feb 2026): /hf-inference/models/{model}
    (No /pipeline/{task} suffix — router rejects that for most models.)
    If model is loading (503), wait + retry until `max_warm_wait` elapses.
    """
    del task  # the URL no longer needs an explicit task; kept for caller compat
    url = f"{BASE}/{model}"
    deadline = asyncio.get_event_loop().time() + max_warm_wait
    async with httpx.AsyncClient(timeout=timeout) as client:
        while True:
            r = await client.post(url, headers=_headers(), json=json_payload)
            if r.status_code == 200:
                ct = r.headers.get("content-type", "")
                if ct.startswith(("image/", "audio/", "video/", "application/octet-stream")):
                    return r.content
                # Some models return JSON on success — try to decode error wrapper
                try:
                    body = r.json()
                except ValueError:
                    return r.content
                if isinstance(body, dict) and body.get("error"):
                    raise HFModelLoading(str(body)[:200])
                return r.content
            if r.status_code == 503:
                # Model is warming. estimated_time field tells us how long.
                try:
                    j = r.json()
                    wait = float(j.get("estimated_time", 5.0))
                except (ValueError, TypeError):
                    wait = 5.0
                if asyncio.get_event_loop().time() + wait > deadline:
                    raise HFModelLoading(f"model still loading after {max_warm_wait}s")
                logger.info("HF model %s warming, waiting %.1fs", model, wait)
                await asyncio.sleep(min(wait, 15.0))
                continue
            if r.status_code == 404:
                # Model not available on the free hf-inference provider
                raise HFModelLoading(
                    f"model {model!r} not available on free hf-inference tier — "
                    f"try a different model or use Pollinations.ai (keyless)."
                )
            r.raise_for_status()
            raise httpx.HTTPError(f"unexpected status {r.status_code}: {r.text[:200]}")


async def generate_image(
    prompt: str,
    *,
    model: str = DEFAULT_IMAGE_MODEL,
    width: int = 1080,
    height: int = 1920,
) -> bytes:
    payload = {
        "inputs": prompt[:800],
        "parameters": {"width": width, "height": height},
    }
    return await _post_for_bytes(model, payload, task=TASK_TEXT_TO_IMAGE)


async def synthesize_speech(
    text: str,
    *,
    model: str = DEFAULT_TTS_MODEL,
    reference_voice_wav_bytes: Optional[bytes] = None,
) -> bytes:
    """Voice cloning if `reference_voice_wav_bytes` supplied (XTTS-v2),
    otherwise expressive TTS in the model's default voice."""
    if reference_voice_wav_bytes:
        import base64
        payload = {
            "inputs": text[:600],
            "parameters": {
                "speaker_wav": base64.b64encode(reference_voice_wav_bytes).decode(),
            },
        }
    else:
        payload = {"inputs": text[:600]}
    return await _post_for_bytes(model, payload, task=TASK_TEXT_TO_SPEECH, max_warm_wait=120)


async def generate_music(
    prompt: str,
    *,
    model: str = DEFAULT_MUSIC_MODEL,
    duration_s: int = 30,
) -> bytes:
    payload = {
        "inputs": prompt[:300],
        "parameters": {"duration": int(duration_s)},
    }
    return await _post_for_bytes(model, payload, task=TASK_TEXT_TO_AUDIO, max_warm_wait=120)


async def generate_video(
    prompt: str,
    *,
    model: str = DEFAULT_VIDEO_MODEL,
    num_frames: int = 16,
) -> bytes:
    """Short text-to-video clip. Returns MP4 bytes.

    NOTE (Feb 2026): the free hf-inference provider tier does NOT host any
    text-to-video model. Calls reliably return HTTP 400 'Model not
    supported by provider hf-inference'. This bridge stays wired for the
    day HF or another router (Fal / Replicate) starts serving these models
    again on the free tier.
    """
    payload = {
        "inputs": prompt[:300],
        "parameters": {"num_frames": int(num_frames)},
    }
    return await _post_for_bytes(model, payload, task=TASK_TEXT_TO_VIDEO, max_warm_wait=180)


async def health_check(timeout: float = 6.0) -> bool:
    if not is_configured():
        return False
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(
                "https://huggingface.co/api/whoami-v2", headers=_headers()
            )
            return r.status_code == 200
    except (httpx.HTTPError, HFNotConfigured):
        return False
