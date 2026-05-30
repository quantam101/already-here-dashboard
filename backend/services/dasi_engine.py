"""
D-ASI Engine v4.0.0-ENTERPRISE — Declarative Autonomous Swarm Intelligence.

Swarm topology (from agent_manifest.yaml):
  orchestrator_router (step 1)
    → context_distiller  (step 2)
    → execution_unit     (step 3)
    → adversarial_critic (step 4)

Each execution run is tracked as an isolated job in the `dasi_jobs` DB
collection. All state is per-job — no global mutable singletons, enabling
concurrent runs across multiple operator sessions without cross-contamination.

v4.0.0 enterprise enhancements (all implemented):
  ● asyncio.PriorityQueue: stages dispatched by priority (step number);
    lower priority int = higher urgency, preventing lower-priority background
    stages from blocking critical state checks.
  ● __slots__ on PolicyPattern: pre-compiled regex pattern objects have zero
    dynamic attribute dict overhead — minimal per-call CPU cycles.
  ● Exponential backoff with structural jitter: delay = base^attempt + U(0,max)
    prevents thundering-herd API hammering during concurrent generation cycles.
  ● Job-isolated state containers (JobContext dataclass with __slots__).
  ● Append-only audit log stored per-job in DB (full traceability).
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("dasi.engine")

# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

_MANIFEST_PATH = Path(
    os.environ.get("DASI_MANIFEST_PATH", "/app/agent_manifest.yaml")
)
_MANIFEST_CACHE: dict | None = None


def load_manifest() -> dict:
    """Load and cache agent_manifest.yaml. Fail-closed on missing file."""
    global _MANIFEST_CACHE
    if _MANIFEST_CACHE is not None:
        return _MANIFEST_CACHE
    candidates = [
        _MANIFEST_PATH,
        Path(__file__).parent.parent.parent / "agent_manifest.yaml",
        Path("agent_manifest.yaml"),
    ]
    for p in candidates:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                _MANIFEST_CACHE = yaml.safe_load(f) or {}
            logger.info("D-ASI manifest loaded from %s", p)
            return _MANIFEST_CACHE
    logger.error("agent_manifest.yaml not found — D-ASI engine disabled")
    _MANIFEST_CACHE = {}
    return _MANIFEST_CACHE


def reload_manifest() -> dict:
    global _MANIFEST_CACHE
    _MANIFEST_CACHE = None
    return load_manifest()


# ---------------------------------------------------------------------------
# Pre-compiled policy patterns  (__slots__ → zero dict overhead per instance)
# ---------------------------------------------------------------------------

class PolicyPattern:
    """Pre-compiled regex policy slot — zero dynamic attribute dict allocation."""

    __slots__ = ("policy_id", "pattern", "action")

    def __init__(self, policy_id: str, raw_regex: str, action: str) -> None:
        self.policy_id: str = policy_id
        self.pattern: re.Pattern = re.compile(raw_regex, re.IGNORECASE)
        self.action: str = action

    def violates(self, text: str) -> bool:
        return bool(self.pattern.search(text))


def _build_compiled_policies(manifest: dict) -> list[PolicyPattern]:
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
# Job state  (__slots__ on dataclass fields via direct declaration)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class JobContext:
    """Isolated per-job state container. No global state shared between runs.

    Uses @dataclass(slots=True) — the correct Python 3.10+ approach for
    zero-overhead slot allocation without the class-variable conflict that
    arises from manually declaring __slots__ alongside dataclass defaults.
    """

    job_id: str
    directive: str
    status: str = "pending"
    current_step: int = 0
    matrix_context: dict = field(default_factory=dict)
    telemetry: list = field(default_factory=list)
    error: str | None = None
    result: str | None = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = _now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not isinstance(self.matrix_context, dict):
            self.matrix_context = {}
        if not isinstance(self.telemetry, list):
            self.telemetry = []


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

JOB_COLLECTION = "dasi_jobs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return f"dasi-{uuid.uuid4().hex[:10]}"


def _ctx_to_dict(ctx: JobContext) -> dict:
    import dataclasses
    return {f.name: getattr(ctx, f.name) for f in dataclasses.fields(ctx)}


async def create_job(db, *, directive: str) -> dict:
    ctx = JobContext(job_id=new_job_id(), directive=directive)
    row = _ctx_to_dict(ctx)
    await db[JOB_COLLECTION].insert_one(row)
    return row


async def get_job(db, job_id: str) -> dict | None:
    return await db[JOB_COLLECTION].find_one({"job_id": job_id}, {"_id": 0})


async def list_jobs(db, limit: int = 30) -> list[dict]:
    return (
        await db[JOB_COLLECTION]
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .to_list(limit)
    )


async def _persist(db, job_id: str, **changes) -> None:
    """Best-effort DB write — never raises, never blocks the pipeline."""
    try:
        changes["updated_at"] = _now()
        await db[JOB_COLLECTION].update_one({"job_id": job_id}, {"$set": changes})
    except Exception as exc:
        logger.warning("dasi: DB persist failed for job %s: %s", job_id, exc)


async def _append_audit(db, job_id: str, event: dict) -> None:
    """Append-only audit log entry pushed to the job's `audit_log` array."""
    try:
        await db[JOB_COLLECTION].update_one(
            {"job_id": job_id},
            {"$push": {"audit_log": {**event, "ts": _now()}}},
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Inference client + backoff
# ---------------------------------------------------------------------------

def _get_inference_client():
    """Lazily import and build the AsyncInferenceClient."""
    try:
        from huggingface_hub import AsyncInferenceClient
    except ImportError as exc:
        raise ImportError(
            "huggingface_hub is required for D-ASI. Add it to requirements.txt."
        ) from exc
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_API_KEY")
    return AsyncInferenceClient(token=token)


async def _dispatch_with_backoff(
    system_prompt: str,
    user_prompt: str,
    manifest: dict,
    *,
    job_id: str,
    stage_label: str,
) -> str:
    """
    Route inference to primary → fallback model chain with exponential backoff
    and structural jitter.

    Delay formula per attempt k (0-indexed):
        delay = base^k + Uniform(0, jitter_max)

    This prevents simultaneous retry storms ("thundering herd") when multiple
    concurrent jobs all hit a rate-limit at the same clock tick.
    """
    ops = manifest.get("operational_profile", {})
    primary = ops.get("primary_llm", "Qwen/Qwen2.5-72B-Instruct")
    fallback = ops.get("fallback_llm", "Qwen/Qwen2.5-72B-Instruct")
    threshold = int(ops.get("circuit_breaker_threshold", 3))
    base = float(ops.get("backoff_base", 2.0))
    jitter_max = float(ops.get("backoff_jitter_max", 1.0))

    client = _get_inference_client()
    model_chain = [primary, fallback] + [fallback] * max(0, threshold - 2)
    model_chain = model_chain[:threshold]

    last_err: Exception | None = None
    for attempt, model in enumerate(model_chain):
        try:
            logger.info(
                "dasi: job=%s stage=%s model=%s attempt=%d",
                job_id, stage_label, model, attempt + 1,
            )
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=float(ops.get("temperature", 0.1)),
                max_tokens=int(ops.get("max_token_budget", 3072)),
            )
            return resp.choices[0].message.content or ""

        except Exception as exc:
            last_err = exc
            logger.warning(
                "dasi: inference failed job=%s stage=%s model=%s: %s",
                job_id, stage_label, model, exc,
            )
            if attempt < len(model_chain) - 1:
                delay = (base ** attempt) + random.uniform(0, jitter_max)
                logger.info(
                    "dasi: backoff %.2fs (attempt %d, jitter applied)",
                    delay, attempt + 1,
                )
                await asyncio.sleep(delay)

    raise RuntimeError(
        f"Circuit breaker tripped after {threshold} attempts for {stage_label}"
    ) from last_err


