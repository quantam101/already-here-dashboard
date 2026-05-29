"""Pexels stock-footage client — free tier, 200 req/hr.

API docs: https://www.pexels.com/api/documentation/
Operator sets PEXELS_API_KEY env var; if unset we fall back to a deterministic
solid-colour video clip generator so the engine works end-to-end even with
zero external creds (great for tests + first-boot dev).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("video.stock")

CACHE_DIR = Path(os.environ.get("VIDEO_STOCK_CACHE", "/app/data/stock_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

PEXELS_ENDPOINT = "https://api.pexels.com/videos/search"


async def _pexels_search(query: str, per_page: int = 5) -> list[dict[str, Any]]:
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                PEXELS_ENDPOINT,
                headers={"Authorization": key},
                params={"query": query, "per_page": per_page, "orientation": "portrait"},
            )
            r.raise_for_status()
            return (r.json() or {}).get("videos", []) or []
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Pexels search failed for %r: %s", query, e)
        return []


async def fetch_clip_for_shot(shot_text: str, duration_target: float = 5.0) -> Path:
    """Return a local .mp4 file for the given shot description.

    Strategy:
      1. Try Pexels — pick smallest portrait clip >= duration_target.
      2. If no key / empty result → generate a deterministic solid-colour
         clip via ffmpeg so the pipeline never deadlocks.
    """
    cache_key = hashlib.sha256(shot_text.encode("utf-8")).hexdigest()[:16]
    cached = CACHE_DIR / f"{cache_key}.mp4"
    if cached.exists() and cached.stat().st_size > 1024:
        return cached

    videos = await _pexels_search(shot_text)
    if videos:
        # Pick the lowest-resolution portrait file with duration >= target
        for v in videos:
            for f in v.get("video_files", []):
                if f.get("file_type") == "video/mp4" and (f.get("height") or 0) >= (f.get("width") or 0):
                    url = f.get("link")
                    if url:
                        try:
                            async with httpx.AsyncClient(timeout=60.0) as client:
                                resp = await client.get(url)
                                resp.raise_for_status()
                                cached.write_bytes(resp.content)
                                logger.info("Pexels clip cached: %s (%d bytes)", cache_key, len(resp.content))
                                return cached
                        except httpx.HTTPError as e:
                            logger.warning("download failed: %s", e)

    # Fallback — generate a solid-colour placeholder clip via ffmpeg
    return await _make_placeholder_clip(shot_text, cache_key, duration_target)


async def _make_placeholder_clip(shot_text: str, cache_key: str, duration: float) -> Path:
    """Deterministic 1080x1920 solid-colour clip with shot text burned in.

    Used when Pexels has no key/results. Lets the pipeline render
    end-to-end so operators can verify wiring before adding the API key.
    """
    out = CACHE_DIR / f"{cache_key}.mp4"
    # Pick a hex colour deterministically from the hash so clips look different per shot
    r = int(cache_key[0:2], 16)
    g = int(cache_key[2:4], 16) // 2 + 40
    b = int(cache_key[4:6], 16) // 2 + 40
    colour = f"0x{r:02x}{g:02x}{b:02x}"
    label = (shot_text or "scene")[:60].replace(":", " ").replace("'", "").replace(",", " ")
    # No font file dependency — use ffmpeg default
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i", f"color=c={colour}:s=1080x1920:d={duration}:r=30",
        "-vf", f"drawtext=text='{label}':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.4:boxborderw=20",
        "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast",
        str(out),
    ]
    proc = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"placeholder ffmpeg failed: {err.decode(errors='replace')[:300]}")
    return out
