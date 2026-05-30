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
import os
import uuid
from datetime import UTC, datetime

import stripe as stripe_sdk
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from services import governance_service as gov
from services.audit_service import log_audit_event
from services.stripe_adapter import (
    CheckoutSessionRequest,
    StripeAdapter,
)

router = APIRouter()

# Sentinel package id used by the live-mode smoke runner (auto-refunds itself)
SMOKE_TEST_PACKAGE = "smoke_test"
SMOKE_TEST_AMOUNT_USD = 0.50

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
    utm_source: str | None = None  # reddit, linkedin, twitter, blog, ...
    utm_medium: str | None = None  # post, dm, email, organic, paid
    utm_campaign: str | None = None
    referrer: str | None = None


class CheckoutCreateResponse(BaseModel):
    url: str
    session_id: str
    package: dict


class CheckoutStatusResponse(BaseModel):
    status: str
    payment_status: str
    amount_total: float
    currency: str
    package_id: str | None = None
    ledger_entry_id: str | None = None
    recorded: bool = False


async def get_db():
    from server import db
    return db


def _get_stripe(http_request: Request) -> StripeAdapter:
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="STRIPE_API_KEY not configured")
    host_url = str(http_request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/payments/webhook"
    return StripeAdapter(api_key=api_key, webhook_url=webhook_url)


def _stripe_mode() -> str:
    """test | live | unknown | missing — matches /api/system/status."""
    key = os.environ.get("STRIPE_API_KEY", "") or ""
    if key.startswith("sk_live_"):
        return "live"
    if key.startswith("sk_test_"):
        return "test"
    if not key:
        return "missing"
    return "unknown"


def _readiness() -> dict:
    """Production-readiness gate for going live. Operator checklist."""
    key = os.environ.get("STRIPE_API_KEY", "") or ""
    mode = _stripe_mode()
    webhook_set = bool(os.environ.get("STRIPE_WEBHOOK_SECRET"))
    operator_email = os.environ.get("OPERATOR_EMAIL", "") or ""
    issues: list[str] = []
    if mode == "missing":
        issues.append("STRIPE_API_KEY is not set")
    if mode == "unknown":
        issues.append("STRIPE_API_KEY is set but doesn't look like sk_test_ or sk_live_")
    if mode == "live" and not webhook_set:
        issues.append("Live mode requires STRIPE_WEBHOOK_SECRET (set via Stripe Dashboard → Webhooks)")
    if mode == "live" and not operator_email:
        issues.append("OPERATOR_EMAIL should be set in live mode so the Command OS is access-locked")
    return {
        "stripe_mode": mode,
        "stripe_key_prefix": (key[:7] + "***") if key else "",
        "webhook_secret_set": webhook_set,
        "operator_email_set": bool(operator_email),
        "go_live_ready": mode == "live" and webhook_set,
        "issues": issues,
        "checklist": [
            "1. Replace STRIPE_API_KEY with sk_live_... from dashboard.stripe.com → Developers → API keys",
            "2. Add webhook endpoint: https://<your-domain>/api/payments/webhook listening on `checkout.session.completed`",
            "3. Paste the webhook signing secret into STRIPE_WEBHOOK_SECRET",
            "4. Set OPERATOR_EMAIL so only you can access /api routes that need auth",
            "5. Restart backend: `docker compose -f docker-compose.sqlite.yml restart backend`",
            "6. Run a $0.50 test purchase against /api/payments/checkout to confirm ledger entry appears",
        ],
    }


async def _ensure_saas_stream(db):
    """Make sure the rev-saas stream exists so paid checkouts have a home."""
    existing = await db.revenue_streams.find_one({"id": REVENUE_STREAM_FOR_PAYMENTS})
    if existing:
        return
    now = datetime.now(UTC).isoformat()
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


@router.get("/mode")
async def get_mode():
    """Lightweight mode probe for frontend banners."""
    return {"mode": _stripe_mode()}


@router.get("/readiness")
async def get_readiness():
    """Operator checklist for switching test → live keys safely."""
    return _readiness()


@router.post("/checkout", response_model=CheckoutCreateResponse)
async def create_checkout(payload: CheckoutCreateRequest, http_request: Request, db=Depends(get_db)):
    """Create a Stripe Checkout session for a FIXED, server-defined package."""
    if payload.package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail=f"Unknown package: {payload.package_id}")
    pkg = PACKAGES[payload.package_id]

    # Safety gate: in live mode, refuse to accept money without a webhook secret.
    # Without the secret, Stripe's webhook events can't be verified → silent
    # double-charges or missed ledger entries are possible.
    if _stripe_mode() == "live" and not os.environ.get("STRIPE_WEBHOOK_SECRET"):
        raise HTTPException(
            status_code=503,
            detail=(
                "Live Stripe key detected but STRIPE_WEBHOOK_SECRET is missing. "
                "Refusing to create a paid checkout — see /api/payments/readiness."
            ),
        )

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
            "utm_source": payload.utm_source or "",
            "utm_medium": payload.utm_medium or "",
            "utm_campaign": payload.utm_campaign or "",
            "referrer": payload.referrer or "",
        },
    )
    try:
        session = await stripe_checkout.create_checkout_session(req)
    except Exception as e:
        err_str = str(e).lower()
        if "authentication" in err_str or "invalid api key" in err_str or "no api key" in err_str:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Stripe API key is missing or invalid. "
                    "Set a real STRIPE_API_KEY (sk_test_… or sk_live_…) in /opt/command-os/.env "
                    "and run: sudo docker compose -f docker-compose.sqlite.yml up -d backend"
                ),
            ) from e
        raise HTTPException(status_code=502, detail=f"Stripe error: {e}") from e

    # MANDATORY: record a pending transaction BEFORE redirect
    await db.payment_transactions.insert_one({
        "id": f"pay-{uuid.uuid4().hex[:10]}",
        "session_id": session.session_id,
        "package_id": payload.package_id,
        "amount": float(pkg["amount"]),
        "currency": pkg["currency"],
        "kind": pkg["kind"],
        "payment_status": "initiated",
        "metadata": {
            "package_name": pkg["name"],
            "utm_source": payload.utm_source or "",
            "utm_medium": payload.utm_medium or "",
            "utm_campaign": payload.utm_campaign or "",
            "referrer": payload.referrer or "",
        },
        "ledger_entry_id": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
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
    today = datetime.now(UTC).date().isoformat()
    entry_id = f"led-{uuid.uuid4().hex[:10]}"
    utm_meta = {k: txn.get("metadata", {}).get(k, "") for k in ("utm_source", "utm_medium", "utm_campaign", "referrer")}
    await db.revenue_ledger.insert_one({
        "id": entry_id,
        "stream_id": REVENUE_STREAM_FOR_PAYMENTS,
        "occurred_on": today,
        "gross_amount": txn["amount"],
        "net_amount": round(txn["amount"] * 0.971, 2),  # Stripe ~2.9% + $0.30 ≈ 2.9% over $49+
        "currency": txn["currency"].upper(),
        "source": "stripe",
        "proof_url": f"stripe://session/{txn['session_id']}",
        "notes": f"Stripe checkout - package {txn['package_id']}"
                 + (f" via {utm_meta['utm_source']}" if utm_meta["utm_source"] else ""),
        "metadata": {**utm_meta, "package_id": txn["package_id"]},
        "created_at": datetime.now(UTC).isoformat(),
    })
    await db.payment_transactions.update_one(
        {"session_id": txn["session_id"]},
        {"$set": {"ledger_entry_id": entry_id, "updated_at": datetime.now(UTC).isoformat()}},
    )
    await log_audit_event(
        db, "payment.recorded_to_ledger", "stripe", "record",
        "ledger_entry", entry_id,
        metadata={"session_id": txn["session_id"], "amount": txn["amount"], **utm_meta},
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
    updates: dict = {"payment_status": new_status, "updated_at": datetime.now(UTC).isoformat()}
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
    """Stripe will POST here on every paid event. Idempotently mirrors to ledger.

    Smoke-test sessions (metadata.smoke_test=true) are auto-refunded the
    moment they're paid — so the operator can verify live keys + webhook
    plumbing end-to-end with a real card and never actually lose the money.
    """
    stripe_checkout = _get_stripe(request)
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")
    try:
        evt = await stripe_checkout.handle_webhook(body, signature)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"webhook handling failed: {e}") from e

    if evt.payment_status == "paid" and evt.session_id:
        txn = await db.payment_transactions.find_one({"session_id": evt.session_id}, {"_id": 0})
        if txn:
            is_smoke = (txn.get("package_id") == SMOKE_TEST_PACKAGE) or \
                       (txn.get("metadata", {}).get("smoke_test") in ("true", True, "1"))
            if is_smoke:
                # Auto-refund — never record to ledger
                await _refund_smoke_test(db, txn)
            elif not txn.get("ledger_entry_id"):
                await _record_paid_to_ledger(db, txn)

    return {"received": True, "event": evt.event_type, "session": evt.session_id}


async def _refund_smoke_test(db, txn: dict) -> None:
    """Issue a full Stripe refund for a smoke-test session and stamp the txn."""
    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        return
    stripe_sdk.api_key = api_key
    session_id = txn["session_id"]
    refund_id = None
    refund_status = "failed"
    try:
        # Fetch the session → payment_intent
        sess = stripe_sdk.checkout.Session.retrieve(session_id)
        payment_intent_id = getattr(sess, "payment_intent", None)
        if payment_intent_id:
            refund = stripe_sdk.Refund.create(
                payment_intent=payment_intent_id,
                reason="requested_by_customer",
                metadata={"source": "command_os_smoke_test"},
            )
            refund_id = refund.id
            refund_status = refund.status
    except Exception as e:
        refund_status = f"error: {e}"

    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {
            "smoke_refund_id": refund_id,
            "smoke_refund_status": refund_status,
            "payment_status": "refunded" if refund_status == "succeeded" else txn.get("payment_status"),
            "updated_at": datetime.now(UTC).isoformat(),
        }},
    )
    await log_audit_event(
        db, "payment.smoke_refunded", "stripe", "refund",
        "payment_transaction", session_id,
        metadata={"refund_id": refund_id, "status": refund_status, "amount": txn.get("amount")},
    )


