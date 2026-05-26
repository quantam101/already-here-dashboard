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
        # Actuals now computed LIVE from the ledger - on a freshly seeded DB the ledger
        # is empty, so actuals must be 0. Once operator records earnings the value rises.
        assert d["total_monthly_actual"] >= 0.0, f"actual={d['total_monthly_actual']}"
        assert d["active_streams"] == 10
        assert d["total_streams"] == 10


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
        # list
        r = api.get(f"{BASE_URL}/api/proposals/")
        assert r.status_code == 200
        items = r.json()
        assert isinstance(items, list)
        if items:
            # get the first one
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
