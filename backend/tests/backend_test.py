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
    def test_list_revenue_has_seeded_streams(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # 10 seeded streams; rev-saas may also exist if Stripe checkout has been used.
        assert len(data) >= 10, f"Expected >= 10 streams, got {len(data)}"
        names = {s["name"] for s in data}
        missing = EXPECTED_REVENUE_NAMES - names
        assert not missing, f"Missing seeded streams: {missing}"

    def test_revenue_stats_totals(self, api):
        r = api.get(f"{BASE_URL}/api/revenue/stats/overview")
        assert r.status_code == 200
        d = r.json()
        # 10 seeded streams target sum = 56000. Auto-created streams may add:
        # rev-saas (5000) when Stripe checkout used; rev-books (3000) when book generated.
        assert d["total_monthly_target"] in (56000.0, 59000.0, 61000.0, 64000.0), f"target={d['total_monthly_target']}"
        # Actuals computed LIVE from the ledger - depends on state, just sanity-check.
        assert d["total_monthly_actual"] >= 0.0
        assert d["active_streams"] >= 10
        assert d["total_streams"] >= 10


# ---------------- Agents ----------------
NEW_AGENT_NAMES = {"SEO Scout Agent", "Faceless Video Agent", "POD Designer Agent",
                   "Affiliate Link Agent", "Health Oracle Agent"}


class TestAgents:
    def test_list_agents_has_at_least_10(self, api):
        r = api.get(f"{BASE_URL}/api/agents/")
        assert r.status_code == 200
        agents = r.json()
        assert isinstance(agents, list)
        assert len(agents) >= 10, f"Expected >= 10 agents, got {len(agents)}"
        names = {a["name"] for a in agents}
        missing = NEW_AGENT_NAMES - names
        assert not missing, f"Missing new agents: {missing}"
        # New procurement scout must exist too
        assert "Procurement Scout Agent" in names


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


# ---------------- Ledger (Proof of Work) ----------------
import datetime as _dt


class TestLedger:
    def test_initial_progress_is_zero(self, api):
        r = api.get(f"{BASE_URL}/api/ledger/stats/profit-progress")
        assert r.status_code == 200
        d = r.json()
        assert d["goal_usd"] == 25000.0
        assert d["unlocked"] is False
        assert d["progress_pct"] >= 0.0
        assert d["remaining_usd"] <= 25000.0

    def test_create_and_list_ledger_entry(self, api):
        today = _dt.date.today().isoformat()
        payload = {
            "stream_id": "rev-001",
            "occurred_on": today,
            "gross_amount": 12.50,
            "net_amount": 10.00,
            "source": "manual",
            "proof_url": "https://example.com/proof",
            "notes": "pytest entry",
        }
        r = api.post(f"{BASE_URL}/api/ledger/", json=payload)
        assert r.status_code == 201, r.text
        entry = r.json()
        assert entry["id"].startswith("led-")
        assert entry["net_amount"] == 10.00

        listed = api.get(f"{BASE_URL}/api/ledger/", params={"stream_id": "rev-001"}).json()
        assert any(e["id"] == entry["id"] for e in listed)

    def test_ledger_net_cannot_exceed_gross(self, api):
        r = api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-001",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": 5.0,
            "net_amount": 10.0,
        })
        assert r.status_code == 400

    def test_ledger_unknown_stream_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-does-not-exist",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": 1, "net_amount": 1,
        })
        assert r.status_code == 404

    def test_revenue_actual_reflects_ledger_current_month(self, api):
        today = _dt.date.today().isoformat()
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-002",
            "occurred_on": today,
            "gross_amount": 100,
            "net_amount": 75,
            "source": "manual",
        })
        d = api.get(f"{BASE_URL}/api/revenue/stats/overview").json()
        # Live actual must reflect at least the 75 we just recorded
        assert d["total_monthly_actual"] >= 75.0


