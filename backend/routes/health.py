from fastapi import APIRouter, Depends
from models import HealthCheck, StatusEnum
from datetime import datetime, timezone
import httpx
import os
import time

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Already Here Command OS"
    }


@router.get("/nodes")
async def two_node_health():
    """Two-node health report for the Free-Only Build Directive.

    Returns dashboard host status + worker (profitengine-server) reachability.
    """
    dashboard_status = {
        "name": "DashboardAlways Free",
        "role": "dashboard / control plane",
        "status": "healthy",
        "backend": os.environ.get("STORAGE_BACKEND", "mongodb"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    worker_url = os.environ.get("WORKER_BASE_URL", "")
    if not worker_url:
        worker_status = {
            "name": "profitengine-server",
            "role": "runtime / worker",
            "status": "not_configured",
            "reason": "set WORKER_BASE_URL in backend/.env to enable cross-node health",
        }
    else:
        try:
            t0 = time.time()
            async with httpx.AsyncClient(timeout=5.0) as cx:
                r = await cx.get(f"{worker_url.rstrip('/')}/api/health/")
            worker_status = {
                "name": "profitengine-server",
                "role": "runtime / worker",
                "status": "healthy" if r.status_code == 200 else "degraded",
                "http_status": r.status_code,
                "response_ms": round((time.time() - t0) * 1000, 1),
                "url": worker_url,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            worker_status = {
                "name": "profitengine-server",
                "role": "runtime / worker",
                "status": "unreachable",
                "error": str(exc)[:200],
                "url": worker_url,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }

    return {"nodes": [dashboard_status, worker_status]}


@router.get("/check/{service_name}")
async def check_service(service_name: str, url: str = None, db=Depends(get_db)):
    """Check health of a specific service"""
    health_check = HealthCheck(service_name=service_name)
    
    if url:
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    health_check.status = StatusEnum.SUCCESS
                    health_check.response_time = response_time
                else:
                    health_check.status = StatusEnum.FAILED
                    health_check.error_message = f"Status code: {response.status_code}"
        except Exception as e:
            health_check.status = StatusEnum.FAILED
            health_check.error_message = str(e)
    
    # Store health check result
    doc = health_check.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.health_checks.insert_one(doc)
    
    return health_check

@router.get("/history")
async def health_check_history(service_name: str = None, limit: int = 50, db=Depends(get_db)):
    """Get health check history"""
    query = {}
    if service_name:
        query['service_name'] = service_name
    
    checks = await db.health_checks.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    for check in checks:
        if isinstance(check.get('timestamp'), str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return checks