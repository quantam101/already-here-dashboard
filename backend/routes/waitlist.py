"""Proof-first waitlist capture.

This route records demand without creating a paid Command OS checkout. Paid
offers stay locked until the proof-of-work ledger clears the operator threshold.
"""
from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

PROOF_THRESHOLD_USD = 25_000
VALID_INTERESTS = {
    "trial",
    "build_for_percentage",
    "affiliate",
    "pod_store",
    "service_opportunity",
    "other",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def get_db():
    from server import db
    return db


class WaitlistSignupCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=254)
    name: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=160)
    role: str | None = Field(default=None, max_length=120)
    interest: str = Field(default="trial", max_length=64)
    message: str | None = Field(default=None, max_length=1200)
    source: str | None = Field(default=None, max_length=120)
    utm_source: str | None = Field(default=None, max_length=120)
    utm_medium: str | None = Field(default=None, max_length=120)
    utm_campaign: str | None = Field(default=None, max_length=120)
    referrer: str | None = Field(default=None, max_length=500)


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "_id"}


@router.post("")
@router.post("/")
async def create_waitlist_signup(payload: WaitlistSignupCreate, db=Depends(get_db)):
    email = payload.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")

    interest = payload.interest.strip().lower()
    if interest not in VALID_INTERESTS:
        interest = "other"

    now = datetime.now(UTC).isoformat()
    existing = await db.waitlist_signups.find_one({"email": email})
    signup_id = existing.get("id") if existing else str(uuid.uuid4())

    record = {
        "id": signup_id,
        "email": email,
        "name": _clean(payload.name),
        "company": _clean(payload.company),
        "role": _clean(payload.role),
        "interest": interest,
        "message": _clean(payload.message),
        "source": _clean(payload.source) or "proof_first_waitlist",
        "utm_source": _clean(payload.utm_source),
        "utm_medium": _clean(payload.utm_medium),
        "utm_campaign": _clean(payload.utm_campaign),
        "referrer": _clean(payload.referrer),
        "status": "waiting_for_proof",
        "offer_locked_until_usd": PROOF_THRESHOLD_USD,
        "updated_at": now,
    }
    if not existing:
        record["created_at"] = now
    else:
        record["created_at"] = existing.get("created_at") or now

    if existing:
        await db.waitlist_signups.update_one({"email": email}, {"$set": record})
    else:
        record["first_seen_at"] = now
        await db.waitlist_signups.insert_one(record)

    await db.analytics_events.insert_one({
        "id": str(uuid.uuid4()),
        "event_name": "lead",
        "event_type": "waitlist_signup",
        "channel": record["utm_source"] or record["source"],
        "source": record["source"],
        "email": email,
        "interest": interest,
        "metadata": {
            "waitlist_id": signup_id,
            "utm_source": record["utm_source"],
            "utm_medium": record["utm_medium"],
            "utm_campaign": record["utm_campaign"],
            "referrer": record["referrer"],
            "offer_locked_until_usd": PROOF_THRESHOLD_USD,
        },
        "ts": now,
        "created_at": now,
    })

    return {
        "id": signup_id,
        "status": "waiting_for_proof",
        "message": "You're on the proof-first waitlist. Paid Command OS offers unlock after verified proof of work.",
        "offer_locked_until_usd": PROOF_THRESHOLD_USD,
    }


@router.get("")
@router.get("/")
async def list_waitlist_signups(limit: int = 100, interest: str | None = None, db=Depends(get_db)):
    query: dict[str, Any] = {}
    if interest:
        query["interest"] = interest.strip().lower()
    rows = await db.waitlist_signups.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return {"items": [_serialize(r) for r in rows], "total": len(rows)}


@router.get("/stats")
async def waitlist_stats(db=Depends(get_db)):
    rows = await db.waitlist_signups.find({}, {"_id": 0, "interest": 1, "created_at": 1}).to_list(5000)
    by_interest: dict[str, int] = {}
    for row in rows:
        key = row.get("interest") or "other"
        by_interest[key] = by_interest.get(key, 0) + 1
    return {
        "total": len(rows),
        "by_interest": by_interest,
        "offer_locked_until_usd": PROOF_THRESHOLD_USD,
    }