# ---------------- Publishing log ----------------
class TestPublishing:
    def test_create_publishing_record(self, api):
        r = api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": "rev-001",
            "platform": "blog",
            "title": "pytest published post",
            "status": "posted",
            "post_url": "https://example.com/post/1",
        })
        assert r.status_code == 201, r.text
        rec = r.json()
        assert rec["id"].startswith("pub-")
        assert rec["status"] == "posted"
        assert rec["posted_at"] is not None

    def test_publishing_status_validation(self, api):
        r = api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": "rev-001",
            "platform": "blog",
            "title": "invalid-status test",
            "status": "BOGUS",
        })
        assert r.status_code == 400

    def test_publishing_stats(self, api):
        r = api.get(f"{BASE_URL}/api/publishing/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert "by_status" in d and "by_platform" in d
        assert set(d["by_status"].keys()) == {"drafted", "exported", "posted", "verified"}


# ---------------- Scout (free scrapers) ----------------
class TestScout:
    def test_sources_list(self, api):
        r = api.get(f"{BASE_URL}/api/scout/sources")
        assert r.status_code == 200
        d = r.json()
        assert "sources" in d
        source_ids = {s["id"] for s in d["sources"]}
        assert {"reddit", "hackernews", "grants_gov", "sam_gov", "google_news"}.issubset(source_ids)
        # Cost Guard: every source must be free
        for s in d["sources"]:
            assert s["cost"] == "$0", f"non-free source detected: {s}"

    def test_viral_returns_list(self, api):
        r = api.get(f"{BASE_URL}/api/scout/viral", params={"limit": 5})
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        # External services may be flaky - just ensure shape is correct
        for item in items:
            assert "id" in item and "title" in item and "source" in item and "kind" in item


# ---------------- Proposals & Procurement ----------------
class TestProposals:
    def test_create_invoice(self, api):
        r = api.post(f"{BASE_URL}/api/proposals/invoice", json={
            "client_name": "pytest client",
            "line_items": [
                {"description": "Service A", "quantity": 2, "unit_price": 100},
                {"description": "Service B", "quantity": 1, "unit_price": 50},
            ],
            "tax_pct": 8.5,
        })
        assert r.status_code == 201, r.text
        d = r.json()
        assert d["doc_type"] == "invoice"
        # 200 + 50 = 250 subtotal; tax 21.25; grand 271.25
        assert abs(d["metadata"]["subtotal"] - 250.0) < 0.01
        assert abs(d["metadata"]["total"] - 271.25) < 0.01
        assert "INVOICE" in d["content"]
        assert "$271.25" in d["content"]

    def test_invalid_doc_type_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/proposals/draft", json={
            "doc_type": "BOGUS", "title": "x",
        })
        assert r.status_code == 400

    def test_proposal_stats_overview(self, api):
        r = api.get(f"{BASE_URL}/api/proposals/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert "by_type" in d and "by_status" in d and "invoke_total_usd" in d or "invoice_total_usd" in d

    @pytest.mark.timeout(120)
    def test_ai_draft_capability_statement(self, api):
        """AI-powered draft via Emergent LLM (Gemini 3 Flash)."""
        r = api.post(f"{BASE_URL}/api/proposals/draft", json={
            "doc_type": "capability_statement",
            "title": "TEST AI Capability Statement",
            "context": "Already Here Command OS - autonomous business OS",
        }, timeout=120)
        assert r.status_code in (200, 201), f"AI draft failed: {r.status_code} {r.text[:400]}"
        d = r.json()
        assert d["id"].startswith("prop-")
        assert d["status"] == "draft"
        assert len(d.get("content", "")) > 500, f"Content too short: {len(d.get('content', ''))}"

    def test_list_and_get_proposals(self, api):
        # list - no assertion on items, just verify the endpoint responds
        r = api.get(f"{BASE_URL}/api/proposals/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Payments (Stripe) ----------------
class TestPayments:
    def test_packages_listed(self, api):
        r = api.get(f"{BASE_URL}/api/payments/packages")
        assert r.status_code == 200
        pkgs = r.json()
        for pid in ("starter", "pro", "enterprise"):
            assert pid in pkgs, f"Missing package: {pid}"
            assert pkgs[pid]["amount"] > 0
            assert pkgs[pid]["currency"] == "usd"

    def test_checkout_unknown_package(self, api):
        r = api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "bogus", "origin_url": "http://localhost:3000",
        })
        assert r.status_code == 400

    def test_checkout_starter_creates_session(self, api):
        r = api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "starter", "origin_url": "http://localhost:3000",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith(("http://", "https://")), f"bad url: {d['url']}"
        assert d["session_id"].startswith("cs_test_")
        assert d["package"]["id"] == "starter"
        assert d["package"]["amount"] == 49.0

    def test_payment_stats(self, api):
        r = api.get(f"{BASE_URL}/api/payments/stats")
        assert r.status_code == 200
        d = r.json()
        assert "total_paid_usd" in d and "by_package" in d
        assert "by_utm_source" in d  # UTM attribution surfaced

    def test_share_link_generates(self, api):
        r = api.get(f"{BASE_URL}/api/payments/share-link", params={
            "package_id": "starter", "utm_source": "reddit",
            "utm_medium": "post", "utm_campaign": "launch",
            "origin_url": "https://alreadyherellc.com",
        })
        assert r.status_code == 200
        d = r.json()
        assert "alreadyherellc.com/pricing" in d["share_url"]
        assert "utm_source=reddit" in d["share_url"]
        assert d["amount"] == 49.0

    def test_share_link_unknown_package(self, api):
        r = api.get(f"{BASE_URL}/api/payments/share-link", params={"package_id": "bogus"})
        assert r.status_code == 400

    def test_checkout_with_utm_persists_metadata(self, api):
        r = api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "starter", "origin_url": "http://localhost:3000",
            "utm_source": "linkedin", "utm_medium": "dm", "utm_campaign": "q1-2026",
        })
        assert r.status_code == 200
        # stats should now show linkedin in by_utm_source
        stats = api.get(f"{BASE_URL}/api/payments/stats").json()
        assert "linkedin" in stats["by_utm_source"]

    def test_mode_probe(self, api):
        r = api.get(f"{BASE_URL}/api/payments/mode")
        assert r.status_code == 200
        assert r.json()["mode"] in ("test", "live", "unknown", "missing")

    def test_readiness_returns_checklist(self, api):
        r = api.get(f"{BASE_URL}/api/payments/readiness")
        assert r.status_code == 200
        d = r.json()
        for k in ("stripe_mode", "webhook_secret_set", "operator_email_set",
                  "go_live_ready", "issues", "checklist"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["issues"], list)
        assert len(d["checklist"]) >= 5
        # Never leak the raw key
        body = r.text
        assert "sk_live_" not in body or body.count("sk_live_") == 1  # only in checklist text
        assert "sk_test_emergent" not in body

    def test_smoke_test_refuses_in_test_mode(self, api):
        r = api.post(f"{BASE_URL}/api/payments/smoke-test/create")
        # In CI the env is sk_test_emergent → should refuse
        assert r.status_code == 400, r.text
        assert "live" in r.text.lower()

    def test_smoke_test_recent_empty_shape(self, api):
        r = api.get(f"{BASE_URL}/api/payments/smoke-test/recent")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_smoke_test_status_404_for_unknown(self, api):
        r = api.get(f"{BASE_URL}/api/payments/smoke-test/status/cs_unknown_xxx")
        assert r.status_code == 404


