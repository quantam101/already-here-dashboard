"""Top-level video render orchestrator + job store.

The pipeline:
  1. Build the narration script (HOOK + SCRIPT + CTA, joined).
  2. TTS → narration.wav  (Piper, local, free)
  3. For each SHOT description → fetch_clip_for_shot (Pexels free tier, falls
     back to a placeholder clip when no API key is set so the pipeline
     never deadlocks during $0 dev).
  4. ffmpeg concat + scale-to-vertical + burn-in captions + audio mix.
  5. Write a manifest JSON next to the MP4 (full provenance).

Jobs are tracked in the `video_jobs` collection so the operator can poll
status from the UI.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.video import composer, stock, tts

logger = logging.getLogger("video.engine")

JOB_COLLECTION = "video_jobs"
WORK_ROOT = Path(os.environ.get("VIDEO_OUTPUT_DIR", "/app/data/videos"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return f"vid-{uuid.uuid4().hex[:10]}"


async def create_job(db, *, script: dict, voice_id: str | None, mode: str = "faceless") -> dict:
    """Insert a `pending` job row and return it. Operator polls /status."""
    row = {
        "id": new_job_id(),
        "mode": mode,
        "status": "pending",
        "script": {
            "hook": script.get("hook", ""),
            "script_body": script.get("script_body") or script.get("body", ""),
            "cta": script.get("cta", ""),
            "shots": script.get("shot_list") or script.get("shots") or [],
        },
        "voice_id": voice_id,
        "progress_pct": 0,
        "message": "queued",
        "output_path": None,
        "error": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db[JOB_COLLECTION].insert_one(row)
    return row


async def get_job(db, job_id: str) -> dict | None:
    return await db[JOB_COLLECTION].find_one({"id": job_id}, {"_id": 0})


async def list_jobs(db, limit: int = 30) -> list[dict]:
    return await db[JOB_COLLECTION].find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def _update(db, job_id: str, **changes) -> None:
    changes["updated_at"] = _now()
    await db[JOB_COLLECTION].update_one({"id": job_id}, {"$set": changes})


async def run_pipeline(db, job_id: str) -> None:
    """Run the full faceless-video render. Updates progress as it goes."""
    job = await get_job(db, job_id)
    if not job:
        logger.error("run_pipeline: job %s missing", job_id)
        return

    script = job["script"]
    shots = [s for s in (script.get("shots") or []) if s and s.strip()]
    if not shots:
        shots = ["Opening", "Main idea", "Detail", "Proof", "Call to action"]

    narration = " ".join([
        script.get("hook", ""), script.get("script_body", ""), script.get("cta", ""),
    ]).strip()

    if not narration:
        await _update(db, job_id, status="failed", error="empty narration script")
        return

    try:
        await _update(db, job_id, status="running", progress_pct=5, message="generating narration")
        wav_path = WORK_ROOT / f"{job_id}.wav"
        await tts.synthesize(narration, wav_path, voice_id=job.get("voice_id"))

        await _update(db, job_id, progress_pct=25, message=f"fetching {len(shots)} stock clips")
        clip_paths: list[Path] = []
        for i, shot in enumerate(shots, 1):
            clip = await stock.fetch_clip_for_shot(shot)
            clip_paths.append(clip)
            pct = 25 + int(50 * i / len(shots))
            await _update(db, job_id, progress_pct=pct, message=f"clip {i}/{len(shots)}: {shot[:40]}")

        await _update(db, job_id, progress_pct=80, message="composing final MP4")
        caption_lines = [
            line.strip()
            for chunk in [script.get("hook"), script.get("script_body"), script.get("cta")]
            for line in (chunk or "").split(". ")
            if line and line.strip()
        ]
        out_mp4 = await composer.compose(
            clips=clip_paths,
            narration_wav=wav_path,
            caption_lines=caption_lines,
            output_filename=job_id,
        )

        await composer.write_manifest(job_id, {
            "job_id": job_id,
            "mode": job["mode"],
            "shots": shots,
            "voice_id": job.get("voice_id"),
            "clip_count": len(clip_paths),
            "size_bytes": out_mp4.stat().st_size,
            "created_at": _now(),
        })

        await _update(
            db, job_id,
            status="complete", progress_pct=100,
            message=f"render complete ({out_mp4.stat().st_size // 1024} KB)",
            output_path=str(out_mp4),
        )
    except Exception as e:
        logger.exception("video pipeline failed: %s", e)
        await _update(db, job_id, status="failed", error=str(e)[:500], message="render failed")


def kickoff(db, job_id: str) -> asyncio.Task:
    """Spawn the pipeline as a background task and return it."""
    return asyncio.create_task(run_pipeline(db, job_id))


# ---------------------------------------------------------------------------
# Capability self-report — used by /api/video/config
# ---------------------------------------------------------------------------

def capability_report() -> dict[str, Any]:
    """What the engine can do RIGHT NOW on this host."""
    import shutil
    ffmpeg = shutil.which("ffmpeg") is not None
    # piper ships as both a script ("piper") AND an importable Python module.
    # Check both — supervisor PATH may not include the venv bin dir even when
    # the venv module is importable.
    piper = shutil.which("piper") is not None
    if not piper:
        try:
            import piper as _piper_mod  # noqa: F401
            piper = True
        except ImportError:
            piper = False
    voices = tts.list_installed_voices()
    pexels_key = bool(os.environ.get("PEXELS_API_KEY", "").strip())
    return {
        "ffmpeg_installed": ffmpeg,
        "piper_installed": piper,
        "voices_installed": [v["id"] for v in voices],
        "pexels_api_key_set": pexels_key,
        "modes_available": {
            "faceless": ffmpeg and piper and bool(voices),
            "avatar_lipsync": False,  # Phase-2 (Wav2Lip ONNX) — scaffolded only
            "external_provider": False,  # Phase-3 (Sora/Veo bridge) — scaffolded only
        },
        "operator_actions": _operator_hints(ffmpeg, piper, voices, pexels_key),
    }


def _operator_hints(ffmpeg: bool, piper: bool, voices: list, pexels: bool) -> list[str]:
    hints: list[str] = []
    if not ffmpeg:
        hints.append("Install ffmpeg: `sudo apt-get install -y ffmpeg`")
    if not piper:
        hints.append("Install Piper TTS: `pip install piper-tts`")
    if not voices:
        hints.append(
            "Download at least one voice into /app/data/voices/ — e.g. "
            "`curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -o /app/data/voices/en_US-amy-medium.onnx` (plus the .json file)"
        )
    if not pexels:
        hints.append(
            "Add a PEXELS_API_KEY env var for real stock footage (free at "
            "https://www.pexels.com/api/). Without it the engine still renders, "
            "but uses solid-colour placeholder clips."
        )
    return hints