@router.post("/smoke-test/create")
async def smoke_test_create(http_request: Request, db=Depends(get_db)):
    """Create a $0.50 live-mode checkout session that auto-refunds on payment.

    Refuses to run if stripe is in test mode (the smoke test only makes sense
    against your real live key + real webhook secret). The operator opens the
    returned URL in a browser, completes payment with a real card, and the
    webhook handler fires a full refund within seconds — confirming end-to-end
    that live keys + webhook secret + signature verification all work BEFORE
    routing real customers through the same path.

    Governance gate: capital_allocation (HITL required below L5).
    """
    mode = _stripe_mode()
    if mode != "live":
        raise HTTPException(
            status_code=400,
            detail=f"smoke-test requires live Stripe key (current mode: {mode}). See /api/payments/readiness.",
        )
    if not os.environ.get("STRIPE_WEBHOOK_SECRET"):
        raise HTTPException(
            status_code=400,
            detail="smoke-test requires STRIPE_WEBHOOK_SECRET (otherwise the auto-refund webhook never fires).",
        )

    # Governance gate (after cheap pre-checks so config errors fail fast first)
    from services import governance_service as gov
    await gov.enforce(
        db=db, request=http_request, action_id="capital_allocation",
        context={"route": "smoke-test/create", "amount_usd": SMOKE_TEST_AMOUNT_USD},
    )

    origin = str(http_request.base_url).rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}&smoke=1"
    cancel_url = f"{origin}/pricing?cancelled=1&smoke=1"

    stripe_checkout = _get_stripe(http_request)
    req = CheckoutSessionRequest(
        amount=SMOKE_TEST_AMOUNT_USD,
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "package_id": SMOKE_TEST_PACKAGE,
            "package_name": "Live-mode smoke test (auto-refunded)",
            "smoke_test": "true",
            "source": "command_os_smoke_test",
        },
    )
    session = await stripe_checkout.create_checkout_session(req)

    await db.payment_transactions.insert_one({
        "id": f"smoke-{uuid.uuid4().hex[:10]}",
        "session_id": session.session_id,
        "package_id": SMOKE_TEST_PACKAGE,
        "amount": SMOKE_TEST_AMOUNT_USD,
        "currency": "usd",
        "kind": "smoke_test",
        "payment_status": "initiated",
        "metadata": {"smoke_test": "true"},
        "ledger_entry_id": None,
        "smoke_refund_id": None,
        "smoke_refund_status": None,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    })
    await log_audit_event(
        db, "payment.smoke_test_created", "operator", "smoke_test",
        "payment_transaction", session.session_id,
        metadata={"amount": SMOKE_TEST_AMOUNT_USD},
    )
    return {
        "url": session.url,
        "session_id": session.session_id,
        "amount": SMOKE_TEST_AMOUNT_USD,
        "instructions": [
            "1. Open `url` in a browser logged into your Stripe-issued card.",
            "2. Complete the $0.50 charge with a REAL card.",
            "3. Watch /api/payments/smoke-test/status/<session_id> — it will flip to 'refunded' within ~10 seconds.",
            "4. If `smoke_refund_status` == 'succeeded' → your live keys + webhook are wired correctly.",
        ],
    }


