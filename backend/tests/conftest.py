"""
Shared pytest fixtures for Already Here Command OS test suite.

Fixture hierarchy:
  app          — FastAPI app instance (integration / e2e)
  client       — TestClient bound to `app`
  anyio_backend — forces asyncio backend for async tests
  live_url     — live deployment URL (env-driven)
  mock_env     — patches os.environ for unit tests
"""
from __future__ import annotations

import os
import sys
import pytest

# Ensure backend package is importable when running tests from /backend/tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Live URL (integration / e2e via requests) ──────────────────────────────────

LIVE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://app.alreadyherellc.com",
).rstrip("/")


@pytest.fixture(scope="session")
def live_url() -> str:
    return LIVE_URL


@pytest.fixture(scope="session")
def api_session():
    import requests
    s = requests.Session()
    s.headers["Content-Type"] = "application/json"
    return s


# ── FastAPI TestClient (integration tests — in-process, no network) ────────────

@pytest.fixture(scope="session")
def app():
    """
    Import and return the FastAPI application.
    Uses SQLite in /tmp so tests never touch the production DB.
    """
    os.environ.setdefault("STORAGE_BACKEND", "sqlite")
    os.environ.setdefault("SQLITE_PATH", "/tmp/test_command_os.db")
    os.environ.setdefault("SYSTEM_MODE", "test")
    os.environ.setdefault("COST_GUARD_ENABLED", "true")
    os.environ.setdefault("ZERO_SPEND_MODE", "true")
    os.environ.setdefault("AUTO_CYCLE_ENABLED", "false")
    os.environ.setdefault("STRIPE_API_KEY", "sk_test_emergent")
    # Suppress LLM calls in integration tests
    os.environ.setdefault("EMERGENT_LLM_KEY", "")

    try:
        from server import app as fastapi_app
        return fastapi_app
    except Exception as e:
        pytest.skip(f"Could not import FastAPI app: {e}")


@pytest.fixture(scope="session")
def client(app):
    """Synchronous TestClient — works for non-async routes."""
    from fastapi.testclient import TestClient
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Environment patching for unit tests ────────────────────────────────────────

@pytest.fixture
def mock_env(monkeypatch):
    """
    Returns a helper that sets env vars for the duration of a test.
    Usage:  mock_env(MEDIUM_INTEGRATION_TOKEN="test-token")
    """
    def _set(**kwargs):
        for k, v in kwargs.items():
            monkeypatch.setenv(k, v)
    return _set


@pytest.fixture
def clean_env(monkeypatch):
    """
    Clears all social-media credential env vars so unit tests start clean.
    """
    keys = [
        "MEDIUM_INTEGRATION_TOKEN", "DEVTO_API_KEY",
        "REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USERNAME", "REDDIT_PASSWORD",
        "REDDIT_SUBREDDITS",
        "FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN",
        "IG_USER_ID", "IG_ACCESS_TOKEN",
        "THREADS_USER_ID", "THREADS_ACCESS_TOKEN",
        "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_PERSON_URN",
        "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
        "TIKTOK_ACCESS_TOKEN",
        "DISCOURSE_BASE_URL", "DISCOURSE_API_KEY", "DISCOURSE_API_USERNAME",
        "EMERGENT_LLM_KEY",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)
