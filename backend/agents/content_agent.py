"""
ContentAgent — Runs every 6 hours. Turns scout opportunities into full articles
and packages them for multi-platform distribution.

Pipeline per opportunity:
  1. Distill the opportunity title + summary → compact prompt
  2. Call LLM (via run_cached) → structured JSON article
  3. Sanitize: tags, slug, meta description
  4. Save to `content_queue` collection (status: ready)
  5. Optionally publish to GitHub Pages and Dev.to if credentials present
     (only when AUTO_PUBLISH env=true, default false — operator approves)

Budget: up to 8,000 tokens per run (split across ≤5 articles).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from agents.base_agent import BaseAgent
from services.llm_runner import llm_complete

logger = logging.getLogger("content_agent")

QUEUE_COLLECTION = "content_queue"
OPPORTUNITIES_COLLECTION = "scout_opportunities"
DEVTO_BASE = "https://dev.to/api"
GH_BASE = "https://api.github.com"

ARTICLE_SYSTEM = (
    "You are an expert SEO content writer specializing in AI tools, passive income, "
    "and digital automation. Write high-quality, helpful articles that rank on Google. "
    "Always respond with valid JSON only — no markdown code fences."
)

ARTICLE_PROMPT = """Write a comprehensive SEO article about: {topic}

Return ONLY a valid JSON object with these exact fields:
{{
  "title": "exact article title",
  "slug": "url-friendly-slug",
  "meta_description": "150-160 char description",
  "tags": ["tag1", "tag2", "tag3", "tag4"],
  "body": "full markdown article body (## for h2, ### for h3, no H1)"
}}

