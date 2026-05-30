"""
D-ASI v4.0.0-ENTERPRISE — Hugging Face Spaces entry point.

Standalone FastAPI app with JSON-file-backed job store (no MongoDB required).
Runs on port 7860 as a single uvicorn worker (--workers 1) under UID 1000
(kernel_worker) — required for HF Spaces container constraints.

Job persistence: /app/data/dasi_jobs/ — one JSON file per job.
Each file is written atomically via a temp-file + os.replace() to prevent
partial reads during concurrent background-task writes.

Usage:
  uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("dasi.spaces")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MANIFEST_PATH = Path(os.environ.get("DASI_MANIFEST_PATH", "/app/agent_manifest.yaml"))
JOBS_DIR = Path(os.environ.get("DASI_JOBS_DIR", "/app/data/dasi_jobs"))
PORT = int(os.environ.get("PORT", 7860))

_MANIFEST_CACHE: dict | None = None


def load_manifest() -> dict:
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    candidates = [
        MANIFEST_PATH,
        Path(__file__).parent / "agent_manifest.yaml",
        Path("agent_manifest.yaml"),
    ]
    for p in candidates:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                _MANIFEST_CACHE = yaml.safe_load(f) or {}
            logger.info("Manifest loaded from %s", p)
            return _MANIFEST_CACHE
    logger.error("agent_manifest.yaml not found")
    _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


# ---------------------------------------------------------------------------
# Pre-compiled security policies
# ---------------------------------------------------------------------------

class PolicyPattern:
    __slots__ = ("policy_id", "pattern", "action")

    def __init__(self, policy_id: str, raw_regex: str, action: str) -> None:
        self.policy_id: str = policy_id
        self.pattern: re.Pattern = re.compile(raw_regex, re.IGNORECASE)
        self.action: str = action

    def violates(self, text: str) -> bool:
        return bool(self.pattern.search(text))


def _build_policies(manifest: dict) -> list[PolicyPattern]:
    return [
        PolicyPattern(
            policy_id=p["id"],
            raw_regex=p["regex_pattern"],
            action=p.get("enforcement_action", "abort_and_recompile"),
        )
        for p in manifest.get("security_policies", [])
        if "regex_pattern" in p and "id" in p
    ]


# ---------------------------------------------------------------------------
# File-backed job store
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_job_id() -> str:
    return f"dasi-{uuid.uuid4().hex[:10]}"


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _write_job(job: dict) -> None:
    """Atomic write: temp file → os.replace() to prevent torn reads."""
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    target = _job_path(job["job_id"])
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, target)


def _read_job(job_id: str) -> dict | None:
    p = _job_path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _list_jobs(limit: int = 30) -> list[dict]:
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(JOBS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    jobs = []
    for f in files[:limit]:
        try:
            jobs.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return jobs


def create_job(directive: str) -> dict:
    job = {
        "job_id": _new_job_id(),
        "directive": directive,
        "status": "pending",
        "current_step": 0,
        "matrix_context": {"root_directive": directive},
        "telemetry": [],
        "audit_log": [],
        "error": None,
        "result": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    _write_job(job)
    return job


def _update_job(job_id: str, **changes) -> None:
    job = _read_job(job_id)
    if not job:
        return
    job.update(changes)
    job["updated_at"] = _now()
    _write_job(job)


def _append_audit(job_id: str, event: dict) -> None:
    job = _read_job(job_id)
    if not job:
        return
    job.setdefault("audit_log", []).append({**event, "ts": _now()})
    job["updated_at"] = _now()
    _write_job(job)


def _append_telemetry(job_id: str, entry: str) -> None:
    job = _read_job(job_id)
    if not job:
        return
    job.setdefault("telemetry", []).append(entry)
    job["updated_at"] = _now()
    _write_job(job)


def _set_matrix_context(job_id: str, key: str, value: str) -> None:
    job = _read_job(job_id)
    if not job:
        return
    job.setdefault("matrix_context", {})[key] = value
    job["updated_at"] = _now()
    _write_job(job)


# ---------------------------------------------------------------------------
# HF Inference with exponential backoff + structural jitter
# ---------------------------------------------------------------------------

def _get_client():
    try:
        from huggingface_hub import AsyncInferenceClient
    except ImportError as exc:
        raise ImportError("huggingface_hub is required") from exc
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    return AsyncInferenceClient(token=token)


async def _dispatch(
    system_prompt: str,
    user_prompt: str,
    manifest: dict,
    *,
    job_id: str,
    stage_label: str,
) -> str:
    """
    Route inference through primary → fallback chain.
    Delay per attempt k: base^k + Uniform(0, jitter_max)
    """
    ops = manifest.get("operational_profile", {})
    primary = ops.get("primary_llm", "Qwen/Qwen2.5-72B-Instruct")
    fallback = ops.get("fallback_llm", "Qwen/Qwen2.5-72B-Instruct")
    threshold = int(ops.get("circuit_breaker_threshold", 3))
    base = float(ops.get("backoff_base", 2.0))
    jitter_max = float(ops.get("backoff_jitter_max", 1.0))

    client = _get_client()
    chain = ([primary, fallback] + [fallback] * max(0, threshold - 2))[:threshold]

    last_err: Exception | None = None
    for attempt, model in enumerate(chain):
        try:
            logger.info("job=%s stage=%s model=%s attempt=%d", job_id, stage_label, model, attempt + 1)
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=float(ops.get("temperature", 0.1)),
                max_tokens=int(ops.get("max_token_budget", 3072)),
            )
            return resp.choices[0].message.content or ""
        except Exception as exc:
            last_err = exc
            logger.warning("inference failed job=%s stage=%s model=%s: %s", job_id, stage_label, model, exc)
            if attempt < len(chain) - 1:
                delay = (base ** attempt) + random.uniform(0, jitter_max)
                logger.info("backoff %.2fs (attempt %d)", delay, attempt + 1)
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Circuit breaker tripped after {threshold} attempts [{stage_label}]"
    ) from last_err


# ---------------------------------------------------------------------------
# Priority-queue stage runner
# ---------------------------------------------------------------------------

async def _run_pipeline(job_id: str, manifest: dict) -> None:
    """Execute the full 4-stage D-ASI swarm pipeline for one job."""
    agents: dict[str, dict] = {
        a["id"]: a for a in manifest.get("swarm_matrix", {}).get("agents", [])
    }
    policies: list[PolicyPattern] = _build_policies(manifest)
    stages: list[dict] = manifest.get("topology_map", {}).get("execution_sequence", [])

    _update_job(job_id, status="PROCESSING")
    _append_audit(job_id, {
        "event": "PIPELINE_START",
        "stages": len(stages),
        "policies": len(policies),
    })

    # Priority queue — lower step = higher priority
    queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    for stage in stages:
        await queue.put((int(stage.get("step", 99)), stage))

    job = _read_job(job_id)
    active_payload = job["directive"] if job else ""
    final_output = ""

    while not queue.empty():
        _, stage = await queue.get()

        step_num = stage["step"]
        node_id = stage["node"]
        dest_reg = stage["register_destination"]
        agent_cfg = agents.get(node_id)

        if not agent_cfg:
            _update_job(
                job_id,
                status="FAILED",
                error=f"Agent '{node_id}' not found in manifest swarm_matrix",
            )
            return

        system_prompt = (
            agent_cfg["system_prompt"].strip()
            + "\nSTRICT ENFORCEMENT: Output complete, production-ready content. "
              "Zero placeholders, zero truncation, zero omissions."
        )

        # Read current matrix_context snapshot for user prompt
        current_job = _read_job(job_id)
        ctx_snapshot = json.dumps(
            current_job.get("matrix_context", {}) if current_job else {},
            ensure_ascii=False,
        )

        output = ""
        retry_payload = active_payload
        for attempt in range(3):
            output = await _dispatch(
                system_prompt,
                f"[System State Matrix]\n{ctx_snapshot}\n\n[Pipeline Active Payload]\n{retry_payload}",
                manifest=manifest,
                job_id=job_id,
                stage_label=f"step{step_num}/{node_id}",
            )

            violations = [p.policy_id for p in policies if p.violates(output)]
            if not violations:
                break

            logger.warning(
                "job=%s step=%d policy violation: %s (retry %d/3)",
                job_id, step_num, violations, attempt + 1,
            )
            retry_payload = (
                active_payload
                + f"\n\nCRITICAL ENFORCEMENT ERROR: Output violated policies "
                  f"{violations}. Re-output the complete artifact with zero "
                  f"placeholders, abbreviations, or omissions."
            )
            _append_audit(job_id, {
                "event": "POLICY_VIOLATION",
                "step": step_num,
                "node": node_id,
                "violations": violations,
                "attempt": attempt + 1,
            })
        else:
            _update_job(
                job_id,
                status="HALTED_ON_SECURITY_VIOLATION",
                error=(
                    f"Step {step_num} [{node_id}] failed security policy after "
                    f"3 attempts. Violations: {violations}"
                ),
            )
            _append_audit(job_id, {
                "event": "PIPELINE_ABORTED",
                "step": step_num,
                "node": node_id,
                "reason": "Placeholder policy breach — max retries exhausted",
            })
            return

        # Persist stage output into matrix_context
        _set_matrix_context(job_id, dest_reg, output)
        _update_job(job_id, current_step=step_num)
        _append_telemetry(job_id, f"Node [{node_id}] step {step_num} validated.")
        _append_audit(job_id, {
            "event": "STAGE_COMPLETED",
            "step": step_num,
            "node": node_id,
            "status": "PROD_READY",
        })

        active_payload = output
        final_output = output
        queue.task_done()

    _update_job(
        job_id,
        status="SUCCESS_STABLE",
        result=final_output,
        current_step=len(stages),
    )
    _append_audit(job_id, {"event": "PIPELINE_SUCCESS"})
    logger.info("job %s complete (%d chars)", job_id, len(final_output))


async def run_pipeline_bg(job_id: str) -> None:
    """Background task wrapper with top-level error handling."""
    try:
        manifest = load_manifest()
        if not manifest:
            _update_job(
                job_id,
                status="FAILED",
                error="agent_manifest.yaml not found or empty",
            )
            return
        await _run_pipeline(job_id, manifest)
    except Exception as exc:
        logger.exception("pipeline failure job=%s", job_id)
        _update_job(job_id, status="FAILED", error=str(exc)[:500])


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("D-ASI Spaces — jobs dir: %s", JOBS_DIR)
    manifest = load_manifest()
    if manifest:
        logger.info("Manifest v%s loaded — %d agents, %d stages",
                    manifest.get("version", "?"),
                    len(manifest.get("swarm_matrix", {}).get("agents", [])),
                    len(manifest.get("topology_map", {}).get("execution_sequence", [])))
    else:
        logger.warning("Manifest missing — engine will be degraded")
    yield


app = FastAPI(
    title="D-ASI v4.0.0-ENTERPRISE",
    description="Declarative Autonomous Swarm Intelligence — HF Spaces deployment",
    version="4.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    directive: str = Field(..., min_length=1, max_length=8192)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    manifest = load_manifest()
    version = manifest.get("version", "unknown") if manifest else "degraded"
    hf_ok = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY"))
    jobs = _list_jobs(5)
    job_rows = "".join(
        f"<tr><td>{j['job_id']}</td><td>{j['status']}</td>"
        f"<td>{j['current_step']}/4</td><td>{j['created_at'][:19]}</td></tr>"
        for j in jobs
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>D-ASI v{version}</title>
  <style>
    body{{font-family:monospace;background:#0a0f1e;color:#c9d1d9;padding:2rem;max-width:900px;margin:0 auto}}
    h1{{color:#6366f1}}h2{{color:#94a3b8;font-size:.9rem;text-transform:uppercase;letter-spacing:.1em}}
    .badge{{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.75rem;font-weight:bold}}
    .ok{{background:#14532d;color:#4ade80}}.err{{background:#7f1d1d;color:#f87171}}
    table{{width:100%;border-collapse:collapse;margin-top:.5rem}}
    th,td{{text-align:left;padding:.4rem .6rem;border-bottom:1px solid #1e293b;font-size:.8rem}}
    th{{color:#64748b}}
    form{{margin-top:1.5rem}}
    textarea{{width:100%;height:120px;background:#0f172a;border:1px solid #334155;color:#e2e8f0;
      padding:.5rem;border-radius:6px;font-family:monospace;font-size:.85rem}}
    button{{margin-top:.5rem;padding:.4rem 1.2rem;background:#6366f1;color:#fff;border:none;
      border-radius:6px;cursor:pointer;font-size:.85rem}}
    button:hover{{background:#4f46e5}}
    pre{{background:#0f172a;padding:1rem;border-radius:6px;overflow:auto;font-size:.8rem;
      border:1px solid #1e293b;white-space:pre-wrap}}
  </style>
</head>
<body>
  <h1>⚡ D-ASI v{version}</h1>
  <p>Declarative Autonomous Swarm Intelligence — HF Spaces</p>
  <p>
    <span class="badge {'ok' if manifest else 'err'}">
      {'MANIFEST OK' if manifest else 'MANIFEST MISSING'}
    </span>
    &nbsp;
    <span class="badge {'ok' if hf_ok else 'err'}">
      {'HF TOKEN SET' if hf_ok else 'HF TOKEN MISSING'}
    </span>
  </p>

  <h2>Execute Directive</h2>
  <form action="/execute" method="post"
        onsubmit="this.btn.disabled=true;this.btn.textContent='Queuing…'">
    <textarea name="directive"
      placeholder="Enter your production directive here…"></textarea><br/>
    <button name="btn" type="submit">▶ Execute Swarm</button>
  </form>

  <h2 style="margin-top:2rem">Recent Jobs</h2>
  <table>
    <thead><tr><th>Job ID</th><th>Status</th><th>Step</th><th>Created</th></tr></thead>
    <tbody>{job_rows if job_rows else '<tr><td colspan="4" style="color:#475569">No jobs yet</td></tr>'}</tbody>
  </table>

  <h2 style="margin-top:2rem">API</h2>
  <pre>POST /execute          — queue a job (JSON or form)
GET  /jobs             — list recent jobs
GET  /jobs/{{id}}        — poll job status
GET  /jobs/{{id}}/result — download final artifact
GET  /health           — system vitality check
GET  /docs             — OpenAPI UI</pre>
</body>
</html>"""


