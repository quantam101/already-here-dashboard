"""
Scout Agent - Discovers viral content, work opportunities, grants, contracts.

ZERO-COST sources only (Cost Guard compliant):
  - Reddit JSON API (no auth required for reads, just User-Agent)
  - HackerNews Firebase API (free, no auth)
  - Grants.gov RSS feed (free)
  - Google News RSS (free)
  - SAM.gov public search (free GET, no key needed for /opportunities preview)

All endpoints return structured opportunities. Operator + content agents can
queue them as ContentIdeas, or the Proposal Engine can use grants/contracts
to draft responses.
"""
import asyncio
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()

DEFAULT_TIMEOUT = 8.0   # per-request timeout (seconds)
HN_ITEM_TIMEOUT = 5.0  # tighter timeout for individual HN item fetches
VIRAL_ENDPOINT_TIMEOUT = 20.0  # overall budget for the /viral endpoint
USER_AGENT = "AlreadyHere-Command-OS/1.0 (zero-spend scout)"


class Opportunity(BaseModel):
    id: str
    title: str
    source: str  # reddit | hackernews | grants_gov | google_news | sam_gov
    kind: str  # viral | grant | contract | news
    url: str
    score: float | None = None
    summary: str | None = None
    posted_at: str | None = None
    metadata: dict = {}


