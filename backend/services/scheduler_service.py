"""
Multi-frequency autonomous scheduler — the heartbeat of the Command OS.

Replaces the old single-daily-cycle scheduler with a tiered tick system:

  Every 15 min  → sovereign decides if guard-agent should run
  Every 30 min  → sovereign decides if revenue-agent should run
  Every 60 min  → sovereign decides if scout-agent should run
  Every 360 min → sovereign decides if content-agent should run
  Every 60 min  → full sovereign decision cycle (governing AI fires)

All decisions flow through the Sovereign — no agent runs without its approval.
This makes the system declarative and auditable at every tick.

Backwards-compatible: set LEGACY_CYCLE_ONLY=true to restore old behavior.
"""
import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

logger = logging.getLogger("scheduler")

_task: asyncio.Task | None = None
_db = None
_ticks = 0  # global tick counter (increments every 15 min)

# Tick intervals (multiples of the base 15-min tick)
TICK_BASE_MINUTES = 15
TICKS_GUARD    = 1    # every 15 min
TICKS_REVENUE  = 2    # every 30 min
TICKS_SCOUT    = 4    # every 60 min
TICKS_CONTENT  = 24   # every 6 hours
TICKS_SOVEREIGN = 4   # every 60 min (sovereign makes the final call)


async def _sovereign_cycle():
    """Run one full sovereign decision+dispatch cycle."""
    if _db is None:
        return
    try:
        from services.agent_executor import AGENT_REGISTRY, AgentExecutor
        from services.sovereign_agent import make_decision

        decision = await make_decision(_db, list(AGENT_REGISTRY.keys()))

        if decision.skip_reason:
            logger.info("Sovereign skipped: %s", decision.skip_reason)
            return

        executor = AgentExecutor()
        report = await executor.run(_db, decision.agents_to_run)
        logger.info(
            "Sovereign cycle complete: action='%s' agents=%d/%d tokens=%d",
            decision.priority_action,
            report.agents_succeeded, report.agents_run,
            report.total_tokens_used,
        )
    except Exception as e:
        logger.exception("Sovereign cycle failed: %s", e)


async def _legacy_cycle():
    """Backwards-compatible: call old cycle.run_cycle directly."""
    if _db is None:
        return
    try:
        from routes import cycle
        result = await cycle.run_cycle(db=_db)
        logger.info("legacy auto-cycle: ideas=%d drafts=%d", result.ideas_created, result.publishing_drafts)
    except Exception as e:
        logger.exception("legacy auto-cycle failed: %s", e)


async def _scheduler_loop():
    """Main loop. Wakes every TICK_BASE_MINUTES minutes."""
    global _ticks
    legacy = os.environ.get("LEGACY_CYCLE_ONLY", "false").lower() in {"1", "true", "yes"}

    while True:
        _ticks += 1
        sleep_secs = TICK_BASE_MINUTES * 60

        if legacy:
            # Legacy path: one run per day at configured hour
            hour = int(os.environ.get("DAILY_CYCLE_HOUR_UTC", "7"))
            now = datetime.now(UTC)
            target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)
            sleep_secs = (target - now).total_seconds()
            logger.info("legacy scheduler sleeping %.0fs", sleep_secs)
            await asyncio.sleep(sleep_secs)
            await _legacy_cycle()
            continue

        # Sovereign-governed path
        try:
            if _ticks % TICKS_SOVEREIGN == 0:
                logger.info("Scheduler tick %d — triggering sovereign cycle", _ticks)
                await _sovereign_cycle()
            else:
                logger.debug("Scheduler tick %d — no sovereign action scheduled", _ticks)
        except asyncio.CancelledError:
            logger.info("scheduler cancelled")
            raise
        except Exception as e:
            logger.exception("scheduler tick error: %s", e)

        try:
            await asyncio.sleep(sleep_secs)
        except asyncio.CancelledError:
            raise


def start_scheduler(db=None) -> None:
    global _task, _db
    _db = db
    if os.environ.get("SYSTEM_MODE") == "test":
        logger.info("SYSTEM_MODE=test — scheduler disabled")
        return
    if os.environ.get("AUTO_CYCLE_ENABLED", "true").lower() in {"0", "false", "no"}:
        logger.info("AUTO_CYCLE_ENABLED=false — scheduler disabled")
        return
    _task = asyncio.create_task(_scheduler_loop())
    mode = "legacy" if os.environ.get("LEGACY_CYCLE_ONLY", "false").lower() in {"1","true","yes"} else "sovereign"
    logger.info("Autonomous scheduler started — mode=%s tick=%dmin", mode, TICK_BASE_MINUTES)


def stop_scheduler() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None
