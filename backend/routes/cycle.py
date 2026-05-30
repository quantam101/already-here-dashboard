"""
Run Cycle - Scout -> Content Ideas -> Auto-Post -> Export Pack.

Full pipeline:
  1. Pull top viral opportunities from free sources
  2. Convert top N into content_ideas
  3. Create publishing drafts for all target platforms
  4. Auto-post to configured text platforms (Medium, Dev.to, Reddit, Facebook,
     Threads, LinkedIn, Discourse) if credentials are set
  5. Generate Export Pack for video (TikTok, YouTube, Instagram Reels) and
     manual platforms (Facebook Groups, Quora, niche forums)
  6. Return full cycle report

Cost Guard: $0 (all sources free; LLM generation via litellm + BYO key).
"""
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from routes.scout import scout_viral
from services import governance_service as gov
from services.audit_service import log_audit_event
from services.social_publisher import connector_status, get_publisher

router = APIRouter()
logger = logging.getLogger("cycle")

# All target platforms — text + video + manual
ALL_PLATFORMS = [
    # Text (auto-post when credentials set)
    "medium", "devto", "reddit", "facebook", "threads", "linkedin", "discourse",
    # Video (export pack + auto when credentials + video provided)
    "youtube", "tiktok", "instagram",
    # Manual export pack only
    "facebook_groups", "quora", "forum",
]

TEXT_PLATFORMS  = ["medium", "devto", "reddit", "facebook", "threads", "linkedin", "discourse"]
VIDEO_PLATFORMS = ["youtube", "tiktok", "instagram"]
MANUAL_PLATFORMS = ["facebook_groups", "quora", "forum"]


class CycleResult(BaseModel):
    cycle_id: str
    opportunities_scanned: int
    ideas_created: int
    scripts_generated: int
    publishing_drafts: int
    auto_posted: int
    export_packs: int
    stream_id: str
    platforms: list[str]
    live_connectors: list[str]
    next_action: str
    started_at: str
    completed_at: str
    error: str | None = None


async def get_db():
    from server import db
    return db


