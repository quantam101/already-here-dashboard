import os
import uuid
from datetime import UTC, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from content_models import (
    ContentAnalytics,
    ContentIdea,
    ContentScript,
    ContentStatusEnum,
    PlatformConnector,
    PlatformEnum,
    ScheduledPost,
)
from services.audit_service import log_audit_event

router = APIRouter()

PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://app.alreadyherellc.com").rstrip("/")


class ContentIdeaCreate(BaseModel):
    title: str
    description: str
    topic: str
    target_platforms: List[PlatformEnum] = Field(default_factory=list)
    priority: str | None = "medium"
    tags: List[str] = Field(default_factory=list)
    inspiration_source: str | None = None


async def get_db():
    from server import db
    return db


def _is_direct_publish_connector(connector: dict) -> bool:
    """Return true when a connector can publish without a manual export pack."""
    if connector.get("cost_class") == "free_local" and connector.get("credential_status") == "configured":
        return True
    return connector.get("cost_class") == "free_external" and bool(connector.get("api_authenticated"))

# Content Ideas
@router.post("/ideas/", response_model=ContentIdea)
async def create_idea(idea: ContentIdeaCreate, db=Depends(get_db)):
    idea_obj = ContentIdea(**idea.model_dump())
    doc = idea_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.content_ideas.insert_one(doc)
    await log_audit_event(db, "content_idea.created", "system", "create", "content_idea", idea_obj.id)
    return idea_obj

@router.get("/ideas/", response_model=List[ContentIdea])
async def list_ideas(status: str = None, db=Depends(get_db)):
    query = {}
    if status:
        query['status'] = status
    ideas = await db.content_ideas.find(query, {"_id": 0}).to_list(1000)
    for idea in ideas:
        if isinstance(idea.get('created_at'), str):
            idea['created_at'] = datetime.fromisoformat(idea['created_at'])
        if isinstance(idea.get('updated_at'), str):
            idea['updated_at'] = datetime.fromisoformat(idea['updated_at'])
    return ideas

@router.post("/ideas/{idea_id}/script", response_model=ContentScript)
async def generate_script(idea_id: str, db=Depends(get_db)):
    idea = await db.content_ideas.find_one({"id": idea_id}, {"_id": 0})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")

    from services.content_generation_service import generate_script_from_idea
    script = await generate_script_from_idea(idea, db=db)

    doc = script.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    await db.content_scripts.insert_one(doc)

    await db.content_ideas.update_one(
        {"id": idea_id},
        {"$set": {"status": "scripted", "updated_at": datetime.now(UTC).isoformat()}}
    )

    await log_audit_event(db, "content_script.generated", "system", "generate", "content_script", script.id)
    return script


