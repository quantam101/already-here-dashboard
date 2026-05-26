"""
Lightweight in-process daily auto-cycle scheduler.

Runs `/api/cycle/run` once every 24h (configurable via DAILY_CYCLE_HOUR_UTC env).
Skipped when SYSTEM_MODE=test to avoid noise in pytest.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("scheduler")

_task: asyncio.Task | None = None


async def _seconds_until_next_run(target_hour: int) -> float:
    now = datetime.now(timezone.utc)
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _run_cycle_safely():
    """Call the cycle.run_cycle function directly (no HTTP roundtrip)."""
    try:
        from routes import cycle
        from server import db
        result = await cycle.run_cycle(db=db)
        logger.info(
            "auto-cycle complete: ideas=%s drafts=%s cycle_id=%s",
            result.ideas_created, result.publishing_drafts, result.cycle_id,
        )
    except Exception as e:
        logger.exception("auto-cycle failed: %s", e)


async def _scheduler_loop(target_hour: int):
    while True:
        try:
            sleep_s = await _seconds_until_next_run(target_hour)
            logger.info("auto-cycle sleeping %.0fs until %sUTC", sleep_s, target_hour)
            await asyncio.sleep(sleep_s)
            await _run_cycle_safely()
        except asyncio.CancelledError:
            logger.info("scheduler cancelled")
            raise
        except Exception as e:
            logger.exception("scheduler loop error: %s", e)
            await asyncio.sleep(60)


def start_scheduler() -> None:
    """Kick off the background task on app startup."""
    global _task
    if os.environ.get("SYSTEM_MODE") == "test":
        logger.info("SYSTEM_MODE=test - scheduler disabled")
        return
    if os.environ.get("AUTO_CYCLE_ENABLED", "true").lower() in {"0", "false", "no"}:
        logger.info("AUTO_CYCLE_ENABLED=false - scheduler disabled")
        return
    hour = int(os.environ.get("DAILY_CYCLE_HOUR_UTC", "7"))
    _task = asyncio.create_task(_scheduler_loop(hour))
    logger.info("auto-cycle scheduler started (daily at %02d:00 UTC)", hour)


def stop_scheduler() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
    _task = None
