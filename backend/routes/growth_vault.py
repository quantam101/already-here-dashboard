"""
Growth Vault -- Phase 2 Growth Command OS
Routes:
  POST /api/growth-vault/capture  -- save an idea/tool/opportunity
  GET  /api/growth-vault          -- list all vault entries (filterable by category)
  POST /api/growth-vault/distill  -- extract key value + monetization angle via LLM
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "growth_vault.db"

VALID_CATEGORIES = {"tool", "product_idea", "opportunity", "prompt", "template", "resource"}
VALID_STATUSES = {"captured", "reviewed", "actioned", "archived"}


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS growth_vault (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                category TEXT,
                source_url TEXT,
                tags TEXT,
                monetization_angle TEXT,
                value_score INTEGER DEFAULT 0,
                status TEXT DEFAULT 'captured',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()


_ensure_table()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CaptureRequest(BaseModel):
    title: str
    description: str | None = ""
    category: str | None = "resource"
    source_url: str | None = ""
    tags: str | None = ""


class DistillRequest(BaseModel):
    url: str | None = ""
    text: str | None = ""
    title: str | None = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/capture")
async def capture_idea(req: CaptureRequest):
    """Save a new idea/tool/opportunity to the Growth Vault."""
    category = req.category if req.category in VALID_CATEGORIES else "resource"
    now = datetime.now(UTC).isoformat()
    entry_id = str(uuid.uuid4())

    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO growth_vault
            (id, title, description, category, source_url, tags,
             monetization_angle, value_score, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, 0, 'captured', ?, ?)
        """, (entry_id, req.title, req.description, category,
              req.source_url, req.tags, now, now))
        conn.commit()

    return {
        "id": entry_id,
        "status": "captured",
        "message": "Entry saved to Growth Vault",
    }


@router.get("")
async def list_vault(category: str | None = None, limit: int = 100):
    """List all vault entries, optionally filtered by category."""
    with _get_conn() as conn:
        if category and category != "all":
            rows = conn.execute(
                "SELECT * FROM growth_vault WHERE category = ? ORDER BY created_at DESC LIMIT ?",
                (category, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM growth_vault ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

    return {
        "entries": [dict(r) for r in rows],
        "total": len(rows),
        "category_filter": category,
    }


@router.post("/distill")
async def distill_entry(req: DistillRequest, request: Request):
    """Use LLM to extract key value + monetization angle from a URL or text."""
    content = req.text or ""
    source_url = req.url or ""

    # Fetch URL content if provided and no text supplied
    if source_url and not content:
        try:
            import urllib.request
            with urllib.request.urlopen(source_url, timeout=10) as resp:
                raw = resp.read(8000).decode("utf-8", errors="replace")
            # Strip HTML tags simply
            import re
            raw = re.sub(r"<[^>]+>", " ", raw)
            raw = re.sub(r"\s+", " ", raw).strip()
            content = raw[:3000]
        except Exception as e:
            log.warning("URL fetch failed for distill: %s", e)
            content = f"URL: {source_url}"

    if not content:
        return {"error": "Provide url or text for distillation"}

    title = req.title or source_url or "Untitled"
    monetization_angle = ""
    description = content[:300]
    value_score = 0

    try:
        db = request.app.state.db
        from services.llm_runner import run_cached
        prompt = (
            f"Analyze this content and respond in plain text with exactly two labeled lines:\n"
            f"VALUE: <one sentence key takeaway>\n"
            f"MONETIZATION: <one sentence monetization angle for an IT freelancer / small business owner>\n\n"
            f"Content:\n{content[:2000]}"
        )
        llm_text = await run_cached(
            db, "auto", "auto",
            "You are a business analyst helping a freelancer identify actionable value.",
            prompt,
            session_id=f"distill-{str(uuid.uuid4())[:8]}",
        )
        if llm_text:
            import re
            vm = re.search(r"VALUE:\s*(.+)", llm_text, re.I)
            mm = re.search(r"MONETIZATION:\s*(.+)", llm_text, re.I)
            if vm:
                description = vm.group(1).strip()
            if mm:
                monetization_angle = mm.group(1).strip()
            value_score = 70 if (vm and mm) else 40
    except Exception as e:
        log.warning("LLM distill skipped: %s", e)

    now = datetime.now(UTC).isoformat()
    entry_id = str(uuid.uuid4())

    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO growth_vault
            (id, title, description, category, source_url, tags,
             monetization_angle, value_score, status, created_at, updated_at)
            VALUES (?, ?, ?, 'resource', ?, '', ?, ?, 'captured', ?, ?)
        """, (entry_id, title, description, source_url,
              monetization_angle, value_score, now, now))
        conn.commit()

    return {
        "id": entry_id,
        "title": title,
        "description": description,
        "monetization_angle": monetization_angle,
        "value_score": value_score,
        "status": "captured",
    }