async def _fetch_json(url: str, headers: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
        r.raise_for_status()
        return r.json()


async def _fetch_text(url: str) -> str:
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT, follow_redirects=True) as c:
        r = await c.get(url, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text


async def _fetch_hn_item(hn_id: int) -> Opportunity | None:
    """Fetch a single HN item with a tight timeout. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=HN_ITEM_TIMEOUT, follow_redirects=True) as c:
            r = await c.get(
                f"https://hacker-news.firebaseio.com/v0/item/{hn_id}.json",
                headers={"User-Agent": USER_AGENT},
            )
            r.raise_for_status()
            story = r.json()
        if not story or not story.get("title"):
            return None
        return Opportunity(
            id=f"hn-{story.get('id')}",
            title=story.get("title", "")[:280],
            source="hackernews",
            kind="viral",
            url=story.get("url", f"https://news.ycombinator.com/item?id={story.get('id')}"),
            score=float(story.get("score", 0)),
            posted_at=datetime.fromtimestamp(story.get("time", 0), tz=UTC).isoformat()
            if story.get("time")
            else None,
            metadata={"by": story.get("by"), "descendants": story.get("descendants", 0)},
        )
    except Exception:
        return None


@router.get("/viral", response_model=list[Opportunity])
async def scout_viral(
    subreddits: str = Query("EntrepreneurRideAlong+SideProject+Entrepreneur+SmallBusiness+passive_income"),
    limit: int = 25,
):
    """Discover viral / trending content from Reddit + HackerNews.

    All external calls run concurrently within a VIRAL_ENDPOINT_TIMEOUT budget
    so this endpoint always returns within ~20s regardless of upstream latency.
    """
    items: list[Opportunity] = []

    async def _reddit() -> list[Opportunity]:
        try:
            reddit = await _fetch_json(
                f"https://www.reddit.com/r/{subreddits}/hot.json?limit={limit}"
            )
            out = []
            for post in reddit.get("data", {}).get("children", []):
                d = post.get("data", {})
                out.append(Opportunity(
                    id=f"reddit-{d.get('id')}",
                    title=d.get("title", "")[:280],
                    source="reddit",
                    kind="viral",
                    url=f"https://reddit.com{d.get('permalink', '')}",
                    score=float(d.get("score", 0)),
                    summary=(d.get("selftext", "") or "")[:500],
                    posted_at=datetime.fromtimestamp(d.get("created_utc", 0), tz=UTC).isoformat()
                    if d.get("created_utc")
                    else None,
                    metadata={"subreddit": d.get("subreddit"), "comments": d.get("num_comments", 0)},
                ))
            return out
        except Exception as e:
            return [Opportunity(
                id="reddit-error", title=f"Reddit fetch error: {e}", source="reddit",
                kind="viral", url="https://reddit.com", metadata={"error": str(e)},
            )]

    async def _hackernews() -> list[Opportunity]:
        try:
            ids = await _fetch_json("https://hacker-news.firebaseio.com/v0/topstories.json")
            # Fetch all items concurrently — dramatically faster than sequential
            tasks = [_fetch_hn_item(hn_id) for hn_id in ids[:min(limit, 15)]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in results if isinstance(r, Opportunity)]
        except Exception as e:
            return [Opportunity(
                id="hn-error", title=f"HackerNews fetch error: {e}", source="hackernews",
                kind="viral", url="https://news.ycombinator.com", metadata={"error": str(e)},
            )]

    # Run Reddit + HackerNews concurrently, with a hard overall timeout
    try:
        reddit_items, hn_items = await asyncio.wait_for(
            asyncio.gather(_reddit(), _hackernews()),
            timeout=VIRAL_ENDPOINT_TIMEOUT,
        )
        items = list(reddit_items) + list(hn_items)
    except TimeoutError:
        items = [Opportunity(
            id="viral-timeout", title="Scout timed out — upstream APIs slow, try again",
            source="scout", kind="viral", url="", metadata={"timeout": VIRAL_ENDPOINT_TIMEOUT},
        )]

    items.sort(key=lambda x: x.score or 0, reverse=True)
    return items[:limit]


def _parse_rss(xml_text: str, source: str, kind: str, limit: int) -> list[Opportunity]:
    out: list[Opportunity] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        return [Opportunity(
            id=f"{source}-parse-error", title=f"RSS parse error: {e}",
            source=source, kind=kind, url="", metadata={"error": str(e)},
        )]
    channel = root.find("channel") or root
    for i, item in enumerate(channel.findall(".//item")[:limit]):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        guid = (item.findtext("guid") or f"{source}-{i}").strip()
        out.append(Opportunity(
            id=f"{source}-{guid[:64]}", title=title[:280], source=source, kind=kind,
            url=link, summary=desc[:500], posted_at=pub or None,
        ))
    return out


@router.get("/grants", response_model=list[Opportunity])
async def scout_grants(limit: int = 25):
    """Federal grants from Grants.gov (FREE). Falls back to Google News RSS."""
    # Try Grants.gov XML feed first, then Google News fallback
    urls = [
        "https://www.grants.gov/rss/GG_NewOppByCategory.xml",
        "https://news.google.com/rss/search?q=federal+grant+opportunity+SBA&hl=en-US&gl=US&ceid=US:en",
    ]
    for url in urls:
        try:
            xml_text = await _fetch_text(url)
            items = _parse_rss(xml_text, "grants_gov" if "grants.gov" in url else "google_news", "grant", limit)
            if items and not any("parse error" in (i.title or "").lower() for i in items):
                return items
        except Exception:
            continue
    return [Opportunity(
        id="grants-empty", title="No grants returned - try again or check connection",
        source="grants_gov", kind="grant", url="https://grants.gov",
    )]


@router.get("/contracts", response_model=list[Opportunity])
async def scout_contracts(
    keywords: str = Query("small business technology innovation"),
    limit: int = 25,
):
    """Federal contracts via SAM.gov public opportunities search (FREE preview)."""
    q = quote_plus(keywords)
    try:
        # SAM.gov has a public JSON endpoint that returns recent opportunities
        url = f"https://sam.gov/api/prod/sgs/v1/search/?index=opp&q={q}&page=0&size={limit}"
        data = await _fetch_json(url)
        out: list[Opportunity] = []
        embedded = data.get("_embedded", {}).get("results", [])
        for r in embedded[:limit]:
            out.append(Opportunity(
                id=f"sam-{r.get('_id', r.get('noticeId', ''))}",
                title=(r.get("title") or "")[:280],
                source="sam_gov",
                kind="contract",
                url=f"https://sam.gov/opp/{r.get('_id', '')}/view",
                summary=(r.get("descriptions", [{}])[0].get("content", "") if r.get("descriptions") else "")[:500],
                posted_at=r.get("postedDate"),
                metadata={
                    "agency": r.get("organizationHierarchy", [{}])[0].get("name") if r.get("organizationHierarchy") else None,
                    "type": r.get("type"),
                    "naics": r.get("naicsCode"),
                },
            ))
        return out
    except Exception as e:
        # Fallback: Google News RSS for "federal contract" keywords
        try:
            url = f"https://news.google.com/rss/search?q={q}+contract+opportunity&hl=en-US&gl=US&ceid=US:en"
            xml_text = await _fetch_text(url)
            return _parse_rss(xml_text, "google_news", "contract", limit)
        except Exception as e2:
            return [Opportunity(
                id="contracts-error", title=f"Contracts fetch error: {e} / {e2}",
                source="sam_gov", kind="contract", url="https://sam.gov",
                metadata={"error": str(e), "fallback_error": str(e2)},
            )]


@router.get("/news", response_model=list[Opportunity])
async def scout_news(query: str = Query("AI automation startup"), limit: int = 25):
    """Free trending news via Google News RSS."""
    q = quote_plus(query)
    try:
        url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        xml_text = await _fetch_text(url)
        return _parse_rss(xml_text, "google_news", "news", limit)
    except Exception as e:
        return [Opportunity(
            id="news-error", title=f"News fetch error: {e}",
            source="google_news", kind="news", url="https://news.google.com",
            metadata={"error": str(e)},
        )]


@router.get("/sources")
async def list_sources():
    """All scout data sources - all FREE, no auth, Cost Guard compliant."""
    return {
        "sources": [
            {"id": "reddit", "name": "Reddit", "cost": "$0", "auth": "none", "rate_limit": "60/min"},
            {"id": "hackernews", "name": "HackerNews", "cost": "$0", "auth": "none", "rate_limit": "unlimited"},
            {"id": "grants_gov", "name": "Grants.gov", "cost": "$0", "auth": "none", "rate_limit": "fair use"},
            {"id": "sam_gov", "name": "SAM.gov", "cost": "$0", "auth": "none for preview", "rate_limit": "fair use"},
            {"id": "google_news", "name": "Google News RSS", "cost": "$0", "auth": "none", "rate_limit": "fair use"},
        ],
    }
