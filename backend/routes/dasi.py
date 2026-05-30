"""
D-ASI v4.0.0-ENTERPRISE — FastAPI router.

Endpoints:
  GET    /api/dasi/health              system vitality check + manifest summary
  POST   /api/dasi/matrix/execute      queue a new swarm job (HTTP 202)
  GET    /api/dasi/matrix/telemetry    list recent jobs (newest first)
  GET    /api/dasi/jobs/{id}           poll job status + matrix context snapshot
  GET    /api/dasi/jobs/{id}/result    download final artifact (text)
  DELETE /api/dasi/jobs/{id}           purge job record from DB
"""
from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from services import dasi_engine as engine
from services.audit_service import log_audit_event

router = APIRouter()


async def get_db():
    from server import db
    return db


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    directive: str = Field(
        ...,
        min_length=1,
        max_length=8192,
        description=(
            "Top-level operational directive for the D-ASI swarm pipeline. "
            "The 4-stage agent graph will decompose, compress, synthesise, and "
            "validate a production artifact in response."
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

@router.get("/health")
async def dasi_health():
    """System vitality check. Returns manifest metadata and model chain."""
    manifest = engine.load_manifest()
    ops = manifest.get("operational_profile", {})
    agents = manifest.get("swarm_matrix", {}).get("agents", [])
    policies = manifest.get("security_policies", [])
    stages = manifest.get("topology_map", {}).get("execution_sequence", [])
    hf_token_set = bool(
        os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    )
    return {
        "status": "operational" if manifest else "degraded",
        "manifest_loaded": bool(manifest),
        "version": manifest.get("version", "unknown"),
        "primary_llm": ops.get("primary_llm", "not configured"),
        "fallback_llm": ops.get("fallback_llm", "not configured"),
        "agent_count": len(agents),
        "stage_count": len(stages),
        "policy_count": len(policies),
        "hf_token_set": hf_token_set,
        "circuit_breaker_threshold": ops.get("circuit_breaker_threshold", 3),
        "temperature": ops.get("temperature", 0.1),
        "max_token_budget": ops.get("max_token_budget", 3072),
        "ready": bool(manifest) and hf_token_set,
        "notes": (
            ["HF_TOKEN or HUGGINGFACE_API_KEY must be set for inference."]
            if not hf_token_set
            else ["D-ASI engine is fully operational."]
        ),
    }


@router.post("/matrix/execute", status_code=202)
async def execute_directive(
    req: ExecuteRequest,
    background: BackgroundTasks,
    db=Depends(get_db),
):
    """Queue a D-ASI swarm pipeline execution. Returns HTTP 202 immediately.

    Pipeline (runs in background):
      1. orchestrator_router   — deconstruct directive into technical task list
      2. context_distiller     — semantic compression to explicit variables/states
      3. execution_unit        — synthesise production-ready code/config artifact
      4. adversarial_critic    — structural completeness + policy compliance check

    Each stage output is stored in the job's matrix_context (DB-backed).
    Security policies enforce zero-placeholder output; violations trigger
    abort_and_recompile (max 3 attempts per stage).

    Poll GET /api/dasi/jobs/{job_id} until status → 'SUCCESS_STABLE' or 'FAILED'.
    Retrieve the final artifact at GET /api/dasi/jobs/{job_id}/result.
    """
    manifest = engine.load_manifest()
    if not manifest:
        raise HTTPException(
            status_code=503,
            detail=(
                "agent_manifest.yaml not found or empty. "
                "Ensure it is present at /app/agent_manifest.yaml or the path "
                "specified by DASI_MANIFEST_PATH."
            ),
        )
    hf_token_set = bool(
        os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    )
    if not hf_token_set:
        raise HTTPException(
            status_code=503,
            detail=(
                "HF inference token not configured. "
                "Set HF_TOKEN or HUGGINGFACE_API_KEY in the server environment."
            ),
        )

    job = await engine.create_job(db, directive=req.directive.strip())
    background.add_task(_run_pipeline_bg, job["job_id"])

    await log_audit_event(
        db,
        "dasi.execute.queued",
        "operator",
        "create",
        "dasi_job",
        job["job_id"],
        metadata={"directive_chars": len(req.directive)},
    )

    return {
        "job_id": job["job_id"],
        "status": "pending",
        "directive_chars": len(req.directive),
        "poll_url": f"/api/dasi/jobs/{job['job_id']}",
        "result_url": f"/api/dasi/jobs/{job['job_id']}/result",
    }


@router.get("/matrix/telemetry")
async def matrix_telemetry(limit: int = 30, db=Depends(get_db)):
    """List recent D-ASI swarm jobs (newest first). Default: last 30 runs."""
    return await engine.list_jobs(db, limit=min(int(limit), 200))


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, db=Depends(get_db)):
    """Poll a specific swarm job.

    Returns status, current_step, matrix_context snapshot, telemetry log,
    and audit_log. Poll until status is 'SUCCESS_STABLE', 'FAILED', or
    'HALTED_ON_SECURITY_VIOLATION'.
    """
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    # Strip audit_log from standard poll response — it can be large
    job_summary = {k: v for k, v in job.items() if k != "audit_log"}
    return job_summary


@router.get("/jobs/{job_id}/audit")
async def get_job_audit(job_id: str, db=Depends(get_db)):
    """Return the full append-only audit log for a job (all stage events)."""
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {
        "job_id": job_id,
        "audit_log": job.get("audit_log", []),
    }


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str, db=Depends(get_db)):
    """Return the final validated artifact as plain text.

    Only available when status is 'SUCCESS_STABLE'.
    """
    job = await engine.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    if job.get("status") != "SUCCESS_STABLE":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Job status is '{job.get('status')}' — result not yet available. "
                f"Poll GET /api/dasi/jobs/{job_id} and retry when status='SUCCESS_STABLE'."
            ),
        )
    result = job.get("result", "")
    if not result:
        raise HTTPException(
            status_code=409,
            detail="Job completed but result is empty — check audit log.",
        )
    return PlainTextResponse(content=result, media_type="text/plain; charset=utf-8")


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, db=Depends(get_db)):
    """Purge a job record from the database (does not affect deployed artifacts)."""
    job = await engine.get_job(db, job_id)
    if not job:
        return {"deleted": False, "reason": "not found"}
    await db[engine.JOB_COLLECTION].delete_one({"job_id": job_id})
    return {"deleted": True, "job_id": job_id}
