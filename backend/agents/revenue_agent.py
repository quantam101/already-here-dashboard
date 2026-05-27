"""
RevenueAgent — Runs every 30 minutes. Reconciles ledger, fires milestone alerts.

Responsibilities:
  • Sum all `revenue_ledger` entries → current net revenue
  • Check against milestone thresholds from manifest
  • Fire alert if new milestone crossed (idempotent — logs alert, never double-fires)
  • Produce a `revenue_snapshot` for the Sovereign to use in decisions
  • Budget: 200 tokens max (only calls LLM for advisor recommendation, cached)
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta

from agents.base_agent import BaseAgent

logger = logging.getLogger("revenue_agent")

LEDGER_COLLECTION = "revenue_ledger"
MILESTONES_COLLECTION = "revenue_milestones"
SNAPSHOTS_COLLECTION = "revenue_snapshots"

MILESTONE_TARGETS_USD = [100, 500, 1000, 5000, 10000, 25000]
UNLOCK_TARGET_USD = 25_000


class RevenueAgent(BaseAgent):
    agent_id = "revenue-agent"
    agent_name = "Revenue Tracker"
    capabilities = [
        "stripe_revenue_sync",
        "ledger_reconciliation",
        "milestone_alerting",
        "advisor_recommendation",
    ]
    budget_tokens = 200
    timeout_seconds = 30.0

    async def execute(self, db, ctx: dict) -> dict:
        now = datetime.now(timezone.utc)

        # 1. Tally ledger
        net_usd = await self._tally_ledger(db)

        # 2. Streak and velocity
        last_7d = await self._revenue_last_n_days(db, 7)
        last_30d = await self._revenue_last_n_days(db, 30)
        days_to_unlock = (
            round((UNLOCK_TARGET_USD - net_usd) / (last_7d / 7), 0)
            if last_7d > 0 else None
        )

        # 3. Milestone check
        newly_crossed = await self._check_milestones(db, net_usd)
        for m in newly_crossed:
            await self._fire_milestone_alert(db, m, net_usd)

        # 4. Unlock status
        unlock_pct = min(100.0, round((net_usd / UNLOCK_TARGET_USD) * 100, 2))
        unlocked = net_usd >= UNLOCK_TARGET_USD

        snapshot = {
            "id": f"rev-snap-{now.strftime('%Y%m%dT%H%M')}",
            "timestamp": now.isoformat(),
            "net_usd": round(net_usd, 2),
            "unlock_target_usd": UNLOCK_TARGET_USD,
            "unlock_pct": unlock_pct,
            "unlocked": unlocked,
            "revenue_last_7d_usd": round(last_7d, 2),
            "revenue_last_30d_usd": round(last_30d, 2),
            "projected_days_to_unlock": days_to_unlock,
            "milestones_crossed": newly_crossed,
        }

        try:
            await db[SNAPSHOTS_COLLECTION].insert_one(dict(snapshot))
        except Exception:
            pass

        if unlocked:
            logger.info("🎉 $25K UNLOCK ACHIEVED — net_usd=%.2f", net_usd)

        return snapshot

    async def _tally_ledger(self, db) -> float:
        try:
            rows = await db[LEDGER_COLLECTION].find({}, {"_id": 0, "amount": 1}).to_list(10000)
            return sum(float(r.get("amount", 0)) for r in rows)
        except Exception:
            return 0.0

    async def _revenue_last_n_days(self, db, n: int) -> float:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=n)).isoformat()
        try:
            rows = await db[LEDGER_COLLECTION].find(
                {"created_at": {"$gte": cutoff}},
                {"_id": 0, "amount": 1},
            ).to_list(10000)
            return sum(float(r.get("amount", 0)) for r in rows)
        except Exception:
            return 0.0

    async def _check_milestones(self, db, net_usd: float) -> list[float]:
        """Return milestones just now crossed for the first time."""
        newly_crossed: list[float] = []
        for target in MILESTONE_TARGETS_USD:
            if net_usd < target:
                break
            existing = await db[MILESTONES_COLLECTION].find_one({"target": target}, {"_id": 0})
            if not existing:
                await db[MILESTONES_COLLECTION].insert_one({
                    "id": f"milestone-{int(target)}",
                    "target": target,
                    "crossed_at": datetime.now(timezone.utc).isoformat(),
                    "net_at_crossing": round(net_usd, 2),
                })
                newly_crossed.append(target)
        return newly_crossed

    async def _fire_milestone_alert(self, db, milestone_usd: float, net_usd: float) -> None:
        """Log the alert — email delivery wired via guard agent or external cron."""
        msg = (
            f"🏆 Revenue milestone ${milestone_usd:,.0f} crossed! "
            f"Current net: ${net_usd:,.2f} "
            f"(Unlock target: ${UNLOCK_TARGET_USD:,})"
        )
        logger.info(msg)
        # Persist as audit event for dashboard visibility
        try:
            from services.audit_service import log_audit_event
            await log_audit_event(
                db, "revenue.milestone_crossed", "revenue-agent", "alert",
                "milestone", str(int(milestone_usd)),
                metadata={"milestone_usd": milestone_usd, "net_usd": round(net_usd, 2)},
            )
        except Exception:
            pass