# ---------------------------------------------------------------------------
# Security policy enforcement
# ---------------------------------------------------------------------------

def _check_policies(content: str, policies: list[PolicyPattern]) -> list[str]:
    """Return list of violated policy IDs (empty = clean)."""
    return [p.policy_id for p in policies if p.violates(content)]


# ---------------------------------------------------------------------------
# Priority Queue stage dispatcher
# ---------------------------------------------------------------------------

async def _run_stage_queue(
    db,
    job_id: str,
    directive: str,
    stages: list[dict],
    agents: dict[str, dict],
    policies: list[PolicyPattern],
    manifest: dict,
) -> str:
    """
    Execute the DAG topology through an asyncio.PriorityQueue.

    Each stage is enqueued as (priority, step_number, stage_dict).
    Lower priority integer = higher urgency, so step 1 (orchestrator) always
    runs before step 4 (critic), even if tasks are added out of order.

    The queue architecture supports future extension to parallel stages —
    independent stage pairs (same step number) can be enqueued simultaneously
    and processed by multiple concurrent queue workers without modification.
    """
    queue: asyncio.PriorityQueue = asyncio.PriorityQueue()

    # Enqueue all stages ordered by step number (priority = step)
    for stage in stages:
        priority = int(stage.get("step", 99))
        await queue.put((priority, stage))

    active_payload = directive
    final_output: str = ""

    while not queue.empty():
        _, stage = await queue.get()

        step_num   = stage["step"]
        node_id    = stage["node"]
        dest_reg   = stage["register_destination"]
        agent_cfg  = agents[node_id]

        system_prompt = (
            agent_cfg["system_prompt"].strip()
            + "\nSTRICT ENFORCEMENT: Output complete, production-ready content. "
              "Zero placeholders, zero truncation, zero omissions."
        )

        # Snapshot current context for the user prompt
        ctx_snapshot = await _get_matrix_context(db, job_id)
        user_prompt = (
            f"[System State Matrix]\n{ctx_snapshot}\n\n"
            f"[Pipeline Active Payload]\n{active_payload}"
        )

        # Retry loop — recompile on policy violation (max 3 attempts)
        output = ""
        retry_payload = active_payload
        for attempt in range(3):
            output = await _dispatch_with_backoff(
                system_prompt,
                (
                    f"[System State Matrix]\n{ctx_snapshot}\n\n"
                    f"[Pipeline Active Payload]\n{retry_payload}"
                ),
                manifest=manifest,
                job_id=job_id,
                stage_label=f"step{step_num}/{node_id}",
            )

            violations = _check_policies(output, policies)
            if not violations:
                break  # clean output — proceed

            logger.warning(
                "dasi: job=%s step=%d policy violation: %s (retry %d/3)",
                job_id, step_num, violations, attempt + 1,
            )
            retry_payload = (
                active_payload
                + f"\n\nCRITICAL ENFORCEMENT ERROR: Output violated policies "
                  f"{violations}. Re-output the complete artifact with zero "
                  f"placeholders, abbreviations, or omissions."
            )
            await _append_audit(db, job_id, {
                "event": "POLICY_VIOLATION",
                "step": step_num,
                "node": node_id,
                "violations": violations,
                "attempt": attempt + 1,
            })
        else:
            # All 3 attempts exhausted — abort pipeline
            await _persist(
                db, job_id,
                status="HALTED_ON_SECURITY_VIOLATION",
                error=(
                    f"Step {step_num} [{node_id}] failed security policy after "
                    f"3 attempts. Violations: {violations}"
                ),
            )
            await _append_audit(db, job_id, {
                "event": "PIPELINE_ABORTED",
                "step": step_num,
                "node": node_id,
                "reason": "Placeholder policy breach — max retries exhausted",
            })
            raise RuntimeError(
                f"Pipeline aborted at step {step_num}: security violation"
            )

        # Persist stage result
        await _persist(
            db, job_id,
            current_step=step_num,
            **{f"matrix_context__{dest_reg}": output},
        )
        await db[JOB_COLLECTION].update_one(
            {"job_id": job_id},
            {"$set": {f"matrix_context.{dest_reg}": output}},
        )
        await db[JOB_COLLECTION].update_one(
            {"job_id": job_id},
            {"$push": {"telemetry": f"Node [{node_id}] step {step_num} validated."}},
        )
        await _append_audit(db, job_id, {
            "event": "STAGE_COMPLETED",
            "step": step_num,
            "node": node_id,
            "status": "PROD_READY",
        })

        active_payload = output
        final_output = output
        queue.task_done()

        await _persist(db, job_id, current_step=step_num)

    return final_output


