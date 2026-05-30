"""
End-to-End tests — Playwright against https://app.alreadyherellc.com

These test the full stack: browser → Caddy → FastAPI backend → SQLite.
They run AFTER integration tests pass.

Requirements:
  pip install playwright pytest-playwright
  playwright install chromium

Set REACT_APP_BACKEND_URL to override the default live URL.

Auth: OPERATOR_EMAIL is empty on the test server so no Google login required.
The AuthGate passes through automatically when no operator email is set.
"""
from __future__ import annotations

import os

import pytest

# Skip entire module if playwright isn't installed
pytest.importorskip("playwright", reason="playwright not installed — skipping E2E tests")

from playwright.sync_api import Browser, Page, expect

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL", "https://app.alreadyherellc.com"
).rstrip("/")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://app.alreadyherellc.com")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser_context(browser: Browser):
    """Create a persistent browser context for the session."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        base_url=FRONTEND_URL,
    )
    yield context
    context.close()


@pytest.fixture
def page(browser_context):
    p = browser_context.new_page()
    # Suppress both first-run overlays so navigation tests can click through:
    #  - pe5_walkthrough_seen   → prevents FirstRunWalkthrough (z-9999 overlay)
    #  - ah_quickstart_completed_v1 → prevents QuickstartWizard Dialog (z-50 overlay)
    # The live server may be running an older build where the wizard auto-opens;
    # setting both keys before React mounts ensures neither overlay intercepts clicks.
    p.add_init_script(
        "localStorage.setItem('pe5_walkthrough_seen', new Date().toISOString());"
        "localStorage.setItem('ah_quickstart_completed_v1', new Date().toISOString());"
    )
    yield p
    p.close()


# ── Health (API smoke via page.request) ────────────────────────────────────────

class TestAPIHealthE2E:
    def test_health_endpoint_200(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/health/")
        assert response.status == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint_200(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/")
        assert response.status == 200
        assert response.json()["status"] == "operational"


# ── Dashboard Navigation ───────────────────────────────────────────────────────

class TestDashboardNavigationE2E:
    def test_overview_page_loads(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        # Dashboard title should be visible
        expect(page.get_by_test_id("dashboard-title")).to_be_visible(timeout=15000)

    def test_sidebar_nav_present(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        expect(page.get_by_test_id("sidebar-nav")).to_be_visible(timeout=15000)

    def test_main_content_area_visible(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        expect(page.get_by_test_id("main-content")).to_be_visible(timeout=10000)

    def test_navigate_to_studio(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        # Click Content Factory nav link
        page.get_by_test_id("nav-content-factory").click()
        page.wait_for_url("**/studio", timeout=10000)
        expect(page).to_have_url(f"{FRONTEND_URL}/studio")

    def test_navigate_to_sovereign(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        page.get_by_test_id("nav-cash-ai").click()
        page.wait_for_url("**/sovereign", timeout=10000)

    def test_navigate_to_scout(self, page: Page):
        page.goto(f"{FRONTEND_URL}/overview")
        page.get_by_test_id("nav-scout").click()
        page.wait_for_url("**/scout", timeout=10000)


# ── Quickstart Wizard ─────────────────────────────────────────────────────────

class TestQuickstartWizardE2E:
    def test_wizard_appears_on_first_visit(self, browser_context):
        """Open a fresh page with cleared localStorage to trigger first-run wizard."""
        page = browser_context.new_page()
        # Clear wizard completion flag
        page.goto(f"{FRONTEND_URL}/overview")
        page.evaluate("window.localStorage.removeItem('ah_quickstart_completed_v1')")
        page.reload()

        # Wizard dialog should open
        wizard = page.get_by_test_id("quickstart-wizard")
        expect(wizard).to_be_visible(timeout=15000)
        page.close()

    def test_wizard_skip_button_dismisses(self, browser_context):
        page = browser_context.new_page()
        page.goto(f"{FRONTEND_URL}/overview")
        page.evaluate("window.localStorage.removeItem('ah_quickstart_completed_v1')")
        page.reload()
        page.wait_for_selector('[data-testid="quickstart-wizard"]', timeout=15000)

        # Click Skip
        page.get_by_test_id("quickstart-skip").click()

        # Wizard should close
        expect(page.get_by_test_id("quickstart-wizard")).not_to_be_visible(timeout=5000)
        page.close()

    def test_wizard_next_button_advances_step(self, browser_context):
        page = browser_context.new_page()
        page.goto(f"{FRONTEND_URL}/overview")
        page.evaluate("window.localStorage.removeItem('ah_quickstart_completed_v1')")
        page.reload()
        page.wait_for_selector('[data-testid="quickstart-wizard"]', timeout=15000)

        # Click Next from step 1
        page.get_by_test_id("quickstart-next").click()

        # Step 2 content should appear (Operator access)
        expect(page.locator("text=Operator access")).to_be_visible(timeout=5000)
        page.close()

    def test_sidebar_quickstart_trigger_reopens_wizard(self, browser_context):
        page = browser_context.new_page()
        page.goto(f"{FRONTEND_URL}/overview")
        # Dismiss wizard first
        page.evaluate("window.localStorage.setItem('ah_quickstart_completed_v1', '2024-01-01')")
        page.reload()

        # Re-open via sidebar button
        page.get_by_test_id("sidebar-quickstart-trigger").click()
        expect(page.get_by_test_id("quickstart-wizard")).to_be_visible(timeout=10000)
        page.close()


# ── Cycle API via browser ─────────────────────────────────────────────────────

class TestCycleE2E:
    def test_connectors_api_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/cycle/connectors")
        assert response.status == 200
        d = response.json()
        assert "live" in d
        assert "missing" in d

    def test_cycle_run_returns_200(self, page: Page):
        """Running a cycle should succeed even with no social credentials."""
        response = page.request.post(f"{BASE_URL}/api/cycle/run")
        assert response.status == 200
        d = response.json()
        assert d["cycle_id"].startswith("cyc-")
        assert "next_action" in d

    def test_export_pack_404_for_unknown_idea(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/cycle/export-pack/idea-does-not-exist")
        assert response.status == 404


# ── Revenue API ───────────────────────────────────────────────────────────────

class TestRevenueE2E:
    def test_revenue_list_returns_list(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/revenue/")
        assert response.status == 200
        assert isinstance(response.json(), list)

    def test_revenue_stats_shape(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/revenue/stats/overview")
        assert response.status == 200
        d = response.json()
        assert "total_monthly_target" in d
        assert "active_streams" in d


# ── Studio / Content Factory ──────────────────────────────────────────────────

class TestStudioE2E:
    def test_ideas_list_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/studio/ideas/")
        assert response.status == 200
        assert isinstance(response.json(), list)

    def test_connectors_list_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/studio/connectors/")
        assert response.status == 200
        connectors = response.json()
        assert len(connectors) >= 7

    def test_create_idea_via_api(self, page: Page):
        payload = {
            "title": "E2E Test Idea — Playwright",
            "description": "Created by Playwright E2E test",
            "topic": "e2e testing",
            "target_platforms": ["medium", "devto"],
            "tags": ["e2e"],
        }
        response = page.request.post(
            f"{BASE_URL}/api/studio/ideas/",
            data=str(payload).replace("'", '"'),
            headers={"Content-Type": "application/json"},
        )
        # Accept 200 or 201
        assert response.status in (200, 201), f"Create idea failed: {response.status}"
        created = response.json()
        assert "id" in created
        assert created["title"] == payload["title"]

    def test_export_pack_for_created_idea(self, page: Page):
        """Create an idea, then get its export pack."""
        import json
        payload = {
            "title": "E2E Export Pack Test",
            "description": "Testing export pack via Playwright",
            "topic": "content creation",
            "target_platforms": ["tiktok", "youtube"],
            "tags": ["export-test"],
        }
        create_r = page.request.post(
            f"{BASE_URL}/api/studio/ideas/",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        if create_r.status not in (200, 201):
            pytest.skip("Could not create idea for export pack test")

        idea_id = create_r.json()["id"]
        pack_r = page.request.get(f"{BASE_URL}/api/cycle/export-pack/{idea_id}")
        assert pack_r.status == 200
        pack = pack_r.json()
        assert "export_pack" in pack
        assert "video_script" in pack["export_pack"]
        assert "facebook_groups" in pack["export_pack"]


# ── Publishing Log ────────────────────────────────────────────────────────────

class TestPublishingE2E:
    def test_stats_overview_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/publishing/stats/overview")
        assert response.status == 200
        d = response.json()
        assert "by_status" in d
        assert "by_platform" in d


# ── Analytics ─────────────────────────────────────────────────────────────────

class TestAnalyticsE2E:
    def test_funnel_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/analytics/funnel")
        assert response.status == 200

    def test_dashboard_accessible(self, page: Page):
        response = page.request.get(f"{BASE_URL}/api/analytics/dashboard")
        assert response.status == 200
