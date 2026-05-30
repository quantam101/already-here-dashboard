"""
Stripe adapter — direct calls to the official `stripe` SDK with a 3-method
surface area used by the payments routes.

Mock mode: when STRIPE_API_KEY starts with `sk_test_placeholder` or
`sk_test_emergent` (legacy), or is unset, the adapter returns synthesized
session objects so the test suite + UI smoke runs work without real keys.
Real production deployments set `sk_live_...` and the SDK is called normally.
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

import stripe as stripe_sdk


_PLACEHOLDER_PREFIXES = ("sk_test_placeholder", "sk_test_emergent")


def _is_placeholder(key: str) -> bool:
    if not key:
        return True
    return key.startswith(_PLACEHOLDER_PREFIXES)


@dataclass
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: dict[str, str]


@dataclass
class CheckoutSession:
    url: str
    session_id: str


@dataclass
class CheckoutStatus:
    status: str
    payment_status: str
    amount_total: int | None
    currency: str = "usd"


@dataclass
class WebhookEvent:
    event_type: str
    session_id: str
    payment_status: str


class StripeAdapter:
    """Minimal Stripe SDK wrapper. Configures stripe.api_key on construction.

    When given a placeholder key, returns synthesized responses (mock mode)
    so the codebase is testable + demoable without real Stripe credentials.
    """

    def __init__(self, api_key: str, webhook_url: str | None = None):
        if not api_key:
            raise ValueError("StripeAdapter requires a non-empty api_key")
        self.api_key = api_key
        self.mock = _is_placeholder(api_key)
        if not self.mock:
            stripe_sdk.api_key = api_key
        self.webhook_url = webhook_url

    async def create_checkout_session(
        self, req: CheckoutSessionRequest
    ) -> CheckoutSession:
        if self.mock:
            sid = f"cs_test_mock_{uuid.uuid4().hex[:20]}"
            return CheckoutSession(
                url=f"{req.success_url.split('?')[0]}?session_id={sid}&mock=1",
                session_id=sid,
            )

        cents = int(round(float(req.amount) * 100))
        metadata = {k: str(v) for k, v in (req.metadata or {}).items() if v is not None}
        session = stripe_sdk.checkout.Session.create(
            mode="payment",
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            line_items=[{
                "price_data": {
                    "currency": (req.currency or "usd").lower(),
                    "product_data": {
                        "name": metadata.get("package_name", "Command OS purchase"),
                    },
                    "unit_amount": cents,
                },
                "quantity": 1,
            }],
            metadata=metadata,
        )
        return CheckoutSession(url=session.url, session_id=session.id)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatus:
        if self.mock or (session_id or "").startswith(("cs_test_mock_", "cs_mock_")):
            # Mock sessions stay "open / unpaid" — operators can't complete a
            # real payment against a fake key, so this never auto-flips to paid.
            return CheckoutStatus(status="open", payment_status="unpaid", amount_total=0)

        sess = stripe_sdk.checkout.Session.retrieve(session_id)
        return CheckoutStatus(
            status=sess.status or "open",
            payment_status=sess.payment_status or "unpaid",
            amount_total=sess.amount_total,
            currency=(sess.currency or "usd").lower(),
        )

    async def handle_webhook(self, body: bytes, signature: str) -> WebhookEvent:
        """Verify signature + return a flat event object.

        Requires STRIPE_WEBHOOK_SECRET env. Raises ValueError on bad signature.
        Mock mode short-circuits with a no-op event (operators can't trigger
        real webhooks without real keys anyway).
        """
        if self.mock:
            return WebhookEvent(event_type="mock.noop", session_id="", payment_status="")
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
        if not secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET not configured")
        event: dict[str, Any] = stripe_sdk.Webhook.construct_event(
            payload=body, sig_header=signature, secret=secret,
        )
        obj = event.get("data", {}).get("object", {}) or {}
        session_id = obj.get("id") or obj.get("session_id") or ""
        payment_status = obj.get("payment_status") or ""
        return WebhookEvent(
            event_type=event.get("type", ""),
            session_id=session_id,
            payment_status=payment_status,
        )