@router.get("/smoke-test/status/{session_id}")
async def smoke_test_status(session_id: str, db=Depends(get_db)):
    """Polled by the operator (or the frontend) to verify auto-refund landed."""
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="smoke-test session not found")
    return {
        "session_id": session_id,
        "amount": txn.get("amount"),
        "payment_status": txn.get("payment_status"),
        "smoke_refund_id": txn.get("smoke_refund_id"),
        "smoke_refund_status": txn.get("smoke_refund_status"),
        "verified_live_pipeline": txn.get("smoke_refund_status") == "succeeded",
        "created_at": txn.get("created_at"),
        "updated_at": txn.get("updated_at"),
    }


@router.get("/smoke-test/recent")
async def smoke_test_recent(limit: int = 10, db=Depends(get_db)):
    """List the last N smoke-test runs."""
    rows = await db.payment_transactions.find(
        {"package_id": SMOKE_TEST_PACKAGE}, {"_id": 0},
    ).sort("created_at", -1).to_list(limit)
    return rows


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
    by_utm_source: dict[str, dict] = {}
    for t in txns:
        by_package[t.get("package_id", "?")] = by_package.get(t.get("package_id", "?"), 0) + 1
        by_status[t.get("payment_status", "?")] = by_status.get(t.get("payment_status", "?"), 0) + 1
        src = (t.get("metadata", {}).get("utm_source") or "direct").lower() or "direct"
        bucket = by_utm_source.setdefault(src, {"clicks": 0, "paid": 0, "paid_usd": 0.0})
        bucket["clicks"] += 1
        if t.get("payment_status") == "paid":
            bucket["paid"] += 1
            bucket["paid_usd"] += t.get("amount", 0.0)
    return {
        "total_transactions": len(txns),
        "total_paid_usd": round(total_paid, 2),
        "by_package": by_package,
        "by_status": by_status,
        "by_utm_source": {k: {**v, "paid_usd": round(v["paid_usd"], 2)} for k, v in by_utm_source.items()},
    }


