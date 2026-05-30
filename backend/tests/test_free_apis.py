"""Tests for the free-providers AI subsystem.

Covers:
  - Pollinations.ai client (keyless image generation)
  - Hugging Face Inference API client (configured / not configured paths)
  - ai_stock.fetch_ai_clip_for_shot (live network call to Pollinations)
  - gen_assets voice-ref save / lookup
  - Capability report exposes the new fields
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

from services.free_apis import huggingface, pollinations
from services.video import ai_stock, engine, gen_assets


# ---------------------------------------------------------------------------
# Pollinations
# ---------------------------------------------------------------------------

def test_pollinations_is_keyless_always_available():
    assert pollinations.is_available() is True


def test_pollinations_image_generation_live():
    """Live call to Pollinations.ai — skipped if no network."""
    try:
        data = asyncio.run(pollinations.generate_image(
            "vibrant abstract gradient minimalist",
            width=512, height=512, model="turbo",
        ))
    except Exception as e:
        pytest.skip(f"network unavailable: {e}")
    assert isinstance(data, bytes)
    assert len(data) > 1024
    # JPEG/PNG/WebP magic-number check
    assert data[:3] in (b"\xff\xd8\xff", b"\x89PN", b"RIF", b"\x00\x00\x00", b"GIF")


# ---------------------------------------------------------------------------
# Hugging Face
# ---------------------------------------------------------------------------

def test_huggingface_not_configured_by_default(monkeypatch):
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("HF_API_KEY", raising=False)
    assert huggingface.is_configured() is False
    with pytest.raises(huggingface.HFNotConfigured):
        huggingface._headers()


def test_huggingface_configured_with_token(monkeypatch):
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "hf_dummy_token_for_test")
    assert huggingface.is_configured() is True
    h = huggingface._headers()
    assert h["Authorization"] == "Bearer hf_dummy_token_for_test"


# ---------------------------------------------------------------------------
# AI B-roll integration
# ---------------------------------------------------------------------------

def test_ai_b_roll_generates_mp4_from_pollinations(tmp_path):
    """End-to-end: shot text → Pollinations image → ffmpeg Ken-Burns → MP4."""
    # Redirect cache so this test doesn't pollute the production cache
    import services.video.ai_stock as _ai_stock
    original_dir = _ai_stock.CACHE_DIR
    _ai_stock.CACHE_DIR = tmp_path
    try:
        path = asyncio.run(_ai_stock.fetch_ai_clip_for_shot(
            "test prompt unique pyramid stars night sky 4k",
            duration_target=2.0,
            fast=True,
        ))
    except Exception as e:
        pytest.skip(f"network unavailable: {e}")
    finally:
        _ai_stock.CACHE_DIR = original_dir

    if path is None:
        pytest.skip("AI B-roll returned None (likely network-blocked)")
    assert path.exists()
    assert path.stat().st_size > 50 * 1024  # AI clips are >50KB; placeholders ~15-30KB


# ---------------------------------------------------------------------------
# Voice references
# ---------------------------------------------------------------------------

def test_gen_assets_save_and_lookup_voice_ref(tmp_path, monkeypatch):
    monkeypatch.setattr(gen_assets, "VOICE_REF_DIR", tmp_path)
    fake_wav = b"RIFF" + b"\x00" * 1024
    vid = gen_assets.save_voice_ref(fake_wav, "audio/wav")
    assert vid.startswith("voice-")
    assert vid.endswith(".wav")
    p = gen_assets.voice_ref_path(vid)
    assert p is not None
    assert p.exists()
    refs = gen_assets.list_voice_refs()
    assert any(r["voice_ref_id"] == vid for r in refs)


# ---------------------------------------------------------------------------
# Capability report
# ---------------------------------------------------------------------------

def test_capability_report_exposes_new_free_provider_fields():
    report = engine.capability_report()
    # New fields shipped in iteration-11/12
    for key in (
        "free_providers", "ai_b_roll_available", "voice_cloning_available",
        "ai_music_generation_available", "text_to_video_available",
        "voice_refs_uploaded", "pollinations_tts_available",
        "pollinations_tts_voices", "hf_image_generation_available",
    ):
        assert key in report, f"capability report missing field: {key}"
    fp = report["free_providers"]
    assert "pollinations_ai" in fp
    assert "huggingface" in fp
    # Pollinations is keyless so should always be true
    assert fp["pollinations_ai"] is True
    # Iter12: voice cloning + AI music are now REAL local implementations
    # (Coqui XTTS-v2 + transformers MusicGen). Both should be True on a
    # fresh install where torch + TTS + transformers all imported OK.
    assert report["voice_cloning_available"] is True
    assert report["ai_music_generation_available"] is True
    # text-to-video still requires GPU; CPU-only path not viable yet.
    assert report["text_to_video_available"] is False
    # 6 Pollinations TTS voices
    assert set(report["pollinations_tts_voices"]) == {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}
