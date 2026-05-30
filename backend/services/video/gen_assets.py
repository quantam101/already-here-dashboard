"""Voice cloning + AI-generated music helpers.

Voice cloning: XTTS-v2 via Hugging Face Inference API. Operator uploads a
short (>= 6s) reference WAV/MP3 → narration is synthesised in their voice.

AI music: MusicGen via HF. Prompt → 30s loopable bed.

Both fail soft — if HF is not configured, callers fall back to Piper TTS
(local, default voice) and the bundled CC0 music beds.
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from services.free_apis import huggingface

logger = logging.getLogger("video.gen_assets")

VOICE_REF_DIR = Path(os.environ.get("VIDEO_VOICE_REFS_DIR", "/app/data/voice_refs"))
VOICE_REF_DIR.mkdir(parents=True, exist_ok=True)

AI_MUSIC_DIR = Path(os.environ.get("VIDEO_AI_MUSIC_DIR", "/app/data/ai_music"))
AI_MUSIC_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Voice cloning
# ---------------------------------------------------------------------------

def list_voice_refs() -> list[dict[str, str]]:
    out = []
    for p in sorted(VOICE_REF_DIR.iterdir(), key=lambda x: -x.stat().st_mtime if x.is_file() else 0):
        if p.is_file() and p.suffix.lower() in {".wav", ".mp3", ".m4a", ".ogg"}:
            out.append({
                "voice_ref_id": p.name,
                "size_bytes": str(p.stat().st_size),
            })
    return out


def save_voice_ref(data: bytes, content_type: str) -> str:
    ext = {
        "audio/wav": ".wav", "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3", "audio/mp3": ".mp3",
        "audio/x-m4a": ".m4a", "audio/mp4": ".m4a",
        "audio/ogg": ".ogg",
    }.get(content_type, ".wav")
    vid = f"voice-{uuid.uuid4().hex[:12]}{ext}"
    p = VOICE_REF_DIR / vid
    p.write_bytes(data)
    return vid


def voice_ref_path(voice_ref_id: str) -> Path | None:
    p = VOICE_REF_DIR / voice_ref_id
    return p if p.exists() and p.is_file() else None


async def synthesize_cloned_voice(
    text: str,
    voice_ref_id: str,
    output_wav: Path,
) -> Path:
    """XTTS-v2 via HF. Raises if HF not configured or model fails to warm."""
    if not huggingface.is_configured():
        raise huggingface.HFNotConfigured(
            "Voice cloning requires HUGGINGFACE_API_KEY (free at "
            "https://huggingface.co/settings/tokens)."
        )
    ref = voice_ref_path(voice_ref_id)
    if not ref:
        raise FileNotFoundError(f"voice reference {voice_ref_id} not found")
    ref_bytes = ref.read_bytes()
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    audio_bytes = await huggingface.synthesize_speech(
        text, reference_voice_wav_bytes=ref_bytes,
    )
    output_wav.write_bytes(audio_bytes)
    logger.info("voice-cloned WAV: %s (%d bytes)", output_wav.name, len(audio_bytes))
    return output_wav


# ---------------------------------------------------------------------------
# AI music generation
# ---------------------------------------------------------------------------

async def generate_music_track(prompt: str, duration_s: int = 30) -> Path | None:
    """MusicGen via HF. Returns the cached path or None if HF unavailable."""
    if not huggingface.is_configured():
        return None
    import hashlib
    key = hashlib.sha256(f"{prompt}:{duration_s}".encode("utf-8")).hexdigest()[:16]
    cached = AI_MUSIC_DIR / f"{key}.wav"
    if cached.exists() and cached.stat().st_size > 1024:
        return cached
    try:
        data = await huggingface.generate_music(prompt, duration_s=duration_s)
        cached.write_bytes(data)
        return cached
    except Exception as e:
        logger.warning("AI music gen failed: %s", str(e)[:120])
        return None
