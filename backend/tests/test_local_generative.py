"""Smoke tests for the REAL local generative pipeline (XTTS-v2 + MusicGen).

These tests are marked as `slow` because they load multi-GB models from
the HuggingFace cache. They run once in CI to confirm the install is
healthy and the operator's pipeline produces real audio.
"""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from services.video import local_music, local_voice


pytestmark = pytest.mark.slow


def test_local_music_module_imports_and_reports_available():
    assert local_music.is_available() is True


def test_local_voice_module_imports_and_reports_available():
    assert local_voice.is_available() is True


def test_local_musicgen_generates_real_wav(tmp_path, monkeypatch):
    """End-to-end: prompt → real PCM WAV from transformers MusicGen."""
    monkeypatch.setattr(local_music, "MUSIC_CACHE", tmp_path)
    path = asyncio.run(local_music.generate_music_track(
        "soft ambient electronic pad", duration_s=3,
    ))
    assert path.exists()
    # 3 seconds at 32kHz mono 16-bit ≈ 192 KB minimum
    assert path.stat().st_size > 80 * 1024, f"musicgen output too small: {path.stat().st_size}"


def test_local_voice_clone_generates_real_wav(tmp_path):
    """End-to-end: reference + text → real cloned WAV from XTTS-v2."""
    ref = tmp_path / "ref.wav"
    subprocess.run([
        "piper", "--model", "/app/data/voices/en_US-amy-medium.onnx",
        "--output_file", str(ref),
    ], input="This is a sample voice for testing the cloning system.",
       text=True, check=True)
    assert ref.exists() and ref.stat().st_size > 1024

    out = tmp_path / "clone.wav"
    asyncio.run(local_voice.synthesize_cloned(
        "Hello, this is a cloned voice output.",
        ref, out,
    ))
    assert out.exists()
    assert out.stat().st_size > 50 * 1024, f"clone output too small: {out.stat().st_size}"
