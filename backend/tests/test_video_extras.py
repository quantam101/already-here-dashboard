"""Tests for the bundled royalty-free music catalogue + adaptive captions."""
from __future__ import annotations

from pathlib import Path

from services.video import captions, music


def test_music_catalogue_has_three_tracks_on_disk():
    tracks = music.list_tracks()
    ids = {t["id"] for t in tracks}
    assert {"cinematic", "upbeat", "chill"}.issubset(ids), (
        f"Expected three bundled CC0 beds on disk, found: {ids}"
    )
    # Every track > 100 KB (sanity check on the generated file)
    for t in tracks:
        assert int(t["size_kb"]) > 100


def test_music_resolve_known_and_unknown():
    p = music.resolve("cinematic")
    assert p is not None
    assert p.exists()
    assert p.suffix == ".mp3"

    assert music.resolve(None) is None
    assert music.resolve("none") is None
    assert music.resolve("does-not-exist") is None


def test_captions_available_flag():
    assert captions.is_available() is True


def test_captions_emit_srt_from_existing_wav(tmp_path):
    # Quick narration: generate a 2-second sine WAV that has speech-like
    # energy. faster-whisper will transcribe nothing but should still emit a
    # valid (possibly empty) SRT structure and not crash.
    import subprocess
    wav = tmp_path / "narration.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "sine=frequency=440:duration=2", "-ar", "16000", "-ac", "1",
         str(wav)],
        check=True,
    )
    assert wav.exists()
    srt = captions.build_adaptive_srt(Path(wav))
    # Either empty (no speech in a sine wave) or a well-formed SRT block.
    assert isinstance(srt, str)
    if srt.strip():
        assert "-->" in srt
