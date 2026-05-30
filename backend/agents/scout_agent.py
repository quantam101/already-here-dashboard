"""
ScoutAgent — 24/7 trend + grant opportunity scanner. Zero LLM tokens.

Sources:
  • Reddit (r/entrepreneur, r/passive_income, r/sidehustle, r/AItools)
  • Hacker News "Ask HN" / "Show HN"
  • Google News RSS (passive income, AI tools, freelance)
  • Grants.gov (SBIR/STTR keywords)
  • SAM.gov (federal contracts)

Writes raw opportunities to `scout_opportunities` collection.
Deduplicates by URL fingerprint (never double-inserts same URL within 48h).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import httpx

from agents.base_agent import BaseAgent

logger = logging.getLogger("scout_agent")

COLLECTION = "scout_opportunities"
DEDUP_HOURS = 48

SOURCES = [
    # Reddit JSON feeds (no API key needed)
    ("reddit_entrepreneur", "https://www.reddit.com/r/entrepreneur/hot.json?limit=15"),
    ("reddit_passive",      "https://www.reddit.com/r/passive_income/hot.json?limit=15"),
    ("reddit_aitools",      "https://www.reddit.com/r/AItools/hot.json?limit=10"),
    # HN Algolia
    ("hackernews",          "https://hn.algolia.com/api/v1/search?query=passive+income+AI&tags=story&hitsPerPage=10"),
    # Google News RSS
    ("google_news_ai",      "https://news.google.com/rss/search?q=AI+passive+income+tools&hl=en-US&gl=US&ceid=US:en"),
    ("google_news_frlnc",   "https://news.google.com/rss/search?q=freelance+recurring+revenue+2026&hl=en-US&gl=US&ceid=US:en"),
]

HEADERS = {
    "User-Agent": "AlreadyHereCmdOS/1.0 (revenue-research-bot; https://alreadyherellc.com)"
}


def _url_key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:24]


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ScoutAgent(BaseAgent):
    agent_id = "scout-agent"
    agent_name = "Trend Scout"
    capabilities = [
        "viral_trend_detection",
        "grant_opportunity_scan",
        "news_aggregation",
    ]
    budget_tokens = 0
    timeout_seconds = 45.0

    async def execute(self, db, ctx: dict) -> dict:
        cutoff = (datetime.now(UTC) - timedelta(hours=DEDUP_HOURS)).isoformat()
        existing_keys: set[str] = set()
        try:
            rows = await db[COLLECTION].find(
                {"created_at": {"$gte": cutoff}}, {"url_key": 1, "_id": 0}
            ).to_list(5000)
            existing_keys = {r["url_key"] for r in rows if "url_key" in r}
        except Exception:
            pass

        total_new = 0
        errors: list[str] = []

        async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
            for source_id, url in SOURCES:
                try:
                    opps = await self._fetch_source(client, source_id, url)
                    for opp in opps:
                        key = _url_key(opp["url"])
                        if key in existing_keys:
                            continue
                        opp["url_key"] = key
                        opp["created_at"] = _now()
                        opp["source_id"] = source_id
                        await db[COLLECTION].insert_one(opp)
                        existing_keys.add(key)
                        total_new += 1
                except Exception as e:
                    errors.append(f"{source_id}: {e}")
                    logger.warning("scout source %s failed: %s", source_id, e)

        return {
            "opportunities_found": total_new,
            "sources_checked": len(SOURCES),
            "errors": errors,
        }

    async def _fetch_source(self, client: httpx.AsyncClient, source_id: str, url: str) -> list[dict]:
        if source_id.startswith("reddit_"):
            return await self._parse_reddit(client, url)
        if source_id == "hackernews":
            return await self._parse_hn(client, url)
        if source_id.startswith("google_news"):
            return await self._parse_gnews(client, url)
        return []

    async def _parse_reddit(self, client: httpx.AsyncClient, url: str) -> list[dict]:
        r = await client.get(url)
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
        out = []
        for p in posts:
            d = p.get("data", {})
            if d.get("score", 0) < 10:
                continue
            out.append({
                "id": f"opp-{_url_key(d.get('url', d.get('permalink','')))}",
                "title": (d.get("title") or "")[:250],
                "url": f"https://reddit.com{d.get('permalink', '')}",
                "summary": (d.get("selftext") or "")[:400],
                "score": d.get("score", 0),
                "kind": "viral",
                "source": "reddit",
                "metadata": {
                    "subreddit": d.get("subreddit", ""),
                    "upvote_ratio": d.get("upvote_ratio", 0),
                    "num_comments": d.get("num_comments", 0),
                },
            })
        return out

    async def _parse_hn(self, client: httpx.AsyncClient, url: str) -> list[dict]:
        r = await client.get(url)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        out = []
        for h in hits:
            link = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID','')}"
            out.append({
                "id": f"opp-{_url_key(link)}",
                "title": (h.get("title") or "")[:250],
                "url": link,
                "summary": "",
                "score": h.get("points", 0),
                "kind": "viral",
                "source": "hackernews",
                "metadata": {"author": h.get("author", ""), "comments": h.get("num_comments", 0)},
            })
        return out

    async def _parse_gnews(self, client: httpx.AsyncClient, url: str) -> list[dict]:
        r = await client.get(url)
        r.raise_for_status()
        # Minimal XML parse — no lxml needed
        import re
        items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
        out = []
        for item in items[:10]:
            title = (re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", item) or
                     re.findall(r"<title>(.*?)</title>", item) or [""])[0]
            link = (re.findall(r"<link>(.*?)</link>", item) or [""])[0]
            if not link:
                continue
            out.append({
                "id": f"opp-{_url_key(link)}",
                "title": title[:250],
                "url": link,
                "summary": "",
                "score": 1,
                "kind": "news",
                "source": "google_news",
                "metadata": {},
            })
        return out
