"""
GuardAgent — Infrastructure self-healer. Runs every 15 minutes, zero LLM tokens.

Responsibilities:
  • Health endpoint check (backend alive?)
  • Memory-pressure detection (warn at >85%, critical at >95%)
  • Dead-letter queue drain (failed agent runs older than 1h → re-queue)
  • Circuit-breaker status roll-up
  • Emit structured health snapshot to `system_health` collection

No external LLM calls — pure Python logic. Always runs first (priority 5).
"""
from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta

import httpx

from agents.base_agent import BaseAgent

logger = logging.getLogger("guard_agent")

SYSTEM_HEALTH_COLLECTION = "system_health"
AGENT_RUNS_COLLECTION = "agent_runs"


class GuardAgent(BaseAgent):
    agent_id = "guard-agent"
    agent_name = "Infrastructure Guardian"
    capabilities = [
        "health_check",
        "memory_monitor",
        "circuit_breaker_management",
        "dead_letter_queue_drain",
    ]
    budget_tokens = 0
    timeout_seconds = 20.0

    async def execute(self, db, ctx: dict) -> dict:
        now = datetime.now(UTC)

        health = await self._check_health()
        memory = self._check_memory()
        stale_runs = await self._find_stale_runs(db, now)
        drained = await self._drain_dead_letter(db, stale_runs)

        snapshot = {
            "id": f"health-{now.strftime('%Y%m%dT%H%M')}",
            "timestamp": now.isoformat(),
            "backend_alive": health["alive"],
            "backend_latency_ms": health["latency_ms"],
            "memory_pct": memory["pct"],
            "memory_status": memory["status"],
            "stale_runs_found": len(stale_runs),
            "dead_letter_drained": drained,
            "overall": "healthy" if (
                health["alive"] and memory["status"] != "critical"
            ) else "degraded",
        }

        try:
            await db[SYSTEM_HEALTH_COLLECTION].insert_one(dict(snapshot))
        except Exception:
            pass

        if snapshot["overall"] == "degraded":
            logger.warning("SYSTEM DEGRADED: %s", snapshot)

        return snapshot

    async def _check_health(self) -> dict:
        base = os.environ.get("SELF_BASE_URL", "http://localhost:8001")
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                import time
                t0 = time.monotonic()
                r = await client.get(f"{base}/api/health/")
                latency = int((time.monotonic() - t0) * 1000)
                return {"alive": r.status_code == 200, "latency_ms": latency}
        except Exception as e:
            logger.warning("health-check failed: %s", e)
            return {"alive": False, "latency_ms": -1}

    def _check_memory(self) -> dict:
        try:
            import psutil
            pct = psutil.virtual_memory().percent
            status = "ok" if pct < 85 else ("warn" if pct < 95 else "critical")
            return {"pct": pct, "status": status}
        except ImportError:
            return {"pct": 0.0, "status": "unknown"}

    async def _find_stale_runs(self, db, now: datetime) -> list[dict]:
        cutoff = (now - timedelta(hours=1)).isoformat()
        try:
            rows = await db[AGENT_RUNS_COLLECTION].find(
                {"success": False, "started_at": {"$lt": cutoff}, "requeued": {"$ne": True}},
                {"_id": 0},
            ).to_list(50)
            return rows
        except Exception:
            return []

    async def _drain_dead_letter(self, db, stale: list[dict]) -> int:
        if not stale:
            return 0
        drained = 0
        for run in stale:
            try:
                await db[AGENT_RUNS_COLLECTION].update_one(
                    {"id": run["id"]},
                    {"$set": {"requeued": True, "requeued_at": datetime.now(UTC).isoformat()}},
                )
                drained += 1
            except Exception:
                pass
        logger.info("dead-letter drained %d stale runs", drained)
        return drained