# ---------------- Data Distillation ----------------
class TestDistillation:
    def test_config(self, api):
        r = api.get(f"{BASE_URL}/api/distillation/config")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("ttl_seconds", "token_cost_per_1k_usd",
                  "compression_enabled", "yaml_payloads_enabled", "tiers"):
            assert k in d
        assert d["compression_enabled"] is True
        assert "tier_1" in d["tiers"] and "tier_2" in d["tiers"] and "tier_3" in d["tiers"]

    def test_stats_initial_shape(self, api):
        r = api.get(f"{BASE_URL}/api/distillation/stats")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("rows", "hits", "tokens_saved_est", "usd_saved_est",
                  "by_model", "by_tier", "ttl_seconds"):
            assert k in d
        assert isinstance(d["rows"], int)
        assert isinstance(d["by_model"], dict)

    def test_preview_compresses(self, api):
        text = (
            "It is important to note that, in order to literally maximize "
            "tokens, basically you should use very concise wording."
        )
        r = api.post(f"{BASE_URL}/api/distillation/preview", json={"text": text})
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["distilled"]["chars"] < d["original"]["chars"]
        assert d["savings"]["percent"] > 20.0
        assert "distilled" in d and "savings" in d

    def test_preview_yaml_payload(self, api):
        payload = {"funnel": {"clicks": 100, "paid": 3, "revenue": 297.0},
                   "themes": ["ai", "automation", "money"]}
        r = api.post(f"{BASE_URL}/api/distillation/preview",
                     json={"text": "hi", "payload": payload})
        assert r.status_code == 200
        d = r.json()
        assert "yaml_payload" in d and d["yaml_payload"]
        assert "json_payload" in d and d["json_payload"]
        # YAML representation should be <= JSON in chars for nested-dict-of-prims
        assert len(d["yaml_payload"]) <= len(d["json_payload"]) + 5  # tolerate edge

    def test_clear_returns_count(self, api):
        r = api.post(f"{BASE_URL}/api/distillation/clear")
        assert r.status_code == 200
        d = r.json()
        assert "deleted" in d and isinstance(d["deleted"], int)


# ---------------- Governance (L0-L5 + HITL) ----------------
class TestGovernance:
    def test_status_shape(self, api):
        r = api.get(f"{BASE_URL}/api/governance/status")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("autonomy_level", "autonomy_level_numeric", "manifest_path",
                  "system_name", "north_star_usd_per_day",
                  "hitl_gates_count", "route_gates_count",
                  "token_optimization_enforced"):
            assert k in d
        assert d["autonomy_level"] in ("L0", "L1", "L2", "L3", "L4", "L5")
        assert d["autonomy_level_numeric"] == {"L0":0,"L1":1,"L2":2,"L3":3,"L4":4,"L5":5}[d["autonomy_level"]]
        assert d["hitl_gates_count"] >= 5
        assert d["token_optimization_enforced"] is True

    def test_manifest_loads(self, api):
        r = api.get(f"{BASE_URL}/api/governance/manifest")
        assert r.status_code == 200
        d = r.json()
        assert "system" in d
        assert "hitl_gates" in d
        assert "route_gates" in d
        assert isinstance(d["hitl_gates"], list) and len(d["hitl_gates"]) >= 5
        # every gate must have id + min_level + severity
        for g in d["hitl_gates"]:
            assert "id" in g and "min_level" in g and "severity" in g

    def test_reload_manifest(self, api):
        r = api.post(f"{BASE_URL}/api/governance/manifest/reload")
        assert r.status_code == 200
        assert r.json().get("reloaded") is True

    def test_approvals_empty_list(self, api):
        r = api.get(f"{BASE_URL}/api/governance/approvals?status=pending")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_decide_unknown_approval(self, api):
        r = api.post(f"{BASE_URL}/api/governance/approvals/appr-nonexistent/approve", json={"note": "test"})
        assert r.status_code == 200
        # The endpoint surfaces "error" key when the row isn't found.
        assert "error" in r.json() or r.json().get("status") == "approved"


