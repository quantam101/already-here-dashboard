"""
SocialAgent — Auto-posts drafted content to all configured social platforms.

Runs after content-agent generates articles. Picks up `content_queue` items
with status="ready" and posts them to every configured platform.

For video platforms (YouTube, TikTok, Instagram): generates export pack.
For text platforms (Medium, Dev.to, Reddit, Facebook, Threads, LinkedIn): auto-posts.
For manual platforms (Facebook Groups, Quora, forums): generates export pack.

Budget: 0 LLM tokens — pure API calls.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from agents.base_agent import BaseAgent
from services.social_publisher import connector_status, get_publisher

logger = logging.getLogger("social_agent")

QUEUE_COLLECTION     = "content_queue"
PUBLISHING_COLLECTION = "publishing_log"

# Text-capable platforms auto-posted when credentials are set
TEXT_PLATFORMS = ["medium", "devto", "reddit", "facebook", "threads", "linkedin", "discourse"]
# Video platforms — export pack only unless video_path provided in ctx
VIDEO_PLATFORMS = ["youtube", "tiktok", "instagram"]
# Always export pack
MANUAL_PLATFORMS = ["facebook_groups", "quora", "forum"]


class SocialAgent(BaseAgent):
    agent_id    = "social-agent"
    agent_name  = "Social Publisher"
    capabilities = [
        "multi_platform_posting",
        "export_pack_generation",
        "publishing_log_update",
    ]
    budget_tokens    = 0
    timeout_seconds  = 120.0

    async def execute(self, db, ctx: dict) -> dict:
        publisher = get_publisher()
        status    = connector_status()

        # Which text platforms are live?
        live_text = [p for p in TEXT_PLATFORMS if status.get(p, {}).get("configured")]
        live_video = [p for p in VIDEO_PLATFORMS if status.get(p, {}).get("configured")]

        if not live_text and not live_video:
            return {
                "posted": 0,
                "export_packs": 0,
                "skipped": "No social credentials configured. Add keys to .env",
                "connector_status": status,
            }

        # Fetch unposted content from queue
        items = await db[QUEUE_COLLECTION].find(
            {"status": "ready", "social_posted": {"$ne": True}},
            {"_id": 0},
        ).sort("created_at", -1).to_list(5)

        if not items:
            return {"posted": 0, "export_packs": 0, "reason": "no_new_content"}

        posted_count = 0
        export_count = 0
        errors: list[str] = []
        now = datetime.now(UTC).isoformat()

        for item in items:
            article = item.get("article", {})
            _opp_src = item.get("opportunity_source", "")
            item_id = item.get("id", "")

            # Enrich article with source URL if available
            opp = await db["scout_opportunities"].find_one(
                {"id": item.get("opportunity_id", "")}, {"_id": 0}
            ) if item.get("opportunity_id") else None
            if opp:
                article["source_url"] = opp.get("url", "")

            # AUTO-POST to text platforms
            if live_text:
                try:
                    results = await publisher.post_article(article, live_text)
                    for res in results:
                        if res.success:
                            posted_count += 1
                            # Log to publishing_log
                            await self._log_published(db, article, res.platform, res.url, now)
                        elif not res.skipped:
                            errors.append(f"{res.platform}: {res.error}")
                except Exception as e:
                    errors.append(f"post_article error: {e}")

            # GENERATE EXPORT PACK for video + manual platforms
            export_platforms = ["tiktok_script", "instagram_caption", "facebook_groups", "quora", "forum"]
            try:
                pack = publisher.export_pack(article, export_platforms)
                # Store pack in queue item
                await db[QUEUE_COLLECTION].update_one(
                    {"id": item_id},
                    {"$set": {"export_pack": pack, "export_pack_at": now}},
                )
                export_count += 1
            except Exception as e:
                errors.append(f"export_pack error: {e}")

            # Mark as socially posted
            await db[QUEUE_COLLECTION].update_one(
                {"id": item_id},
                {"$set": {"social_posted": True, "social_posted_at": now}},
            )

        return {
            "posted": posted_count,
            "export_packs": export_count,
            "live_platforms": live_text + live_video,
            "errors": errors,
            "connector_status": {k: v["configured"] for k, v in status.items()},
        }

    async def _log_published(self, db, article: dict, platform: str, url: str, now: str) -> None:
        """Write a 'posted' record to publishing_log."""
        import uuid
        doc = {
            "id": f"pub-{uuid.uuid4().hex[:10]}",
            "stream_id": "rev-001",
            "platform": platform,
            "title": article.get("title", ""),
            "status": "posted",
            "post_url": url,
            "notes": "Auto-posted by SocialAgent",
            "metrics": {},
            "posted_at": now,
            "verified_at": None,
            "created_at": now,
            "updated_at": now,
        }
        try:
            await db[PUBLISHING_COLLECTION].insert_one(doc)
        except Exception as e:
            logger.warning("social_agent: failed to log publishing record: %s", e)