def _make_idea_doc(opp, platform_list: list[str], cycle_id: str, timestamp_iso: str) -> dict:
    """Convert one scout Opportunity into a content_idea document."""
    return {
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


def _make_publishing_draft(
    idea_id: str, title: str, stream_id: str, platform: str,
    cycle_id: str, source: str, timestamp_iso: str,
) -> dict:
    """Build a publishing_log draft record for an idea+platform pair."""
    return {
        "id": f"pub-{uuid.uuid4().hex[:10]}",
        "stream_id": stream_id,
        "platform": platform,
        "title": title[:200],
        "idea_id": idea_id,
        "status": "drafted",
        "post_url": None,
        "notes": f"Cycle {cycle_id} - draft from {source}",
        "metrics": {},
        "posted_at": None,
        "verified_at": None,
        "created_at": timestamp_iso,
        "updated_at": timestamp_iso,
    }


@router.post("/run", response_model=CycleResult)
async def run_cycle(
    http_request: Request,
    stream_id: str = "rev-001",
    max_ideas: int = 3,
    db=Depends(get_db),
):
    """Execute one full content cycle and return a report.

    Note: This is the operator-driven "drafted" flow. Operator still publishes
    manually (Cost Guard - no auto-posting without approval) then advances each
    publishing record's status to 'posted' with the live URL.

    Gated on `mass_outreach` (HITL required below L4).
    """
    await gov.enforce(
        db=db, request=http_request, action_id="mass_outreach",
        context={"route": "cycle/run", "stream_id": stream_id, "max_ideas": max_ideas, "platforms": ALL_PLATFORMS},
    )
    started = datetime.now(UTC)
    cycle_id = f"cyc-{uuid.uuid4().hex[:8]}"
    opps: list = []

    # Check which connectors are live
    conn_status = connector_status()
    live_text  = [p for p in TEXT_PLATFORMS  if conn_status.get(p, {}).get("configured")]
    live_video = [p for p in VIDEO_PLATFORMS if conn_status.get(p, {}).get("configured")]
    live_all   = live_text + live_video

    # 1. Scout viral opportunities
    try:
        opps = await scout_viral(limit=15)
    except Exception as e:
        return CycleResult(
            cycle_id=cycle_id, opportunities_scanned=0, ideas_created=0,
            scripts_generated=0, publishing_drafts=0, auto_posted=0, export_packs=0,
            stream_id=stream_id, platforms=ALL_PLATFORMS, live_connectors=live_all,
            next_action="Retry cycle — scout external API failed",
            started_at=started.isoformat(),
            completed_at=datetime.now(UTC).isoformat(),
            error=f"scout failed: {e}",
        )

    valid = [o for o in opps if o.id and "error" not in o.id]
    top   = valid[:max_ideas]

    ideas_created  = 0
    drafts_created = 0
    auto_posted    = 0
    export_packs   = 0
    timestamp_iso  = datetime.now(UTC).isoformat()
    publisher      = get_publisher()

    for opp in top:
        # 2. Create content idea
        idea_doc = _make_idea_doc(opp, ALL_PLATFORMS, cycle_id, timestamp_iso)
        await db.content_ideas.insert_one(idea_doc)
        ideas_created += 1

        # 3. Create publishing drafts for all platforms
        for plat in ALL_PLATFORMS:
            pub_doc = _make_publishing_draft(
                idea_doc["id"], opp.title, stream_id, plat, cycle_id, opp.source, timestamp_iso,
            )
            await db.publishing_log.insert_one(pub_doc)
            drafts_created += 1

        # Build minimal article dict from opportunity for immediate posting
        article = {
            "title": opp.title,
            "body": opp.summary or opp.title,
            "meta_description": opp.summary or "",
            "tags": [opp.source, opp.kind] + list(opp.metadata.get("tags", [])),
            "source_url": opp.url,
            "slug": opp.id,
        }

        # 4. Auto-post to live text platforms
        if live_text:
            try:
                results = await publisher.post_article(article, live_text)
                for res in results:
                    if res.success:
                        auto_posted += 1
                        # Advance the matching draft to "posted"
                        await db.publishing_log.update_one(
                            {"idea_id": idea_doc["id"], "platform": res.platform.split("/")[0]},
                            {"$set": {"status": "posted", "post_url": res.url, "posted_at": timestamp_iso}},
                        )
                        logger.info("Cycle auto-posted %s → %s", res.platform, res.url)
                    elif not res.skipped and res.error:
                        logger.warning("Cycle post failed %s: %s", res.platform, res.error)
            except Exception as e:
                logger.warning("Cycle auto-post error: %s", e)

        # 5. Generate Export Pack for video + manual platforms
        try:
            pack = publisher.export_pack(article)
            await db.content_ideas.update_one(
                {"id": idea_doc["id"]},
                {"$set": {"export_pack": pack, "export_pack_at": timestamp_iso}},
            )
            export_packs += 1
        except Exception as e:
            logger.warning("Cycle export_pack error: %s", e)

    completed = datetime.now(UTC)
    await log_audit_event(
        db, "cycle.completed", "sovereign_orchestrator", "run",
        "cycle", cycle_id,
        metadata={
            "ideas": ideas_created, "drafts": drafts_created,
            "auto_posted": auto_posted, "export_packs": export_packs,
            "live_connectors": live_all,
            "duration_ms": int((completed - started).total_seconds() * 1000),
        },
    )

    # Build next action message
    if live_text:
        next_action = (
            f"Auto-posted {auto_posted} posts to: {', '.join(live_text)}. "
            f"Export packs ready for: TikTok, YouTube, Instagram, Facebook Groups, Quora. "
            f"Go to Publishing → Export Pack to copy-paste video scripts."
        )
    else:
        next_action = (
            "No social credentials configured yet. "
            "Export packs generated for all platforms — go to Publishing → Export Pack. "
            "To enable auto-posting: add credentials to server .env (see SOCIAL_SETUP.md)."
        )

    return CycleResult(
        cycle_id=cycle_id,
        opportunities_scanned=len(opps),
        ideas_created=ideas_created,
        scripts_generated=0,
        publishing_drafts=drafts_created,
        auto_posted=auto_posted,
        export_packs=export_packs,
        stream_id=stream_id,
        platforms=ALL_PLATFORMS,
        live_connectors=live_all,
        next_action=next_action,
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
    )


@router.get("/last", response_model=CycleResult | None)
async def last_cycle(db=Depends(get_db)):
    """Return summary of the most recent run cycle."""
    event = await db.audit_log.find_one(
        {"event_type": "cycle.completed"},
        {"_id": 0},
        sort=[("timestamp", -1)],
    )
    if not event:
        return None
    meta = event.get("metadata", {})
    return CycleResult(
        cycle_id=event.get("resource_id", "unknown"),
        opportunities_scanned=meta.get("ideas", 0),
        ideas_created=meta.get("ideas", 0),
        scripts_generated=0,
        publishing_drafts=meta.get("drafts", 0),
        auto_posted=meta.get("auto_posted", 0),
        export_packs=meta.get("export_packs", 0),
        stream_id="rev-001",
        platforms=ALL_PLATFORMS,
        live_connectors=meta.get("live_connectors", []),
        next_action="See /publishing for status and export packs.",
        started_at=event.get("timestamp", ""),
        completed_at=event.get("timestamp", ""),
    )


@router.get("/connectors")
async def cycle_connectors():
    """Show which social platform credentials are configured."""
    status = connector_status()
    live   = [p for p, v in status.items() if v["configured"]]
    missing = [p for p, v in status.items() if not v["configured"]]
    return {
        "live": live,
        "missing": missing,
        "detail": status,
        "setup_guide": "https://github.com/quantam101/already-here-dashboard/blob/main/SOCIAL_SETUP.md",
    }


@router.get("/export-pack/{idea_id}")
async def get_export_pack(idea_id: str, db=Depends(get_db)):
    """Return the export pack for a specific content idea (copy-paste for manual platforms)."""
    idea = await db.content_ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Idea not found")

    pack = idea.get("export_pack")
    if not pack:
        # Generate on demand
        publisher = get_publisher()
        article = {
            "title": idea.get("title", ""),
            "body": idea.get("description", ""),
            "meta_description": idea.get("description", ""),
            "tags": idea.get("tags", []),
            "source_url": idea.get("inspiration_source", ""),
        }
        pack = publisher.export_pack(article)
        await db.content_ideas.update_one(
            {"id": idea_id},
            {"$set": {"export_pack": pack}},
        )

    return {"idea_id": idea_id, "title": idea.get("title", ""), "export_pack": pack}
