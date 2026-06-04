"""
Gmail Work Order Scanner -- Phase 2 Growth Command OS
Routes:
  GET  /api/gmail/scan    -- scan Gmail inbox for work order alerts
  POST /api/gmail/connect -- validate credentials and return connection status
  GET  /api/gmail/status  -- return scanner status: last_scan, emails_found, orders_scored
"""
from __future__ import annotations

import email as _email_stdlib
import imaplib
import logging
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from email.header import decode_header
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

from routes.work_orders import _score_work_order, _get_conn as _wo_get_conn

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Scanner state DB (reuse work_orders.db)
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "work_orders.db"


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_scanner_table() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gmail_scanner_status (
                id TEXT PRIMARY KEY DEFAULT 'singleton',
                last_scan TEXT,
                emails_found INTEGER DEFAULT 0,
                orders_scored INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            INSERT OR IGNORE INTO gmail_scanner_status (id, last_scan, emails_found, orders_scored)
            VALUES ('singleton', NULL, 0, 0)
        """)
        conn.commit()


_ensure_scanner_table()

# ---------------------------------------------------------------------------
# Target senders / subjects
# ---------------------------------------------------------------------------
SENDER_FILTERS = [
    "noreply@fieldnation.com",
    "noreply@workmarket.com",
]

SUBJECT_KEYWORDS = [
    "work order",
    "new assignment",
    "tech needed",
    "new opportunity",
]

# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def _imap_credentials() -> tuple[str, str]:
    user = os.environ.get("GMAIL_IMAP_USER", "")
    password = os.environ.get("GMAIL_APP_PASSWORD", "")
    return user, password


def _configured() -> bool:
    user, pw = _imap_credentials()
    return bool(user and pw)


def _decode_mime_words(s: str) -> str:
    parts = decode_header(s)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _get_email_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in cd:
                charset = part.get_content_charset() or "utf-8"
                try:
                    return part.get_payload(decode=True).decode(charset, errors="replace")
                except Exception:
                    pass
    else:
        charset = msg.get_content_charset() or "utf-8"
        try:
            return msg.get_payload(decode=True).decode(charset, errors="replace")
        except Exception:
            pass
    return ""


def _scan_imap() -> List[Dict[str, Any]]:
    """Connect via IMAP and return list of raw parsed email dicts."""
    user, password = _imap_credentials()
    results: List[Dict[str, Any]] = []

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(user, password)
        mail.select("inbox")

        # Build IMAP OR search for senders + subjects
        search_criteria = []
        for sender in SENDER_FILTERS:
            search_criteria.append(f'(FROM "{sender}")')
        for kw in SUBJECT_KEYWORDS:
            search_criteria.append(f'(SUBJECT "{kw}")')

        found_ids: set = set()
        for criterion in search_criteria:
            _, data = mail.search(None, criterion)
            if data and data[0]:
                for uid in data[0].split():
                    found_ids.add(uid)

        for uid in list(found_ids)[:50]:
            _, msg_data = mail.fetch(uid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
            if not raw:
                continue
            msg = _email_stdlib.message_from_bytes(raw)
            subject = _decode_mime_words(msg.get("Subject", ""))
            sender_raw = msg.get("From", "")
            body = _get_email_body(msg)
            results.append({
                "subject": subject,
                "sender": sender_raw,
                "body": body,
            })

        mail.logout()
    except Exception as e:
        log.warning("IMAP scan error: %s", e)

    return results


# ---------------------------------------------------------------------------
# Parsing helpers (reuse logic similar to work_orders parse-email)
# ---------------------------------------------------------------------------

def _find_dollar(text: str) -> Optional[float]:
    m = re.search(r"\$\s?([\d,]+(?:\.\d{1,2})?)", text)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"([\d,]+(?:\.\d{1,2})?)\s*(?:/hr|per hour|hourly)", text, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _find_hours(text: str) -> Optional[float]:
    m = re.search(r"([\d.]+)\s*(?:hour|hr)", text, re.I)
    return float(m.group(1)) if m else None


def _find_miles(text: str) -> Optional[float]:
    m = re.search(r"([\d.]+)\s*mile", text, re.I)
    return float(m.group(1)) if m else None


def _detect_rate_type(text: str) -> str:
    if re.search(r"/hr|per hour|hourly", text, re.I):
        return "hourly"
    if re.search(r"flat|fixed|lump", text, re.I):
        return "flat"
    return "unknown"


def _detect_category(text: str) -> str:
    cats = {
        "IT support": ["it support", "helpdesk", "tech support", "it tech"],
        "POS": ["pos", "point of sale"],
        "AV": ["av ", "audio visual", "projector", "screen"],
        "access point": ["access point", "wifi", "wireless ap", "ubiquiti", "meraki"],
        "cabling": ["cabling", "cable run", "cat5", "cat6", "ethernet"],
        "smart hands": ["smart hands", "smarthand"],
        "printer support": ["printer", "mfp", "copier"],
        "computer repair": ["computer repair", "desktop repair", "pc repair"],
        "laptop repair": ["laptop repair", "laptop screen", "laptop keyboard"],
        "TV mounting": ["tv mount", "tv install", "television mount"],
        "camera installation": ["camera install", "cctv", "security camera"],
        "Ring installation": ["ring doorbell", "ring camera", "ring install"],
        "door lock installation": ["smart lock", "door lock", "deadbolt"],
        "appliance repair": ["appliance", "washer", "dryer", "dishwasher", "refrigerator"],
        "pest spraying": ["pest", "termite", "exterminator"],
        "weed spraying": ["weed", "lawn spray", "herbicide"],
    }
    tl = text.lower()
    for cat, keywords in cats.items():
        if any(k in tl for k in keywords):
            return cat
    return "unknown"


def _detect_source(sender: str) -> str:
    if "fieldnation" in sender.lower():
        return "field_nation"
    if "workmarket" in sender.lower():
        return "work_market"
    return "direct_inquiry"


def _parse_email_to_wo(em: Dict[str, Any]) -> Dict[str, Any]:
    subject = em.get("subject", "")
    body = em.get("body", "")
    sender = em.get("sender", "")
    combined = subject + "\n" + body

    lines = [l.strip() for l in combined.split("\n") if l.strip()]
    title = subject[:120] if subject else (lines[0][:120] if lines else "Work Order")

    company = ""
    for line in lines[:10]:
        m = re.search(r"(?:from|company|client|vendor):\s*(.+)", line, re.I)
        if m:
            company = m.group(1).strip()[:80]
            break

    location = ""
    for line in lines:
        m = re.search(r"(?:location|site|address):\s*(.+)", line, re.I)
        if m:
            location = m.group(1).strip()[:100]
            break
    if not location:
        m = re.search(r"\b([A-Z][a-z]+,?\s+AZ\b)", combined)
        if m:
            location = m.group(1)

    return {
        "id": str(uuid.uuid4()),
        "source": _detect_source(sender),
        "raw_text": combined[:4000],
        "title": title,
        "company": company,
        "location": location or "Phoenix, AZ",
        "rate_offered": _find_dollar(combined) or 0.0,
        "rate_type": _detect_rate_type(combined),
        "estimated_hours": _find_hours(combined) or 0.0,
        "travel_miles": _find_miles(combined) or 0.0,
        "category": _detect_category(combined),
    }


def _save_work_order(wo: Dict[str, Any], score: int, recommendation: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    approval_required = int(recommendation == "accept")
    with _wo_get_conn() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO work_orders
            (id, source, raw_text, title, company, location, rate_offered,
             rate_type, estimated_hours, travel_miles, category,
             score, recommendation, status, approval_required,
             counteroffer_text, created_at, updated_at)
            VALUES (:id, :source, :raw_text, :title, :company, :location,
                    :rate_offered, :rate_type, :estimated_hours, :travel_miles,
                    :category, :score, :recommendation, 'pending',
                    :approval_required, NULL, :created_at, :updated_at)
        """, {**wo, "score": score, "recommendation": recommendation,
              "approval_required": approval_required,
              "created_at": now, "updated_at": now})
        conn.commit()


