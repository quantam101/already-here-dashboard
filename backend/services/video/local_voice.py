"""Local voice cloning via Coqui XTTS-v2.

No HF hosting required — runs on CPU using the multilingual XTTS-v2 model
(~1.8GB cached after first download). Generates speech in the operator's
voice from a 6-30s reference clip.

First call cold-starts the model (~30-60s), subsequent calls are ~1-3s
per ~10s of output text. Memory footprint: ~3-4 GB RAM during inference.
"""
from __future__ import annotations

import asyncio
import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("video.local_voice")

_MODEL_NAME = os.environ.get("LOCAL_XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")


@lru_cache(maxsize=1)
def _load_tts():
    """Lazy load. Patches the transformers API drift in Coqui first."""
    import torch
    import transformers.pytorch_utils as _ptu
    if not hasattr(_ptu, "isin_mps_friendly"):
        _ptu.isin_mps_friendly = torch.isin
    # The TTS library checks XttsConfig safe-load; allow it.
    from TTS.api import TTS  # type: ignore

    # XTTS v2 is gated behind a CPML license agreement. Auto-accept since
    # the operator explicitly opted in by selecting voice cloning.
    os.environ.setdefault("COQUI_TOS_AGREED", "1")
    logger.info("loading Coqui XTTS-v2 (cold-start ~30-60s, then cached)")
    tts = TTS(_MODEL_NAME, progress_bar=False, gpu=False)
    return tts


def _sync_clone(text: str, reference_wav: str, output_path: str, language: str = "en") -> None:
    tts = _load_tts()
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_wav,
        language=language,
        file_path=output_path,
        split_sentences=True,
    )


async def synthesize_cloned(
    text: str,
    reference_wav: Path,
    output_wav: Path,
    language: str = "en",
) -> Path:
    """Synthesise `text` in the voice from `reference_wav`. Returns the WAV path."""
    if not reference_wav.exists():
        raise FileNotFoundError(f"reference voice not found: {reference_wav}")
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None, _sync_clone, text, str(reference_wav), str(output_wav), language,
    )
    if not output_wav.exists() or output_wav.stat().st_size < 1024:
        raise RuntimeError("local voice clone produced an empty/too-small WAV")
    logger.info("local clone WAV: %s (%d KB)", output_wav.name, output_wav.stat().st_size // 1024)
    return output_wav


def _apply_compat_patch():
    """Patch the missing `transformers.pytorch_utils.isin_mps_friendly`
    that Coqui-TTS's bundled tortoise layer expects but was removed in
    newer transformers versions. Idempotent."""
    try:
        import torch
        import transformers.pytorch_utils as _ptu
        if not hasattr(_ptu, "isin_mps_friendly"):
            _ptu.isin_mps_friendly = torch.isin
    except ImportError:
        pass


# Apply on module import so even `import TTS` succeeds downstream.
_apply_compat_patch()


def is_available() -> bool:
    _apply_compat_patch()
    try:
        import torch  # noqa: F401
        import TTS  # noqa: F401
        return True
    except ImportError:
        return False