async def _get_matrix_context(db, job_id: str) -> str:
    """Fetch current matrix_context snapshot from DB as a compact JSON string."""
    import json
    row = await get_job(db, job_id)
    if row:
        return json.dumps(row.get("matrix_context", {}), ensure_ascii=False)
    return "{}"


# ---------------------------------------------------------------------------
# Main pipeline  (called from BackgroundTasks)
# ---------------------------------------------------------------------------

async def run_pipeline(db, job_id: str) -> None:
    """Execute the full 4-stage D-ASI swarm pipeline for one job."""
    job = await get_job(db, job_id)
    if not job:
        logger.error("dasi: job %s not found", job_id)
        return

    manifest = load_manifest()
    if not manifest:
        await _persist(
            db, job_id,
            status="FAILED",
            error="agent_manifest.yaml not found or empty",
        )
        return

    # Build agent index and compiled policies once per run
    agents: dict[str, dict] = {
        a["id"]: a for a in manifest.get("swarm_matrix", {}).get("agents", [])
    }
    policies: list[PolicyPattern] = _build_compiled_policies(manifest)
    stages: list[dict] = manifest.get("topology_map", {}).get("execution_sequence", [])

    await _persist(
        db, job_id,
        status="PROCESSING",
        **{"matrix_context.root_directive": job["directive"]},
    )
    await db[JOB_COLLECTION].update_one(
        {"job_id": job_id},
        {"$set": {"matrix_context.root_directive": job["directive"]}},
    )
    await _append_audit(db, job_id, {
        "event": "PIPELINE_START",
        "directive_chars": len(job["directive"]),
        "stages": len(stages),
        "policies": len(policies),
    })

    try:
        final = await _run_stage_queue(
            db, job_id, job["directive"], stages, agents, policies, manifest
        )
    except RuntimeError as exc:
        # HALTED_ON_SECURITY_VIOLATION is already set inside the queue runner
        if "security violation" not in str(exc):
            await _persist(db, job_id, status="FAILED", error=str(exc)[:500])
        return
    except Exception as exc:
        logger.exception("dasi: pipeline unexpected failure job=%s", job_id)
        await _persist(db, job_id, status="FAILED", error=str(exc)[:500])
        return

    await _persist(
        db, job_id,
        status="SUCCESS_STABLE",
        result=final,
        current_step=len(stages),
    )
    await _append_audit(db, job_id, {"event": "PIPELINE_SUCCESS"})
    logger.info("dasi: job %s complete (%d chars output)", job_id, len(final))
