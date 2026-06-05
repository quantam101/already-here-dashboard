from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class ResilientRuntimeClientError(RuntimeError):
    pass


class ResilientRuntimeClient:
    """Thin HTTP adapter for repos that should not embed the runtime engine."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 15.0) -> None:
        self.base_url = (base_url or os.environ.get("RESILIENT_RUNTIME_URL") or "http://127.0.0.1:8000").rstrip("/")
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
            {
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
            {
                "work_order": work_order,
                "technicians": technicians,
                "min_skill_ratio": min_skill_ratio,
            },
        )

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise ResilientRuntimeClientError(f"runtime HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise ResilientRuntimeClientError(f"runtime unavailable: {exc}") from exc
