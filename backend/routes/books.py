"""
Books & Long-Form Agent - Generates books, ebooks, manuals, journals, workbooks.

Output formats: markdown (downloadable), plain text (for browser audiobook playback
via Web Speech API SpeechSynthesis - $0 cost, runs on operator's device).

Generation: chapter-by-chapter via litellm (Gemini 3 Flash by default, $0-cheap, BYO key).
Stored in MongoDB `books` collection; downloadable from frontend.

Adds a new revenue stream: rev-books.
"""
import os
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field

from services import governance_service as gov
from services.audit_service import log_audit_event
from services.llm_runner import run_cached

router = APIRouter()

ALLOWED_BOOK_TYPES = {"ebook", "manual", "journal", "workbook", "guide", "memoir"}
DEFAULT_CHAPTER_COUNT = 6
MAX_CHAPTER_COUNT = 20
REVENUE_STREAM_BOOKS = "rev-books"

BOOK_SYSTEM_MSG = "You are an expert author and editor. Write clear, valuable, well-structured content."


class BookCreateRequest(BaseModel):
    title: str
    book_type: str = "ebook"
    audience: str = "general"
    tone: str = "professional"  # professional | conversational | inspirational | technical
    word_target_per_chapter: int = 800
    chapter_count: int = DEFAULT_CHAPTER_COUNT
    outline_hints: list[str] = Field(default_factory=list)
    instructions: str | None = None


class BookChapter(BaseModel):
    number: int
    title: str
    content: str
    word_count: int = 0


class Book(BaseModel):
    id: str = Field(default_factory=lambda: f"book-{uuid.uuid4().hex[:10]}")
    title: str
    book_type: str
    audience: str
    tone: str
    status: str = "drafting"  # drafting | complete | failed
    chapters: list[BookChapter] = Field(default_factory=list)
    total_word_count: int = 0
    download_count: int = 0
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


async def get_db():
    from server import db
    return db


def _validate_book_type(book_type: str) -> None:
    if book_type not in ALLOWED_BOOK_TYPES:
        raise HTTPException(status_code=400, detail=f"book_type must be one of {sorted(ALLOWED_BOOK_TYPES)}")


async def _ensure_books_stream(db):
    """Ensure rev-books revenue stream exists."""
    if await db.revenue_streams.find_one({"id": REVENUE_STREAM_BOOKS}):
        return
    now = datetime.now(UTC).isoformat()
    await db.revenue_streams.insert_one({
        "id": REVENUE_STREAM_BOOKS, "name": "Books & Ebooks", "type": "content",
        "status": "active", "monthly_target": 3000.0, "monthly_actual": 0.0,
        "description": "AI-generated books, manuals, journals - sold on Amazon KDP, Gumroad, direct",
        "metadata": {"cost_class": "free_local", "delivery": "PDF/EPUB/audio"},
        "created_at": now, "updated_at": now,
    })


def _build_outline_prompt(req: BookCreateRequest) -> str:
    hints = "\n".join(f"- {h}" for h in req.outline_hints) if req.outline_hints else "- (none)"
    return f"""You are an expert {req.book_type} author. Generate an outline for:

TITLE: {req.title}
AUDIENCE: {req.audience}
TONE: {req.tone}
CHAPTER COUNT: {req.chapter_count}
WORD TARGET PER CHAPTER: ~{req.word_target_per_chapter}

HINTS:
{hints}

ADDITIONAL INSTRUCTIONS:
{req.instructions or '(none)'}

Output strictly as a JSON array of objects, each with "number" (int) and "title" (string).
Do NOT include any prose, just the JSON array. Example:
[{{"number": 1, "title": "Introduction"}}, {{"number": 2, "title": "..."}}]"""


