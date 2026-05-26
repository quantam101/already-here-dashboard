from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import Build, BuildCreate
from datetime import datetime, timezone
from services.audit_service import log_audit_event

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=Build)
async def create_build(build: BuildCreate, db=Depends(get_db)):
    """Create a new build"""
    build_obj = Build(**build.model_dump())
    doc = build_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('last_deploy'):
        doc['last_deploy'] = doc['last_deploy'].isoformat()
    
    await db.builds.insert_one(doc)
    await log_audit_event(db, "build.created", "system", "create", "build", build_obj.id)
    return build_obj

@router.get("/", response_model=List[Build])
async def list_builds(status: str = None, db=Depends(get_db)):
    """List all builds"""
    query = {}
    if status:
        query['status'] = status
    
    builds = await db.builds.find(query, {"_id": 0}).to_list(1000)
    for build in builds:
        if isinstance(build.get('created_at'), str):
            build['created_at'] = datetime.fromisoformat(build['created_at'])
        if isinstance(build.get('updated_at'), str):
            build['updated_at'] = datetime.fromisoformat(build['updated_at'])
        if build.get('last_deploy') and isinstance(build['last_deploy'], str):
            build['last_deploy'] = datetime.fromisoformat(build['last_deploy'])
    return builds

@router.get("/{build_id}", response_model=Build)
async def get_build(build_id: str, db=Depends(get_db)):
    """Get a specific build"""
    build = await db.builds.find_one({"id": build_id}, {"_id": 0})
    if not build:
        raise HTTPException(status_code=404, detail="Build not found")
    
    if isinstance(build.get('created_at'), str):
        build['created_at'] = datetime.fromisoformat(build['created_at'])
    if isinstance(build.get('updated_at'), str):
        build['updated_at'] = datetime.fromisoformat(build['updated_at'])
    if build.get('last_deploy') and isinstance(build['last_deploy'], str):
        build['last_deploy'] = datetime.fromisoformat(build['last_deploy'])
    return build

@router.patch("/{build_id}", response_model=Build)
async def update_build(build_id: str, updates: dict, db=Depends(get_db)):
    """Update a build"""
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await db.builds.update_one(
        {"id": build_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Build not found")
    
    build = await db.builds.find_one({"id": build_id}, {"_id": 0})
    if isinstance(build.get('created_at'), str):
        build['created_at'] = datetime.fromisoformat(build['created_at'])
    if isinstance(build.get('updated_at'), str):
        build['updated_at'] = datetime.fromisoformat(build['updated_at'])
    if build.get('last_deploy') and isinstance(build['last_deploy'], str):
        build['last_deploy'] = datetime.fromisoformat(build['last_deploy'])
    
    await log_audit_event(db, "build.updated", "system", "update", "build", build_id)
    return build