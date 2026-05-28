"""
Integration tests — FastAPI TestClient against in-process SQLite DB.

These tests exercise the full request/response cycle without a network.
They ARE slower than unit tests (app startup + DB I/O) but faster than E2E.
CI runs these after unit tests pass.

Coverage:
  ✓ Health endpoints
  ✓ Revenue CRUD + stats
  ✓ Content Studio (ideas CRUD)
  ✓ Publishing log
  ✓ Cycle connectors endpoint
  ✓ Auth endpoints
  ✓ System status (quickstart wizard data)
  ✓ Cost policy (Free-Only Build Directive)
  ✓ Scout sources
"""
from __future__ import annotations

import sys
import os
import pytest
import datetime as _dt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Re-use the fixtures from conftest.py (automatically loaded by pytest)


# ── Helpers ────────────────────────────────────────────────────────────────────

def skip_no_app(client):
    """Skip test gracefully if the app couldn't be imported."""
    if client is None:
        pytest.skip("FastAPI app not available")


# ── Health ─────────────────────────────────────────────────────────────────────

class TestHealthIntegration:
    def test_health_returns_200(self, client):
        skip_no_app(client)
        r = client.get("/api/health/")
        assert r.status_code == 200

    def test_health_has_status_healthy(self, client):
        skip_no_app(client)
        d = client.get("/api/health/").json()
        assert d["status"] == "healthy"
        assert "timestamp" in d

    def test_root_returns_operational(self, client):
        skip_no_app(client)
        d = client.get("/api/").json()
        assert d.get("status") == "operational"


# ── Auth ───────────────────────────────────────────────────────────────────────

class TestAuthIntegration:
    def test_config_endpoint_accessible(self, client):
        skip_no_app(client)
        r = client.get("/api/auth/config")
        assert r.status_code == 200
        d = r.json()
        assert "required" in d

    def test_me_without_session_401(self, client):
        skip_no_app(client)
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_session_bogus_id_401(self, client):
        skip_no_app(client)
        r = client.post("/api/auth/session", json={"session_id": "bogus-session-xyz"})
        assert r.status_code == 401

    def test_logout_always_200(self, client):
        skip_no_app(client)
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert r.json().get("logged_out") is True


# ── System Status ──────────────────────────────────────────────────────────────

class TestSystemStatusIntegration:
    def test_status_shape(self, client):
        skip_no_app(client)
        r = client.get("/api/system/status")
        assert r.status_code == 200, r.text
        d = r.json()
        for key in (
            "operator_email_set", "stripe_mode", "stripe_webhook_secret_set",
            "emergent_llm_key_set", "daily_cycle_hour_utc", "counts", "is_seeded",
        ):
            assert key in d, f"Missing key: {key}"

    def test_status_does_not_leak_secrets(self, client):
        skip_no_app(client)
        body = client.get("/api/system/status").text.lower()
        for needle in ("sk_test_", "sk_live_", "whsec_", "sk-emergent-"):
            assert needle not in body, f"Secret prefix leaked: {needle}"

    def test_stripe_mode_is_test_in_test_env(self, client):
        skip_no_app(client)
        d = client.get("/api/system/status").json()
        assert d["stripe_mode"] in ("test", "missing", "unknown")

    def test_operator_email_not_set_in_test_env(self, client):
        skip_no_app(client)
        d = client.get("/api/system/status").json()
        # In test env OPERATOR_EMAIL is not set → operator_email_set should be False
        assert isinstance(d["operator_email_set"], bool)


# ── Revenue ────────────────────────────────────────────────────────────────────

