"""FFmpeg-based video composer.

Takes N stock clips + a single TTS narration WAV + a script and produces a
final 1080x1920 vertical MP4 with:
  - Concatenated stock B-roll trimmed to match narration duration
  - Burned-in caption overlay (one line per ~2.5s)
  - TTS audio mixed at full volume (no background music in $0 default)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("video.compose")

OUT_DIR = Path(os.environ.get("VIDEO_OUTPUT_DIR", "/app/data/videos"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


async def probe_duration(path: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await proc.communicate()
    try:
        return float(out.decode().strip())
    except (ValueError, AttributeError):
        return 0.0


def _build_caption_srt(lines: Iterable[str], total_seconds: float) -> str:
    items = [line for line in lines if line and line.strip()]
    if not items:
        return ""
    per = max(total_seconds / max(len(items), 1), 1.5)

    def fmt(ts: float) -> str:
        h, m, s = int(ts // 3600), int((ts % 3600) // 60), ts % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    out: list[str] = []
    for i, line in enumerate(items):
        start = i * per
        end = min(start + per, total_seconds)
        out.append(f"{i+1}\n{fmt(start)} --> {fmt(end)}\n{line}\n")
    return "\n".join(out)


async def compose(
    *,
    clips: list[Path],
    narration_wav: Path,
    caption_lines: list[str],
    output_filename: str,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    if not clips:
        raise ValueError("compose() requires at least one clip")
    if not narration_wav.exists():
        raise FileNotFoundError(narration_wav)

    target_seconds = await probe_duration(narration_wav)
    if target_seconds <= 0:
        target_seconds = max(len(clips) * 5.0, 10.0)

    # Build a concat file pointing at the source clips
    concat_path = OUT_DIR / f"{output_filename}.concat.txt"
    concat_path.write_text("\n".join(f"file {shlex.quote(str(c.resolve()))}" for c in clips))

    # Burn in subtitles
    srt_text = _build_caption_srt(caption_lines, target_seconds)
    srt_path = OUT_DIR / f"{output_filename}.srt"
    srt_path.write_text(srt_text or "1\n00:00:00,000 --> 00:00:01,000\n \n")

    out_path = OUT_DIR / f"{output_filename}.mp4"

    # First pass: concat + scale + pad to vertical 1080x1920
    pre_path = OUT_DIR / f"{output_filename}.pre.mp4"
    scale_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,setsar=1"
    )
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_path),
        "-t", str(target_seconds),
        "-vf", scale_filter,
        "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        str(pre_path),
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"concat ffmpeg failed: {err.decode(errors='replace')[:500]}")

    # Second pass: subtitle burn + audio mix
    subtitle_filter = f"subtitles={shlex.quote(str(srt_path))}:force_style='Fontsize=22,PrimaryColour=&Hffffff&,OutlineColour=&H000000&,Outline=2,Alignment=2,MarginV=120'"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(pre_path), "-i", str(narration_wav),
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_path),
        stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"compose ffmpeg failed: {err.decode(errors='replace')[:500]}")

    # Tidy intermediates
    for tmp in (concat_path, pre_path):
        try:
            tmp.unlink()
        except OSError:
            pass

    return out_path


def manifest_for(output_filename: str) -> Path:
    return OUT_DIR / f"{output_filename}.manifest.json"


async def write_manifest(output_filename: str, payload: dict) -> Path:
    p = manifest_for(output_filename)
    p.write_text(json.dumps(payload, indent=2))
    return p
