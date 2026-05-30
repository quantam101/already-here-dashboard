"""
Governance API — operator-facing controls for L0-L5 + HITL approval queue.

  GET  /api/governance/status              -> current level, manifest summary
  GET  /api/governance/manifest            -> full parsed manifest
  POST /api/governance/manifest/reload     -> re-read governance.yaml from disk
  GET  /api/governance/approvals           -> list pending/approved/rejected
  POST /api/governance/approvals/{id}/approve   {note?: str}
  POST /api/governance/approvals/{id}/reject    {note?: str}
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from services import governance_service as gov

router = APIRouter()


async def get_db():
    from server import db
    return db


class DecisionBody(BaseModel):
    note: str = ""
    actor: str = "operator"


@router.get("/status")
async def status():
    m = gov.load_manifest()
    return {
        "autonomy_level": gov.current_level(),
        "autonomy_level_numeric": gov.level_numeric(),
        "manifest_path": gov.DEFAULT_MANIFEST_PATH,
        "system_name": (m.get("system", {}) or {}).get("name"),
        "north_star_usd_per_day": (m.get("system", {}) or {}).get("north_star_usd_per_day"),
        "hitl_gates_count": len(m.get("hitl_gates", []) or []),
        "route_gates_count": len(m.get("route_gates", {}) or {}),
        "token_optimization_enforced": (m.get("system", {}) or {}).get("token_optimization_enforced", False),
    }


@router.get("/manifest")
async def manifest():
    return gov.load_manifest()


@router.post("/manifest/reload")
async def reload():
    gov.reload_manifest()
    return {"reloaded": True, "autonomy_level": gov.current_level()}


@router.get("/approvals")
async def approvals(status: str | None = None, limit: int = 50, db=Depends(get_db)):
    rows = await gov.list_approvals(db, status=status, limit=min(int(limit), 200))
    return rows


@router.post("/approvals/{approval_id}/approve")
async def approve(approval_id: str, body: DecisionBody, db=Depends(get_db)):
    row = await gov.decide_approval(db, approval_id, approve=True, note=body.note, actor=body.actor)
    if not row:
        return {"error": "not found", "id": approval_id}
    return row


@router.post("/approvals/{approval_id}/reject")
async def reject(approval_id: str, body: DecisionBody, db=Depends(get_db)):
    row = await gov.decide_approval(db, approval_id, approve=False, note=body.note, actor=body.actor)
    if not row:
        return {"error": "not found", "id": approval_id}
    return row