def _build_chapter_prompt(req: BookCreateRequest, chapter: dict, prev_titles: list[str]) -> str:
    prev = "\n".join(f"- Chapter {i+1}: {t}" for i, t in enumerate(prev_titles)) or "(none yet)"
    return f"""You are an expert {req.book_type} author writing in a {req.tone} tone for {req.audience}.

BOOK TITLE: {req.title}
CHAPTER {chapter['number']}: {chapter['title']}
WORD TARGET: ~{req.word_target_per_chapter}

PREVIOUS CHAPTERS (for continuity):
{prev}

Write Chapter {chapter['number']} in clean markdown. Use headings (## sections), short paragraphs,
concrete examples, and actionable insights. Do NOT include the chapter number or title heading
(it will be added separately). Just write the chapter body."""


def _parse_outline(raw: str, fallback_count: int) -> list[dict]:
    """Robust parse of outline JSON array - falls back to numbered list."""
    import json as _json
    import re
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        parsed = _json.loads(raw[start:end])
        if isinstance(parsed, list) and parsed:
            return [{"number": int(c.get("number", i + 1)), "title": str(c.get("title", f"Chapter {i+1}"))[:200]}
                    for i, c in enumerate(parsed)]
    except Exception:
        pass
    # Fallback: extract any "1. Title" / "Chapter 1: Title" lines
    items = []
    for line in raw.splitlines():
        m = re.match(r"\s*(?:Chapter\s+)?(\d+)[\.\):]\s*(.+)", line.strip())
        if m:
            items.append({"number": int(m.group(1)), "title": m.group(2).strip()[:200]})
    if items:
        return items
    return [{"number": i + 1, "title": f"Chapter {i+1}"} for i in range(fallback_count)]


@router.post("/", status_code=202)
async def create_book(
    req: BookCreateRequest,
    http_request: Request,
    background: BackgroundTasks,
    db=Depends(get_db),
):
    """Queue book generation and return immediately (HTTP 202) with the book ID.

    Generation runs as a background task (6 chapters × ~10s each = 60–90s).
    Poll GET /api/books/{id} until status is "complete" or "failed".
    Each chapter is written to DB as it completes, so progress is visible.

    Gated on `compliance_content` (HITL required below L4).
    """
    _validate_book_type(req.book_type)
    if req.chapter_count < 1 or req.chapter_count > MAX_CHAPTER_COUNT:
        raise HTTPException(status_code=400, detail=f"chapter_count must be 1..{MAX_CHAPTER_COUNT}")

    await gov.enforce(
        db=db, request=http_request, action_id="compliance_content",
        context={"route": "books/", "book_type": req.book_type, "title": req.title[:120], "chapters": req.chapter_count},
    )

    await _ensure_books_stream(db)

    book = Book(
        title=req.title.strip(), book_type=req.book_type, audience=req.audience,
        tone=req.tone, metadata={"word_target": req.word_target_per_chapter},
    )
    await db.books.insert_one(book.model_dump())

    background.add_task(_generate_book_task, db, book.id, req)

    return {"id": book.id, "status": "drafting", "poll_url": f"/api/books/{book.id}"}


async def _generate_book_task(db, book_id: str, req: BookCreateRequest) -> None:
    """Background worker: generate outline + chapters and persist progress to DB."""
    import logging as _logging
    logger = _logging.getLogger("books")
    session = f"book_{book_id}"
    try:
        # 1) Generate outline
        outline_raw = await run_cached(
            db, "gemini", "gemini-2.5-flash",
            BOOK_SYSTEM_MSG, _build_outline_prompt(req),
            session_id=f"{session}_outline",
        )
        outline = _parse_outline(outline_raw, req.chapter_count)[:req.chapter_count]

        # 2) Generate each chapter; persist after every chapter so the poll
        #    endpoint shows real-time progress.
        chapters: list[BookChapter] = []
        prev_titles: list[str] = []
        for entry in outline:
            body = await run_cached(
                db, "gemini", "gemini-2.5-flash",
                BOOK_SYSTEM_MSG,
                _build_chapter_prompt(req, entry, prev_titles),
                session_id=f"{session}_c{entry['number']}",
            )
            word_count = len(body.split())
            chapters.append(
                BookChapter(
                    number=entry["number"], title=entry["title"],
                    content=body, word_count=word_count,
                )
            )
            prev_titles.append(entry["title"])
            # Write progress so operators can poll without waiting for all chapters
            await db.books.update_one(
                {"id": book_id},
                {"$set": {
                    "chapters": [c.model_dump() for c in chapters],
                    "updated_at": datetime.now(UTC).isoformat(),
                }},
            )

        total_words = sum(c.word_count for c in chapters)
        await db.books.update_one(
            {"id": book_id},
            {"$set": {
                "chapters": [c.model_dump() for c in chapters],
                "status": "complete",
                "total_word_count": total_words,
                "updated_at": datetime.now(UTC).isoformat(),
            }},
        )
        await log_audit_event(
            db, "book.generated", "books_agent", "create",
            "book", book_id,
            metadata={"chapters": len(chapters), "words": total_words, "type": req.book_type},
        )
        logger.info("book %s complete: %d chapters, %d words", book_id, len(chapters), total_words)
    except Exception as e:
        logger.exception("book generation failed for %s: %s", book_id, e)
        await db.books.update_one(
            {"id": book_id},
            {"$set": {
                "status": "failed",
                "metadata.error": str(e)[:500],
                "updated_at": datetime.now(UTC).isoformat(),
            }},
        )


