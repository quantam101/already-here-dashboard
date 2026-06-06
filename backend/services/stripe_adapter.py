"""Stripe adapter for Already Here Command OS payments.

This module intentionally wraps the official Stripe SDK behind a tiny async
interface so FastAPI routes can stay testable while production uses real Stripe
Checkout and signed webhook verification.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CheckoutSessionRequest:
    amount: float
    currency: str
    success_url: str
    cancel_url: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CheckoutSession:
    url: str
    session_id: str


@dataclass(frozen=True)
class CheckoutStatus:
    status: str
    payment_status: str
    amount_total: int | None
    currency: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StripeWebhookEvent:
    event_id: str
    event_type: str
    session_id: str | None
    payment_status: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


class StripeAdapter:
    def __init__(self, api_key: str, webhook_url: str, webhook_secret: str | None = None) -> None:
        self.api_key = (api_key or "").strip()
        self.webhook_url = webhook_url
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET")

    def _validate_api_key(self) -> None:
        if not self.api_key:
            raise ValueError("invalid api key: STRIPE_API_KEY is not configured")
        if self.api_key == "sk_test_placeholder" or not self.api_key.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
            raise ValueError("invalid api key: STRIPE_API_KEY must be a real Stripe key")

    @staticmethod
    def _metadata(metadata: dict[str, Any]) -> dict[str, str]:
        return {str(key): "" if value is None else str(value)[:500] for key, value in metadata.items()}

    async def create_checkout_session(self, req: CheckoutSessionRequest) -> CheckoutSession:
        self._validate_api_key()
        if req.amount <= 0:
            raise ValueError("amount must be greater than zero")
        currency = (req.currency or "usd").lower()
        unit_amount = int(round(float(req.amount) * 100))
        metadata = self._metadata(req.metadata)

        import stripe

        stripe.api_key = self.api_key
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": metadata.get("package_name") or metadata.get("package_id") or "Command OS package",
                        },
                        "unit_amount": unit_amount,
                    },
                    "quantity": 1,
                }
            ],
            success_url=req.success_url,
            cancel_url=req.cancel_url,
            metadata=metadata,
        )
        url = getattr(session, "url", None)
        session_id = getattr(session, "id", None)
        if not url or not session_id:
            raise RuntimeError("Stripe returned an incomplete checkout session")
        return CheckoutSession(url=url, session_id=session_id)

    async def get_checkout_status(self, session_id: str) -> CheckoutStatus:
        self._validate_api_key()
        if not session_id:
            raise ValueError("session_id is required")

        import stripe

        stripe.api_key = self.api_key
        session = await asyncio.to_thread(stripe.checkout.Session.retrieve, session_id)
        return CheckoutStatus(
            status=getattr(session, "status", None) or "open",
            payment_status=getattr(session, "payment_status", None) or "unpaid",
            amount_total=getattr(session, "amount_total", None),
            currency=getattr(session, "currency", None),
            metadata=dict(getattr(session, "metadata", None) or {}),
        )

    async def handle_webhook(self, body: bytes, signature: str) -> StripeWebhookEvent:
        self._validate_api_key()
        if not self.webhook_secret:
            raise ValueError("STRIPE_WEBHOOK_SECRET is required for webhook verification")
        if not signature:
            raise ValueError("Stripe-Signature header is required")

        import stripe

        event = stripe.Webhook.construct_event(body, signature, self.webhook_secret)
        event_type = event.get("type", "")
        data = (event.get("data") or {}).get("object") or {}
        session_id = data.get("id") if event_type.startswith("checkout.session") else None
        return StripeWebhookEvent(
            event_id=event.get("id", ""),
            event_type=event_type,
            session_id=session_id,
            payment_status=data.get("payment_status"),
            metadata=dict(data.get("metadata") or {}),
        )
