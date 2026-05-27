"""
AgentExecutor — Parallel multi-agent dispatcher with per-agent timeouts.

Responsibilities:
  • Load agent instances from registered class registry
  • Run selected agents concurrently (asyncio.gather with return_exceptions)
  • Collect AgentResults, log failures, never let one failure stop others
  • Respect agent priority ordering (guard always first, then parallel batch)
  • Return ExecutionReport — consumed by sovereign and /sovereign/status API

Usage:
    from services.agent_executor import AgentExecutor
    executor = AgentExecutor()
    report = await executor.run(db, agent_ids=["guard-agent", "scout-agent"])
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from agents.base_agent import AgentResult, BaseAgent

logger = logging.getLogger("agent_executor")

# ── Registry: maps agent_id → class (lazy import avoids circular imports) ─────
AGENT_REGISTRY: dict[str, str] = {
    "guard-agent":   "agents.guard_agent.GuardAgent",
    "scout-agent":   "agents.scout_agent.ScoutAgent",
    "content-agent": "agents.content_agent.ContentAgent",
    "revenue-agent": "agents.revenue_agent.RevenueAgent",
}

# Agents that must run BEFORE the parallel batch (ordered by priority ASC)
SEQUENTIAL_PRIORITY_AGENTS = ["guard-agent"]


class ExecutionReport:
    """Summary returned after a multi-agent run."""

    def __init__(self, results: list[AgentResult], duration_ms: int):
        self.results = results
        self.duration_ms = duration_ms
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.agents_run = len(results)
        self.agents_succeeded = sum(1 for r in results if r.success)
        self.agents_failed = self.agents_run - self.agents_succeeded
        self.total_tokens_used = sum(r.tokens_used for r in results)

    def to_dict(self) -> dict:
        return {
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "agents_run": self.agents_run,
            "agents_succeeded": self.agents_succeeded,
            "agents_failed": self.agents_failed,
            "total_tokens_used": self.total_tokens_used,
            "results": [r.to_dict() for r in self.results],
        }


def _load_agent(agent_id: str) -> BaseAgent | None:
    """Instantiate an agent from the registry by importing its class path."""
    class_path = AGENT_REGISTRY.get(agent_id)
    if not class_path:
        logger.warning("agent_executor: unknown agent_id '%s'", agent_id)
        return None
    module_path, class_name = class_path.rsplit(".", 1)
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        return cls()
    except Exception as e:
        logger.error("agent_executor: failed to load %s: %s", class_path, e)
        return None


class AgentExecutor:
    """Runs a set of agents: sequential priority agents first, then parallel batch."""

    async def run(
        self,
        db,
        agent_ids: list[str],
        ctx: dict | None = None,
    ) -> ExecutionReport:
        ctx = ctx or {}
        t0 = time.monotonic()
        results: list[AgentResult] = []

        # Split into sequential (high-priority) and parallel
        sequential = [aid for aid in SEQUENTIAL_PRIORITY_AGENTS if aid in agent_ids]
        parallel = [aid for aid in agent_ids if aid not in sequential]

        # Sequential batch (guard-agent always first)
        for agent_id in sequential:
            agent = _load_agent(agent_id)
            if agent:
                result = await agent.run(db, ctx)
                results.append(result)
                # Update ctx with guard output for downstream agents
                if result.success and result.data:
                    ctx["guard"] = result.data

        # Parallel batch
        if parallel:
            tasks = []
            agent_instances = []
            for agent_id in parallel:
                agent = _load_agent(agent_id)
                if agent:
                    agent_instances.append(agent)
                    tasks.append(agent.run(db, dict(ctx)))  # each gets its own ctx copy

            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, raw in enumerate(raw_results):
                if isinstance(raw, Exception):
                    agent_id = parallel[i] if i < len(parallel) else "unknown"
                    logger.error("agent %s raised unhandled exception: %s", agent_id, raw)
                    results.append(AgentResult(
                        agent_id, f"run-err-{i}",
                        success=False, error=str(raw),
                    ))
                else:
                    results.append(raw)

        duration_ms = int((time.monotonic() - t0) * 1000)
        report = ExecutionReport(results, duration_ms)
        logger.info(
            "AgentExecutor: %d/%d succeeded in %dms, tokens=%d",
            report.agents_succeeded, report.agents_run,
            duration_ms, report.total_tokens_used,
        )
        return report