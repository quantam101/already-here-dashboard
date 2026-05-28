"""
Proposal Engine - AI-powered grant, contract, RFP, invoice, capability statement writer.

Uses Emergent LLM Key (Cost Guard compliant - $0 to operator).

Document types supported:
  - grant_proposal: federal/foundation grant response
  - contract_proposal: government/commercial contract bid
  - rfp_response: full RFP response with sections
  - capability_statement: SBA-style 1-2 page capability statement
  - invoice: itemized invoice
  - cover_letter: cover letter for any of the above
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import os
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: F401 (kept for downstream imports)
from services.audit_service import log_audit_event
from services.llm_runner import run_cached, llm_complete

router = APIRouter()

ALLOWED_TYPES = {
    "grant_proposal", "contract_proposal", "rfp_response",
    "capability_statement", "invoice", "cover_letter",
}

DEFAULT_SYSTEM_MESSAGE = (
    "You are an expert proposal writer specialized in federal/foundation grants, "
    "government contracts, RFP responses, and procurement documents. Write clear, "
    "evidence-driven, compliant documents that win. Always include measurable outcomes, "
    "specific past performance, and explicit alignment to evaluation criteria."
)

# Section templates by document type - extracted to module level to reduce
# _build_prompt complexity and make the templates trivially editable.
SECTIONS_BY_TYPE: dict[str, list[str]] = {
    "grant_proposal": [
        "1. Executive Summary",
        "2. Problem Statement (with cited evidence)",
        "3. Proposed Solution & Approach",
        "4. Goals & Measurable Outcomes",
        "5. Implementation Timeline",
        "6. Budget Narrative",
        "7. Organizational Capability & Past Performance",
        "8. Evaluation & Sustainability Plan",
    ],
    "contract_proposal": [
        "1. Cover Page",
        "2. Technical Approach",
        "3. Past Performance (specific projects, metrics)",
        "4. Management & Staffing Plan",
        "5. Pricing Summary",
        "6. Compliance Matrix (line-by-line)",
    ],
    "rfp_response": [
        "1. Compliance / Cross-Reference Matrix",
        "2. Executive Summary",
        "3. Technical Response (section-by-section to RFP)",
        "4. Management Response",
        "5. Past Performance",
        "6. Price/Cost Response",
    ],
    "capability_statement": [
        "1. Core Competencies (bullet list)",
        "2. Past Performance (3-5 specific projects)",
        "3. Differentiators",
        "4. Company Data (NAICS, CAGE, UEI, certifications)",
        "5. Contact Information",
    ],
    "cover_letter": [
        "1. Opening hook tied to opportunity",
        "2. Why this team / company is uniquely qualified",
        "3. Specific evidence of past performance",
        "4. Clear call to action",
    ],
}

DEFAULT_COMPANY = {
    "name": "Already Here",
    "mission": "Build governed, zero-cost autonomous systems for revenue and proof of work.",
    "proof": "H&M RFID US0275 successful deployment - 55 readers, 61 data runs, 4 new APs.",
    "naics": "541512",
    "certifications": ["SBA Small Business"],
}


class ProposalDraftRequest(BaseModel):
    doc_type: str
    title: str
    target_org: Optional[str] = None  # agency, foundation, client
    opportunity_url: Optional[str] = None
    deadline: Optional[str] = None
    budget_usd: Optional[float] = None
    company_profile: dict = Field(default_factory=dict)
    requirements: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    instructions: Optional[str] = None


class InvoiceLineItem(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    total: Optional[float] = None


class InvoiceRequest(BaseModel):
    client_name: str
    client_email: Optional[str] = None
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = None
    due_date: Optional[str] = None
    line_items: list[InvoiceLineItem]
    notes: Optional[str] = None
    company_name: str = "Already Here"
    tax_pct: float = 0.0


class ProposalDocument(BaseModel):
    id: str = Field(default_factory=lambda: f"prop-{uuid.uuid4().hex[:10]}")
    doc_type: str
    title: str
    target_org: Optional[str] = None
    content: str
    metadata: dict = Field(default_factory=dict)
    status: str = "draft"  # draft | finalized | submitted
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


async def get_db():
    from server import db
    return db


def _validate_doc_type(doc_type: str) -> None:
    if doc_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"doc_type must be one of {sorted(ALLOWED_TYPES)}")


def _format_bullet_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"- {empty_text}"
    return "\n".join(f"- {it}" for it in items)


def _build_prompt(req: ProposalDraftRequest) -> str:
    company = {**DEFAULT_COMPANY, **(req.company_profile or {})}
    sections = "\n".join(SECTIONS_BY_TYPE.get(req.doc_type, SECTIONS_BY_TYPE["grant_proposal"]))
    reqs_block = _format_bullet_list(req.requirements, "(none specified)")
    evid_block = _format_bullet_list(req.evidence, "(use company profile proof above)")

    return f"""Generate a professional {req.doc_type.replace('_', ' ')} with the following details:

TITLE: {req.title}
TARGET ORGANIZATION: {req.target_org or 'Not specified'}
OPPORTUNITY URL: {req.opportunity_url or 'N/A'}
DEADLINE: {req.deadline or 'TBD'}
BUDGET (USD): {req.budget_usd if req.budget_usd is not None else 'TBD'}

COMPANY PROFILE:
- Name: {company['name']}
- Mission: {company['mission']}
- Key proof: {company['proof']}
- NAICS: {company['naics']}
- Certifications: {', '.join(company['certifications'])}