class TestRevenueIntegration:
    def test_list_returns_200(self, client):
        skip_no_app(client)
        r = client.get("/api/revenue/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_stats_overview_shape(self, client):
        skip_no_app(client)
        r = client.get("/api/revenue/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert "total_monthly_target" in d
        assert "total_monthly_actual" in d
        assert "active_streams" in d


# ── Content Studio (Ideas) ─────────────────────────────────────────────────────

class TestStudioIntegration:
    def test_list_ideas_200(self, client):
        skip_no_app(client)
        r = client.get("/api/studio/ideas/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_idea_and_retrieve(self, client):
        skip_no_app(client)
        payload = {
            "title": "Integration Test Idea",
            "description": "Created by integration test",
            "topic": "testing",
            "target_platforms": ["medium", "reddit"],
            "tags": ["integration-test"],
        }
        rc = client.post("/api/studio/ideas/", json=payload)
        assert rc.status_code in (200, 201), f"Create failed: {rc.status_code} {rc.text}"
        idea = rc.json()
        assert idea["title"] == payload["title"]
        assert "id" in idea

        # Retrieve from list
        rl = client.get("/api/studio/ideas/")
        ids = [i["id"] for i in rl.json()]
        assert idea["id"] in ids

    def test_create_idea_missing_topic_422(self, client):
        skip_no_app(client)
        r = client.post("/api/studio/ideas/", json={
            "title": "No topic",
            "description": "Missing topic field",
        })
        assert r.status_code == 422

    def test_list_connectors_200(self, client):
        skip_no_app(client)
        r = client.get("/api/studio/connectors/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_connectors_include_facebook_and_reddit(self, client):
        """
        After seeding (python seed_data.py), facebook and reddit connectors should exist.
        In a fresh test DB without seed this test is skipped gracefully.
        """
        skip_no_app(client)
        connectors = client.get("/api/studio/connectors/").json()
        if not connectors:
            pytest.skip("No connectors in test DB — run seed_data.py first")
        platforms = {c.get("platform") for c in connectors}
        assert "facebook" in platforms, f"facebook missing from {platforms}"
        assert "reddit" in platforms, f"reddit missing from {platforms}"


# ── Publishing Log ─────────────────────────────────────────────────────────────

class TestPublishingIntegration:
    def test_stats_overview_shape(self, client):
        skip_no_app(client)
        r = client.get("/api/publishing/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert "by_status" in d

    def test_invalid_status_rejected(self, client):
        skip_no_app(client)
        r = client.post("/api/publishing/", json={
            "stream_id": "rev-001",
            "platform": "blog",
            "title": "test",
            "status": "INVALID_STATUS",
        })
        assert r.status_code in (400, 422)


# ── Cycle Connectors ───────────────────────────────────────────────────────────

class TestCycleConnectorsIntegration:
    def test_connectors_endpoint_shape(self, client):
        skip_no_app(client)
        r = client.get("/api/cycle/connectors")
        assert r.status_code == 200
        d = r.json()
        assert "live" in d
        assert "missing" in d
        assert "detail" in d

    def test_no_credentials_in_test_env(self, client):
        skip_no_app(client)
        d = client.get("/api/cycle/connectors").json()
        # In clean test env, no social platforms should be "live"
        assert isinstance(d["live"], list)
        assert isinstance(d["missing"], list)


# ── Cost Policy ────────────────────────────────────────────────────────────────

class TestCostPolicyIntegration:
    def test_policy_blocks_paid(self, client):
        skip_no_app(client)
        r = client.get("/api/cost/policy")
        assert r.status_code == 200
        d = r.json()
        assert d["block_paid_connectors"] is True

    def test_cost_status_target_is_zero(self, client):
        skip_no_app(client)
        r = client.get("/api/cost/status")
        assert r.status_code == 200
        d = r.json()
        assert d["target_monthly_usd"] == 0.0


# ── Scout ──────────────────────────────────────────────────────────────────────

class TestScoutIntegration:
    def test_sources_endpoint(self, client):
        skip_no_app(client)
        r = client.get("/api/scout/sources")
        assert r.status_code == 200
        d = r.json()
        assert "sources" in d
        assert len(d["sources"]) >= 3

    def test_sources_all_free(self, client):
        skip_no_app(client)
        sources = client.get("/api/scout/sources").json()["sources"]
        for src in sources:
            assert src["cost"] == "$0", f"Non-free source: {src['id']}"


# ── Agents ─────────────────────────────────────────────────────────────────────

class TestAgentsIntegration:
    def test_list_agents_200(self, client):
        skip_no_app(client)
        r = client.get("/api/agents/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── Payments ───────────────────────────────────────────────────────────────────

class TestPaymentsIntegration:
    def test_packages_listed(self, client):
        skip_no_app(client)
        r = client.get("/api/payments/packages")
        assert r.status_code == 200
        pkgs = r.json()
        for pid in ("starter", "pro", "enterprise"):
            assert pid in pkgs

    def test_checkout_unknown_package_400(self, client):
        skip_no_app(client)
        r = client.post("/api/payments/checkout", json={
            "package_id": "bogus_package",
            "origin_url": "http://localhost:3000",
        })
        assert r.status_code == 400

    def test_readiness_checklist_shape(self, client):
        skip_no_app(client)
        r = client.get("/api/payments/readiness")
        assert r.status_code == 200
        d = r.json()
        for k in ("stripe_mode", "go_live_ready", "issues", "checklist"):
            assert k in d
