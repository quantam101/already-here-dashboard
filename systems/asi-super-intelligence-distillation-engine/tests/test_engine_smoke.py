from pathlib import Path
import importlib.util
import tempfile

module_path = Path(__file__).resolve().parents[1] / "asi_master_engine.py"
spec = importlib.util.spec_from_file_location("asi_master_engine", module_path)
assert spec is not None
assert spec.loader is not None
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)


def test_asi_engine_scores_500_anchor():
    decision = engine.score({
        "source": "direct_vendor",
        "company": "Phoenix MSP",
        "title": "Emergency Server Smart Hands",
        "location": "Phoenix, AZ",
        "service_type": "server_smart_hands",
        "fixed_pay": 500,
        "estimated_travel_minutes": 20,
        "estimated_onsite_minutes": 120,
        "retainer_potential": True,
    })
    assert decision.grade == "A"
    assert decision.expected_revenue == 500
    assert decision.target_rate >= 500


def test_asi_engine_rejects_low_pay_travel():
    decision = engine.score({
        "source": "workmarket",
        "company": "Distant Buyer",
        "title": "LTE Test",
        "location": "Flagstaff, AZ",
        "service_type": "network_support",
        "listed_rate": 65,
        "max_hours": 2,
        "estimated_travel_minutes": 240,
        "estimated_onsite_minutes": 90,
    })
    assert decision.grade == "AVOID"
    assert "travel_burden" in decision.risk_flags
    assert decision.target_rate >= 450


def test_asi_engine_persists_approval_gated_action():
    with tempfile.NamedTemporaryFile(suffix=".db") as tmp:
        result = engine.run_cycle(tmp.name, engine.demo_tasks())
        assert result["processed"] == 3
        assert len(result["summary"]["pending_actions"]) >= 3
        for item in result["summary"]["pending_actions"]:
            assert item["approval_required"] == 1
