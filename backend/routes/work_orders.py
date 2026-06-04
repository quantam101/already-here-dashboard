"""
Work Order Intelligence — Phase 1 Growth Command OS
Routes:
  POST /api/work-orders/score          — score a work order dict
  GET  /api/work-orders/queue          — return pending/scored work orders
  POST /api/work-orders/counteroffer   — generate counteroffer text (approval required)
  POST /api/work-orders/parse-email    — parse Gmail alert email body into structured WO
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "work_orders.db"


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS work_orders (
                id TEXT PRIMARY KEY,
                source TEXT,
                raw_text TEXT,
                title TEXT,
                company TEXT,
                location TEXT,
                rate_offered REAL,
                rate_type TEXT,
                estimated_hours REAL,
                travel_miles REAL,
                category TEXT,
                score INTEGER,
                recommendation TEXT,
                status TEXT DEFAULT 'pending',
                approval_required INTEGER DEFAULT 0,
                counteroffer_text TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()


_ensure_table()

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
PREFERRED_CATEGORIES = {
    "it support", "pos", "av", "access point", "cabling", "smart hands",
    "printer support", "computer repair", "laptop repair", "tv repair",
    "tv mounting", "camera installation", "ring installation",
    "door lock installation", "appliance repair", "pest spraying", "weed spraying",
}

MINIMUM_HOURLY = 65.0
MINIMUM_HOURS = 2.0
MINIMUM_TOTAL = 130.0
RADIUS_MILES = 60.0
LONG_DISTANCE_MIN_RATE = 175.0


def _score_work_order(wo: Dict[str, Any]) -> tuple[int, str]:
    """Return (score 0-100, recommendation)."""
    score = 50  # baseline
    flags: List[str] = []

    rate = wo.get("rate_offered") or 0.0
    rate_type = (wo.get("rate_type") or "unknown").lower()
    hours = wo.get("estimated_hours") or 0.0
    travel = wo.get("travel_miles") or 0.0
    category = (wo.get("category") or "").lower()
    title = (wo.get("title") or "").lower()
    raw = (wo.get("raw_text") or "").lower()

    # --- Category bonus ---
    cat_match = any(c in category or c in title for c in PREFERRED_CATEGORIES)
    if cat_match:
        score += 15
    else:
        score -= 10
        flags.append("non_preferred_category")

    # --- Rate scoring ---
    if rate_type == "hourly":
        effective_total = rate * max(hours, MINIMUM_HOURS)
        if rate >= MINIMUM_HOURLY and effective_total >= MINIMUM_TOTAL:
            score += 20
        elif rate >= MINIMUM_HOURLY:
            score += 5
            flags.append("low_hours")
        else:
            score -= 25
            flags.append("weak_rate")
    elif rate_type == "flat":
        effective_total = rate
        if effective_total >= MINIMUM_TOTAL:
            score += 10
        else:
            score -= 30
            flags.append("fixed_fee_under_130")
    else:
        score -= 15
        flags.append("unclear_scope")

    # --- Travel penalty ---
    if travel > RADIUS_MILES:
        if rate_type == "hourly" and rate >= LONG_DISTANCE_MIN_RATE:
            score += 5  # compensated long-distance OK
        elif rate_type == "flat" and rate < LONG_DISTANCE_MIN_RATE:
            score -= 20
            flags.append("long_distance_under_175")
        else:
            score -= 10
            flags.append("long_distance_low_rate")

    if travel > 0 and "travel" not in raw and "mileage" not in raw:
        score -= 5
        flags.append("unpaid_travel")

    # --- Scope clarity ---
    scope_words = ["scope", "description", "task", "install", "repair", "replace", "configure"]
    if not any(w in raw for w in scope_words):
        score -= 10
        flags.append("unclear_scope")

    # --- Clamp ---
    score = max(0, min(100, score))

    # --- Recommendation ---
    if score >= 80:
        recommendation = "accept"
    elif score >= 50:
        recommendation = "counteroffer"
    else:
        recommendation = "avoid"

    if "unclear_scope" in flags and score < 70:
        recommendation = "avoid"

    return score, recommendation


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class WorkOrderIn(BaseModel):
    id: Optional[str] = None
    source: Optional[str] = "manual"
    raw_text: Optional[str] = ""
    title: Optional[str] = ""
    company: Optional[str] = ""
    location: Optional[str] = ""
    rate_offered: Optional[float] = 0.0
    rate_type: Optional[str] = "unknown"
    estimated_hours: Optional[float] = 0.0
    travel_miles: Optional[float] = 0.0
    category: Optional[str] = ""


class CounterOfferRequest(BaseModel):
    work_order_id: Optional[str] = None
    work_order: Optional[WorkOrderIn] = None
    travel_miles: Optional[float] = 0.0


class ParseEmailRequest(BaseModel):
    email_body: str
    source: Optional[str] = "gmail"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/score")
async def score_work_order(wo: WorkOrderIn):
    """Score a work order and persist it."""
    wo_dict = wo.model_dump()
    wo_id = wo_dict.get("id") or str(uuid.uuid4())
    wo_dict["id"] = wo_id

    score, recommendation = _score_work_order(wo_dict)
    approval_required = recommendation in ("accept",)

    now = datetime.now(timezone.utc).isoformat()
    wo_dict.update(
        score=score,
        recommendation=recommendation,
        approval_required=int(approval_required),
        status="pending",
        created_at=now,
        updated_at=now,
    )

    with _get_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO work_orders
            (id, source, raw_text, title, company, location, rate_offered,
             rate_type, estimated_hours, travel_miles, category,
             score, recommendation, status, approval_required,
             counteroffer_text, created_at, updated_at)
            VALUES (:id, :source, :raw_text, :title, :company, :location,
                    :rate_offered, :rate_type, :estimated_hours, :travel_miles,
                    :category, :score, :recommendation, :status,
                    :approval_required, NULL, :created_at, :updated_at)
        """, wo_dict)
        conn.commit()

    return {
        "id": wo_id,
        "score": score,
        "recommendation": recommendation,
        "approval_required": approval_required,
        "score_label": "strong_match" if score >= 80 else ("counteroffer" if score >= 50 else "avoid"),
    }