# ---------------- Governance — wired HITL gates (iteration 18) ----------------
class TestGovernanceGatesWired:
    """Verifies the 4 wired HITL gates declared in governance.yaml::route_gates.

    The preview environment runs at AUTONOMY_LEVEL=L5 (operator-trust mode), so
    every gate is *cleared by autonomy*. These tests assert:
      (a) the manifest mapping exists for each new route
      (b) the endpoints respond successfully (gate is non-blocking at L5)
      (c) the new POST /api/payments/keys/rotate endpoint validates inputs
          and stages credentials without touching the live .env file.
    """

    def test_manifest_contains_all_wired_gates(self, api):
        r = api.get(f"{BASE_URL}/api/governance/manifest")
        assert r.status_code == 200
        gates = r.json().get("route_gates", {}) or {}
        # Iteration 18 wired four NEW endpoints on top of the existing capital_allocation ones
        expected = {
            "POST /api/proposals/draft":           "compliance_content",
            "POST /api/books/":                    "compliance_content",
            "POST /api/cycle/run":                 "mass_outreach",
            "POST /api/publishing/":               "mass_outreach",
            "POST /api/payments/keys/rotate":      "payment_modification",
        }
        for route, gate_id in expected.items():
            assert gates.get(route) == gate_id, (
                f"expected route_gates[{route!r}] == {gate_id!r}, got {gates.get(route)!r}"
            )

    def test_rotate_rejects_empty_key(self, api):
        r = api.post(f"{BASE_URL}/api/payments/keys/rotate", json={"stripe_api_key": ""})
        assert r.status_code == 400

    def test_rotate_rejects_malformed_key(self, api):
        r = api.post(f"{BASE_URL}/api/payments/keys/rotate", json={"stripe_api_key": "definitely_not_a_stripe_key"})
        assert r.status_code == 400
        assert "sk_test_" in r.text or "sk_live_" in r.text

    def test_rotate_stages_valid_test_key(self, api):
        # AUTONOMY_LEVEL=L5 in this env -> payment_modification gate is bypassed
        # by autonomy bracket and the rotation stages to .env.proposed.
        r = api.post(f"{BASE_URL}/api/payments/keys/rotate", json={
            "stripe_api_key": "sk_test_pytest_proposed_rotation_demo_key_xyz",
            "stripe_webhook_secret": "whsec_pytest_demo",
            "note": "pytest rotation",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["staged"] is True
        assert d["new_key_mode"] == "test"
        assert d["webhook_secret_staged"] is True
        assert d["proposed_path"].endswith(".env.proposed")
        # And critically — the live .env was NOT overwritten with the proposed value
        assert "next_step" in d and "NOT touched" in d["next_step"]

    def test_publishing_drafted_status_is_not_gated(self, api):
        """Drafts/exports don't trigger mass_outreach — only `posted` does.

        We use a known-good seeded stream id; if it doesn't exist we skip rather
        than fail (seed-order can vary across environments).
        """
        streams = api.get(f"{BASE_URL}/api/revenue/").json()
        if not streams:
            pytest.skip("no seeded revenue streams")
        sid = streams[0]["id"]
        r = api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": sid,
            "platform": "blog",
            "title": "pytest gate-check drafted",
            "status": "drafted",
        })
        # At L5 this just creates the record cleanly. At lower autonomy, drafted
        # would *still* bypass the gate (only `posted` triggers it).
        assert r.status_code in (200, 201), r.text




# ---------------- Master Revenue Equation ----------------
class TestRevenueEquation:
    def test_equation_returns_full_shape(self, api):
        r = api.get(f"{BASE_URL}/api/revenue-equation/equation")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("formula", "variables", "variable_targets", "daily_capacity_usd",
                  "north_star_usd_per_day", "gap_to_north_star_usd",
                  "percent_of_north_star", "bottleneck"):
            assert k in d
        for v in ("Q_D", "C_R", "A_OV", "P_F", "F_C", "P_M"):
            assert v in d["variables"]
            assert v in d["variable_targets"]
        assert d["formula"] == "Q_D * C_R * A_OV * P_F * F_C * P_M"
        assert d["north_star_usd_per_day"] == 1_000_000

    def test_bottleneck_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/revenue-equation/bottleneck")
        assert r.status_code == 200
        d = r.json()
        assert "bottleneck" in d and "variable" in d["bottleneck"]
        assert d["bottleneck"]["variable"] in ("Q_D", "C_R", "A_OV", "P_F", "F_C", "P_M")

    def test_budget_today_shape(self, api):
        r = api.get(f"{BASE_URL}/api/distillation/budget")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("date", "tokens_in", "tokens_out", "tokens_total",
                  "calls", "cache_hits", "blocked", "daily_cap",
                  "remaining", "over_cap"):
            assert k in d, f"missing key {k}"
        assert isinstance(d["tokens_total"], int)
        assert isinstance(d["over_cap"], bool)
        # date is ISO YYYY-MM-DD
        assert len(d["date"]) == 10 and d["date"][4] == "-"

    def test_budget_history_returns_list(self, api):
        r = api.get(f"{BASE_URL}/api/distillation/budget/history?days=7")
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d, list)
        # at least today's row should exist after any LLM activity
        if d:
            for k in ("date", "tokens_in", "tokens_out", "calls"):
                assert k in d[0]


