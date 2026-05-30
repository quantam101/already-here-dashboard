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
from services.video import avatar, captions as _captions, engine, gen_assets, music as _music, tts

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
    music_id: str | None = None  # cinematic | upbeat | chill | None
    music_volume: float = 0.15
    adaptive_captions: bool = False  # use faster-whisper word-level timing
    voice_ref_id: str | None = None  # XTTS-v2 voice clone source (legacy; HF pruned)
    ai_music_prompt: str | None = None  # if set, MusicGen overrides bundled bed (HF pruned)
    pollinations_voice: str | None = None  # alloy|echo|fable|onyx|nova|shimmer — keyless free TTS


class RenderFromScriptRequest(BaseModel):
    script_id: str
    voice_id: str | None = None
    mode: str = "faceless"
    portrait_id: str | None = None
    music_id: str | None = None
    music_volume: float = 0.15
    adaptive_captions: bool = False
    voice_ref_id: str | None = None
    ai_music_prompt: str | None = None
    pollinations_voice: str | None = None
    pollinations_voice: str | None = None


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


@router.get("/music")
async def music():
    """List bundled royalty-free background music tracks."""
    return {
        "available": _music.list_tracks(),
        "default_volume": 0.15,
        "note": "Procedurally generated CC0 beds. Mixed under TTS at the supplied volume (0-1).",
    }


@router.get("/free-providers")
async def free_providers():
    """Status of the keyless/free-tier AI providers wired into the engine."""
    from services.free_apis import huggingface as _hf, pollinations as _poll
    return {
        "pollinations": {
            "available": _poll.is_available(),
            "keyless": True,
            "capabilities": ["image", "text", "audio"],
            "endpoint": "https://pollinations.ai",
        },
        "huggingface": {
            "configured": _hf.is_configured(),
            "capabilities": [
                "image (FLUX.1-schnell)",
                "voice_clone (XTTS-v2)",
                "music (MusicGen)",
                "text_to_video (AnimateDiff / text-to-video-ms)",
            ],
            "models": {
                "image": _hf.DEFAULT_IMAGE_MODEL,
                "tts": _hf.DEFAULT_TTS_MODEL,
                "music": _hf.DEFAULT_MUSIC_MODEL,
                "video": _hf.DEFAULT_VIDEO_MODEL,
            },
            "note": "Free tier — set HUGGINGFACE_API_KEY env (https://huggingface.co/settings/tokens).",
        },
    }


@router.get("/voice-refs")
async def list_voice_refs_endpoint():
    """List uploaded voice-reference clips for XTTS-v2 cloning."""
    return gen_assets.list_voice_refs()


@router.post("/voice-refs/upload")
async def upload_voice_ref(file: UploadFile = File(...)):
    """Upload a voice reference for XTTS-v2 cloning (6-30s of clean speech)."""
    allowed = {
        "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
        "audio/x-m4a", "audio/mp4", "audio/ogg",
    }
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"unsupported content type: {file.content_type}")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="voice reference must be < 8 MB")
    if len(data) < 1024:
        raise HTTPException(status_code=400, detail="voice reference suspiciously tiny (< 1 KB)")
    voice_ref_id = gen_assets.save_voice_ref(data, file.content_type)
    return {
        "voice_ref_id": voice_ref_id,
        "size_bytes": len(data),
        "next": "use this voice_ref_id in POST /api/video/render with `voice_ref_id`",
    }


@router.delete("/voice-refs/{voice_ref_id}")
async def delete_voice_ref(voice_ref_id: str):
    p = gen_assets.voice_ref_path(voice_ref_id)
    if p and p.exists():
        p.unlink()
        return {"deleted": True}
    return {"deleted": False}


class GenerativeImageRequest(BaseModel):
    prompt: str = Field(..., min_length=2, max_length=600)
    provider: str = "pollinations"  # pollinations | huggingface
    width: int = 1080
    height: int = 1920


@router.post("/generative/image")
async def generative_image_preview(req: GenerativeImageRequest):
    """One-off prompt → image, for the Generative Suite preview tile."""
    from services.free_apis import huggingface as _hf, pollinations as _poll
    import base64
    try:
        if req.provider == "huggingface":
            if not _hf.is_configured():
                raise HTTPException(status_code=503, detail="HUGGINGFACE_API_KEY not set")
            data = await _hf.generate_image(req.prompt, width=req.width, height=req.height)
        else:
            data = await _poll.generate_image(req.prompt, width=req.width, height=req.height)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"image generation failed: {e}") from e
    return {
        "provider": req.provider,
        "size_bytes": len(data),
        "data_url": "data:image/jpeg;base64," + base64.b64encode(data).decode(),
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
        music_id=req.music_id, music_volume=req.music_volume,
        adaptive_captions=req.adaptive_captions,
        voice_ref_id=req.voice_ref_id,
        ai_music_prompt=req.ai_music_prompt,
        pollinations_voice=req.pollinations_voice,
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
        music_id=req.music_id,
        music_volume=req.music_volume,
        adaptive_captions=req.adaptive_captions,
        voice_ref_id=req.voice_ref_id,
        ai_music_prompt=req.ai_music_prompt,
        pollinations_voice=req.pollinations_voice,
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