@router.get("/", response_model=list[Book])
async def list_books(status: str | None = None, db=Depends(get_db)):
    query: dict = {}
    if status:
        query["status"] = status
    rows = await db.books.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@router.get("/{book_id}", response_model=Book)
async def get_book(book_id: str, db=Depends(get_db)):
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    return doc


def _render_markdown(book: dict) -> str:
    lines = [f"# {book.get('title')}", "", f"_{book.get('book_type', 'ebook').title()} · for {book.get('audience','general')}_", ""]
    for c in book.get("chapters", []):
        lines.append("")
        lines.append(f"## Chapter {c['number']}: {c['title']}")
        lines.append("")
        lines.append(c.get("content", ""))
    return "\n".join(lines)


def _render_plain(book: dict) -> str:
    """Plain text - perfect for browser SpeechSynthesis audiobook playback."""
    parts = [f"{book.get('title')}.", ""]
    for c in book.get("chapters", []):
        parts.append(f"Chapter {c['number']}. {c['title']}.")
        # Strip simple markdown for cleaner TTS
        body = c.get("content", "")
        for ch in ["#", "*", "_", "`"]:
            body = body.replace(ch, "")
        parts.append(body)
        parts.append("")
    return "\n".join(parts)


@router.get("/{book_id}/download.md")
async def download_markdown(book_id: str, db=Depends(get_db)):
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.books.update_one({"id": book_id}, {"$inc": {"download_count": 1}})
    md = _render_markdown(doc)
    filename = doc.get("title", "book").replace(" ", "_")[:60] + ".md"
    return Response(
        content=md, media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{book_id}/download.txt", response_class=PlainTextResponse)
async def download_plain(book_id: str, db=Depends(get_db)):
    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")
    await db.books.update_one({"id": book_id}, {"$inc": {"download_count": 1}})
    return _render_plain(doc)


@router.post("/{book_id}/audio/generate")
async def generate_audiobook(book_id: str, background: BackgroundTasks, voice_id: str | None = None, db=Depends(get_db)):
    """Kick off audiobook synthesis as a background task and return immediately.

    The proxy in front of FastAPI in many deployments times out at 60s. Books
    longer than ~600 words take longer than that through Piper TTS on CPU,
    so we run the render in the background and let the client poll for the
    MP3 via GET /audio.mp3 (returns 202 until ready, 200 + file when ready).
    """
    from pathlib import Path

    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")

    AUDIO_DIR = Path(os.environ.get("BOOKS_AUDIO_DIR", "/app/data/audiobooks"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = f"{book_id}-{voice_id or 'default'}.mp3"
    out_mp3 = AUDIO_DIR / cache_key
    lock_file = AUDIO_DIR / f"{cache_key}.lock"

    if out_mp3.exists() and out_mp3.stat().st_size > 1024:
        return {"status": "ready", "mp3_url": f"/api/books/{book_id}/audio.mp3", "cached": True}
    if lock_file.exists():
        return {"status": "rendering", "mp3_url": f"/api/books/{book_id}/audio.mp3"}

    text = _render_plain(doc)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Book has no text content")

    background.add_task(_render_audiobook_task, str(out_mp3), str(lock_file), text, voice_id)
    return {"status": "queued", "mp3_url": f"/api/books/{book_id}/audio.mp3"}


async def _render_audiobook_task(out_mp3: str, lock_file: str, text: str, voice_id: str | None) -> None:
    """Background worker that synthesises the audiobook + encodes to MP3."""
    import asyncio
    import logging
    import shutil
    from pathlib import Path

    logger = logging.getLogger("audiobook")
    out_path = Path(out_mp3)
    lock_path = Path(lock_file)
    lock_path.write_text("")
    try:
        from services.video import tts as _tts
        wav_path = out_path.with_suffix(".wav")
        await _tts.synthesize(text, wav_path, voice_id=voice_id)
        if not shutil.which("ffmpeg"):
            raise RuntimeError("ffmpeg not installed — cannot encode MP3")
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-qscale:a", "4", str(out_path),
            stderr=asyncio.subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"mp3 encode failed: {err.decode(errors='replace')[:300]}")
        try:
            wav_path.unlink()
        except OSError:
            pass
        logger.info("audiobook MP3 cached: %s (%d bytes)", out_path.name, out_path.stat().st_size)
    except Exception as e:
        logger.exception("audiobook render failed: %s", e)
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass


@router.get("/{book_id}/audio.mp3")
async def download_audiobook(book_id: str, voice_id: str | None = None, db=Depends(get_db)):
    """Stream the cached audiobook MP3 if it exists, else return 202 + job hint.

    Idempotent: the first GET kicks off the background render and returns
    202 so the client polls. Subsequent GETs stream the file when ready.
    """
    from pathlib import Path

    doc = await db.books.find_one({"id": book_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Book not found")

    AUDIO_DIR = Path(os.environ.get("BOOKS_AUDIO_DIR", "/app/data/audiobooks"))
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = f"{book_id}-{voice_id or 'default'}.mp3"
    out_mp3 = AUDIO_DIR / cache_key
    lock_file = AUDIO_DIR / f"{cache_key}.lock"

    if out_mp3.exists() and out_mp3.stat().st_size > 1024:
        await db.books.update_one({"id": book_id}, {"$inc": {"download_count": 1}})
        filename = (doc.get("title", "book").replace(" ", "_")[:60] + ".mp3")
        return FileResponse(
            out_mp3, media_type="audio/mpeg",
            filename=filename,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # Not ready yet — kick off a background render if we haven't already
    if not lock_file.exists():
        text = _render_plain(doc)
        if text.strip():
            import asyncio
            asyncio.create_task(_render_audiobook_task(str(out_mp3), str(lock_file), text, voice_id))

    raise HTTPException(
        status_code=202,
        detail={
            "status": "rendering",
            "message": "audiobook is being synthesised — poll this same URL until status=200",
            "estimated_seconds": max(int(len(_render_plain(doc).split()) / 25), 5),
        },
    )


@router.delete("/{book_id}")
async def delete_book(book_id: str, db=Depends(get_db)):
    r = await db.books.delete_one({"id": book_id})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"deleted": book_id}


@router.get("/stats/overview")
async def book_stats(db=Depends(get_db)):
    rows = await db.books.find({}, {"_id": 0}).to_list(2000)
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    total_words = 0
    total_downloads = 0
    for r in rows:
        by_type[r.get("book_type", "?")] = by_type.get(r.get("book_type", "?"), 0) + 1
        by_status[r.get("status", "?")] = by_status.get(r.get("status", "?"), 0) + 1
        total_words += r.get("total_word_count", 0)
        total_downloads += r.get("download_count", 0)
    return {
        "total_books": len(rows), "total_word_count": total_words,
        "total_downloads": total_downloads,
        "by_type": by_type, "by_status": by_status,
    }