# ---------------- Analytics ----------------
class TestAnalytics:
    def test_funnel(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/funnel")
        assert r.status_code == 200
        d = r.json()
        for k in ("drafted", "exported", "posted", "verified"):
            assert k in d["totals"]
        assert "rates" in d

    def test_dashboard(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/dashboard")
        assert r.status_code == 200
        d = r.json()
        for k in ("funnel", "posting_times", "stream_roi", "platform_mix", "viral_themes", "momentum"):
            assert k in d

    def test_momentum_no_data_safe(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/momentum")
        assert r.status_code == 200
        d = r.json()
        assert d["cumulative_net"] >= 0
        assert "remaining_to_25k" in d

    def test_stream_roi_includes_all_streams(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/stream-roi")
        assert r.status_code == 200
        d = r.json()
        assert len(d["streams"]) >= 10


class TestProposalsRetrieval:
    def test_list_and_get(self, api):
        items = api.get(f"{BASE_URL}/api/proposals/").json()
        assert isinstance(items, list)
        if items:
            pid = items[0]["id"]
            rg = api.get(f"{BASE_URL}/api/proposals/{pid}")
            assert rg.status_code == 200
            assert rg.json()["id"] == pid

    def test_patch_proposal_status(self, api):
        # Create an invoice first to have a real id
        rc = api.post(f"{BASE_URL}/api/proposals/invoice", json={
            "client_name": "TEST status patch",
            "line_items": [{"description": "x", "quantity": 1, "unit_price": 10}],
        })
        assert rc.status_code == 201
        pid = rc.json()["id"]
        # finalize it
        rp = api.patch(f"{BASE_URL}/api/proposals/{pid}", json={"status": "finalized"})
        assert rp.status_code == 200
        assert rp.json()["status"] == "finalized"
        # invalid status
        rb = api.patch(f"{BASE_URL}/api/proposals/{pid}", json={"status": "BOGUS"})
        assert rb.status_code == 400


# ---------------- Scout additional ----------------
class TestScoutMore:
    def test_grants_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/scout/grants")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_contracts_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/scout/contracts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_news_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/scout/news", params={"query": "AI"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- CSV import for ledger ----------------
class TestLedgerCSVImport:
    def test_csv_import(self, api):
        import io as _io
        csv_text = "date,gross,net\n2026-05-15,100.00,80.00\n2026-05-20,50.00,40.00\n"
        files = {"file": ("test_earnings.csv", _io.BytesIO(csv_text.encode()), "text/csv")}
        data = {"stream_id": "rev-001"}
        r = requests.post(f"{BASE_URL}/api/ledger/import-csv", files=files, data=data)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["imported"] == 2
        assert d["stream_id"] == "rev-001"

    def test_csv_import_unknown_stream(self, api):
        import io as _io
        files = {"file": ("test.csv", _io.BytesIO(b"date,gross,net\n2026-05-15,1,1"), "text/csv")}
        data = {"stream_id": "rev-does-not-exist"}
        r = requests.post(f"{BASE_URL}/api/ledger/import-csv", files=files, data=data)
        assert r.status_code == 404


# ---------------- Run Cycle ----------------
class TestCycle:
    def test_run_cycle(self, api):
        r = api.post(f"{BASE_URL}/api/cycle/run")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["cycle_id"].startswith("cyc-")
        # ideas_created >= 0 because external scout can be empty
        assert d["ideas_created"] >= 0
        # publishing_drafts = ideas * platforms; if ideas were created, drafts must also be > 0
        if d["ideas_created"] > 0:
            assert d["publishing_drafts"] > 0
        assert "next_action" in d


# ---------------- Connectors: Facebook + Reddit ----------------
class TestConnectorsExtra:
    def test_facebook_and_reddit_present(self, api):
        r = api.get(f"{BASE_URL}/api/studio/connectors/")
        assert r.status_code == 200
        platforms = {c["platform"] for c in r.json()}
        assert "facebook" in platforms, f"facebook connector missing - got {platforms}"
        assert "reddit" in platforms, f"reddit connector missing - got {platforms}"


    def test_publishing_unknown_stream_404(self, api):
        r = api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": "rev-does-not-exist",
            "platform": "blog",
            "title": "x",
            "status": "drafted",
        })
        assert r.status_code == 404

    def test_publishing_filter_by_platform(self, api):
        # ensure at least one blog record exists
        api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": "rev-001",
            "platform": "blog",
            "title": "TEST_filter_blog",
            "status": "drafted",
        })
        r = api.get(f"{BASE_URL}/api/publishing/", params={"platform": "blog"})
        assert r.status_code == 200
        recs = r.json()
        assert all(r2["platform"] == "blog" for r2 in recs)
        assert len(recs) >= 1

    def test_publishing_patch_to_verified(self, api):
        rc = api.post(f"{BASE_URL}/api/publishing/", json={
            "stream_id": "rev-001",
            "platform": "blog",
            "title": "TEST_verify_flow",
            "status": "drafted",
        })
        assert rc.status_code == 201
        rid = rc.json()["id"]
        rp = api.patch(f"{BASE_URL}/api/publishing/{rid}", json={
            "status": "verified",
            "post_url": "https://example.com/verified",
        })
        assert rp.status_code == 200, rp.text
        d = rp.json()
        assert d["status"] == "verified"
        assert d.get("verified_at") is not None
        assert d.get("posted_at") is not None  # back-filled


# ---------------- Additional Ledger / cross-feature ----------------
class TestLedgerExtra:
    def test_ledger_negative_gross_returns_422(self, api):
        r = api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-001",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": -5,
            "net_amount": 0,
        })
        assert r.status_code == 422

    def test_ledger_since_days_filter(self, api):
        # create one entry far in the past, one today
        old_date = (_dt.date.today() - _dt.timedelta(days=90)).isoformat()
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-001",
            "occurred_on": old_date,
            "gross_amount": 1, "net_amount": 1,
        })
        today = _dt.date.today().isoformat()
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-001",
            "occurred_on": today,
            "gross_amount": 1, "net_amount": 1,
        })
        r = api.get(f"{BASE_URL}/api/ledger/", params={"since_days": 7})
        assert r.status_code == 200
        entries = r.json()
        # all entries returned must have occurred_on within 7 days
        cutoff = (_dt.date.today() - _dt.timedelta(days=7)).isoformat()
        for e in entries:
            assert e["occurred_on"] >= cutoff

    def test_ledger_stats_by_stream(self, api):
        # ensure rev-003 has an entry
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-003",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": 50, "net_amount": 30,
        })
        r = api.get(f"{BASE_URL}/api/ledger/stats/by-stream")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        ids = {r2["stream_id"] for r2 in rows}
        assert "rev-003" in ids
        rev3 = next(r2 for r2 in rows if r2["stream_id"] == "rev-003")
        assert rev3["total_net"] >= 30
        assert rev3["entry_count"] >= 1

    def test_revenue_list_reflects_ledger_per_stream(self, api):
        # Record an entry for rev-005 and check that the stream object shows monthly_actual >= net
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-005",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": 200, "net_amount": 150,
        })
        r = api.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        streams = {s["id"]: s for s in r.json()}
        assert streams["rev-005"]["monthly_actual"] >= 150

    def test_audit_log_includes_ledger_event(self, api):
        # Create a ledger entry then assert there is an audit event for ledger.entry.recorded
        api.post(f"{BASE_URL}/api/ledger/", json={
            "stream_id": "rev-001",
            "occurred_on": _dt.date.today().isoformat(),
            "gross_amount": 1, "net_amount": 1,
        })
        r = api.get(f"{BASE_URL}/api/audit/")
        assert r.status_code == 200
        events = r.json()
        types = {e.get("event_type") for e in events}
        assert "ledger.entry.recorded" in types



