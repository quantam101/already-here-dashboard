"""
Sovereign API — REST endpoints for the governing AI layer.

GET  /api/sovereign/status        — Last decision + agent health overview
GET  /api/sovereign/history       — Last N decisions (audit trail)
POST /api/sovereign/trigger       — Manually trigger one sovereign cycle now
GET  /api/sovereign/agents        — Registered agent registry + circuit-breaker status
DELETE /api/sovereign/cache       — Clear LLM decision cache (force fresh reasoning)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import logging

logger = logging.getLogger("sovereign_route")

router = APIRouter()

SOVEREIGN_COLLECTION = "sovereign_decisions"
AGENT_RUNS_COLLECTION = "agent_runs"


async def get_db():
    from server import db
    return db


@router.get("/status")
async def sovereign_status(db=Depends(get_db)):
    """Return the most recent sovereign decision plus per-agent health."""
    last_decision = await db[SOVEREIGN_COLLECTION].find_one(
        {}, {"_id": 0}, sort=[("made_at", -1)]
    )
    # Per-agent last-run status
    agent_ids = ["guard-agent", "scout-agent", "content-agent", "revenue-agent"]
    agent_status = {}
    for aid in agent_ids:
        last_run = await db[AGENT_RUNS_COLLECTION].find_one(
            {"agent_id": aid}, {"_id": 0},
            sort=[("started_at", -1)],
        )
        agent_status[aid] = {
            "last_run": last_run.get("started_at") if last_run else None,
            "last_success": last_run.get("success") if last_run else None,
            "last_error": last_run.get("error") if last_run else None,
            "duration_ms": last_run.get("duration_ms") if last_run else None,
        }

    return {
        "sovereign": last_decision or {"status": "no_decisions_yet"},
        "agents": agent_status,
    }


@router.get("/history")
async def sovereign_history(limit: int = 20, db=Depends(get_db)):
    """Return last N sovereign decisions (audit trail)."""
    decisions = await db[SOVEREIGN_COLLECTION].find(
        {}, {"_id": 0}
    ).sort("made_at", -1).to_list(min(limit, 100))
    return {"decisions": decisions, "count": len(decisions)}


@router.post("/trigger")
async def trigger_sovereign_cycle(db=Depends(get_db)):
    """Manually trigger one full sovereign cycle (decision + agent dispatch)."""
    from services.sovereign_agent import make_decision
    from services.agent_executor import AgentExecutor, AGENT_REGISTRY

    decision = await make_decision(db, list(AGENT_REGISTRY.keys()))
    if decision.skip_reason:
        return {
            "status": "skipped",
            "skip_reason": decision.skip_reason,
            "decision_id": decision.decision_id,
        }

    executor = AgentExecutor()
    report = await executor.run(db, decision.agents_to_run)
    return {
        "status": "completed",
        "decision_id": decision.decision_id,
        "priority_action": decision.priority_action,
        "agents_dispatched": decision.agents_to_run,
        "execution": report.to_dict(),
    }


@router.get("/agents")
async def list_agent_registry():
    """Return the registered agent registry (class paths and IDs)."""
    from services.agent_executor import AGENT_REGISTRY
    return {"agents": AGENT_REGISTRY}


@router.delete("/cache")
async def clear_sovereign_cache(db=Depends(get_db)):
    """Wipe sovereign decision cache (forces fresh LLM reasoning next cycle)."""
    from services.distillation_service import cache_clear
    from services.sovereign_agent import SOVEREIGN_SYSTEM
    # Only clear entries matching sovereign system prompt fingerprint
    n = await cache_clear(db)
    return {"cleared": n, "note": "Next Cash cycle will call LLM fresh."}