@router.get("/share-link")
async def generate_share_link(
    package_id: str = "starter",
    utm_source: str = "reddit",
    utm_medium: str = "post",
    utm_campaign: str = "launch",
    origin_url: str = "",
):
    """Generate a pre-tagged share URL the operator can drop in DMs / posts.

    The pricing page reads utm_* query params and forwards them to /checkout so
    the eventual sale credits the right channel in by_utm_source analytics.
    """
    if package_id not in PACKAGES:
        raise HTTPException(status_code=400, detail=f"Unknown package: {package_id}")
    from urllib.parse import urlencode

    # Resolve origin: query param > REACT_APP_BACKEND_URL env > APP_PUBLIC_URL env
    resolved_origin = (
        origin_url.rstrip("/")
        or os.environ.get("APP_PUBLIC_URL", "").rstrip("/")
        or os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
        or "https://app.alreadyherellc.com"
    )
    qs = urlencode({
        "pkg": package_id,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
    })
    return {
        "share_url": f"{resolved_origin}/pricing?{qs}",
        "package_id": package_id,
        "amount": PACKAGES[package_id]["amount"],
    }


# ---------------------------------------------------------------------------
# Stripe key rotation — payment_modification gate (HITL required below L5)
# ---------------------------------------------------------------------------

class StripeKeyRotation(BaseModel):
    stripe_api_key: str
    stripe_webhook_secret: str | None = None
    note: str | None = None


