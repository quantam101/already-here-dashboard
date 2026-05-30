"""AI B-roll generation — replaces Pexels stock with prompt-generated images.

Strategy:
  1. Try Pollinations.ai (keyless, free, no rate limit).
  2. Fall back to Hugging Face Inference API if available.
  3. Fall back to the existing colour-card placeholder.

Each "B-roll clip" is a still PNG rendered at 1080×1920 with a subtle
ffmpeg `zoompan` Ken-Burns motion applied for `duration_target` seconds.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path

from services.free_apis import huggingface, pollinations

logger = logging.getLogger("video.ai_stock")

CACHE_DIR = Path(os.environ.get("VIDEO_STOCK_CACHE", "/app/data/stock_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)


async def fetch_ai_clip_for_shot(
    shot_text: str,
    *,
    duration_target: float = 5.0,
    style_suffix: str = "cinematic, vertical 9:16, high detail",
    fast: bool = True,
) -> Path | None:
    """Generate a single AI image and Ken-Burns it into an MP4.

    Returns the MP4 path on success, or None if every provider fails so
    the caller can fall back to the colour-card placeholder.
    """
    cache_key = hashlib.sha256(
        f"ai:{shot_text}:{style_suffix}".encode()
    ).hexdigest()[:16]
    cached = CACHE_DIR / f"{cache_key}.mp4"
    if cached.exists() and cached.stat().st_size > 1024:
        return cached

    image_bytes = await _generate_image(shot_text, style_suffix, fast=fast)
    if not image_bytes:
        return None

    image_path = CACHE_DIR / f"{cache_key}.png"
    image_path.write_bytes(image_bytes)

    # Ken-Burns: slow zoom-in from 1.0 → 1.2 over duration_target seconds
    fps = 30
    frames = int(duration_target * fps)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", str(image_path),
        "-vf", (
            f"scale=2160:3840:force_original_aspect_ratio=increase,"
            f"crop=2160:3840,"
            f"zoompan=z='min(zoom+0.0015,1.2)':d={frames}:s=1080x1920:fps={fps},"
            f"format=yuv420p"
        ),
        "-t", str(duration_target),
        "-c:v", "libx264", "-preset", "ultrafast",
        str(cached),
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        logger.warning("ai b-roll ffmpeg failed: %s", err.decode(errors="replace")[:200])
        return None
    return cached


async def _generate_image(shot_text: str, style_suffix: str, *, fast: bool = True) -> bytes | None:
    """Try Pollinations first (no key needed), fall back to HF if configured."""
    prompt = f"{shot_text}, {style_suffix}"
    try:
        # `turbo` model is ~3-5x faster than `flux` on Pollinations.
        # Quality is still solid for vertical short-form B-roll.
        return await pollinations.generate_image(
            prompt, model="turbo" if fast else "flux",
        )
    except Exception as e:
        logger.info("pollinations failed: %s — falling back", str(e)[:120])

    if huggingface.is_configured():
        try:
            return await huggingface.generate_image(prompt)
        except Exception as e:
            logger.warning("HF image gen failed: %s", str(e)[:120])
    return None
