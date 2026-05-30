"""
Compatibility shim for emergentintegrations.payments.stripe.checkout.
Replaces the private package with direct calls to the stripe library.

Public API (matches original):
    CheckoutSessionRequest(amount, currency, success_url, cancel_url, metadata)

    StripeCheckout(api_key, webhook_url)
    await StripeCheckout.create_checkout_session(req) -> CheckoutSession
    await StripeCheckout.get_checkout_status(session_id) -> CheckoutStatus
    await StripeCheckout.handle_webhook(body, signature) -> WebhookEvent
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict

logger = logging.getLogger("emergentintegrations.payments.stripe.checkout")


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckoutSession:
    url: str
    session_id: str


@dataclass
class CheckoutStatus:
    status: str           # "open" | "complete" | "expired"
    payment_status: str   # "paid" | "unpaid" | "no_payment_required"
    amount_total: float | None  # in cents
    currency: str | None
    session_id: str


@dataclass
class WebhookEvent:
    event_type: str
    payment_status: str
    session_id: str | None


class StripeCheckout:
    """Thin async wrapper around the stripe library."""

    def __init__(self, api_key: str, webhook_url: str = ""):
        self._api_key = api_key
        self._webhook_url = webhook_url

    def _configure(self):
        import stripe as _stripe  # type: ignore
        _stripe.api_key = self._api_key
        return _stripe

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSession:
        stripe = self._configure()
        loop = asyncio.get_event_loop()

        # Amount must be an integer (cents)
        amount_cents = int(round(req.amount * 100))

        def _create():
            return stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": req.currency,
                        "product_data": {"name": req.metadata.get("package_name", "Command OS")},
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=req.success_url,
                cancel_url=req.cancel_url,
                metadata=req.metadata,
            )

        session = await loop.run_in_executor(None, _create)
        return CheckoutSession(url=session.url, session_id=session.id)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatus:
        stripe = self._configure()
        loop = asyncio.get_event_loop()

        def _retrieve():
            return stripe.checkout.Session.retrieve(session_id)

        session = await loop.run_in_executor(None, _retrieve)
        return CheckoutStatus(
            status=session.status or "open",
            payment_status=session.payment_status or "unpaid",
            amount_total=session.amount_total,  # in cents; caller divides by 100
            currency=session.currency,
            session_id=session.id,
        )

    async def handle_webhook(self, body: bytes, signature: str) -> WebhookEvent:
        stripe = self._configure()
        webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

        loop = asyncio.get_event_loop()

        def _construct():
            if webhook_secret:
                return stripe.Webhook.construct_event(body, signature, webhook_secret)
            # No secret — parse body as JSON (test/dev mode)
            import json
            return stripe.Event.construct_from(json.loads(body), stripe.api_key)

        event = await loop.run_in_executor(None, _construct)
        event_type = event.get("type", "")
        session_id = None
        payment_status = "unknown"

        if event_type in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
            session_obj = event.get("data", {}).get("object", {})
            session_id = session_obj.get("id")
            payment_status = session_obj.get("payment_status", "unknown")

        return WebhookEvent(
            event_type=event_type,
            payment_status=payment_status,
            session_id=session_id,
        )
