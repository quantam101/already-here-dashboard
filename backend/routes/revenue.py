from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import RevenueStream, RevenueStreamCreate, StatusEnum
from datetime import datetime, timezone
from services.audit_service import log_audit_event
import os

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=RevenueStream)
async def create_revenue_stream(stream: RevenueStreamCreate, db=Depends(get_db)):
    """Create a new revenue stream"""
    stream_obj = RevenueStream(**stream.model_dump())
    doc = stream_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.revenue_streams.insert_one(doc)
    await log_audit_event(db, "revenue.created", "system", "create", "revenue_stream", stream_obj.id)
    return stream_obj

@router.get("/", response_model=List[RevenueStream])
async def list_revenue_streams(db=Depends(get_db)):
    """List all revenue streams"""
    streams = await db.revenue_streams.find({}, {"_id": 0}).to_list(1000)
    for stream in streams:
        if isinstance(stream.get('created_at'), str):
            stream['created_at'] = datetime.fromisoformat(stream['created_at'])
        if isinstance(stream.get('updated_at'), str):
            stream['updated_at'] = datetime.fromisoformat(stream['updated_at'])
    return streams

@router.get("/{stream_id}", response_model=RevenueStream)
async def get_revenue_stream(stream_id: str, db=Depends(get_db)):
    """Get a specific revenue stream"""
    stream = await db.revenue_streams.find_one({"id": stream_id}, {"_id": 0})
    if not stream:
        raise HTTPException(status_code=404, detail="Revenue stream not found")
    
    if isinstance(stream.get('created_at'), str):
        stream['created_at'] = datetime.fromisoformat(stream['created_at'])
    if isinstance(stream.get('updated_at'), str):
        stream['updated_at'] = datetime.fromisoformat(stream['updated_at'])
    return stream

@router.patch("/{stream_id}", response_model=RevenueStream)
async def update_revenue_stream(stream_id: str, updates: dict, db=Depends(get_db)):
    """Update a revenue stream"""
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await db.revenue_streams.update_one(
        {"id": stream_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Revenue stream not found")
    
    stream = await db.revenue_streams.find_one({"id": stream_id}, {"_id": 0})
    if isinstance(stream.get('created_at'), str):
        stream['created_at'] = datetime.fromisoformat(stream['created_at'])
    if isinstance(stream.get('updated_at'), str):
        stream['updated_at'] = datetime.fromisoformat(stream['updated_at'])
    
    await log_audit_event(db, "revenue.updated", "system", "update", "revenue_stream", stream_id)
    return stream

@router.delete("/{stream_id}")
async def delete_revenue_stream(stream_id: str, db=Depends(get_db)):
    """Delete a revenue stream"""
    result = await db.revenue_streams.delete_one({"id": stream_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Revenue stream not found")
    
    await log_audit_event(db, "revenue.deleted", "system", "delete", "revenue_stream", stream_id)
    return {"message": "Revenue stream deleted successfully"}

@router.get("/stats/overview")
async def get_revenue_stats(db=Depends(get_db)):
    """Get revenue statistics overview"""
    streams = await db.revenue_streams.find({}, {"_id": 0}).to_list(1000)
    
    total_target = sum(s.get('monthly_target', 0) for s in streams)
    total_actual = sum(s.get('monthly_actual', 0) for s in streams)
    active_streams = sum(1 for s in streams if s.get('status') == 'active')
    
    return {
        "total_monthly_target": total_target,
        "total_monthly_actual": total_actual,
        "achievement_percentage": (total_actual / total_target * 100) if total_target > 0 else 0,
        "active_streams": active_streams,
        "total_streams": len(streams),
        "streams": streams
    }