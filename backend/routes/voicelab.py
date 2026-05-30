"""
Voice Lab Matrix Engine — FastAPI router.

Endpoints:
  GET    /api/voicelab/config              capability self-report
  POST   /api/voicelab/compile             queue a new matrix job (HTTP 202)
  GET    /api/voicelab/jobs                list recent jobs
  GET    /api/voicelab/jobs/{id}           poll job status
  GET    /api/voicelab/jobs/{id}/download  stream the finished matrix MP4
  DELETE /api/voicelab/jobs/{id}           delete job record + work files
"""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services import voicelab_engine as engine
from services.audit_service import log_audit_event

router = APIRouter()

VALID_VOICES: frozenset[str] = frozenset(engine.VOICES)


async def get_db():
    from server import db
    return db


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class CompileRequest(BaseModel):
    script: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="Text to synthesise across all selected voice channels",
    )
    voices: list[str] | None = Field(
        default=None,
        description=(
            "Voice subset. Omit or pass null for all 6: "
            "alloy, echo, fable, onyx, nova, shimmer"
        ),
    )


# ---------------------------------------------------------------------------
# BackgroundTasks wrapper
# ---------------------------------------------------------------------------

async def _run_pipeline_bg(job_id: str) -> None:
    """Lazily resolve db at execution time — safe for background task context."""
    from server import db as _db
    await engine.run_pipeline(_db, job_id)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def voicelab_config():
    """Capability self-report: ffmpeg present, Pollinations endpoint, voices list."""
    ffmpeg_ok = bool(shutil.which("ffmpeg"))
    import os
    has_api_key = bool(os.environ.get("POLLINATIONS_API_KEY", "").strip())
    return {
        "ffmpeg_available": ffmpeg_ok,
        "voices": list(engine.VOICES),
        "tts_endpoint": engine.POLLINATIONS_TTS_URL,
        "output_dir": str(engine.WORK_ROOT),
        "pollinations_api_key_set": has_api_key,
        "ready": ffmpeg_ok,
        "notes": (
            [
                "ffmpeg missing — install on the host and restart the container.",
                "Matrix compilation will fail until ffmpeg is available.",
            ]
            if not ffmpeg_ok
            else [
                "Unauthenticated Pollinations usage is subject to fair-use quotas.",
                "Set POLLINATIONS_API_KEY in .env for authenticated tier.",
            ]
        ),
    }


@router.post("/compile", status_code=202)
async def compile_matrix(
    req: CompileRequest,
    background: BackgroundTasks,
    db=Depends(get_db),
):
    """Queue a multi-channel matrix compilation job. Returns HTTP 202 immediately.

    Pipeline (runs in background):
      1. Concurrent TTS extraction — one Pollinations call per voice channel,
         semaphore-limited to 6, with exponential back-off retry.
      2. Memory-mapped file integrity check (min 1 KB) + atomic rename.
      3. ffmpeg filtergraph — 2×3 grid with centred voice labels + mixed audio.

    Poll GET /api/voicelab/jobs/{job_id} until status → 'complete' or 'failed'.
    Download the matrix MP4 at GET /api/voicelab/jobs/{job_id}/download.
    """
    voices = list(req.voices) if req.voices else list(engine.VOICES)
    invalid = [v for v in voices if v not in VALID_VOICES]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid voice(s): {invalid}. Valid choices: {sorted(VALID_VOICES)}",
        )
    if len(voices) < 1:
        raise HTTPException(status_code=400, detail="At least one voice is required")

    if not shutil.which("ffmpeg"):
        raise HTTPException(
            status_code=503,
            detail=(
                "ffmpeg not found in PATH. Install ffmpeg on the host and restart "
                "the container before attempting matrix compilation."
            ),
        )

    job = await engine.create_job(db, script=req.script.strip(), selected_voices=voices)
    background.add_task(_run_pipeline_bg, job["id"])

    await log_audit_event(
        db,
        "voicelab.compile.queued",
        "operator",
        "create",
        "voicelab_job",
        job["id"],
        metadata={"voices": voices, "script_chars": len(req.script)},
    )

    return {
        "job_id": job["id"],
        "status": "pending",
        "voices": voices,
        "script_chars": len(req.script),
        "poll_url": f"/api/voicelab/jobs/{job['id']}",
        "download_url": f"/api/voicelab/jobs/{job['id']}/download",
    }


@router.get("/jobs")
async def list_jobs(limit: int = 30, db=Depends(get_db)):
    """List recent Voice Lab compilation jobs (newest first)."""
    return await engine.list_jobs(db, limit=min(int(limit), 200))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db=Depends(get_db)):
    """Poll a specific job. Returns status, progress_pct, voice_results, output_path."""
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return job


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str, db=Depends(get_db)):
    """Stream the compiled 6-up matrix MP4 once the job is complete."""
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    out = job.get("output_path")
    if not out or not Path(out).exists():
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job status is '{job.get('status')}' — no MP4 available yet. "
                f"Poll GET /api/voicelab/jobs/{job_id} and retry when status='complete'."
            ),
        )
    return FileResponse(
        out,
        media_type="video/mp4",
        filename=f"{job_id}_voicelab_matrix.mp4",
    )


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db=Depends(get_db)):
    """Delete a job record and all associated work files (MP3s + MP4)."""
    job = await engine.get_job(db, job_id)
    if not job:
        return {"deleted": False, "reason": "not found"}
    work_dir = engine.WORK_ROOT / job_id
    if work_dir.exists():
        try:
            shutil.rmtree(work_dir)
        except OSError as exc:
            pass  # non-fatal — record still removed from DB
    await db[engine.JOB_COLLECTION].delete_one({"id": job_id})
    return {"deleted": True, "id": job_id}
