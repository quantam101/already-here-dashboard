"""
Content Sync — Bridge between Already Here Growth Command OS and ProfitEngine.

Routes:
  GET  /api/content-sync/topics        — ProfitEngine pulls queued topics from Growth Vault
  POST /api/content-sync/published     — ProfitEngine posts back when an article goes live
  GET  /api/content-sync/log           — Content ledger: all published articles
  POST /api/content-sync/queue-topic   — Manually queue a topic for next ProfitEngine run
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_DB = Path(__file__).parent.parent / "data" / "content_sync.db"


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(_DB))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    return c


def _ensure_tables() -> None:
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS topic_queue (
                id        TEXT PRIMARY KEY,
                topic     TEXT NOT NULL,
                source    TEXT DEFAULT 'manual',  -- manual | growth_vault | product_factory | work_orders
                source_id TEXT,
                priority  INTEGER DEFAULT 5,       -- 1 (urgent) - 10 (low)
                status    TEXT DEFAULT 'queued',   -- queued | published | skipped
                created_at TEXT,
                used_at   TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS published_log (
                id           TEXT PRIMARY KEY,
                title        TEXT,
                topic        TEXT,
                canonical_url TEXT,
                devto_url    TEXT,
                medium_url   TEXT,
                hashnode_url TEXT,
                platforms    TEXT,   -- JSON list of platforms published to
                published_at TEXT,
                source       TEXT DEFAULT 'profitengine'
            )
        """)
        c.commit()


_ensure_tables()


# ── Models ─────────────────────────────────────────────────────────────────

class TopicQueueIn(BaseModel):
    topic: str
    source: Optional[str] = "manual"
    source_id: Optional[str] = None
    priority: Optional[int] = 5


class PublishedArticle(BaseModel):
    title: str
    topic: Optional[str] = ""
    canonical_url: Optional[str] = ""
    devto_url: Optional[str] = ""
    medium_url: Optional[str] = ""
    hashnode_url: Optional[str] = ""
    platforms: Optional[list] = []


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/topics")
async def get_queued_topics(limit: int = 5):
    """
    ProfitEngine calls this before each daily publish run.
    Returns highest-priority queued topics, falling back to Growth Vault ideas.
    """
    topics = []
    now = datetime.now(timezone.utc).isoformat()

    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM topic_queue WHERE status='queued' ORDER BY priority ASC, created_at ASC LIMIT ?",
            (limit,)
        ).fetchall()
        topics = [{"id": r["id"], "topic": r["topic"], "source": r["source"], "priority": r["priority"]}
                  for r in rows]

    # If queue is empty, pull unactioned Growth Vault ideas
    if not topics:
        vault_db = Path(__file__).parent.parent / "data" / "growth_vault.db"
        if vault_db.exists():
            try:
                vc = sqlite3.connect(str(vault_db))
                vc.row_factory = sqlite3.Row
                vault_rows = vc.execute(
                    "SELECT id, title FROM growth_vault WHERE status='captured' AND category IN "
                    "('product_idea','opportunity','tool') ORDER BY value_score DESC, created_at ASC LIMIT ?",
                    (limit,)
                ).fetchall()
                vc.close()
                for r in vault_rows:
                    topics.append({
                        "id": r["id"],
                        "topic": f"How to Use {r['title']} for Passive Income in 2026"
                                 if len(r["title"]) < 60 else r["title"],
                        "source": "growth_vault",
                        "priority": 5,
                    })
            except Exception:
                pass

    return {"topics": topics, "count": len(topics)}


@router.post("/published")
async def log_published(article: PublishedArticle):
    """
    ProfitEngine calls this after every successful publish.
    Logs the article and marks the topic as used if it came from the queue.
    """
    now = datetime.now(timezone.utc).isoformat()
    article_id = str(uuid.uuid4())

    with _conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO published_log
               (id, title, topic, canonical_url, devto_url, medium_url, hashnode_url, platforms, published_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (article_id, article.title, article.topic, article.canonical_url,
             article.devto_url, article.medium_url, article.hashnode_url,
             str(article.platforms), now)
        )
        # Mark queue topic as published if it matches
        if article.topic:
            c.execute(
                "UPDATE topic_queue SET status='published', used_at=? WHERE topic=? AND status='queued'",
                (now, article.topic)
            )
        c.commit()

    return {"ok": True, "id": article_id, "logged_at": now}


@router.get("/log")
async def get_published_log(limit: int = 20):
    """Content ledger — all articles published via ProfitEngine."""
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM published_log ORDER BY published_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"articles": [dict(r) for r in rows], "count": len(rows)}


@router.post("/queue-topic")
async def queue_topic(req: TopicQueueIn):
    """Manually add a topic to the ProfitEngine content queue."""
    now = datetime.now(timezone.utc).isoformat()
    topic_id = str(uuid.uuid4())
    with _conn() as c:
        c.execute(
            """INSERT INTO topic_queue (id, topic, source, source_id, priority, created_at)
               VALUES (?,?,?,?,?,?)""",
            (topic_id, req.topic, req.source, req.source_id, req.priority, now)
        )
        c.commit()
    return {"ok": True, "id": topic_id, "topic": req.topic}