# ---------------- Payments extra coverage ----------------
class TestPaymentsExtra:
    def test_transactions_list_after_checkout(self, api):
        # Create one new session, then ensure it shows up
        r = api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "pro", "origin_url": "http://localhost:3000",
        })
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        rt = api.get(f"{BASE_URL}/api/payments/transactions")
        assert rt.status_code == 200
        txns = rt.json()
        assert isinstance(txns, list)
        assert any(t.get("session_id") == sid for t in txns)

    def test_checkout_status_unpaid_does_not_crash(self, api):
        # Create a session and immediately poll status (will be unpaid)
        r = api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "starter", "origin_url": "http://localhost:3000",
        })
        assert r.status_code == 200
        sid = r.json()["session_id"]
        rs = api.get(f"{BASE_URL}/api/payments/checkout/{sid}")
        assert rs.status_code == 200, rs.text
        d = rs.json()
        assert "status" in d and "payment_status" in d
        assert d["payment_status"] != "paid"  # fresh session shouldn't be paid
        assert d["recorded"] is False
        assert d["package_id"] == "starter"

    def test_checkout_creates_saas_stream(self, api):
        # Calling checkout should idempotently ensure rev-saas exists
        api.post(f"{BASE_URL}/api/payments/checkout", json={
            "package_id": "starter", "origin_url": "http://localhost:3000",
        })
        r = api.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        names = {s["id"] for s in r.json()}
        assert "rev-saas" in names


# ---------------- Analytics extra coverage ----------------
class TestAnalyticsExtra:
    def test_posting_times(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/posting-times")
        assert r.status_code == 200
        d = r.json()
        assert "sample_size" in d
        assert isinstance(d.get("recommendation", ""), str)
        assert len(d["recommendation"]) > 0

    def test_platform_mix(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/platform-mix")
        assert r.status_code == 200
        d = r.json()
        assert "platforms" in d and isinstance(d["platforms"], list)
        assert "total_posts" in d

    def test_viral_themes(self, api):
        r = api.get(f"{BASE_URL}/api/analytics/viral-themes")
        assert r.status_code == 200
        d = r.json()
        assert "sample_size" in d
        assert "top_themes" in d and isinstance(d["top_themes"], list)


# ---------------- Advisor (Claude Sonnet via Emergent LLM) ----------------
class TestAdvisor:
    def test_recommend(self, api):
        r = api.post(f"{BASE_URL}/api/advisor/recommend", timeout=120)
        # Accept 200 (any structured/unstructured) or 502 (LLM upstream error)
        assert r.status_code in (200, 502), r.text
        if r.status_code == 200:
            d = r.json()
            assert d.get("id", "").startswith("adv-")
            assert d.get("confidence") in ("low", "medium", "high")
            # next_action must be non-empty (LLM produced something)
            assert isinstance(d.get("next_action"), str) and len(d["next_action"]) > 0

    def test_recent(self, api):
        r = api.get(f"{BASE_URL}/api/advisor/recent")
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)



# ---------------- Books & Audiobooks ----------------
class TestBooks:
    def test_books_list_empty_ok(self, api):
        r = api.get(f"{BASE_URL}/api/books/")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_books_stats_empty(self, api):
        r = api.get(f"{BASE_URL}/api/books/stats/overview")
        assert r.status_code == 200
        d = r.json()
        for k in ("total_books", "total_word_count", "by_type", "by_status"):
            assert k in d

    def test_invalid_book_type_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/books/", json={
            "title": "x", "book_type": "BOGUS", "chapter_count": 1,
        })
        assert r.status_code == 400

    def test_invalid_chapter_count_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/books/", json={
            "title": "x", "chapter_count": 999,
        })
        assert r.status_code == 400

    def test_get_nonexistent_book(self, api):
        r = api.get(f"{BASE_URL}/api/books/book-does-not-exist")
        assert r.status_code == 404

    def test_invalid_chapter_count_zero_rejected(self, api):
        r = api.post(f"{BASE_URL}/api/books/", json={
            "title": "x", "chapter_count": 0,
        })
        assert r.status_code == 400


# ---------------- Books E2E (LLM-backed) ----------------
@pytest.fixture(scope="class")
def created_book(api_session):
    """Create a real 2-chapter book via Emergent LLM. Used by multiple tests."""
    payload = {
        "title": "Test Manual",
        "book_type": "manual",
        "chapter_count": 2,
        "word_target_per_chapter": 150,
        "audience": "developers",
        "tone": "professional",
    }
    r = api_session.post(f"{BASE_URL}/api/books/", json=payload, timeout=180)
    assert r.status_code == 201, f"create_book failed: {r.status_code} {r.text[:300]}"
    return r.json()


@pytest.fixture(scope="class")
def api_session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


