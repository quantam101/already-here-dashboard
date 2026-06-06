from __future__ import annotations

import asyncio

import pytest

from services.stripe_adapter import CheckoutSessionRequest, StripeAdapter


def test_stripe_adapter_exports_route_contract() -> None:
    req = CheckoutSessionRequest(
        amount=49.0,
        currency="usd",
        success_url="https://app.alreadyherellc.com/payment-success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://app.alreadyherellc.com/pricing?cancelled=1",
        metadata={"package_id": "starter"},
    )
    assert req.amount == 49.0
    assert req.metadata["package_id"] == "starter"
    assert StripeAdapter(api_key="sk_test_placeholder", webhook_url="https://example.test/webhook") is not None


def test_placeholder_stripe_key_is_rejected_before_network() -> None:
    adapter = StripeAdapter(api_key="sk_test_placeholder", webhook_url="https://example.test/webhook")
    req = CheckoutSessionRequest(
        amount=49.0,
        currency="usd",
        success_url="https://app.alreadyherellc.com/payment-success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://app.alreadyherellc.com/pricing?cancelled=1",
        metadata={"package_id": "starter"},
    )
    with pytest.raises(ValueError, match="invalid api key"):
        asyncio.run(adapter.create_checkout_session(req))


def test_webhook_requires_signature_and_secret() -> None:
    adapter = StripeAdapter(api_key="sk_test_valid_shape_for_unit_test_123", webhook_url="https://example.test/webhook")
    with pytest.raises(ValueError, match="STRIPE_WEBHOOK_SECRET"):
        asyncio.run(adapter.handle_webhook(b"{}", ""))
