"""
Product Factory -- Phase 2 Growth Command OS
Routes:
  POST /api/products/create  -- create a new product spec (approval_required enforced)
  GET  /api/products         -- list all product specs
  GET  /api/products/{id}    -- get a single product with full content
"""
from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

log = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
_DB_PATH = Path(__file__).parent.parent / "data" / "product_factory.db"

VALID_TYPES = {"checklist", "kit", "guide", "template", "audit"}
VALID_STATUSES = {"draft", "ready", "live"}


def _get_conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table() -> None:
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                title TEXT,
                product_type TEXT,
                status TEXT DEFAULT 'draft',
                description TEXT,
                content TEXT,
                price_usd REAL DEFAULT 0,
                audience TEXT,
                approval_required INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.commit()


def _seed_products() -> None:
    """Seed the 5 initial products if not already present."""
    seeds = [
        {
            "id": "prod-field-tech-cash-stack-kit",
            "title": "Field Tech Cash Stack Kit",
            "product_type": "kit",
            "description": (
                "Complete toolkit for field IT technicians to maximize earnings: "
                "rate sheets, counteroffer scripts, platform comparison guide, "
                "and daily dispatch checklist."
            ),
            "content": (
                "# Field Tech Cash Stack Kit\n\n"
                "## What's Included\n"
                "- Rate Sheet Template ($45-$100/hr tiers)\n"
                "- Counteroffer Script Library\n"
                "- Platform Comparison: Field Nation vs WorkMarket vs Direct\n"
                "- Daily Dispatch Checklist\n"
                "- Invoice Template\n\n"
                "## Target Audience\n"
                "Independent IT field technicians in metropolitan markets."
            ),
            "audience": "Independent IT field technicians",
        },
        {
            "id": "prod-phoenix-same-day-checklist",
            "title": "Phoenix Same-Day Tech Support Checklist",
            "product_type": "checklist",
            "description": (
                "Step-by-step checklist for delivering same-day IT support in the Phoenix metro area. "
                "Covers dispatch, on-site protocol, common fixes, and close-out documentation."
            ),
            "content": (
                "# Phoenix Same-Day Tech Support Checklist\n\n"
                "## Pre-Dispatch\n"
                "- [ ] Confirm work order details and site address\n"
                "- [ ] Verify required tools and parts\n"
                "- [ ] Confirm parking / access instructions\n\n"
                "## On-Site\n"
                "- [ ] Sign in with site contact\n"
                "- [ ] Document existing equipment state (photos)\n"
                "- [ ] Complete repair/install per scope\n"
                "- [ ] Test all work before leaving\n\n"
                "## Close-Out\n"
                "- [ ] Obtain customer signature\n"
                "- [ ] Submit completion notes on platform\n"
                "- [ ] Send invoice within 24 hours"
            ),
            "audience": "Phoenix area IT field technicians",
        },
        {
            "id": "prod-small-biz-cyber-hygiene",
            "title": "Small Business Cyber Hygiene Checklist",
            "product_type": "checklist",
            "description": (
                "Practical cybersecurity checklist for small businesses with 1-50 employees. "
                "Covers passwords, backups, network security, and employee awareness."
            ),
            "content": (
                "# Small Business Cyber Hygiene Checklist\n\n"
                "## Passwords & Access\n"
                "- [ ] All accounts use unique passwords (12+ characters)\n"
                "- [ ] MFA enabled on email and critical apps\n"
                "- [ ] Shared passwords stored in password manager\n\n"
                "## Backups\n"
                "- [ ] Daily automated backups configured\n"
                "- [ ] Backup restoration tested quarterly\n"
                "- [ ] Offsite/cloud backup in place\n\n"
                "## Network\n"
                "- [ ] Router firmware up to date\n"
                "- [ ] Guest WiFi separate from business network\n"
                "- [ ] Firewall enabled on all devices\n\n"
                "## Awareness\n"
                "- [ ] Staff trained on phishing recognition\n"
                "- [ ] Incident response contact list posted"
            ),
            "audience": "Small business owners (1-50 employees)",
        },
        {
            "id": "prod-ai-office-manager-audit",
            "title": "AI Office Manager Business Audit",
            "product_type": "audit",
            "description": (
                "Structured audit template for evaluating where AI tools can replace or augment "
                "office management tasks in a small business. Includes ROI calculator framework."
            ),
            "content": (
                "# AI Office Manager Business Audit\n\n"
                "## Section 1: Current Manual Processes\n"
                "List all tasks currently done manually:\n"
                "- Scheduling / calendar management\n"
                "- Email triage and responses\n"
                "- Invoice creation and follow-up\n"
                "- Data entry and reporting\n"
                "- Customer communications\n\n"
                "## Section 2: AI Replacement Assessment\n"
                "For each task, score: Automatable (1-5) | Cost to automate | Time saved/week\n\n"
                "## Section 3: Tool Recommendations\n"
                "- Scheduling: Calendly + AI assistant\n"
                "- Email: Gmail AI features / Superhuman\n"
                "- Invoicing: Wave + automation rules\n"
                "- Reporting: Notion AI / ChatGPT\n\n"
                "## Section 4: 30-Day Implementation Roadmap\n"
                "Week 1: Implement highest-ROI tool\n"
                "Week 2-3: Train and refine\n"
                "Week 4: Measure and document savings"
            ),
            "audience": "Small business owners exploring AI automation",
        },
        {
            "id": "prod-veteran-it-contractor-sheet",
            "title": "Veteran-Owned IT Contractor Capability Sheet",
            "product_type": "template",
            "description": (
                "Professional one-page capability statement template for veteran-owned IT contractors. "
                "Formatted for government contracting, small business set-asides, and enterprise RFPs."
            ),
            "content": (
                "# Veteran-Owned IT Contractor Capability Sheet\n\n"
                "## Company Overview\n"
                "[Business Name] | SDVOSB / VOB Certified\n"
                "NAICS: 541512, 541519, 811212\n"
                "SAM.gov Registered: [Yes/No]\n\n"
                "## Core Competencies\n"
                "- IT Infrastructure Support & Deployment\n"
                "- Network Installation & Configuration\n"
                "- End-User Device Repair & Maintenance\n"
                "- POS System Installation\n"
                "- Smart Home / Commercial AV Integration\n\n"
                "## Past Performance\n"
                "[Client 1] — [Scope] — [Completion Date]\n"
                "[Client 2] — [Scope] — [Completion Date]\n\n"
                "## Differentiators\n"
                "- Veteran-owned, mission-focused\n"
                "- Same-day dispatch in [Metro Area]\n"
                "- Licensed, insured, background-checked\n\n"
                "## Contact\n"
                "[Name] | [Phone] | [Email] | [Website]"
            ),
            "audience": "Veteran-owned IT contractors pursuing government and enterprise contracts",
        },
    ]

    now = datetime.now(UTC).isoformat()
    with _get_conn() as conn:
        for p in seeds:
            conn.execute("""
                INSERT OR IGNORE INTO products
                (id, title, product_type, status, description, content,
                 price_usd, audience, approval_required, created_at, updated_at)
                VALUES (?, ?, ?, 'draft', ?, ?, 0, ?, 1, ?, ?)
            """, (p["id"], p["title"], p["product_type"],
                  p["description"], p["content"], p["audience"], now, now))
        conn.commit()


