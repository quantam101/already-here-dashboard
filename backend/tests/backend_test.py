"""Backend API tests for Already Here Command OS."""
import os
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://gmaos-control.preview.emergentagent.com').rstrip('/')


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------- Health ----------------
class TestHealth:
    def test_health_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/health/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_root_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/")
        assert r.status_code == 200
        assert r.json().get("status") == "operational"


# ---------------- Revenue ----------------
class TestRevenue:
    def test_list_revenue(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # seeded 3 streams per request
        assert len(data) >= 1

    def test_revenue_stats(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert "total_monthly_target" in d
        assert "total_monthly_actual" in d
        assert "active_streams" in d
        assert "total_streams" in d


# ---------------- Agents ----------------
class TestAgents:
    def test_list_agents(self, api):
        r = api.get(f"{BASE_URL}/api/agents/")
        assert r.status_code == 200
        agents = r.json()
        assert isinstance(agents, list)
        assert len(agents) >= 5, f"Expected 5 seeded agents, got {len(agents)}"
        # check first has run_count and success metrics fields
        a = agents[0]
        assert "id" in a
        assert "name" in a


# ---------------- Builds ----------------
class TestBuilds:
    def test_list_builds(self, api):
        r = api.get(f"{BASE_URL}/api/builds/")
        assert r.status_code == 200
        builds = r.json()
        assert isinstance(builds, list)
        assert len(builds) >= 5, f"Expected 5 seeded builds, got {len(builds)}"


# ---------------- Deployments ----------------
class TestDeployments:
    def test_list_deployments(self, api):
        r = api.get(f"{BASE_URL}/api/deployments/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Content ----------------
class TestContent:
    def test_list_content(self, api):
        r = api.get(f"{BASE_URL}/api/content/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Audit ----------------
class TestAudit:
    def test_list_audit(self, api):
        r = api.get(f"{BASE_URL}/api/audit/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_audit_stats(self, api):
        r = api.get(f"{BASE_URL}/api/audit/stats")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)


# ---------------- Approvals ----------------
class TestApprovals:
    def test_list_approvals(self, api):
        r = api.get(f"{BASE_URL}/api/approvals/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Content Factory / Studio ----------------
class TestStudio:
    def test_list_connectors(self, api):
        r = api.get(f"{BASE_URL}/api/studio/connectors/")
        assert r.status_code == 200
        connectors = r.json()
        assert isinstance(connectors, list)
        assert len(connectors) >= 7, f"Expected 7 connectors, got {len(connectors)}"
        # verify cost_class field present and contains expected classes
        classes = {c.get("cost_class") for c in connectors}
        assert "free_local" in classes or "manual_free" in classes or "paid_blocked" in classes, \
            f"Missing expected cost classes, got {classes}"

    def test_list_ideas(self, api):
        r = api.get(f"{BASE_URL}/api/studio/ideas/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_idea_and_persist(self, api):
        payload = {
            "title": "TEST_Idea_From_Backend_Test",
            "description": "Testing idea creation flow",
            "topic": "Backend testing topic",
            "target_platforms": ["tiktok", "youtube"],
            "tags": ["test"]
        }
        r = api.post(f"{BASE_URL}/api/studio/ideas/", json=payload)
        assert r.status_code in (200, 201), f"Create idea failed: {r.status_code} {r.text}"
        created = r.json()
        assert created["title"] == payload["title"]
        assert "id" in created
        idea_id = created["id"]

        # GET back to verify persisted
        rl = api.get(f"{BASE_URL}/api/studio/ideas/")
        assert rl.status_code == 200
        ids = [i["id"] for i in rl.json()]
        assert idea_id in ids

    @pytest.mark.timeout(60)
    def test_generate_script_uses_ai(self, api):
        # Create idea first
        payload = {
            "title": "TEST_Script_Gen_Idea",
            "description": "Short test idea for AI script generation",
            "topic": "AI testing for content generation",
            "target_platforms": ["tiktok"],
            "tags": ["ai-test"]
        }
        rc = api.post(f"{BASE_URL}/api/studio/ideas/", json=payload)
        assert rc.status_code in (200, 201)
        idea_id = rc.json()["id"]

        # Generate script - AI call may take time
        r = api.post(f"{BASE_URL}/api/studio/ideas/{idea_id}/script", timeout=90)
        assert r.status_code == 200, f"Script generation failed: {r.status_code} {r.text[:400]}"
        script = r.json()
        assert "id" in script
        # Expect some script content
        assert any(k in script for k in ("hook", "body", "script_text", "content", "outro"))
