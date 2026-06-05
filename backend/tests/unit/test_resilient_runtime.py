from __future__ import annotations

from pathlib import Path

from services.resilient_runtime import ResilientRuntime, match_technicians


def test_runtime_validates_records_offline(tmp_path: Path) -> None:
    runtime = ResilientRuntime(db_path=tmp_path / "runtime.db")
    result = runtime.execute(
        query="validate revenue not null and revenue range 0 to 100000 then describe",
        records=[
            {"customer": "A", "revenue": 1200.0, "state": "AZ"},
            {"customer": "B", "revenue": 3000.0, "state": "AZ"},
        ],
        session_id="unit-test",
    )

    assert result["status"] == "success"
    assert result["mode"] == "local_deterministic"
    assert result["telemetry"]["final_row_count"] == 2
    assert result["telemetry"]["operations"][0]["result"]["passed"] is True
    assert result["telemetry"]["operations"][1]["result"]["passed"] is True


def test_runtime_rejects_unknown_column(tmp_path: Path) -> None:
    runtime = ResilientRuntime(db_path=tmp_path / "runtime.db")
    result = runtime.execute(
        query='{ "plan_id": "bad", "operations": [{"op": "validate_not_null", "column": "missing", "parameters": {}}] }',
        records=[{"revenue": 100}],
        session_id="unit-test",
    )

    assert result["status"] == "rejected"
    assert "column not present" in result["errors"][0].lower()


def test_runtime_idempotent_cache(tmp_path: Path) -> None:
    runtime = ResilientRuntime(db_path=tmp_path / "runtime.db")
    first = runtime.execute(query="count", records=[{"revenue": 1}], session_id="unit-test")
    second = runtime.execute(query="count", records=[{"revenue": 1}], session_id="unit-test")

    assert first == second
    assert first["telemetry"]["operations"][0]["result"]["row_count"] == 1


def test_matcher_prioritizes_eligible_local_1099_technician() -> None:
    work_order = {
        "city": "Phoenix",
        "state": "AZ",
        "pay_rate": 85,
        "minimum_hours": 2,
        "required_skills": ["smart hands", "data center", "network support"],
    }
    technicians = [
        {
            "id": "sf",
            "name": "Stephen Franklin / Already Here LLC",
            "city": "Phoenix",
            "state": "AZ",
            "accepts_1099": True,
            "minimum_effective_rate": 65,
            "minimum_hours": 2,
            "availability": "priority",
            "skills": ["smart hands", "data center", "network support", "printer", "pos"],
        },
        {
            "id": "low-fit",
            "name": "Low Fit Tech",
            "city": "Tucson",
            "state": "AZ",
            "accepts_1099": True,
            "minimum_effective_rate": 95,
            "minimum_hours": 4,
            "skills": ["desktop"],
        },
    ]

    matches = match_technicians(work_order=work_order, technicians=technicians)

    assert matches[0]["technician_id"] == "sf"
    assert matches[0]["eligible"] is True
    assert matches[0]["skill_match_ratio"] == 1.0
    assert matches[1]["eligible"] is False
