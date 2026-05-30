"""
Publishing Log - Proof-of-work for actual content distribution.

Every post the operator publishes (manually or via approved API) is logged here:
  - drafted: AI generated, in studio
  - exported: ready-to-post pack delivered to operator
  - posted:   operator pasted/uploaded to the platform, captured URL
  - verified: post URL confirmed live + (optionally) metrics ingested

This is the auditable chain: idea -> script -> export -> post URL -> verified.
"""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from services import governance_service as gov
from services.audit_service import log_audit_event

router = APIRouter()

ALLOWED_STATUSES = {"drafted", "exported", "posted", "verified"}


class PublishingCreate(BaseModel):
    stream_id: str
    platform: str  # blog | medium | youtube | tiktok | instagram | linkedin | etsy | redbubble | ...
    title: str
    content_id: str | None = None
    idea_id: str | None = None
    status: str = "drafted"
    post_url: str | None = None
    notes: str | None = None


class PublishingRecord(PublishingCreate):
    id: str = Field(default_factory=lambda: f"pub-{uuid.uuid4().hex[:10]}")
    metrics: dict = Field(default_factory=dict)
    posted_at: str | None = None
    verified_at: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class PublishingUpdate(BaseModel):
    status: str | None = None
    post_url: str | None = None
    metrics: dict | None = None
    notes: str | None = None


async def get_db():
    from server import db
    return db


def _validate_status(status: str) -> None:
    if status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(ALLOWED_STATUSES)}",
        )


@router.post("/", response_model=PublishingRecord, status_code=201)
async def create_publishing_record(payload: PublishingCreate, http_request: Request, db=Depends(get_db)):
    """Log a new publishing event (idea/exported/posted).

    Gated on `mass_outreach` ONLY when the record is being marked `posted`
    (the actual external-facing outreach event). Drafted/exported records are
    internal staging and bypass the gate.
    """
    _validate_status(payload.status)
    stream = await db.revenue_streams.find_one({"id": payload.stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail=f"Revenue stream '{payload.stream_id}' not found")

    if payload.status == "posted":
        await gov.enforce(
            db=db, request=http_request, action_id="mass_outreach",
            context={"route": "publishing/", "platform": payload.platform,
                     "stream_id": payload.stream_id, "title": payload.title[:120]},
        )

    record = PublishingRecord(**payload.model_dump())
    if payload.status == "posted" and payload.post_url:
        record.posted_at = record.created_at
    doc = record.model_dump()
    await db.publishing_log.insert_one(doc)
    await log_audit_event(
        db, f"publishing.{payload.status}", "operator", "publish",
        "publishing_record", record.id,
        metadata={"platform": payload.platform, "stream_id": payload.stream_id},
    )
    return record


@router.get("/", response_model=list[PublishingRecord])
async def list_publishing_records(
    stream_id: str | None = None,
    platform: str | None = None,
    status: str | None = None,
    limit: int = 500,
    db=Depends(get_db),
):
    """List publishing records with optional filters."""
    query: dict = {}
    if stream_id:
        query["stream_id"] = stream_id
    if platform:
        query["platform"] = platform
    if status:
        _validate_status(status)
        query["status"] = status
    cursor = db.publishing_log.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return await cursor.to_list(limit)


@router.patch("/{record_id}", response_model=PublishingRecord)
async def update_publishing_record(record_id: str, updates: PublishingUpdate, db=Depends(get_db)):
    """Advance a publishing record (e.g. drafted -> posted -> verified)."""
    record = await db.publishing_log.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Publishing record not found")

    patch: dict = {"updated_at": datetime.now(UTC).isoformat()}
    payload = updates.model_dump(exclude_none=True)
    if "status" in payload:
        _validate_status(payload["status"])
        if payload["status"] == "posted":
            patch["posted_at"] = patch["updated_at"]
        if payload["status"] == "verified":
            patch["verified_at"] = patch["updated_at"]
            if not record.get("posted_at"):
                patch["posted_at"] = patch["updated_at"]
    patch.update(payload)

    await db.publishing_log.update_one({"id": record_id}, {"$set": patch})
    await log_audit_event(
        db, f"publishing.{payload.get('status', 'updated')}", "operator", "update",
        "publishing_record", record_id, metadata=payload,
    )
    merged = {**record, **patch}
    return merged


@router.get("/stats/overview")
async def publishing_stats(db=Depends(get_db)):
    """Counts by status + platform for the proof-of-work feed."""
    records = await db.publishing_log.find({}, {"_id": 0}).to_list(10000)
    by_status: dict[str, int] = dict.fromkeys(ALLOWED_STATUSES, 0)
    by_platform: dict[str, int] = {}
    verified_urls: list[str] = []
    for r in records:
        st = r.get("status", "drafted")
        if st in by_status:
            by_status[st] += 1
        plat = r.get("platform", "unknown")
        by_platform[plat] = by_platform.get(plat, 0) + 1
        if st == "verified" and r.get("post_url"):
            verified_urls.append(r["post_url"])
    return {
        "total": len(records),
        "by_status": by_status,
        "by_platform": by_platform,
        "verified_post_count": len(verified_urls),
    }