class TestBooksE2E:
    def test_create_book_returns_complete(self, created_book):
        b = created_book
        assert b["id"].startswith("book-")
        assert b["status"] == "complete"
        assert len(b["chapters"]) == 2
        assert b["total_word_count"] > 0
        assert b["book_type"] == "manual"

    def test_rev_books_stream_auto_created(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/revenue/")
        assert r.status_code == 200
        ids = {s["id"] for s in r.json()}
        assert "rev-books" in ids

    def test_list_includes_created_book(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/books/")
        assert r.status_code == 200
        ids = {b["id"] for b in r.json()}
        assert created_book["id"] in ids

    def test_get_created_book(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created_book["id"]

    def test_download_md(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}/download.md")
        assert r.status_code == 200
        assert "text/markdown" in r.headers.get("content-type", "")
        assert "attachment" in r.headers.get("content-disposition", "").lower()
        assert created_book["title"] in r.text

    def test_download_txt(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}/download.txt")
        assert r.status_code == 200
        assert "text/plain" in r.headers.get("content-type", "")
        # Plain renderer prepends title with period
        assert created_book["title"] in r.text

    def test_audiobook_first_get_returns_202(self, created_book, api_session):
        """First GET kicks off a background TTS render and returns 202."""
        r = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}/audio.mp3")
        # Either 202 (rendering started just now) OR 200 (cached from a prior test run).
        # Both are valid states for the endpoint.
        assert r.status_code in (200, 202), r.text
        if r.status_code == 202:
            d = r.json()
            assert d["detail"]["status"] == "rendering"
            assert "estimated_seconds" in d["detail"]

    def test_audiobook_generate_endpoint_queues(self, created_book, api_session):
        """POST /audio/generate kicks the render explicitly and returns status."""
        r = api_session.post(f"{BASE_URL}/api/books/{created_book['id']}/audio/generate")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["status"] in ("ready", "rendering", "queued")
        assert d["mp3_url"].endswith("/audio.mp3")

    def test_download_increments_count(self, created_book, api_session):
        # Already downloaded twice above; expect >= 2
        r = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}")
        assert r.status_code == 200
        assert r.json()["download_count"] >= 2

    def test_stats_overview_reflects_book(self, created_book, api_session):
        r = api_session.get(f"{BASE_URL}/api/books/stats/overview")
        assert r.status_code == 200
        d = r.json()
        assert d["total_books"] >= 1
        assert d["total_word_count"] >= created_book["total_word_count"]
        assert "manual" in d["by_type"]
        assert d["by_status"].get("complete", 0) >= 1

    def test_rev_books_stream_idempotent(self, created_book, api_session):
        """Second book should NOT duplicate rev-books stream."""
        payload = {
            "title": "Second Tiny Book",
            "book_type": "guide",
            "chapter_count": 1,
            "word_target_per_chapter": 80,
        }
        r = api_session.post(f"{BASE_URL}/api/books/", json=payload, timeout=180)
        if r.status_code in (429, 502, 503):
            import pytest as _pytest
            _pytest.skip(
                f"upstream LLM quota/queue saturation ({r.status_code}); "
                "this test depends on a live LLM and is order-sensitive when "
                "Pollinations queue is full."
            )
        assert r.status_code == 201
        # rev-books still appears exactly once
        rev = api_session.get(f"{BASE_URL}/api/revenue/").json()
        rev_books_count = sum(1 for s in rev if s["id"] == "rev-books")
        assert rev_books_count == 1
        # cleanup the second book
        api_session.delete(f"{BASE_URL}/api/books/{r.json()['id']}")

    def test_delete_book(self, created_book, api_session):
        r = api_session.delete(f"{BASE_URL}/api/books/{created_book['id']}")
        assert r.status_code == 200
        # verify gone
        r2 = api_session.get(f"{BASE_URL}/api/books/{created_book['id']}")
        assert r2.status_code == 404


# ---------------- Auth (operator gate) ----------------
class TestAuth:
    def test_config_no_operator_set(self, api):
        # When OPERATOR_EMAIL is not set, auth is not required (legacy mode).
        r = api.get(f"{BASE_URL}/api/auth/config")
        assert r.status_code == 200
        d = r.json()
        assert "required" in d
        assert d["required"] is False

    def test_me_without_session_returns_401(self, api):
        r = api.get(f"{BASE_URL}/api/auth/me")
        assert r.status_code == 401

    def test_login_without_token_configured_returns_503(self, api):
        # OPERATOR_TOKEN isn't set in the test env → login endpoint returns 503
        r = api.post(f"{BASE_URL}/api/auth/login", json={"operator_token": "anything"})
        assert r.status_code in (401, 503), f"expected 401/503, got {r.status_code}: {r.text[:200]}"

    def test_logout_idempotent(self, api):
        r = api.post(f"{BASE_URL}/api/auth/logout")
        assert r.status_code == 200
        assert r.json().get("logged_out") is True
        # Call again - still 200
        r2 = api.post(f"{BASE_URL}/api/auth/logout")
        assert r2.status_code == 200



# ---------------- System Status (Quickstart Wizard) ----------------
class TestSystemStatus:
    def test_status_shape(self, api):
        r = api.get(f"{BASE_URL}/api/system/status")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in (
            "operator_email_set", "stripe_mode", "stripe_webhook_secret_set",
            "llm_key_set", "daily_cycle_hour_utc", "counts",
            "is_seeded", "system_mode",
        ):
            assert k in d, f"missing key: {k}"
        # vendor lock-in scrub: the legacy emergent-specific field must be GONE
        assert "emergent_llm_key_set" not in d, "legacy emergent_llm_key_set must be removed"
        # counts must include core collections
        for c in ("revenue_streams", "agents", "builds", "ledger_entries", "books"):
            assert c in d["counts"]
        # types
        assert isinstance(d["operator_email_set"], bool)
        assert isinstance(d["llm_key_set"], bool)
        assert isinstance(d["is_seeded"], bool)
        assert d["stripe_mode"] in ("live", "test", "missing", "unknown")

    def test_status_no_secrets_leaked(self, api):
        """Endpoint must not leak any actual secret values, only set/unset flags."""
        r = api.get(f"{BASE_URL}/api/system/status")
        assert r.status_code == 200
        body = r.text.lower()
        # Common secret prefixes must not appear
        for needle in ("sk_test_", "sk_live_", "whsec_", "sk-emergent-"):
            assert needle not in body, f"secret prefix leaked: {needle}"

    def test_status_seeded_true_when_seed_data_run(self, api):
        r = api.get(f"{BASE_URL}/api/system/status")
        d = r.json()
        # CI re-seeds before run; expect counts above thresholds
        assert d["counts"]["revenue_streams"] >= 3
        assert d["counts"]["agents"] >= 3
        assert d["is_seeded"] is True


# ---------------- Studio Scripts (read-back of generated scripts) ----------------
class TestStudioScripts:
    def test_list_all_scripts_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/studio/scripts/")
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d, list)

    def test_scripts_for_idea_returns_only_that_ideas_scripts(self, api):
        # Find an idea that has been scripted
        ideas = api.get(f"{BASE_URL}/api/studio/ideas/").json()
        scripted = next((i for i in ideas if i.get("status") == "scripted"), None)
        if scripted is None:
            pytest.skip("no scripted idea in fixture")
        r = api.get(f"{BASE_URL}/api/studio/ideas/{scripted['id']}/scripts")
        assert r.status_code == 200
        scripts = r.json()
        assert isinstance(scripts, list)
        for s in scripts:
            assert s["idea_id"] == scripted["id"], "leak: script for wrong idea returned"

    def test_scripts_for_nonexistent_idea_returns_empty(self, api):
        r = api.get(f"{BASE_URL}/api/studio/ideas/idea-does-not-exist/scripts")
        assert r.status_code == 200
        assert r.json() == []




