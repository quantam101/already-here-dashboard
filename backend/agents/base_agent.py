"""
BaseAgent — Abstract foundation for every sub-agent in the governance layer.

Provides:
  • Declarative identity (id, name, capabilities)
  • Typed AgentResult contract
  • Circuit-breaker (fail-fast after N consecutive errors, reset after TTL)
  • Mandatory audit trail: every run is logged to `agent_runs` collection
  • Budget enforcement hook (`check_budget` — override to add LLM pre-checks)
  • Async-safe `run(db, ctx)` entrypoint → implementors override `execute(db, ctx)`
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

from fastapi import HTTPException

logger = logging.getLogger("base_agent")

AGENT_RUNS_COLLECTION = "agent_runs"


class AgentResult:
    """Typed return value from every agent run."""
    __slots__ = ("agent_id", "run_id", "success", "data", "error",
                 "tokens_used", "duration_ms", "started_at", "completed_at")

    def __init__(
        self,
        agent_id: str,
        run_id: str,
        *,
        success: bool,
        data: dict | None = None,
        error: str | None = None,
        tokens_used: int = 0,
        duration_ms: int = 0,
        started_at: str = "",
        completed_at: str = "",
    ):
        self.agent_id = agent_id
        self.run_id = run_id
        self.success = success
        self.data = data or {}
        self.error = error
        self.tokens_used = tokens_used
        self.duration_ms = duration_ms
        self.started_at = started_at
        self.completed_at = completed_at

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


class CircuitBreaker:
    """Per-agent 3-failure open / 900s reset circuit breaker."""

    def __init__(self, agent_id: str, threshold: int = 3, reset_seconds: float = 900.0):
        self.agent_id = agent_id
        self.threshold = threshold
        self.reset_seconds = reset_seconds
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.reset_seconds:
            self._failures = 0
            self._opened_at = None
            logger.info("circuit-breaker RESET for %s", self.agent_id)
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = time.monotonic()
            logger.warning(
                "circuit-breaker OPEN for %s (%d failures)", self.agent_id, self._failures
            )

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "failures": self._failures,
            "is_open": self.is_open,
            "threshold": self.threshold,
            "reset_seconds": self.reset_seconds,
        }


class BaseAgent(ABC):
    """Abstract agent base. Subclass and implement `execute(db, ctx) -> dict`."""

    # Subclasses declare these at class level
    agent_id: str = "base"
    agent_name: str = "Base Agent"
    capabilities: list[str] = []
    budget_tokens: int = 0
    timeout_seconds: float = 60.0

    def __init__(self):
        self._cb = CircuitBreaker(self.agent_id)

    # ── Public entrypoint ──────────────────────────────────────────────────────

    async def run(self, db, ctx: dict | None = None) -> AgentResult:
        """Run the agent with full safety wrapping: circuit-breaker, timeout, audit."""
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        started = datetime.now(UTC)
        start_mono = time.monotonic()
        ctx = ctx or {}

        # Circuit-breaker gate
        if self._cb.is_open:
            result = AgentResult(
                self.agent_id, run_id,
                success=False,
                error="circuit-breaker open — too many recent failures",
                started_at=started.isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
            )
            await self._persist_run(db, result)
            return result

        try:
            # Budget pre-check
            await self.check_budget(db)

            # Timeout wrapper
            data = await asyncio.wait_for(
                self.execute(db, ctx), timeout=self.timeout_seconds
            )
            completed = datetime.now(UTC)
            self._cb.record_success()
            result = AgentResult(
                self.agent_id, run_id,
                success=True,
                data=data or {},
                tokens_used=data.get("_tokens_used", 0) if isinstance(data, dict) else 0,
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                started_at=started.isoformat(),
                completed_at=completed.isoformat(),
            )
        except TimeoutError:
            self._cb.record_failure()
            result = AgentResult(
                self.agent_id, run_id, success=False,
                error=f"timeout after {self.timeout_seconds}s",
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                started_at=started.isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
            )
        except HTTPException as exc:
            # Budget / auth errors — record but don't open circuit
            result = AgentResult(
                self.agent_id, run_id, success=False,
                error=f"HTTP {exc.status_code}: {exc.detail}",
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                started_at=started.isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
            )
        except Exception as exc:  # noqa: BLE001
            self._cb.record_failure()
            logger.exception("agent %s run %s failed", self.agent_id, run_id)
            result = AgentResult(
                self.agent_id, run_id, success=False,
                error=str(exc),
                duration_ms=int((time.monotonic() - start_mono) * 1000),
                started_at=started.isoformat(),
                completed_at=datetime.now(UTC).isoformat(),
            )

        await self._persist_run(db, result)
        return result

    # ── Override in subclasses ─────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, db, ctx: dict) -> dict:
        """Agent logic. Return a dict payload; include `_tokens_used` if applicable."""
        ...

    async def check_budget(self, db) -> None:  # noqa: B027
        """Override to add LLM budget pre-check. Default: no-op."""

    # ── Internals ──────────────────────────────────────────────────────────────

    async def _persist_run(self, db, result: AgentResult) -> None:
        """Best-effort: write run record to agent_runs collection."""
        try:
            doc = {
                "id": result.run_id,
                **result.to_dict(),
                "agent_name": self.agent_name,
                "capabilities": self.capabilities,
            }
            await db[AGENT_RUNS_COLLECTION].insert_one(doc)
        except Exception as e:
            logger.warning("agent run persist failed: %s", e)

    @property
    def circuit_breaker_status(self) -> dict:
        return self._cb.to_dict()
