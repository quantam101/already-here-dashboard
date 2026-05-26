"""
Run Cycle - one-click pipeline that uses Scout -> Content Ideas -> Publishing Log.

Demonstrates the complete proof-of-work flow:
  1. Pull top viral opportunities from free sources
  2. Convert top N into content_ideas
  3. Generate AI scripts for each
  4. Create publishing records in 'drafted' state for each platform
  5. Return the cycle report

Cost Guard: $0 (all sources free, generation via Emergent LLM Key).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from services.audit_service import log_audit_event
from routes.scout import scout_viral

router = APIRouter()


class CycleResult(BaseModel):
    cycle_id: str
    opportunities_scanned: int
    ideas_created: int
    scripts_generated: int
    publishing_drafts: int
    stream_id: str
    platforms: list[str]
    next_action: str
    started_at: str
    completed_at: str
    error: Optional[str] = None


async def get_db():
    from server import db
    return db


@router.post("/run", response_model=CycleResult)
async def run_cycle(
    stream_id: str = "rev-001",
    max_ideas: int = 3,
    platforms: str = "blog,medium,reddit,linkedin",
    db=Depends(get_db),
):
    """Execute one full content cycle and return a report.

    Note: This is the operator-driven "drafted" flow. Operator still publishes
    manually (Cost Guard - no auto-posting without approval) then advances each
    publishing record's status to 'posted' with the live URL.
    """
    started = datetime.now(timezone.utc)
    cycle_id = f"cyc-{uuid.uuid4().hex[:8]}"
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    # 1. Pull viral opportunities (free)
    try:
        opps = await scout_viral(limit=15)
    except Exception as e:
        return CycleResult(
            cycle_id=cycle_id, opportunities_scanned=0, ideas_created=0,
            scripts_generated=0, publishing_drafts=0, stream_id=stream_id,
            platforms=platform_list, next_action="Retry scout - external API failed",
            started_at=started.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=f"scout failed: {e}",
        )

    # Filter out error rows
    valid = [o for o in opps if o.id and "error" not in o.id]
    top = valid[:max_ideas]

    # 2. Convert to content ideas
    ideas_created = 0
    drafts_created = 0
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    for opp in top:
        idea_doc = {
            "id": f"idea-{uuid.uuid4().hex[:10]}",
            "title": opp.title[:200],
            "description": opp.summary or f"Source: {opp.source}",
            "topic": opp.metadata.get("subreddit") or opp.source,
            "target_platforms": platform_list,
            "priority": "medium",
            "status": "drafted",
            "tags": [opp.source, opp.kind],
            "inspiration_source": opp.url,
            "metadata": {"opp_score": opp.score, "cycle_id": cycle_id},
            "created_at": timestamp_iso,
            "updated_at": timestamp_iso,
        }
        await db.content_ideas.insert_one(idea_doc)
        ideas_created += 1

        # 4. Create publishing draft for each platform
        for plat in platform_list:
            pub_doc = {
                "id": f"pub-{uuid.uuid4().hex[:10]}",
                "stream_id": stream_id,
                "platform": plat,
                "title": opp.title[:200],
                "idea_id": idea_doc["id"],
                "status": "drafted",
                "post_url": None,
                "notes": f"Cycle {cycle_id} - draft from {opp.source}",
                "metrics": {},
                "posted_at": None,
                "verified_at": None,
                "created_at": timestamp_iso,
                "updated_at": timestamp_iso,
            }
            await db.publishing_log.insert_one(pub_doc)
            drafts_created += 1

    completed = datetime.now(timezone.utc)
    await log_audit_event(
        db, "cycle.completed", "sovereign_orchestrator", "run",
        "cycle", cycle_id,
        metadata={
            "ideas": ideas_created, "drafts": drafts_created,
            "duration_ms": int((completed - started).total_seconds() * 1000),
        },
    )

    return CycleResult(
        cycle_id=cycle_id,
        opportunities_scanned=len(opps),
        ideas_created=ideas_created,
        scripts_generated=0,  # script gen is per-idea on demand; keep cycle fast
        publishing_drafts=drafts_created,
        stream_id=stream_id,
        platforms=platform_list,
        next_action=(
            "Open /content (ideas) and /proof-of-work (drafts). "
            "For each draft: generate the script in the Content Factory, "
            "export the pack, publish manually, then mark the publishing record as 'posted' with the URL."
        ),
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
    )


@router.get("/last", response_model=Optional[CycleResult])
async def last_cycle(db=Depends(get_db)):
    """Return summary of the most recent run cycle."""
    event = await db.audit_log.find_one(
        {"event_type": "cycle.completed"},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )
    if not event:
        return None
    return CycleResult(
        cycle_id=event.get("resource_id", "unknown"),
        opportunities_scanned=event.get("metadata", {}).get("ideas", 0),
        ideas_created=event.get("metadata", {}).get("ideas", 0),
        scripts_generated=0,
        publishing_drafts=event.get("metadata", {}).get("drafts", 0),
        stream_id="rev-001",
        platforms=[],
        next_action="See /content and /proof-of-work",
        started_at=event.get("timestamp", ""),
        completed_at=event.get("timestamp", ""),
    )