_ensure_table()
_seed_products()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ProductCreateRequest(BaseModel):
    title: str
    product_type: str | None = "guide"
    description: str | None = ""
    content: str | None = ""
    price_usd: float | None = 0.0
    audience: str | None = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/create")
async def create_product(req: ProductCreateRequest):
    """
    Create a new product spec.
    approval_required is always True when price_usd > 0.
    Products are never auto-published or auto-priced.
    """
    product_type = req.product_type if req.product_type in VALID_TYPES else "guide"
    price = req.price_usd or 0.0
    # Enforce: pricing always requires approval
    approval_required = 1 if price > 0 else 1  # always 1 per spec

    now = datetime.now(UTC).isoformat()
    product_id = str(uuid.uuid4())

    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO products
            (id, title, product_type, status, description, content,
             price_usd, audience, approval_required, created_at, updated_at)
            VALUES (?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?)
        """, (product_id, req.title, product_type, req.description,
              req.content, price, req.audience, approval_required, now, now))
        conn.commit()

    return {
        "id": product_id,
        "status": "draft",
        "approval_required": True,
        "message": "Product created as draft. Review and approve before publishing or pricing.",
    }


@router.get("")
async def list_products(status: str | None = None, limit: int = 100):
    """List all product specs, optionally filtered by status."""
    with _get_conn() as conn:
        if status and status in VALID_STATUSES:
            rows = conn.execute(
                "SELECT id, title, product_type, status, description, price_usd, audience, "
                "approval_required, created_at FROM products WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, product_type, status, description, price_usd, audience, "
                "approval_required, created_at FROM products ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

    return {
        "products": [dict(r) for r in rows],
        "total": len(rows),
    }


@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get a single product with full content."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Product not found")

    return dict(row)
