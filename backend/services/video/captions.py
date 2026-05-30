"""Adaptive captions via faster-whisper.

Replaces the uniform "total_duration / N lines" caption timing in
composer._build_caption_srt with REAL word-aligned timings transcribed
from the actual Piper TTS narration WAV.

Uses the `tiny.en` model (~40 MB, CPU-friendly, English-only). Cold-start
~3-5s, subsequent calls ~1-2s for a 30s narration. $0/mo: no API, runs
fully local on the same OCI VM as the rest of the engine.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("video.captions")

# Model size: tiny (39MB) is plenty for short-form. Larger models add latency
# without meaningfully improving accuracy on Piper-clean TTS.
_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "tiny.en")
_DEVICE = os.environ.get("WHISPER_DEVICE", "cpu")
_COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8")


@lru_cache(maxsize=1)
def _load_model():
    from faster_whisper import WhisperModel
    logger.info("loading faster-whisper model: %s (%s/%s)", _MODEL_SIZE, _DEVICE, _COMPUTE_TYPE)
    return WhisperModel(_MODEL_SIZE, device=_DEVICE, compute_type=_COMPUTE_TYPE)


def _fmt_ts(ts: float) -> str:
    h, m, s = int(ts // 3600), int((ts % 3600) // 60), ts % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def build_adaptive_srt(narration_wav: Path, max_words_per_line: int = 6) -> str:
    """Transcribe `narration_wav` and emit SRT with real word timings.

    Words are grouped into lines of `max_words_per_line` words each to keep
    captions readable on vertical 1080×1920 video.

    Returns the SRT text. Raises on transcription failure (callers may
    catch and fall back to composer._build_caption_srt for uniform timing).
    """
    if not narration_wav.exists():
        raise FileNotFoundError(narration_wav)
    model = _load_model()
    segments, _info = model.transcribe(
        str(narration_wav),
        word_timestamps=True,
        vad_filter=False,
        beam_size=1,
    )

    out_lines: list[str] = []
    counter = 1
    word_buffer: list = []

    def _flush():
        nonlocal counter
        if not word_buffer:
            return
        start = word_buffer[0].start
        end = word_buffer[-1].end
        text = " ".join(w.word.strip() for w in word_buffer).strip()
        if not text:
            word_buffer.clear()
            return
        out_lines.append(f"{counter}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{text}\n")
        counter += 1
        word_buffer.clear()

    for seg in segments:
        for w in (seg.words or []):
            word_buffer.append(w)
            if len(word_buffer) >= max_words_per_line:
                _flush()
    _flush()
    return "\n".join(out_lines)


def is_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False