@app.get("/health")
async def health():
    manifest = load_manifest()
    ops = manifest.get("operational_profile", {}) if manifest else {}
    hf_ok = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY"))
    return {
        "status": "operational" if (manifest and hf_ok) else "degraded",
        "version": manifest.get("version", "unknown") if manifest else "unknown",
        "manifest_loaded": bool(manifest),
        "hf_token_set": hf_ok,
        "primary_llm": ops.get("primary_llm", "not configured"),
        "fallback_llm": ops.get("fallback_llm", "not configured"),
        "agent_count": len(manifest.get("swarm_matrix", {}).get("agents", [])) if manifest else 0,
        "stage_count": len(manifest.get("topology_map", {}).get("execution_sequence", [])) if manifest else 0,
        "policy_count": len(manifest.get("security_policies", [])) if manifest else 0,
        "ready": bool(manifest and hf_ok),
    }


@app.post("/execute", status_code=202)
async def execute(req: ExecuteRequest, background: BackgroundTasks):
    """Queue a D-ASI pipeline. Returns 202 immediately; poll /jobs/{id}."""
    manifest = load_manifest()
    if not manifest:
        raise HTTPException(503, "agent_manifest.yaml missing")
    hf_ok = bool(os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY"))
    if not hf_ok:
        raise HTTPException(503, "HF_TOKEN or HUGGINGFACE_API_KEY not set")

    job = create_job(req.directive.strip())
    background.add_task(run_pipeline_bg, job["job_id"])
    return {
        "job_id": job["job_id"],
        "status": "pending",
        "poll_url": f"/jobs/{job['job_id']}",
        "result_url": f"/jobs/{job['job_id']}/result",
    }


@app.get("/jobs")
async def list_jobs_endpoint(limit: int = 30):
    return _list_jobs(min(limit, 200))


@app.get("/jobs/{job_id}")
async def get_job_endpoint(job_id: str):
    job = _read_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    # Omit full audit_log from polling response
    return {k: v for k, v in job.items() if k != "audit_log"}


@app.get("/jobs/{job_id}/audit")
async def get_job_audit(job_id: str):
    job = _read_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    return {"job_id": job_id, "audit_log": job.get("audit_log", [])}


@app.get("/jobs/{job_id}/result")
async def get_result(job_id: str):
    job = _read_job(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' not found")
    if job.get("status") != "SUCCESS_STABLE":
        raise HTTPException(
            409,
            f"Job status is '{job.get('status')}'. "
            f"Poll /jobs/{job_id} until status='SUCCESS_STABLE'.",
        )
    result = job.get("result") or ""
    if not result:
        raise HTTPException(409, "Job complete but result is empty — check audit log")
    return PlainTextResponse(result, media_type="text/plain; charset=utf-8")


@app.delete("/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    p = _job_path(job_id)
    if not p.exists():
        return {"deleted": False, "reason": "not found"}
    p.unlink(missing_ok=True)
    return {"deleted": True, "job_id": job_id}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        workers=1,          # CRITICAL: single worker — in-memory state isolation
        log_level="info",
    )