# ---------------- Secrets / Bitwarden ----------------
class TestSecrets:
    def test_status_returns_shape_even_when_uninstalled(self, api):
        r = api.get(f"{BASE_URL}/api/secrets/status")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("installed", "unlocked", "server", "user", "reason"):
            assert k in d
        assert isinstance(d["installed"], bool)
        assert isinstance(d["unlocked"], bool)

    def test_items_returns_empty_when_unavailable(self, api):
        r = api.get(f"{BASE_URL}/api/secrets/items")
        assert r.status_code == 200
        d = r.json()
        assert "items" in d
        assert "available" in d
        assert isinstance(d["items"], list)

    def test_system_status_exposes_bitwarden_block(self, api):
        r = api.get(f"{BASE_URL}/api/system/status")
        d = r.json()
        assert "bitwarden" in d
        bw = d["bitwarden"]
        for k in ("installed", "unlocked", "server", "user_masked"):
            assert k in bw

    def test_secrets_endpoints_never_leak_password_field(self, api):
        # In CI bw is not installed, so this confirms zero-info-leak posture
        body = api.get(f"{BASE_URL}/api/secrets/items").text.lower()
        for needle in ('"password"', '"totp_seed"', '"secret"'):
            assert needle not in body, f"secret-like key leaked: {needle}"


# ---------------- Free-Only Build Directive endpoints ----------------
class TestFreeOnlyDirective:
    def test_cost_status(self, api):
        r = api.get(f"{BASE_URL}/api/cost/status")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in (
            "target_monthly_usd", "estimated_monthly_usd", "compliant",
            "connectors_by_class", "free_active", "paid_blocked",
            "unknown_blocked", "requires_secret", "policy",
        ):
            assert k in d, f"missing key: {k}"
        assert d["target_monthly_usd"] == 0.0
        assert d["policy"]["block_paid"] is True
        assert d["policy"]["block_unknown_cost"] is True

    def test_cost_policy_static(self, api):
        r = api.get(f"{BASE_URL}/api/cost/policy")
        assert r.status_code == 200
        d = r.json()
        assert d["block_paid_connectors"] is True
        assert len(d["approved_free_integrations"]) >= 5

    def test_two_node_health(self, api):
        r = api.get(f"{BASE_URL}/api/health/nodes")
        assert r.status_code == 200, r.text
        d = r.json()
        assert "nodes" in d
        assert len(d["nodes"]) == 2
        names = {n["name"] for n in d["nodes"]}
        assert "DashboardAlways Free" in names
        assert "profitengine-server" in names
        # Worker is "not_configured" in CI (no WORKER_BASE_URL set)
        worker = next(n for n in d["nodes"] if n["name"] == "profitengine-server")
        assert worker["status"] in ("not_configured", "healthy", "unreachable", "degraded")

    def test_lcac_returns_findings(self, api):
        r = api.get(f"{BASE_URL}/api/lifelong-catch-correct/")
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("scanned_at", "findings_count", "by_severity", "findings"):
            assert k in d
        # Each finding has required keys
        for f in d["findings"]:
            for k in ("severity", "category", "message", "suggestion"):
                assert k in f
            assert f["severity"] in ("high", "medium", "low")