@router.get("/ideas/{idea_id}/scripts", response_model=List[ContentScript])
async def list_scripts_for_idea(idea_id: str, db=Depends(get_db)):
    """List every generated script for an idea (newest first)."""
    rows = await db.content_scripts.find(
        {"idea_id": idea_id}, {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    for s in rows:
        if isinstance(s.get('created_at'), str):
            s['created_at'] = datetime.fromisoformat(s['created_at'])
        if isinstance(s.get('updated_at'), str):
            s['updated_at'] = datetime.fromisoformat(s['updated_at'])
    return rows


@router.get("/scripts/", response_model=List[ContentScript])
async def list_all_scripts(limit: int = 200, db=Depends(get_db)):
    """Operator view: every generated script across all ideas, newest first."""
    rows = await db.content_scripts.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    for s in rows:
        if isinstance(s.get('created_at'), str):
            s['created_at'] = datetime.fromisoformat(s['created_at'])
        if isinstance(s.get('updated_at'), str):
            s['updated_at'] = datetime.fromisoformat(s['updated_at'])
    return rows

# Platform Connectors
@router.get("/connectors/", response_model=List[PlatformConnector])
async def list_connectors(db=Depends(get_db)):
    connectors = await db.platform_connectors.find({}, {"_id": 0}).to_list(1000)
    for conn in connectors:
        if isinstance(conn.get('created_at'), str):
            conn['created_at'] = datetime.fromisoformat(conn['created_at'])
        if isinstance(conn.get('updated_at'), str):
            conn['updated_at'] = datetime.fromisoformat(conn['updated_at'])
    return connectors

@router.get("/connectors/{connector_id}", response_model=PlatformConnector)
async def get_connector(connector_id: str, db=Depends(get_db)):
    connector = await db.platform_connectors.find_one({"id": connector_id}, {"_id": 0})
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    if isinstance(connector.get('created_at'), str):
        connector['created_at'] = datetime.fromisoformat(connector['created_at'])
    if isinstance(connector.get('updated_at'), str):
        connector['updated_at'] = datetime.fromisoformat(connector['updated_at'])
    return connector

# Scheduled Posts
@router.post("/schedule/", response_model=ScheduledPost)
async def schedule_post(post: dict, db=Depends(get_db)):
    post_obj = ScheduledPost(**post)

    # Check platform connector
    connector = await db.platform_connectors.find_one(
        {"platform": post_obj.platform},
        {"_id": 0}
    )

    if not connector:
        raise HTTPException(status_code=400, detail=f"No connector configured for {post_obj.platform}")

    # Determine publishing method based on connector status
    if _is_direct_publish_connector(connector):
        post_obj.publishing_method = "direct_api"
    else:
        post_obj.publishing_method = "manual_export"
        post_obj.status = ContentStatusEnum.MANUAL_UPLOAD_REQUIRED

    doc = post_obj.model_dump()
    doc['scheduled_time'] = doc['scheduled_time'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('published_at'):
        doc['published_at'] = doc['published_at'].isoformat()

    await db.scheduled_posts.insert_one(doc)
    await log_audit_event(db, "post.scheduled", "system", "schedule", "scheduled_post", post_obj.id)
    return post_obj

@router.get("/schedule/", response_model=List[ScheduledPost])
async def list_scheduled_posts(platform: str = None, status: str = None, db=Depends(get_db)):
    query = {}
    if platform:
        query['platform'] = platform
    if status:
        query['status'] = status

    posts = await db.scheduled_posts.find(query, {"_id": 0}).sort("scheduled_time", 1).to_list(1000)
    for post in posts:
        if isinstance(post.get('scheduled_time'), str):
            post['scheduled_time'] = datetime.fromisoformat(post['scheduled_time'])
        if isinstance(post.get('created_at'), str):
            post['created_at'] = datetime.fromisoformat(post['created_at'])
        if isinstance(post.get('updated_at'), str):
            post['updated_at'] = datetime.fromisoformat(post['updated_at'])
        if post.get('published_at') and isinstance(post['published_at'], str):
            post['published_at'] = datetime.fromisoformat(post['published_at'])
    return posts

@router.post("/schedule/{post_id}/export")
async def generate_export_pack(post_id: str, db=Depends(get_db)):
    post = await db.scheduled_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    from services.export_service import create_export_pack
    export_path = await create_export_pack(post)

    await db.scheduled_posts.update_one(
        {"id": post_id},
        {"$set": {
            "export_pack_path": export_path,
            "status": "manual_upload_required",
            "updated_at": datetime.now(UTC).isoformat()
        }}
    )

    return {"export_pack_path": export_path, "message": "Export pack ready for manual upload"}


@router.post("/schedule/{post_id}/publish")
async def publish_scheduled_post(post_id: str, db=Depends(get_db)):
    post = await db.scheduled_posts.find_one({"id": post_id}, {"_id": 0})
    if not post:
        raise HTTPException(status_code=404, detail="Scheduled post not found")

    connector = await db.platform_connectors.find_one({"platform": post["platform"]}, {"_id": 0})
    if not connector:
        raise HTTPException(status_code=400, detail=f"No connector configured for {post['platform']}")
    if not _is_direct_publish_connector(connector):
        raise HTTPException(
            status_code=400,
            detail=f"{post['platform']} is not authenticated for direct publishing; use export pack",
        )
    if post["platform"] != PlatformEnum.BLOG:
        raise HTTPException(
            status_code=400,
            detail=f"Direct publishing for {post['platform']} requires its OAuth/API credentials",
        )

    now = datetime.now(UTC).isoformat()
    content_id = post.get("content_id") or f"blog-{post_id}"
    if content_id.startswith("manual-"):
        content_id = f"blog-{post_id}"
    published_url = f"{PUBLIC_BASE_URL}/api/content/{content_id}"

    content_doc = {
        "id": content_id,
        "title": post.get("title") or "Published blog post",
        "content_type": "blog",
        "body": post["caption"],
        "status": "published",
        "platform": "blog",
        "revenue_stream_id": post.get("metadata", {}).get("stream_id"),
        "generated_by": "scheduled_publisher",
        "published_at": now,
        "metadata": {
            **post.get("metadata", {}),
            "scheduled_post_id": post_id,
            "published_url": published_url,
            "hashtags": post.get("hashtags", []),
        },
        "created_at": post.get("created_at", now),
        "updated_at": now,
    }
    existing = await db.content.find_one({"id": content_id}, {"_id": 0})
    if existing:
        await db.content.update_one({"id": content_id}, {"$set": content_doc})
    else:
        await db.content.insert_one(content_doc)

    await db.scheduled_posts.update_one(
        {"id": post_id},
        {"$set": {
            "status": "published",
            "publishing_method": "direct_api",
            "published_url": published_url,
            "published_at": now,
            "updated_at": now,
        }},
    )

    record = {
        "id": f"pub-{uuid.uuid4().hex[:10]}",
        "stream_id": post.get("metadata", {}).get("stream_id") or "rev-001",
        "platform": "blog",
        "title": post.get("title") or content_doc["title"],
        "content_id": content_id,
        "idea_id": post.get("metadata", {}).get("idea_id"),
        "status": "posted",
        "post_url": published_url,
        "notes": f"Direct local blog publish from scheduled post {post_id}",
        "metrics": {},
        "posted_at": now,
        "verified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.publishing_log.insert_one(record)
    await log_audit_event(db, "post.published", "system", "publish", "scheduled_post", post_id)
    return {"ok": True, "post_id": post_id, "content_id": content_id, "published_url": published_url}

# Analytics
@router.get("/analytics/", response_model=List[ContentAnalytics])
async def list_analytics(platform: str = None, db=Depends(get_db)):
    query = {}
    if platform:
        query['platform'] = platform
    analytics = await db.content_analytics.find(query, {"_id": 0}).to_list(1000)
    for item in analytics:
        if isinstance(item.get('last_updated'), str):
            item['last_updated'] = datetime.fromisoformat(item['last_updated'])
    return analytics

@router.get("/analytics/top-performing")
async def get_top_performing(limit: int = 10, db=Depends(get_db)):
    analytics = await db.content_analytics.find({}, {"_id": 0}).sort("engagement_rate", -1).to_list(limit)
    return analytics
