"""
Revenue Ledger - Immutable proof-of-work record of REAL earnings.

Every entry is an attested earning event from a revenue stream.
Sources: manual operator entry, CSV import, webhook ingest.
This is the single source of truth for revenue actuals (vs. seeded targets).

Goal: $25,000 net profit -> commercialization unlock.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
import csv
import io

from services.audit_service import log_audit_event

router = APIRouter()

PROFIT_GOAL_USD = 25000.0


class LedgerEntryCreate(BaseModel):
    stream_id: str
    occurred_on: str  # ISO date YYYY-MM-DD
    gross_amount: float = Field(ge=0)
    net_amount: float = Field(ge=0)
    currency: str = "USD"
    source: str = "manual"  # manual | csv | webhook | api
    proof_url: Optional[str] = None  # screenshot, dashboard URL, csv hash
    notes: Optional[str] = None


class LedgerEntry(LedgerEntryCreate):
    id: str = Field(default_factory=lambda: f"led-{uuid.uuid4().hex[:10]}")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


async def get_db():
    from server import db
    return db


@router.post("/", response_model=LedgerEntry, status_code=201)
async def create_ledger_entry(entry: LedgerEntryCreate, db=Depends(get_db)):
    """Record a real earning event. Immutable - no PATCH/DELETE."""
    stream = await db.revenue_streams.find_one({"id": entry.stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail=f"Revenue stream '{entry.stream_id}' not found")

    if entry.net_amount > entry.gross_amount:
        raise HTTPException(status_code=400, detail="net_amount cannot exceed gross_amount")

    record = LedgerEntry(**entry.model_dump())
    doc = record.model_dump()
    await db.revenue_ledger.insert_one(doc)
    await log_audit_event(
        db, "ledger.entry.recorded", "operator", "record",
        "ledger_entry", record.id,
        metadata={"stream_id": entry.stream_id, "net": entry.net_amount, "source": entry.source},
    )
    return record


@router.get("/", response_model=list[LedgerEntry])
async def list_ledger_entries(
    stream_id: Optional[str] = None,
    since_days: Optional[int] = None,
    limit: int = 500,
    db=Depends(get_db),
):
    """List ledger entries with optional filters."""
    query: dict = {}
    if stream_id:
        query["stream_id"] = stream_id
    if since_days is not None and since_days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).date().isoformat()
        query["occurred_on"] = {"$gte": cutoff}
    cursor = db.revenue_ledger.find(query, {"_id": 0}).sort("occurred_on", -1).limit(limit)
    return await cursor.to_list(limit)


@router.get("/stats/profit-progress")
async def profit_progress(db=Depends(get_db)):
    """Aggregate net profit toward the $25K commercialization goal."""
    entries = await db.revenue_ledger.find({}, {"_id": 0}).to_list(10000)
    total_net = sum(e.get("net_amount", 0.0) for e in entries)
    total_gross = sum(e.get("gross_amount", 0.0) for e in entries)

    today = datetime.now(timezone.utc).date()
    month_start = today.replace(day=1).isoformat()
    last30 = (today - timedelta(days=30)).isoformat()

    monthly_net = sum(
        e.get("net_amount", 0.0) for e in entries
        if e.get("occurred_on", "0000") >= month_start
    )
    last30_net = sum(
        e.get("net_amount", 0.0) for e in entries
        if e.get("occurred_on", "0000") >= last30
    )

    by_stream: dict[str, float] = {}
    for e in entries:
        sid = e.get("stream_id", "unknown")
        by_stream[sid] = by_stream.get(sid, 0.0) + e.get("net_amount", 0.0)

    return {
        "goal_usd": PROFIT_GOAL_USD,
        "total_net": round(total_net, 2),
        "total_gross": round(total_gross, 2),
        "monthly_net": round(monthly_net, 2),
        "last30_net": round(last30_net, 2),
        "progress_pct": round(min(100.0, (total_net / PROFIT_GOAL_USD * 100.0) if PROFIT_GOAL_USD else 0), 2),
        "remaining_usd": round(max(0.0, PROFIT_GOAL_USD - total_net), 2),
        "entry_count": len(entries),
        "unlocked": total_net >= PROFIT_GOAL_USD,
        "by_stream": {k: round(v, 2) for k, v in by_stream.items()},
    }


@router.get("/stats/by-stream")
async def stats_by_stream(db=Depends(get_db)):
    """Per-stream aggregated net + entry count."""
    pipeline = [
        {"$group": {
            "_id": "$stream_id",
            "total_net": {"$sum": "$net_amount"},
            "total_gross": {"$sum": "$gross_amount"},
            "entry_count": {"$sum": 1},
            "last_entry": {"$max": "$occurred_on"},
        }},
    ]
    rows = await db.revenue_ledger.aggregate(pipeline).to_list(1000)
    return [
        {
            "stream_id": r["_id"],
            "total_net": round(r["total_net"], 2),
            "total_gross": round(r["total_gross"], 2),
            "entry_count": r["entry_count"],
            "last_entry": r.get("last_entry"),
        }
        for r in rows
    ]



@router.post("/import-csv")
async def import_ledger_csv(
    stream_id: str = Form(...),
    file: UploadFile = File(...),
    date_column: str = Form("date"),
    gross_column: str = Form("gross"),
    net_column: str = Form("net"),
    source_label: str = Form("csv"),
    db=Depends(get_db),
):
    """Bulk-import earnings from a CSV file.

    Expected CSV: header row with at least `date`, `gross`, `net` columns
    (case-insensitive, customisable via form fields). Each row becomes one
    ledger entry. Creates an audit event with import filename + row count.
    """
    stream = await db.revenue_streams.find_one({"id": stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail=f"Revenue stream '{stream_id}' not found")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty CSV")
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot decode CSV: {e}") from e

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no header row")

    # Normalise column lookup (case-insensitive)
    norm = {h.lower().strip(): h for h in reader.fieldnames}
    date_key = norm.get(date_column.lower())
    gross_key = norm.get(gross_column.lower())
    net_key = norm.get(net_column.lower())
    if not (date_key and gross_key and net_key):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns '{date_column}', '{gross_column}', '{net_column}' (case-insensitive). Found: {reader.fieldnames}",
        )

    entries: list[dict] = []
    errors: list[str] = []
    for i, row in enumerate(reader, start=2):  # data starts on line 2
        try:
            occurred = (row.get(date_key) or "").strip()[:10]
            if not occurred:
                continue
            gross = float(str(row.get(gross_key, "0")).replace("$", "").replace(",", "").strip() or 0)
            net = float(str(row.get(net_key, "0")).replace("$", "").replace(",", "").strip() or 0)
            if net > gross:
                errors.append(f"row {i}: net>{gross} > gross={gross}")
                continue
            entries.append({
                "id": f"led-{uuid.uuid4().hex[:10]}",
                "stream_id": stream_id,
                "occurred_on": occurred,
                "gross_amount": gross,
                "net_amount": net,
                "currency": "USD",
                "source": source_label,
                "proof_url": f"csv://{file.filename}",
                "notes": f"row {i} of {file.filename}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as exc:
            errors.append(f"row {i}: {exc}")

    if entries:
        await db.revenue_ledger.insert_many(entries)
    await log_audit_event(
        db, "ledger.csv.imported", "operator", "import",
        "ledger_csv", file.filename or "upload.csv",
        metadata={"stream_id": stream_id, "rows_imported": len(entries), "errors": len(errors)},
    )

    return {
        "imported": len(entries),
        "errors": errors,
        "filename": file.filename,
        "stream_id": stream_id,
    }