Article: 900-1100 words, 5-7 sections, real actionable content, natural keyword placement."""


class ContentAgent(BaseAgent):
    agent_id = "content-agent"
    agent_name = "Content Generator"
    capabilities = [
        "script_generation",
        "article_generation",
        "multi_platform_packaging",
    ]
    budget_tokens = 8000
    timeout_seconds = 120.0

    async def check_budget(self, db) -> None:
        from services.llm_runner import check_daily_budget
        await check_daily_budget(db, expected_tokens=self.budget_tokens)

    async def execute(self, db, ctx: dict) -> dict:
        # Pull top unprocessed opportunities
        opps = await self._get_fresh_opportunities(db, limit=5)
        if not opps:
            return {"articles_generated": 0, "published": 0, "reason": "no_new_opportunities"}

        generated = 0
        published = 0
        tokens_used = 0
        errors: list[str] = []

        for opp in opps:
            try:
                article, tok = await self._generate_article(db, opp)
                tokens_used += tok
                await self._save_to_queue(db, article, opp)
                generated += 1

                if os.environ.get("AUTO_PUBLISH", "false").lower() == "true":
                    pub_result = await self._publish_article(article)
                    if pub_result.get("github_url"):
                        published += 1

                # Mark opportunity as processed
                await db[OPPORTUNITIES_COLLECTION].update_one(
                    {"id": opp["id"]},
                    {"$set": {"processed": True, "processed_at": datetime.now(UTC).isoformat()}},
                )
            except Exception as e:
                errors.append(f"{opp.get('id', '?')}: {e}")
                logger.warning("content-agent failed on opp %s: %s", opp.get("id"), e)

        return {
            "articles_generated": generated,
            "published": published,
            "opportunities_processed": len(opps),
            "errors": errors,
            "_tokens_used": tokens_used,
        }

    async def _get_fresh_opportunities(self, db, limit: int) -> list[dict]:
        try:
            rows = await db[OPPORTUNITIES_COLLECTION].find(
                {"processed": {"$ne": True}},
                {"_id": 0},
            ).sort("score", -1).to_list(limit)
            return rows
        except Exception:
            return []

    async def _generate_article(self, db, opp: dict) -> tuple[dict, int]:
        topic = opp.get("title", "AI tools for passive income")
        session_id = f"content-{uuid.uuid4().hex[:10]}"
        raw = await llm_complete(
            system=ARTICLE_SYSTEM,
            user=ARTICLE_PROMPT.format(topic=topic),
            max_tokens=1500,
            session_id=session_id,
        )
        # Strip code fences if model wraps response
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)
        try:
            article = json.loads(raw)
        except json.JSONDecodeError:
            article = json.loads(raw, strict=False)

        # Sanitize slug
        slug = re.sub(r"[^a-z0-9-]", "", article.get("slug", "")[:60].lower()).strip("-")
        if not slug:
            slug = re.sub(r"[^a-z0-9-]", "", topic.lower().replace(" ", "-"))[:50]
        article["slug"] = slug

        # Sanitize tags for Dev.to (lowercase, alphanumeric, max 20 chars)
        raw_tags = article.get("tags", [])
        clean_tags = []
        for t in raw_tags:
            s = re.sub(r"[^a-z0-9]", "", t.lower().replace(" ", "").replace("-", ""))[:20]
            if s and s not in clean_tags:
                clean_tags.append(s)
        article["tags"] = clean_tags[:4]

        tok = len(ARTICLE_PROMPT) // 4 + len(raw) // 4
        return article, tok

    async def _save_to_queue(self, db, article: dict, opp: dict) -> None:
        now = datetime.now(UTC).isoformat()
        doc = {
            "id": f"cq-{uuid.uuid4().hex[:10]}",
            "article": article,
            "opportunity_id": opp.get("id"),
            "opportunity_source": opp.get("source"),
            "status": "ready",
            "platforms": ["blog", "devto"],
            "created_at": now,
            "updated_at": now,
        }
        await db[QUEUE_COLLECTION].insert_one(doc)

    async def _publish_article(self, article: dict) -> dict:
        """Publish to GitHub Pages and Dev.to. Returns published URLs."""
        result: dict[str, str] = {}
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        slug = article.get("slug", "article")
        filename = f"{date_str}-{slug}.md"
        jekyll_content = self._make_jekyll_post(article, date_str)

        # GitHub Pages
        gh_token = os.environ.get("CONTENT_REPO_TOKEN", "")
        gh_owner = os.environ.get("GITHUB_CONTENT_OWNER", "quantam101")
        gh_repo = os.environ.get("GITHUB_CONTENT_REPO", "content")
        if gh_token:
            try:
                path = f"posts/{filename}"
                b64 = base64.b64encode(jekyll_content.encode()).decode()
                # Check for existing SHA
                sha = None
                async with httpx.AsyncClient(timeout=15) as client:
                    r = await client.get(
                        f"{GH_BASE}/repos/{gh_owner}/{gh_repo}/contents/{path}",
                        headers={"Authorization": f"token {gh_token}", "User-Agent": "AlreadyHereCmdOS/1.0"},
                        params={"ref": "main"},
                    )
                    if r.status_code == 200:
                        sha = r.json().get("sha")
                    payload: dict[str, Any] = {
                        "message": f"Add post: {article.get('title', 'untitled')}",
                        "content": b64,
                        "branch": "main",
                    }
                    if sha:
                        payload["sha"] = sha
                    r2 = await client.put(
                        f"{GH_BASE}/repos/{gh_owner}/{gh_repo}/contents/{path}",
                        headers={"Authorization": f"token {gh_token}", "User-Agent": "AlreadyHereCmdOS/1.0"},
                        json=payload,
                    )
                    if r2.status_code in (200, 201):
                        result["github_url"] = f"https://{gh_owner}.github.io/{gh_repo}/posts/{filename.replace('.md', '.html')}"
                        logger.info("ContentAgent: GitHub Pages → %s", result["github_url"])
            except Exception as e:
                logger.warning("ContentAgent: GitHub publish failed: %s", e)

        # Dev.to
        devto_key = os.environ.get("DEVTO_API_KEY", "")
        if devto_key:
            try:
                body = article.get("body", "")
                meta = article.get("meta_description", "")
                body_md = f"> {meta}\n\n{body}" if meta else body
                payload = {
                    "article": {
                        "title": article.get("title", ""),
                        "published": True,
                        "body_markdown": body_md,
                        "tags": article.get("tags", []),
                    }
                }
                if result.get("github_url"):
                    payload["article"]["canonical_url"] = result["github_url"]
                async with httpx.AsyncClient(timeout=20) as client:
                    r = await client.post(
                        f"{DEVTO_BASE}/articles",
                        headers={"api-key": devto_key, "Content-Type": "application/json"},
                        json=payload,
                    )
                    if r.status_code in (200, 201):
                        result["devto_url"] = r.json().get("url", "")
                        logger.info("ContentAgent: Dev.to → %s", result["devto_url"])
            except Exception as e:
                logger.warning("ContentAgent: Dev.to publish failed: %s", e)

        return result

    def _make_jekyll_post(self, article: dict, date_str: str) -> str:
        title = article.get("title", "Untitled").replace('"', '\\"')
        meta = article.get("meta_description", "").replace('"', '\\"')
        tags = article.get("tags", [])
        body = article.get("body", "")
        tags_yaml = "\n".join(f"  - {t}" for t in tags)
        return (
            f"---\n"
            f'title: "{title}"\n'
            f'description: "{meta}"\n'
            f"date: {date_str}\n"
            f"tags:\n{tags_yaml}\n"
            f"layout: post\n"
            f"---\n\n{body}\n"
        )
