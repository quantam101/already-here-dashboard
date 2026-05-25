from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import AuditEvent, AuditEventCreate
from datetime import datetime, timezone

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=AuditEvent)
async def create_audit_event(event: AuditEventCreate, db=Depends(get_db)):
    """Create a new audit event"""
    event_obj = AuditEvent(**event.model_dump())
    doc = event_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    await db.audit_log.insert_one(doc)
    return event_obj

@router.get("/", response_model=List[AuditEvent])
async def list_audit_events(
    event_type: str = None,
    actor: str = None,
    resource_type: str = None,
    limit: int = 100,
    db=Depends(get_db)
):
    """List audit events with optional filters"""
    query = {}
    if event_type:
        query['event_type'] = event_type
    if actor:
        query['actor'] = actor
    if resource_type:
        query['resource_type'] = resource_type
    
    events = await db.audit_log.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)
    for event in events:
        if isinstance(event.get('timestamp'), str):
            event['timestamp'] = datetime.fromisoformat(event['timestamp'])
    return events

@router.get("/stats")
async def get_audit_stats(db=Depends(get_db)):
    """Get audit statistics"""
    total_events = await db.audit_log.count_documents({})
    
    # Count by event type
    pipeline = [
        {"$group": {"_id": "$event_type", "count": {"$sum": 1}}}
    ]
    event_types = await db.audit_log.aggregate(pipeline).to_list(100)
    
    return {
        "total_events": total_events,
        "by_event_type": {item['_id']: item['count'] for item in event_types}
    }