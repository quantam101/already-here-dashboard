"""Royalty-free background music — bundled CC0 procedural beds.

Tracks are synthesized at build time by ffmpeg using deterministic sine
oscillators (see scripts/generate_music_beds.sh). Output: three 2-minute
1080×1920-compatible mono/stereo MP3 files mixed at -18dB under TTS.

$0/mo cost. No external API. No licensing risk — they were generated from
basic math, not from any copyrighted source material.
"""
from __future__ import annotations

import os
from pathlib import Path

MUSIC_DIR = Path(os.environ.get("VIDEO_MUSIC_DIR", "/app/data/music"))

# Catalogue: mood_id → filename + display label
CATALOGUE: dict[str, dict[str, str]] = {
    "cinematic": {
        "file": "cinematic_bed.mp3",
        "label": "Cinematic — deep low pad",
    },
    "upbeat": {
        "file": "upbeat_bed.mp3",
        "label": "Upbeat — arpeggiated bright synth",
    },
    "chill": {
        "file": "chill_bed.mp3",
        "label": "Chill — warm slow pad",
    },
}


def list_tracks() -> list[dict[str, str]]:
    """Tracks currently on disk."""
    out: list[dict[str, str]] = []
    for mood_id, meta in CATALOGUE.items():
        p = MUSIC_DIR / meta["file"]
        if p.exists():
            out.append({
                "id": mood_id,
                "label": meta["label"],
                "size_kb": str(p.stat().st_size // 1024),
            })
    return out


def resolve(mood_id: str | None) -> Path | None:
    """Return the path to the track file, or None if unknown / disabled."""
    if not mood_id or mood_id == "none":
        return None
    meta = CATALOGUE.get(mood_id.lower())
    if not meta:
        return None
    p = MUSIC_DIR / meta["file"]
    return p if p.exists() else None