@router.get("/queue")
async def get_queue(status: Optional[str] = None, limit: int = 50):
    """Return work orders, optionally filtered by status."""
    with _get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM work_orders WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM work_orders ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

    return {"work_orders": [dict(r) for r in rows], "total": len(rows)}


@router.post("/counteroffer")
async def generate_counteroffer(req: CounterOfferRequest, request: Request):
    """Generate counteroffer text. Always returns approval_required=true."""
    travel = req.travel_miles or 0.0

    # Resolve WO data
    wo_data: Dict[str, Any] = {}
    if req.work_order_id:
        with _get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM work_orders WHERE id = ?", (req.work_order_id,)
            ).fetchone()
        if row:
            wo_data = dict(row)
            travel = travel or (wo_data.get("travel_miles") or 0.0)
    elif req.work_order:
        wo_data = req.work_order.model_dump()

    title = wo_data.get("title") or "this work order"
    company = wo_data.get("company") or "the platform"

    # Build counteroffer text
    travel_clause = ""
    if travel > 30:
        extra_miles = travel - 30
        travel_fee = round(extra_miles * 0.67, 2)  # IRS mileage rate approx
        travel_clause = f", plus ${travel_fee:.2f} travel fee ({extra_miles:.0f} miles over 30-mile radius)"

    counteroffer_text = (
        f"Thank you for the opportunity on '{title}'. "
        f"My rate for this type of work is $65/hr with a 2-hour minimum ($130 total){travel_clause}. "
        f"Please confirm if this works and I'll get it scheduled."
    )

    # Try to enhance with LLM if available
    try:
        db = request.app.state.db
        from services.llm_runner import run_cached
        prompt = (
            f"Write a professional, brief work order counteroffer for '{title}' from {company}. "
            f"My minimum rate: $65/hr, 2-hour minimum ($130 total){travel_clause}. "
            "Keep it under 3 sentences. Be direct and professional."
        )
        llm_text = await run_cached(
            db, "auto", "auto",
            "You are a professional field service technician drafting a counteroffer.",
            prompt,
            session_id=f"counteroffer-{req.work_order_id or 'new'}",
        )
        if llm_text and len(llm_text) > 20:
            counteroffer_text = llm_text
    except Exception as e:
        log.warning("LLM counteroffer generation skipped: %s", e)

    # Persist if we have a WO ID
    if req.work_order_id:
        now = datetime.now(timezone.utc).isoformat()
        with _get_conn() as conn:
            conn.execute(
                "UPDATE work_orders SET counteroffer_text=?, status='countered', updated_at=? WHERE id=?",
                (counteroffer_text, now, req.work_order_id)
            )
            conn.commit()

    return {
        "approval_required": True,
        "counteroffer_text": counteroffer_text,
        "message": "Review and approve before sending. This was NOT sent automatically.",
    }