def _update_status(emails_found: int, orders_scored: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _get_conn() as conn:
        conn.execute("""
            UPDATE gmail_scanner_status
            SET last_scan=?, emails_found=?, orders_scored=?
            WHERE id='singleton'
        """, (now, emails_found, orders_scored))
        conn.commit()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/scan")
async def scan_gmail():
    """Scan Gmail inbox for work order alerts and score them."""
    if not _configured():
        return {
            "status": "not_configured",
            "message": "Add GMAIL_APP_PASSWORD and GMAIL_IMAP_USER to enable scanning",
            "orders": [],
        }

    raw_emails = _scan_imap()
    scored_orders = []
    orders_scored = 0

    for em in raw_emails:
        try:
            wo = _parse_email_to_wo(em)
            score, recommendation = _score_work_order(wo)
            _save_work_order(wo, score, recommendation)
            scored_orders.append({
                "id": wo["id"],
                "title": wo["title"],
                "source": wo["source"],
                "company": wo["company"],
                "location": wo["location"],
                "rate_offered": wo["rate_offered"],
                "rate_type": wo["rate_type"],
                "estimated_hours": wo["estimated_hours"],
                "travel_miles": wo["travel_miles"],
                "category": wo["category"],
                "score": score,
                "recommendation": recommendation,
            })
            orders_scored += 1
        except Exception as e:
            log.warning("Failed to parse/score email: %s", e)

    _update_status(len(raw_emails), orders_scored)

    return {
        "status": "ok",
        "emails_found": len(raw_emails),
        "orders_scored": orders_scored,
        "orders": scored_orders,
    }


@router.post("/connect")
async def connect_gmail():
    """Validate Gmail credentials are configured."""
    user, pw = _imap_credentials()
    if not user or not pw:
        return {
            "status": "not_configured",
            "message": "Set GMAIL_IMAP_USER and GMAIL_APP_PASSWORD environment variables",
            "configured": False,
        }

    # Quick connectivity test
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(user, pw)
        mail.logout()
        return {
            "status": "connected",
            "message": f"Successfully connected as {user}",
            "configured": True,
            "user": user,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)[:200]}",
            "configured": True,
        }


@router.get("/status")
async def scanner_status():
    """Return current scanner status."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM gmail_scanner_status WHERE id='singleton'"
        ).fetchone()

    if row:
        return {
            "status": "configured" if _configured() else "not_configured",
            "last_scan": row["last_scan"],
            "emails_found": row["emails_found"],
            "orders_scored": row["orders_scored"],
            "credentials_set": _configured(),
        }

    return {
        "status": "not_configured",
        "last_scan": None,
        "emails_found": 0,
        "orders_scored": 0,
        "credentials_set": False,
    }
