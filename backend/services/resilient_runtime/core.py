from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from pathlib import Path
from statistics import mean
from typing import Any

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_ .-]{0,63}$")
_RANGE_PATTERN = re.compile(
    r"(?P<column>[A-Za-z_][A-Za-z0-9_ .-]{0,63}).*?range\s+"
    r"(?P<min>-?\d+(?:\.\d+)?)\s+to\s+(?P<max>-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

ALLOWED_OPERATIONS = {
    "describe", "count_rows", "validate_not_null", "validate_range", "validate_type",
    "filter_equals", "group_sum", "sort", "limit",
}
COLUMN_OPERATIONS = {"validate_not_null", "validate_range", "validate_type", "filter_equals", "sort"}
PARAMETER_ALLOWLIST = {
    "describe": set(),
    "count_rows": set(),
    "validate_not_null": set(),
    "validate_range": {"min", "max"},
    "validate_type": {"type"},
    "filter_equals": {"value"},
    "group_sum": {"group_by", "sum_column"},
    "sort": {"descending"},
    "limit": {"n"},
}


class RuntimePolicyError(ValueError):
    pass


class RuntimeStore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        configured = db_path or os.environ.get("RUNTIME_SQLITE_PATH")
        if configured is None:
            configured = Path(__file__).resolve().parents[2] / "data" / "resilient_runtime.db"
        self.db_path = Path(configured)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runtime_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS ux_runtime_event_key
                ON runtime_events(idempotency_key, event_type)
                """
            )

    def record(self, session_id: str, idempotency_key: str, event_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO runtime_events
                (created_at, session_id, idempotency_key, event_type, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (time.time(), session_id, idempotency_key, event_type, json.dumps(payload, default=str)),
            )

    def get(self, idempotency_key: str, event_type: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM runtime_events WHERE idempotency_key = ? AND event_type = ? ORDER BY id DESC LIMIT 1",
                (idempotency_key, event_type),
            ).fetchone()
        return None if row is None else json.loads(str(row["payload_json"]))

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 250))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT created_at, session_id, idempotency_key, event_type, payload_json FROM runtime_events ORDER BY id DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        return [
            {
                "created_at": row["created_at"],
                "session_id": row["session_id"],
                "idempotency_key": row["idempotency_key"],
                "event_type": row["event_type"],
                "payload": json.loads(str(row["payload_json"])),
            }
            for row in rows
        ]


class ResilientRuntime:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.store = RuntimeStore(db_path)

    def execute(
        self,
        query: str,
        records: list[dict[str, Any]],
        schema_context: dict[str, str] | None = None,
        session_id: str = "dashboard",
    ) -> dict[str, Any]:
        if not isinstance(query, str) or not query.strip():
            return rejected("query must be a non-empty string")
        if not isinstance(records, list) or not records:
            return rejected("records must contain at least one row")
        normalized_records = tuple(dict(row) for row in records)
        key = stable_key(query, normalized_records, schema_context or {}, session_id)
        cached = self.store.get(key, "result")
        if cached is not None:
            return cached
        try:
            columns = {k for row in normalized_records for k in row}
            plan = make_plan(query, columns)
            validate_plan(plan, columns)
            telemetry = run_plan(plan, list(normalized_records))
            result = {
                "status": "success",
                "mode": "local_deterministic",
                "plan_id": plan["plan_id"],
                "rationale": plan["analytical_rationale"],
                "telemetry": telemetry,
                "errors": [],
            }
            self.store.record(session_id, key, "plan", plan)
        except RuntimePolicyError as exc:
            result = rejected(str(exc))
        self.store.record(session_id, key, "result", result)
        return result

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.store.recent(limit)


def make_plan(query: str, columns: set[str]) -> dict[str, Any]:
    query = query.strip()
    try:
        payload = json.loads(query)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        return normalize_plan(payload)
    if payload is not None:
        raise RuntimePolicyError("JSON plan must be an object")
    lower = query.lower()
    operations: list[dict[str, Any]] = []
    for column in sorted(columns):
        c = column.lower()
        if f"{c} not null" in lower or f"not null {c}" in lower:
            operations.append({"op": "validate_not_null", "column": column, "parameters": {}})
    match = _RANGE_PATTERN.search(query)
    if match:
        column = match_column(match.group("column"), columns)
        if column:
            operations.append({"op": "validate_range", "column": column, "parameters": {"min": float(match.group("min")), "max": float(match.group("max"))}})
    if "count" in lower:
        operations.append({"op": "count_rows", "column": None, "parameters": {}})
    if "describe" in lower or "summary" in lower or not operations:
        operations.append({"op": "describe", "column": None, "parameters": {}})
    return {
        "plan_id": "plan-" + hashlib.sha256(query.encode("utf-8")).hexdigest()[:16],
        "analytical_rationale": "Deterministic local plan generated without external inference.",
        "required_packages": [],
        "operations": operations,
    }


def normalize_plan(payload: dict[str, Any]) -> dict[str, Any]:
    operations = payload.get("operations", [])
    if not isinstance(operations, list):
        raise RuntimePolicyError("operations must be a list")
    return {
        "plan_id": str(payload.get("plan_id") or "adhoc"),
        "analytical_rationale": str(payload.get("analytical_rationale") or "No rationale supplied."),
        "required_packages": list(payload.get("required_packages") or []),
        "operations": operations,
    }


def validate_plan(plan: dict[str, Any], columns: set[str]) -> None:
    operations = plan["operations"]
    if len(operations) > 25:
        raise RuntimePolicyError("too many operations")
    if plan.get("required_packages"):
        raise RuntimePolicyError("external packages are blocked in deterministic mode")
    for operation in operations:
        op = operation.get("op")
        if op not in ALLOWED_OPERATIONS:
            raise RuntimePolicyError(f"unsupported operation: {op}")
        column = operation.get("column")
        params = operation.get("parameters") or {}
        if op in COLUMN_OPERATIONS:
            validate_column(column, columns)
        unknown = set(params) - PARAMETER_ALLOWLIST[op]
        if unknown:
            raise RuntimePolicyError(f"unsupported parameters for {op}: {sorted(unknown)}")
        if op == "validate_range":
            for k in ("min", "max"):
                if k in params and not isinstance(params[k], (int, float)):
                    raise RuntimePolicyError(f"{k} must be numeric")
        if op == "validate_type" and params.get("type") not in {"str", "int", "float", "number", "bool"}:
            raise RuntimePolicyError("validate_type requires type str/int/float/number/bool")
        if op == "limit":
            n = params.get("n")
            if not isinstance(n, int) or n < 1 or n > 50000:
                raise RuntimePolicyError("limit n must be between 1 and 50000")


def validate_column(column: Any, columns: set[str]) -> None:
    if not isinstance(column, str) or not column:
        raise RuntimePolicyError("operation requires a column")
    if not _IDENTIFIER.fullmatch(column):
        raise RuntimePolicyError(f"rejected unsafe column identifier: {column}")
    if column not in columns:
        raise RuntimePolicyError(f"column not present in records: {column}")


def run_plan(plan: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    working = list(records)
    telemetry: dict[str, Any] = {"operations": []}
    for operation in plan["operations"]:
        op = operation["op"]
        result = run_operation(op, operation.get("column"), operation.get("parameters") or {}, working)
        telemetry["operations"].append({"operation": operation, "result": result})
        if op in {"filter_equals", "sort", "limit"}:
            working = result["records"]
    telemetry["final_row_count"] = len(working)
    return telemetry


def run_operation(op: str, column: str | None, params: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    if op == "describe":
        return describe(records)
    if op == "count_rows":
        return {"row_count": len(records)}
    if op == "validate_not_null":
        bad = [i for i, row in enumerate(records) if row.get(column) in (None, "")]
        return {"passed": not bad, "bad_row_indices": bad, "bad_count": len(bad)}
    if op == "validate_range":
        bad: list[int] = []
        conversion: list[int] = []
        min_value = params.get("min", -math.inf)
        max_value = params.get("max", math.inf)
        for i, row in enumerate(records):
            try:
                value = float(row.get(column))
            except (TypeError, ValueError):
                conversion.append(i)
                continue
            if value < float(min_value) or value > float(max_value):
                bad.append(i)
        return {"passed": not bad and not conversion, "bad_row_indices": bad, "conversion_error_indices": conversion, "bad_count": len(bad) + len(conversion)}
    if op == "validate_type":
        bad = [i for i, row in enumerate(records) if not type_matches(row.get(column), params["type"])]
        return {"passed": not bad, "bad_row_indices": bad, "bad_count": len(bad)}
    if op == "filter_equals":
        filtered = [row for row in records if row.get(column) == params.get("value")]
        return {"row_count": len(filtered), "records": filtered}
    if op == "group_sum":
        return group_sum(records, params)
    if op == "sort":
        sorted_records = sorted(records, key=lambda row: str(row.get(column, "")), reverse=bool(params.get("descending", False)))
        return {"row_count": len(sorted_records), "records": sorted_records}
    if op == "limit":
        limited = records[: int(params["n"])]
        return {"row_count": len(limited), "records": limited}
    raise RuntimePolicyError(f"unsupported operation: {op}")


def describe(records: list[dict[str, Any]]) -> dict[str, Any]:
    columns = sorted({key for row in records for key in row})
    profile: dict[str, Any] = {"row_count": len(records), "columns": columns, "numeric": {}}
    for column in columns:
        numeric_values: list[float] = []
        null_count = 0
        for row in records:
            value = row.get(column)
            if value is None or value == "":
                null_count += 1
                continue
            try:
                numeric_values.append(float(value))
            except (TypeError, ValueError):
                continue
        column_profile: dict[str, Any] = {"null_count": null_count}
        if numeric_values:
            column_profile.update({"count": len(numeric_values), "min": min(numeric_values), "max": max(numeric_values), "mean": mean(numeric_values)})
        profile["numeric"][column] = column_profile
    return profile


def group_sum(records: list[dict[str, Any]], params: dict[str, Any]) -> dict[str, Any]:
    group_by = params.get("group_by")
    sum_column = params.get("sum_column")
    if not isinstance(group_by, str) or not isinstance(sum_column, str):
        raise RuntimePolicyError("group_sum requires group_by and sum_column string parameters")
    groups: dict[str, float] = {}
    conversion_errors: list[int] = []
    for i, row in enumerate(records):
        key = str(row.get(group_by, ""))
        try:
            value = float(row.get(sum_column, 0))
        except (TypeError, ValueError):
            conversion_errors.append(i)
            continue
        groups[key] = groups.get(key, 0.0) + value
    return {"groups": groups, "conversion_error_indices": conversion_errors}


def type_matches(value: Any, expected: str) -> bool:
    if expected == "str":
        return isinstance(value, str)
    if expected == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "float":
        return isinstance(value, float)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "bool":
        return isinstance(value, bool)
    return False


def match_column(candidate: str, columns: set[str]) -> str | None:
    candidate_lower = candidate.strip().lower()
    for column in columns:
        if column.lower() == candidate_lower:
            return column
    for column in columns:
        if column.lower() in candidate_lower or candidate_lower in column.lower():
            return column
    return None


def stable_key(query: str, records: tuple[dict[str, Any], ...], schema_context: dict[str, str], session_id: str) -> str:
    payload = {"query": query, "records": records, "schema_context": schema_context, "session_id": session_id}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def rejected(error: str) -> dict[str, Any]:
    return {"status": "rejected", "mode": "rejected", "plan_id": "rejected", "rationale": "Plan rejected by deterministic runtime policy.", "telemetry": {}, "errors": [error]}
