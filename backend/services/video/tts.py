"""Piper TTS wrapper — free, local, ARM-compatible neural voiceover.

Voices are .onnx + .json files stored under VIDEO_VOICES_DIR.
A default voice (en_US-amy-medium) ships with the install.
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

logger = logging.getLogger("video.tts")

VOICES_DIR = Path(os.environ.get("VIDEO_VOICES_DIR", "/app/data/voices"))
DEFAULT_VOICE = os.environ.get("VIDEO_DEFAULT_VOICE", "en_US-amy-medium")


def list_installed_voices() -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not VOICES_DIR.exists():
        return out
    for onnx in sorted(VOICES_DIR.glob("*.onnx")):
        cfg = onnx.with_suffix(".onnx.json")
        if cfg.exists():
            out.append({"id": onnx.stem, "onnx_path": str(onnx), "config_path": str(cfg)})
    return out


def _resolve_voice(voice_id: str | None) -> Path:
    target = voice_id or DEFAULT_VOICE
    candidate = VOICES_DIR / f"{target}.onnx"
    if not candidate.exists():
        # Fallback: first installed voice
        voices = list_installed_voices()
        if not voices:
            raise FileNotFoundError(
                f"No Piper voices installed in {VOICES_DIR}. "
                f"Download from https://huggingface.co/rhasspy/piper-voices."
            )
        return Path(voices[0]["onnx_path"])
    return candidate


async def synthesize(text: str, output_wav: Path, voice_id: str | None = None) -> Path:
    """Generate a WAV file from text using Piper TTS."""
    text = (text or "").strip()
    if not text:
        raise ValueError("synthesize() requires non-empty text")
    model = _resolve_voice(voice_id)
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    # Resolve the piper binary (PATH first, then the venv bin alongside this python)
    import shutil
    import sys
    binary = shutil.which("piper")
    if not binary:
        candidate = Path(sys.executable).parent / "piper"
        if candidate.exists():
            binary = str(candidate)
    if not binary:
        raise RuntimeError(
            "Piper CLI not found — install with `pip install piper-tts`."
        )

    proc = await asyncio.create_subprocess_exec(
        binary, "--model", str(model), "--output_file", str(output_wav),
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await proc.communicate(text.encode("utf-8"))
    if proc.returncode != 0 or not output_wav.exists():
        raise RuntimeError(f"piper failed: {err.decode(errors='replace')[:300]}")
    logger.info("piper WAV: %s (%d bytes)", output_wav.name, output_wav.stat().st_size)
    return output_wav
