"""Local AI music generation via transformers MusicGen.

No HF hosting required — runs entirely on CPU using the `musicgen-small`
model (~300MB, loaded once and cached). Generates 30-second royalty-free
backing tracks from a text prompt at $0/mo.

This replaces the now-removed HF Inference hosted endpoint (Feb 2026
pruning) with a truly $0 local pipeline.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

logger = logging.getLogger("video.local_music")

MUSIC_CACHE = Path(os.environ.get("VIDEO_AI_MUSIC_DIR", "/app/data/ai_music"))
MUSIC_CACHE.mkdir(parents=True, exist_ok=True)

_MODEL_NAME = os.environ.get("LOCAL_MUSICGEN_MODEL", "facebook/musicgen-small")
_SAMPLE_RATE = 32_000  # MusicGen native output rate


@lru_cache(maxsize=1)
def _load():
    """Lazy load — first call is ~30s (model download), subsequent ~instant."""
    # Patch missing function for transformers compat (also done in tts loader)
    import torch
    import transformers.pytorch_utils as _ptu
    if not hasattr(_ptu, "isin_mps_friendly"):
        _ptu.isin_mps_friendly = torch.isin
    from transformers import AutoProcessor, MusicgenForConditionalGeneration
    logger.info("loading MusicGen model: %s (cold-start ~30s, then cached)", _MODEL_NAME)
    processor = AutoProcessor.from_pretrained(_MODEL_NAME)
    model = MusicgenForConditionalGeneration.from_pretrained(_MODEL_NAME)
    model.eval()
    return processor, model


def _sync_generate(prompt: str, duration_s: int) -> np.ndarray:
    import torch
    processor, model = _load()
    inputs = processor(text=[prompt], padding=True, return_tensors="pt")
    # MusicGen generates ~0.02s per token; 1500 tokens ≈ 30s
    max_new_tokens = max(64, min(int(duration_s * 50), 1500))
    with torch.no_grad():
        audio_values = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            guidance_scale=3.0,
        )
    arr = audio_values[0, 0].cpu().numpy()
    return arr.astype(np.float32)


async def generate_music_track(prompt: str, duration_s: int = 20) -> Path:
    """Returns cached WAV path. Uses prompt hash for idempotent caching."""
    key = hashlib.sha256(f"{prompt}:{duration_s}:{_MODEL_NAME}".encode("utf-8")).hexdigest()[:16]
    wav_path = MUSIC_CACHE / f"musicgen-{key}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 4096:
        return wav_path

    loop = asyncio.get_running_loop()
    arr = await loop.run_in_executor(None, _sync_generate, prompt, duration_s)

    # Persist as a 16-bit PCM WAV at the native sample rate
    import wave
    pcm = (np.clip(arr, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_SAMPLE_RATE)
        w.writeframes(pcm)
    logger.info("MusicGen wrote %s (%d KB)", wav_path.name, wav_path.stat().st_size // 1024)
    return wav_path


def is_available() -> bool:
    try:
        import transformers  # noqa: F401
        import torch  # noqa: F401
        return True
    except ImportError:
        return False
