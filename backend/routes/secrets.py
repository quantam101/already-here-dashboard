"""Read-only Bitwarden / Vaultwarden vault browser.

Endpoints:
  GET /api/secrets/status          -> {installed, unlocked, server, user}
  GET /api/secrets/items           -> [{id, name, type, username, has_password, ...}]

Passwords are NEVER returned over the wire — only metadata. Code that needs a
secret value should call `get_bitwarden_service().get_secret(name)` from the
backend process directly.
"""
from fastapi import APIRouter
from services.bitwarden_service import get_bitwarden_service

router = APIRouter()


@router.get("/status")
async def secrets_status():
    return await get_bitwarden_service().status()


@router.get("/items")
async def secrets_items(limit: int = 200):
    svc = get_bitwarden_service()
    if not await svc.is_available():
        return {"items": [], "available": False}
    items = await svc.list_items(limit=limit)
    return {"items": items, "available": True, "count": len(items)}
