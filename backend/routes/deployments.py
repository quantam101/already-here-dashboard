from datetime import UTC, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from models import Deployment, DeploymentCreate

from services.audit_service import log_audit_event

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=Deployment)
async def create_deployment(deployment: DeploymentCreate, db=Depends(get_db)):
    """Create a new deployment"""
    deployment_obj = Deployment(**deployment.model_dump())
    doc = deployment_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()

    await db.deployments.insert_one(doc)
    await log_audit_event(db, "deployment.created", "system", "create", "deployment", deployment_obj.id)
    return deployment_obj

@router.get("/", response_model=List[Deployment])
async def list_deployments(build_id: str = None, environment: str = None, db=Depends(get_db)):
    """List all deployments"""
    query = {}
    if build_id:
        query['build_id'] = build_id
    if environment:
        query['environment'] = environment

    deployments = await db.deployments.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for deployment in deployments:
        if isinstance(deployment.get('created_at'), str):
            deployment['created_at'] = datetime.fromisoformat(deployment['created_at'])
        if isinstance(deployment.get('updated_at'), str):
            deployment['updated_at'] = datetime.fromisoformat(deployment['updated_at'])
    return deployments

@router.get("/{deployment_id}", response_model=Deployment)
async def get_deployment(deployment_id: str, db=Depends(get_db)):
    """Get a specific deployment"""
    deployment = await db.deployments.find_one({"id": deployment_id}, {"_id": 0})
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if isinstance(deployment.get('created_at'), str):
        deployment['created_at'] = datetime.fromisoformat(deployment['created_at'])
    if isinstance(deployment.get('updated_at'), str):
        deployment['updated_at'] = datetime.fromisoformat(deployment['updated_at'])
    return deployment

@router.patch("/{deployment_id}", response_model=Deployment)
async def update_deployment(deployment_id: str, updates: dict, db=Depends(get_db)):
    """Update a deployment"""
    updates['updated_at'] = datetime.now(UTC).isoformat()
    result = await db.deployments.update_one(
        {"id": deployment_id},
        {"$set": updates}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Deployment not found")

    deployment = await db.deployments.find_one({"id": deployment_id}, {"_id": 0})
    if isinstance(deployment.get('created_at'), str):
        deployment['created_at'] = datetime.fromisoformat(deployment['created_at'])
    if isinstance(deployment.get('updated_at'), str):
        deployment['updated_at'] = datetime.fromisoformat(deployment['updated_at'])

    await log_audit_event(db, "deployment.updated", "system", "update", "deployment", deployment_id)
    return deployment
