from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from services.resilient_runtime import ResilientRuntime, match_technicians

router = APIRouter()
runtime = ResilientRuntime()


class ExecuteRuntimeRequest(BaseModel):
    query: str = Field(..., min_length=1)
    records: list[dict[str, Any]] = Field(..., min_length=1)
    schema_context: dict[str, str] = Field(default_factory=dict)
    session_id: str = Field(default="dashboard", min_length=1)


class TechnicianMatchRequest(BaseModel):
    work_order: dict[str, Any]
    technicians: list[dict[str, Any]] = Field(..., min_length=1)
    min_skill_ratio: float = Field(default=0.55, ge=0.0, le=1.0)


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "operational",
        "mode": "local_deterministic",
        "runtime": "already_here_resilient_runtime",
        "arbitrary_code_execution": False,
        "cloud_required": False,
    }


@router.post("/execute")
async def execute_runtime(request: ExecuteRuntimeRequest) -> dict[str, Any]:
    return runtime.execute(
        query=request.query,
        records=request.records,
        schema_context=request.schema_context,
        session_id=request.session_id,
    )


@router.get("/events")
async def recent_events(limit: int = Query(default=50, ge=1, le=250)) -> dict[str, Any]:
    return {"events": runtime.recent_events(limit=limit)}


@router.post("/match-technicians")
async def match_technician_pool(request: TechnicianMatchRequest) -> dict[str, Any]:
    return {
        "matches": match_technicians(
            work_order=request.work_order,
            technicians=request.technicians,
            min_skill_ratio=request.min_skill_ratio,
        )
    }
