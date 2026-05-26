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
EXPECTED_REVENUE_NAMES = {
    "AI Blog Network", "Faceless Videos", "Print-on-Demand A", "Print-on-Demand B",
    "Affiliate Links", "Social Automation", "SEO Content Farm", "Federal Contracting",
    "Service Automation", "Newsletter Sponsorships",
}


class TestRevenue:
    def test_list_revenue_has_10_streams(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) == 10, f"Expected exactly 10 streams, got {len(data)}"
        names = {s["name"] for s in data}
        assert names == EXPECTED_REVENUE_NAMES, f"Stream name mismatch. Got: {names}"

    def test_revenue_stats_totals(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/stats/overview")
        assert r.status_code == 200
        d = r.json()
        # Targets sum = 4000+6000+3500+3500+5000+2500+4500+15000+10000+2000 = 56000
        assert abs(d["total_monthly_target"] - 56000.0) < 1.0, f"target={d['total_monthly_target']}"
        # Actuals sum = 1850+2400+1200+980+2100+1340+2780+3000+4250+820 = 20720
        assert abs(d["total_monthly_actual"] - 20720.0) < 1.0, f"actual={d['total_monthly_actual']}"
        # 20720/56000 = ~37%
        ap = d.get("achievement_percentage", 0)
        assert 36 <= ap <= 38, f"achievement_percentage={ap}"
        assert d["active_streams"] == 10
        assert d["total_streams"] == 10


# ---------------- Agents ----------------
NEW_AGENT_NAMES = {"SEO Scout Agent", "Faceless Video Agent", "POD Designer Agent",
                   "Affiliate Link Agent", "Health Oracle Agent"}


class TestAgents:
    def test_list_agents_has_10(self, api):
        r = api.get(f"{BASE_URL}/api/agents/")
        assert r.status_code == 200
        agents = r.json()
        assert isinstance(agents, list)
        assert len(agents) == 10, f"Expected 10 agents, got {len(agents)}"
        names = {a["name"] for a in agents}
        missing = NEW_AGENT_NAMES - names
        assert not missing, f"Missing new agents: {missing}"


# ---------------- Builds ----------------
class TestBuilds:
    def test_list_builds(self, api):
        r = api.get(f"{BASE_URL}/api/builds/")
        assert r.status_code == 200
        builds = r.json()
        assert isinstance(builds, list)
        assert len(builds) == 5, f"Expected 5 builds, got {len(builds)}"

    def test_profitengine_v5_live_and_pass(self, api):
        r = api.get(f"{BASE_URL}/api/builds/")
        assert r.status_code == 200
        builds = {b["id"]: b for b in r.json()}
        b1 = builds.get("build-001")
        assert b1 is not None, "build-001 missing"
        assert b1["status"] == "live", f"build-001 status={b1['status']}"
        assert b1["last_ci_status"] == "pass", f"build-001 ci={b1['last_ci_status']}"
        assert b1["name"] == "ProfitEngine v5"

    def test_vhll_distillation_live(self, api):
        r = api.get(f"{BASE_URL}/api/builds/")
        assert r.status_code == 200
        builds = {b["id"]: b for b in r.json()}
        b4 = builds.get("build-004")
        assert b4 is not None, "build-004 missing"
        assert b4["status"] == "live", f"build-004 status={b4['status']}"
        assert b4["name"] == "VHLL Distillation Engine"


# ---------------- Deployments ----------------
class TestDeployments:
    def test_list_deployments_all_success(self, api):
        r = api.get(f"{BASE_URL}/api/deployments/")
        assert r.status_code == 200
        deps = r.json()
        assert isinstance(deps, list)
        assert len(deps) == 4, f"Expected 4 deployments, got {len(deps)}"
        bad = [d for d in deps if d["status"] != "success"]
        assert not bad, f"Non-success deployments: {[(d['id'], d['status']) for d in bad]}"

    def test_deployments_include_laptop_target(self, api):
        r = api.get(f"{BASE_URL}/api/deployments/")
        assert r.status_code == 200
        targets = {d["target"] for d in r.json()}
        assert "laptop" in targets, f"laptop target missing, got {targets}"
        assert "oci" in targets, f"oci target missing, got {targets}"


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

    def test_create_idea_missing_topic_returns_422(self, api):
        payload = {
            "title": "TEST_Missing_Topic",
            "description": "No topic provided",
            "target_platforms": ["tiktok"],
        }
        r = api.post(f"{BASE_URL}/api/studio/ideas/", json=payload)
        assert r.status_code == 422, f"Expected 422 for missing topic, got {r.status_code}: {r.text[:300]}"
        data = r.json()
        assert "detail" in data
        # ensure 'topic' is mentioned in validation error
        details_str = str(data["detail"]).lower()
        assert "topic" in details_str

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
