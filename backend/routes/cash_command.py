"""
Daily Cash Command — Phase 1 Growth Command OS
Routes:
  GET /api/cash-command  — today's summary: pending WOs, revenue this week, action items
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request

log = logging.getLogger(__name__)

router = APIRouter()

_WO_DB_PATH = Path(__file__).parent.parent / "data" / "work_orders.db"


def _wo_conn() -> sqlite3.Connection:
    if not _WO_DB_PATH.exists():
        return None
    conn = sqlite3.connect(str(_WO_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


async def _get_revenue_7d(db) -> float:
    """Pull 7-day revenue from the main DB (MongoDB or SQLite)."""
    try:
        seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        # Try MongoDB-style access first
        if hasattr(db, "revenue_events"):
            cursor = db.revenue_events.find(
                {"created_at": {"$gte": seven_days_ago}},
                {"amount": 1}
            )
            total = 0.0
            async for doc in cursor:
                total += float(doc.get("amount") or 0)
            return total
    except Exception as e:
        log.debug("Revenue 7d query skipped: %s", e)
    return 0.0


def _get_pending_work_orders() -> List[Dict[str, Any]]:
    conn = _wo_conn()
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT * FROM work_orders WHERE status IN ('pending','approved') ORDER BY score DESC LIMIT 20"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def _get_top_opportunities() -> List[Dict[str, Any]]:
    conn = _wo_conn()
    if not conn:
        return []
    try:
        rows = conn.execute(
            "SELECT * FROM work_orders WHERE score >= 50 AND status = 'pending' ORDER BY score DESC LIMIT 5"
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def _build_action_items(pending: List[Dict], revenue_7d: float) -> List[str]:
    actions = []
    strong = [w for w in pending if (w.get("score") or 0) >= 80]
    counteroffer = [w for w in pending if 50 <= (w.get("score") or 0) < 80]
    avoid = [w for w in pending if (w.get("score") or 0) < 50]

    if strong:
        actions.append(f"Review {len(strong)} strong-match work order(s) — ready for approval")
    if counteroffer:
        actions.append(f"Generate counteroffers for {len(counteroffer)} work order(s) with weak rates")
    if avoid:
        actions.append(f"Decline {len(avoid)} low-margin work order(s)")
    if revenue_7d < 500:
        actions.append("Revenue below $500 this week — prioritize high-score work orders")
    if not pending:
        actions.append("No pending work orders — check Gmail and Field Nation for new opportunities")

    return actions or ["All clear — no immediate actions required"]


def _build_alerts(pending: List[Dict]) -> List[str]:
    alerts = []
    for wo in pending:
        if wo.get("recommendation") == "avoid":
            alerts.append(f"Low-margin WO flagged: {wo.get('title', 'Unknown')[:60]}")
        if wo.get("travel_miles") and float(wo["travel_miles"]) > 60:
            alerts.append(f"Long-distance WO outside 60-mile radius: {wo.get('title', 'Unknown')[:60]}")
    return alerts[:5]  # cap at 5 alerts


@router.get("")
async def get_cash_command(request: Request):
    """Return today's operational summary for the Daily Cash Command view."""
    db = request.app.state.db

    pending = _get_pending_work_orders()
    top_opps = _get_top_opportunities()
    revenue_7d = await _get_revenue_7d(db)
    action_items = _build_action_items(pending, revenue_7d)
    alerts = _build_alerts(pending)

    # Score distribution
    strong = [w for w in pending if (w.get("score") or 0) >= 80]
    counteroffer_wo = [w for w in pending if 50 <= (w.get("score") or 0) < 80]
    avoid_wo = [w for w in pending if (w.get("score") or 0) < 50]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "work_orders_pending": {
            "total": len(pending),
            "strong_match": len(strong),
            "counteroffer": len(counteroffer_wo),
            "avoid": len(avoid_wo),
            "items": pending[:10],
        },
        "revenue_7d": {
            "total_usd": round(revenue_7d, 2),
            "currency": "USD",
            "period": "last_7_days",
        },
        "top_opportunities": [
            {
                "id": w.get("id"),
                "title": w.get("title") or "Untitled",
                "company": w.get("company") or "",
                "rate_offered": w.get("rate_offered") or 0,
                "rate_type": w.get("rate_type") or "unknown",
                "score": w.get("score") or 0,
                "recommendation": w.get("recommendation") or "unknown",
                "category": w.get("category") or "",
                "location": w.get("location") or "",
            }
            for w in top_opps
        ],
        "alerts": alerts,
        "action_items": action_items,
        "config": {
            "base_market": "Phoenix AZ",
            "radius_miles": 60,
            "minimum_hourly": 65,
            "minimum_total": 130,
        },
    }