@router.post("/parse-email")
async def parse_email(req: ParseEmailRequest):
    """Parse a work order alert email body into structured WO fields."""
    import re

    body = req.email_body
    body_lower = body.lower()

    # Simple heuristic extraction
    def _find_dollar(text: str) -> Optional[float]:
        m = re.search(r"\$\s?([\d,]+(?:\.\d{1,2})?)", text)
        if m:
            return float(m.group(1).replace(",", ""))
        m = re.search(r"([\d,]+(?:\.\d{1,2})?)\s*(?:/hr|per hour|hourly)", text, re.I)
        if m:
            return float(m.group(1).replace(",", ""))
        return None

    def _find_hours(text: str) -> Optional[float]:
        m = re.search(r"([\d.]+)\s*(?:hour|hr)", text, re.I)
        return float(m.group(1)) if m else None

    def _find_miles(text: str) -> Optional[float]:
        m = re.search(r"([\d.]+)\s*mile", text, re.I)
        return float(m.group(1)) if m else None

    def _detect_rate_type(text: str) -> str:
        if re.search(r"/hr|per hour|hourly", text, re.I):
            return "hourly"
        if re.search(r"flat|fixed|lump", text, re.I):
            return "flat"
        return "unknown"

    def _detect_category(text: str) -> str:
        cats = {
            "IT support": ["it support", "helpdesk", "tech support", "it tech"],
            "POS": ["pos", "point of sale"],
            "AV": ["av ", "audio visual", "projector", "screen"],
            "access point": ["access point", "wifi", "wireless ap", "ubiquiti", "meraki"],
            "cabling": ["cabling", "cable run", "cat5", "cat6", "ethernet"],
            "smart hands": ["smart hands", "smarthand"],
            "printer support": ["printer", "mfp", "copier"],
            "computer repair": ["computer repair", "desktop repair", "pc repair"],
            "laptop repair": ["laptop repair", "laptop screen", "laptop keyboard"],
            "TV mounting": ["tv mount", "tv install", "television mount"],
            "camera installation": ["camera install", "cctv", "security camera"],
            "Ring installation": ["ring doorbell", "ring camera", "ring install"],
            "door lock installation": ["smart lock", "door lock", "deadbolt"],
            "appliance repair": ["appliance", "washer", "dryer", "dishwasher", "refrigerator"],
            "pest spraying": ["pest", "termite", "exterminator"],
            "weed spraying": ["weed", "lawn spray", "herbicide"],
        }
        tl = text.lower()
        for cat, keywords in cats.items():
            if any(k in tl for k in keywords):
                return cat
        return "unknown"

    # Extract title — first non-empty line or subject-like line
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    title = lines[0][:120] if lines else "Work Order"

    # Extract company from "From:" line or similar
    company = ""
    for line in lines[:10]:
        m = re.search(r"(?:from|company|client|vendor):\s*(.+)", line, re.I)
        if m:
            company = m.group(1).strip()[:80]
            break

    # Location
    location = ""
    for line in lines:
        m = re.search(r"(?:location|site|address):\s*(.+)", line, re.I)
        if m:
            location = m.group(1).strip()[:100]
            break
    if not location:
        m = re.search(r"\b([A-Z][a-z]+,?\s+AZ\b)", body)
        if m:
            location = m.group(1)

    wo = WorkOrderIn(
        source=req.source,
        raw_text=body[:4000],
        title=title,
        company=company,
        location=location or "Phoenix, AZ",
        rate_offered=_find_dollar(body) or 0.0,
        rate_type=_detect_rate_type(body),
        estimated_hours=_find_hours(body) or 0.0,
        travel_miles=_find_miles(body) or 0.0,
        category=_detect_category(body),
    )

    # Auto-score the parsed WO
    wo_dict = wo.model_dump()
    score, recommendation = _score_work_order(wo_dict)

    return {
        "parsed": wo_dict,
        "score": score,
        "recommendation": recommendation,
        "parsed_fields": {
            "rate_offered": wo.rate_offered,
            "rate_type": wo.rate_type,
            "estimated_hours": wo.estimated_hours,
            "travel_miles": wo.travel_miles,
            "category": wo.category,
            "location": wo.location,
        },
    }
