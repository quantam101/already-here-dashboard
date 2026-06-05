from __future__ import annotations

import os
from typing import Any

import requests


class ResilientRuntimeClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 20.0) -> None:
        self.base_url = (base_url or os.environ.get("ALREADY_HERE_DASHBOARD_URL") or "http://127.0.0.1:8000").rstrip("/")
        self.timeout_seconds = timeout_seconds

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/api/resilient-runtime/health")

    def execute(
        self,
        query: str,
        records: list[dict[str, Any]],
        schema_context: dict[str, str] | None = None,
        session_id: str = "adapter",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/resilient-runtime/execute",
            json={
                "query": query,
                "records": records,
                "schema_context": schema_context or {},
                "session_id": session_id,
            },
        )

    def match_technicians(
        self,
        work_order: dict[str, Any],
        technicians: list[dict[str, Any]],
        min_skill_ratio: float = 0.55,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/resilient-runtime/match-technicians",
            json={
                "work_order": work_order,
                "technicians": technicians,
                "min_skill_ratio": min_skill_ratio,
            },
        )

    def recent_events(self, limit: int = 50) -> dict[str, Any]:
        return self._request("GET", f"/api/resilient-runtime/events?limit={limit}")

    def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        response = requests.request(
            method=method,
            url=f"{self.base_url}{path}",
            json=json,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Resilient runtime returned a non-object response")
        return payload