REQUIREMENTS (from the opportunity):
{reqs_block}

EVIDENCE / PAST PERFORMANCE TO LEVERAGE:
{evid_block}

ADDITIONAL INSTRUCTIONS:
{req.instructions or '(none)'}

REQUIRED SECTIONS:
{sections}

OUTPUT FORMAT:
Produce the FULL document in clean markdown. Each numbered section must be present with substantive content. Include measurable outcomes, dates, and concrete deliverables. No placeholders like [TBD] in critical sections - infer reasonable defaults from the company profile."""


@router.post("/draft", response_model=ProposalDocument, status_code=201)
async def draft_proposal(req: ProposalDraftRequest, db=Depends(get_db)):
    """Generate a full draft using Emergent LLM (Gemini 3 Flash - FREE)."""
    _validate_doc_type(req.doc_type)

    response = await llm_complete(
        system=DEFAULT_SYSTEM_MESSAGE,
        user=_build_prompt(req),
        max_tokens=2000,
        session_id=f"prop_{uuid.uuid4().hex[:8]}",
    )

    doc = ProposalDocument(
        doc_type=req.doc_type,
        title=req.title,
        target_org=req.target_org,
        content=response,
        metadata={
            "opportunity_url": req.opportunity_url,
            "deadline": req.deadline,
            "budget_usd": req.budget_usd,
            "model": "llm_complete_failover",
        },
    )
    await db.proposals.insert_one(doc.model_dump())
    await log_audit_event(
        db, "proposal.drafted", "proposal_engine_agent", "draft",
        "proposal", doc.id, metadata={"doc_type": doc.doc_type, "title": doc.title},
    )
    return doc


@router.post("/invoice", response_model=ProposalDocument, status_code=201)
async def create_invoice(req: InvoiceRequest, db=Depends(get_db)):
    """Generate a structured invoice markdown - no LLM needed (deterministic)."""
    issue = req.issue_date or datetime.now(timezone.utc).date().isoformat()
    invoice_num = req.invoice_number or f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
    subtotal = 0.0
    rows = []
    for item in req.line_items:
        total = item.total if item.total is not None else item.quantity * item.unit_price
        subtotal += total
        rows.append(f"| {item.description} | {item.quantity:g} | ${item.unit_price:,.2f} | ${total:,.2f} |")
    tax = subtotal * (req.tax_pct / 100.0)
    grand = subtotal + tax

    content = f"""# INVOICE {invoice_num}

**From:** {req.company_name}
**To:** {req.client_name}{f' ({req.client_email})' if req.client_email else ''}

**Issue Date:** {issue}
**Due Date:** {req.due_date or 'Net 30'}

| Description | Qty | Unit Price | Total |
|---|---|---|---|
{chr(10).join(rows)}

| | | **Subtotal** | **${subtotal:,.2f}** |
| | | Tax ({req.tax_pct}%) | ${tax:,.2f} |
| | | **TOTAL DUE** | **${grand:,.2f}** |

{f'**Notes:** {req.notes}' if req.notes else ''}
"""
    doc = ProposalDocument(
        doc_type="invoice",
        title=f"Invoice {invoice_num} - {req.client_name}",
        target_org=req.client_name,
        content=content,
        metadata={
            "invoice_number": invoice_num,
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "total": round(grand, 2),
            "line_count": len(req.line_items),
        },
    )
    await db.proposals.insert_one(doc.model_dump())
    await log_audit_event(
        db, "invoice.created", "proposal_engine_agent", "draft",
        "invoice", doc.id, metadata={"total": grand, "client": req.client_name},
    )
    return doc


@router.get("/", response_model=list[ProposalDocument])
async def list_proposals(doc_type: Optional[str] = None, status: Optional[str] = None, db=Depends(get_db)):
    """List all proposals/invoices/etc."""
    query: dict = {}
    if doc_type:
        _validate_doc_type(doc_type)
        query["doc_type"] = doc_type
    if status:
        query["status"] = status
    rows = await db.proposals.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return rows


@router.get("/{prop_id}", response_model=ProposalDocument)
async def get_proposal(prop_id: str, db=Depends(get_db)):
    doc = await db.proposals.find_one({"id": prop_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return doc


@router.patch("/{prop_id}", response_model=ProposalDocument)
async def update_proposal(prop_id: str, updates: dict, db=Depends(get_db)):
    if "status" in updates and updates["status"] not in {"draft", "finalized", "submitted"}:
        raise HTTPException(status_code=400, detail="status must be draft|finalized|submitted")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.proposals.update_one({"id": prop_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return await db.proposals.find_one({"id": prop_id}, {"_id": 0})


@router.get("/stats/overview")
async def proposal_stats(db=Depends(get_db)):
    docs = await db.proposals.find({}, {"_id": 0}).to_list(2000)
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    invoice_total = 0.0
    for d in docs:
        by_type[d.get("doc_type", "unknown")] = by_type.get(d.get("doc_type", "unknown"), 0) + 1
        by_status[d.get("status", "draft")] = by_status.get(d.get("status", "draft"), 0) + 1
        if d.get("doc_type") == "invoice":
            invoice_total += float(d.get("metadata", {}).get("total", 0))
    return {
        "total": len(docs),
        "by_type": by_type,
        "by_status": by_status,
        "invoice_total_usd": round(invoice_total, 2),
    }
