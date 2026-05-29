"""Video Engine API — render faceless videos from scripts.

Endpoints:
  GET    /api/video/config              capability self-report
  GET    /api/video/voices              list installed Piper voices
  POST   /api/video/render              kick off a faceless render
  POST   /api/video/render-from-script  helper: pull a script from /studio
  GET    /api/video/jobs                list recent jobs
  GET    /api/video/jobs/{id}           job status
  GET    /api/video/jobs/{id}/download  download the final MP4
  DELETE /api/video/jobs/{id}           delete the job + its files
"""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services import governance_service as gov
from services.audit_service import log_audit_event
from services.video import avatar, engine, tts

router = APIRouter()


async def get_db():
    from server import db
    return db


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ScriptBlock(BaseModel):
    hook: str = ""
    script_body: str = ""
    cta: str = ""
    shot_list: list[str] = Field(default_factory=list)


class RenderRequest(BaseModel):
    script: ScriptBlock
    voice_id: str | None = None
    mode: str = "faceless"  # faceless | avatar_lipsync | external_provider
    portrait_id: str | None = None  # for avatar_lipsync — file id from /portraits/upload


class RenderFromScriptRequest(BaseModel):
    script_id: str
    voice_id: str | None = None
    mode: str = "faceless"
    portrait_id: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config")
async def config():
    return engine.capability_report()


@router.get("/voices")
async def voices():
    return {
        "installed": tts.list_installed_voices(),
        "default": os.environ.get("VIDEO_DEFAULT_VOICE", "en_US-amy-medium"),
    }


@router.post("/render")
async def render(req: RenderRequest, http_request: Request, background: BackgroundTasks, db=Depends(get_db)):
    if req.mode not in {"faceless", "avatar_lipsync", "external_provider"}:
        raise HTTPException(status_code=400, detail=f"unknown mode: {req.mode}")

    caps = engine.capability_report()
    if not caps["modes_available"].get(req.mode):
        details = caps["external_provider_status"] if req.mode == "external_provider" else None
        raise HTTPException(
            status_code=503,
            detail={
                "error": f"{req.mode} mode unavailable",
                "missing": caps["operator_actions"],
                "external_provider_status": details,
            },
        )

    portrait_path: str | None = None
    if req.mode == "avatar_lipsync":
        if not req.portrait_id:
            raise HTTPException(
                status_code=400,
                detail="avatar_lipsync mode requires `portrait_id` from POST /api/video/portraits/upload",
            )
        candidate = avatar.PORTRAITS_DIR / req.portrait_id
        if not candidate.exists():
            raise HTTPException(status_code=404, detail=f"portrait {req.portrait_id} not found")
        portrait_path = str(candidate)

    script_dict = req.script.model_dump()
    job = await engine.create_job(
        db, script=script_dict, voice_id=req.voice_id, mode=req.mode, portrait_path=portrait_path,
    )
    background.add_task(_run_pipeline_task, job["id"])
    await log_audit_event(
        db, "video.render.started", "operator", "render", "video_job", job["id"],
        metadata={
            "mode": req.mode, "voice": req.voice_id,
            "shots": len(script_dict.get("shot_list") or []),
            "portrait_id": req.portrait_id,
        },
    )
    return {"job_id": job["id"], "status": job["status"], "mode": req.mode, "next": f"GET /api/video/jobs/{job['id']}"}


@router.post("/portraits/upload")
async def upload_portrait(file: UploadFile = File(...)):
    """Upload a portrait image for avatar_lipsync mode.

    Returns a portrait_id (the filename on disk) that the operator passes
    to POST /render. Files are stored in /app/data/portraits/ with a
    random uuid prefix to avoid collisions.

    Constraints:
      - Max 10 MB
      - Must be image/jpeg, image/png, or image/webp
      - File extension is preserved
    """
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=400, detail=f"unsupported content type: {file.content_type}")
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="portrait must be < 10 MB")
    if len(data) < 1024:
        raise HTTPException(status_code=400, detail="portrait suspiciously tiny (< 1 KB)")
    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[file.content_type]
    portrait_id = f"{uuid.uuid4().hex[:12]}{ext}"
    dest = avatar.PORTRAITS_DIR / portrait_id
    dest.write_bytes(data)
    return {
        "portrait_id": portrait_id,
        "size_bytes": len(data),
        "content_type": file.content_type,
        "next": "use this portrait_id in POST /api/video/render with mode='avatar_lipsync'",
    }


@router.get("/portraits")
async def list_portraits():
    """List uploaded portraits (filename, size, mtime)."""
    rows = []
    for p in sorted(avatar.PORTRAITS_DIR.iterdir(), key=lambda x: -x.stat().st_mtime if x.is_file() else 0):
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            rows.append({"portrait_id": p.name, "size_bytes": p.stat().st_size, "mtime": p.stat().st_mtime})
    return rows


@router.delete("/portraits/{portrait_id}")
async def delete_portrait(portrait_id: str):
    p = avatar.PORTRAITS_DIR / portrait_id
    if p.exists() and p.is_file():
        p.unlink()
        return {"deleted": True}
    return {"deleted": False}


async def _run_pipeline_task(job_id: str) -> None:
    """BackgroundTasks-compatible wrapper that re-resolves db lazily."""
    from server import db as _db
    await engine.run_pipeline(_db, job_id)


@router.post("/render-from-script")
async def render_from_script(
    req: RenderFromScriptRequest, http_request: Request, background: BackgroundTasks, db=Depends(get_db),
):
    """Helper: fetch a stored script from /studio and render it directly."""
    script = await db.content_scripts.find_one({"id": req.script_id}, {"_id": 0})
    if not script:
        raise HTTPException(status_code=404, detail=f"script {req.script_id} not found")
    payload = RenderRequest(
        script=ScriptBlock(
            hook=script.get("hook", ""),
            script_body=script.get("script_body") or script.get("body", ""),
            cta=script.get("cta", ""),
            shot_list=script.get("shot_list") or [],
        ),
        voice_id=req.voice_id,
        mode=req.mode,
        portrait_id=req.portrait_id,
    )
    return await render(payload, http_request, background, db)


@router.get("/jobs")
async def list_jobs(limit: int = 30, db=Depends(get_db)):
    return await engine.list_jobs(db, limit=min(int(limit), 200))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db=Depends(get_db)):
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    return job


@router.get("/jobs/{job_id}/download")
async def download_job(job_id: str, db=Depends(get_db)):
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    out = job.get("output_path")
    if not out or not Path(out).exists():
        raise HTTPException(status_code=409, detail=f"job is {job.get('status')} — no MP4 yet")
    return FileResponse(out, media_type="video/mp4", filename=f"{job_id}.mp4")


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db=Depends(get_db)):
    job = await engine.get_job(db, job_id)
    if not job:
        return {"deleted": False, "reason": "not found"}
    if job.get("output_path"):
        try:
            Path(job["output_path"]).unlink()
        except OSError:
            pass
    await db[engine.JOB_COLLECTION].delete_one({"id": job_id})
    return {"deleted": True, "id": job_id}
