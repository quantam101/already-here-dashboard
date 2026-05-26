"""
Stripe Payments Integration - Receive real money into the Already Here Command OS.

Three packages defined SERVER-SIDE (security: never accept amount from frontend):
  - starter:     $49.00 one-time   (white-label deployment install)
  - pro:         $99.00/month      (recurring SaaS access)
  - enterprise:  $499.00/month     (recurring enterprise access)

Successful paid checkouts automatically write a ledger entry into revenue_ledger
under a "rev-saas" stream, so the $25K Proof-of-Work meter increments on REAL
revenue. This is the bridge between the dashboard and actual cash.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
import os
import uuid

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)
from services.audit_service import log_audit_event

router = APIRouter()

# Server-side fixed packages - frontend can only choose the package_id
# CAUTION: amount must be a FLOAT (1.00) not int (1) per Stripe SDK rules
PACKAGES: dict[str, dict] = {
    "starter": {
        "name": "Starter - white-label install",
        "amount": 49.00,
        "currency": "usd",
        "kind": "one_time",
        "description": "One-time white-label Command OS deployment install pack",
    },
    "pro": {
        "name": "Pro - monthly access",
        "amount": 99.00,
        "currency": "usd",
        "kind": "recurring_simulated",  # test-mode acts as one-time charge but recorded as recurring
        "description": "Monthly Command OS SaaS access (test mode)",
    },
    "enterprise": {
        "name": "Enterprise - monthly access",
        "amount": 499.00,
        "currency": "usd",
        "kind": "recurring_simulated",
        "description": "Monthly enterprise multi-tenant Command OS (test mode)",
    },
}

REVENUE_STREAM_FOR_PAYMENTS = "rev-saas"


class CheckoutCreateRequest(BaseModel):
    package_id: str
    origin_url: str  # frontend's window.location.origin (used for success/cancel)


class CheckoutCreateResponse(BaseModel):
    url: str
    session_id: str
    package: dict


class CheckoutStatusResponse(BaseModel):
    status: str
    payment_status: str
    amount_total: float
    currency: str
    package_id: Optional[str] = None
    ledger_entry_id: Optional[str] = None
    recorded: bool = False


async def get_db():
    from server import db
    return db


def _get_stripe(http_request: Request) -> StripeCheckout:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="STRIPE_API_KEY not configured")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/payments/webhook"
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


async def _ensure_saas_stream(db):
    """Make sure the rev-saas stream exists so paid checkouts have a home."""
    existing = await db.revenue_streams.find_one({"id": REVENUE_STREAM_FOR_PAYMENTS})
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    await db.revenue_streams.insert_one({
        "id": REVENUE_STREAM_FOR_PAYMENTS,
        "name": "SaaS Subscriptions",
        "type": "subscription",
        "status": "active",
        "monthly_target": 5000.0,
        "monthly_actual": 0.0,
        "description": "Stripe-collected paid subscriptions and one-time license fees",
        "metadata": {"cost_class": "free_local", "source": "stripe"},
        "created_at": now, "updated_at": now,
    })


@router.get("/packages")
async def list_packages():
    """Public package list for the frontend pricing page."""
    return {pid: {**pkg, "id": pid} for pid, pkg in PACKAGES.items()}


@router.post("/checkout", response_model=CheckoutCreateResponse)
async def create_checkout(payload: CheckoutCreateRequest, http_request: Request, db=Depends(get_db)):
    """Create a Stripe Checkout session for a FIXED, server-defined package."""
    if payload.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail=f"Unknown package: {payload.package_id}")
    pkg = PACKAGES[payload.package_id]

    await _ensure_saas_stream(db)

    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/pricing?cancelled=1"

    stripe_checkout = _get_stripe(http_request)
    req = CheckoutSessionRequest(
        amount=float(pkg["amount"]),
        currency=pkg["currency"],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "package_id": payload.package_id,
            "package_name": pkg["name"],
            "kind": pkg["kind"],
            "source": "command_os_checkout",
        },
    )
    session = await stripe_checkout.create_checkout_session(req)

    # MANDATORY: record a pending transaction BEFORE redirect
    await db.payment_transactions.insert_one({
        "id": f"pay-{uuid.uuid4().hex[:10]}",
        "session_id": session.session_id,
        "package_id": payload.package_id,
        "amount": float(pkg["amount"]),
        "currency": pkg["currency"],
        "kind": pkg["kind"],
        "payment_status": "initiated",
        "metadata": {"package_name": pkg["name"]},
        "ledger_entry_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    await log_audit_event(
        db, "payment.initiated", "operator", "checkout",
        "payment_transaction", session.session_id,
        metadata={"package": payload.package_id, "amount": pkg["amount"]},
    )

    return CheckoutCreateResponse(url=session.url, session_id=session.session_id, package={**pkg, "id": payload.package_id})


async def _record_paid_to_ledger(db, txn: dict) -> str:
    """Idempotently record a paid Stripe transaction into revenue_ledger."""
    if txn.get("ledger_entry_id"):
        return txn["ledger_entry_id"]  # already recorded
    today = datetime.now(timezone.utc).date().isoformat()
    entry_id = f"led-{uuid.uuid4().hex[:10]}"
    await db.revenue_ledger.insert_one({
        "id": entry_id,
        "stream_id": REVENUE_STREAM_FOR_PAYMENTS,
        "occurred_on": today,
        "gross_amount": txn["amount"],
        "net_amount": round(txn["amount"] * 0.971, 2),  # Stripe ~2.9% + $0.30 ≈ 2.9% over $49+
        "currency": txn["currency"].upper(),
        "source": "stripe",
        "proof_url": f"stripe://session/{txn['session_id']}",
        "notes": f"Stripe checkout - package {txn['package_id']}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await db.payment_transactions.update_one(
        {"session_id": txn["session_id"]},
        {"$set": {"ledger_entry_id": entry_id, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await log_audit_event(
        db, "payment.recorded_to_ledger", "stripe", "record",
        "ledger_entry", entry_id,
        metadata={"session_id": txn["session_id"], "amount": txn["amount"]},
    )
    return entry_id


@router.get("/checkout/{session_id}", response_model=CheckoutStatusResponse)
async def get_checkout_status(session_id: str, http_request: Request, db=Depends(get_db)):
    """Poll endpoint - frontend hits this after Stripe redirect.
    Idempotently records to ledger when payment_status == 'paid'.
    """
    stripe_checkout = _get_stripe(http_request)
    try:
        status = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Stripe session not found: {e}") from e

    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Update local status
    new_status = status.payment_status
    updates: dict = {"payment_status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}
    ledger_entry_id = txn.get("ledger_entry_id")
    recorded = bool(ledger_entry_id)

    if new_status == "paid" and not recorded:
        ledger_entry_id = await _record_paid_to_ledger(db, txn)
        recorded = True
        updates["ledger_entry_id"] = ledger_entry_id

    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": updates})

    return CheckoutStatusResponse(
        status=status.status,
        payment_status=status.payment_status,
        amount_total=(status.amount_total / 100.0) if status.amount_total else float(txn.get("amount", 0)),
        currency=status.currency or txn.get("currency", "usd"),
        package_id=txn.get("package_id"),
        ledger_entry_id=ledger_entry_id,
        recorded=recorded,
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db=Depends(get_db)):
    """Stripe will POST here on every paid event. Idempotently mirrors to ledger."""
    stripe_checkout = _get_stripe(request)
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        evt = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"webhook handling failed: {e}") from e

    if evt.payment_status == "paid" and evt.session_id:
        txn = await db.payment_transactions.find_one({"session_id": evt.session_id}, {"_id": 0})
        if txn and not txn.get("ledger_entry_id"):
            await _record_paid_to_ledger(db, txn)

    return {"received": True, "event": evt.event_type, "session": evt.session_id}


@router.get("/transactions")
async def list_transactions(limit: int = 100, db=Depends(get_db)):
    rows = await db.payment_transactions.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return rows


@router.get("/stats")
async def payment_stats(db=Depends(get_db)):
    txns = await db.payment_transactions.find({}, {"_id": 0}).to_list(2000)
    total_paid = sum(t["amount"] for t in txns if t.get("payment_status") == "paid")
    by_package: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for t in txns:
        by_package[t.get("package_id", "?")] = by_package.get(t.get("package_id", "?"), 0) + 1
        by_status[t.get("payment_status", "?")] = by_status.get(t.get("payment_status", "?"), 0) + 1
    return {
        "total_transactions": len(txns),
        "total_paid_usd": round(total_paid, 2),
        "by_package": by_package,
        "by_status": by_status,
    }