def _validate_stripe_key_shape(key: str) -> str:
    """Cheap structural check — refuses obvious garbage before any gate fires."""
    k = (key or "").strip()
    if not k:
        raise HTTPException(status_code=400, detail="stripe_api_key is required")
    if not k.startswith(("sk_test_", "sk_live_", "rk_live_", "rk_test_")):
        raise HTTPException(
            status_code=400,
            detail="stripe_api_key must start with sk_test_, sk_live_, rk_test_, or rk_live_",
        )
    if len(k) < 20:
        raise HTTPException(status_code=400, detail="stripe_api_key looks too short to be valid")
    return k


@router.post("/keys/rotate")
async def rotate_stripe_keys(
    body: StripeKeyRotation,
    http_request: Request,
    db=Depends(get_db),
):
    """Stage a Stripe API key + webhook secret rotation for operator review.

    HITL-gated on `payment_modification` (requires L5 / approval below).

    The endpoint NEVER overwrites the live `backend/.env`. Instead, it writes
    the proposed credentials to `backend/.env.proposed` so the operator can
    diff, copy, and restart on their own terms. This guarantees you can never
    silently brick live payments by hitting the wrong button in the UI.
    """
    new_key = _validate_stripe_key_shape(body.stripe_api_key)

    await gov.enforce(
        db=db, request=http_request, action_id="payment_modification",
        context={
            "route": "payments/keys/rotate",
            "new_key_mode": "live" if new_key.startswith("sk_live_") else "test",
            "new_key_suffix": new_key[-4:],
            "webhook_secret_provided": bool(body.stripe_webhook_secret),
            "note": (body.note or "")[:240],
        },
    )

    # Approval cleared — write the stage file. Never the live .env.
    proposed_path = os.environ.get("ENV_PROPOSED_PATH", "/app/backend/.env.proposed")
    lines = [f"STRIPE_API_KEY={new_key}"]
    if body.stripe_webhook_secret:
        lines.append(f"STRIPE_WEBHOOK_SECRET={body.stripe_webhook_secret.strip()}")
    lines.append(f"# proposed {datetime.now(UTC).isoformat()} via /api/payments/keys/rotate")
    try:
        import pathlib
        pathlib.Path(proposed_path).parent.mkdir(parents=True, exist_ok=True)
        with open(proposed_path, "w") as f:
            f.write("\n".join(lines) + "\n")
    except OSError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not write staged credentials to {proposed_path}: {e}. "
                   "Set ENV_PROPOSED_PATH to a writable path inside the container.",
        ) from e

    await log_audit_event(
        db, "stripe.keys.proposed", "operator", "rotate",
        "stripe_credentials", new_key[-4:],
        metadata={
            "mode": "live" if new_key.startswith("sk_live_") else "test",
            "webhook_secret_proposed": bool(body.stripe_webhook_secret),
            "proposed_path": proposed_path,
        },
    )

    return {
        "staged": True,
        "proposed_path": proposed_path,
        "new_key_mode": "live" if new_key.startswith("sk_live_") else "test",
        "new_key_suffix": new_key[-4:],
        "webhook_secret_staged": bool(body.stripe_webhook_secret),
        "next_step": (
            "Operator: review `cat /app/backend/.env.proposed`, then on the host run "
            "`cp /app/backend/.env.proposed /app/backend/.env && sudo supervisorctl restart backend` "
            "to apply. The live `.env` is intentionally NOT touched by this endpoint."
        ),
    }

