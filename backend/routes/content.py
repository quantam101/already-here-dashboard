from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import ContentPiece, ContentGenerateRequest, ContentUpdateRequest, StatusEnum
from datetime import datetime, timezone
from services.content_service import generate_content
from services.audit_service import log_audit_event
import os

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/generate", response_model=ContentPiece)
async def create_content(request: ContentGenerateRequest, db=Depends(get_db)):
    """Generate new content using AI"""
    content_body = await generate_content(request)
    
    content_obj = ContentPiece(
        title=f"{request.topic} - {request.content_type}",
        content_type=request.content_type,
        body=content_body,
        status=StatusEnum.DRAFT,
        platform=request.platform,
        revenue_stream_id=request.revenue_stream_id,
        metadata={"keywords": request.keywords, "tone": request.tone, "length": request.length}
    )
    
    doc = content_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('published_at'):
        doc['published_at'] = doc['published_at'].isoformat()
    
    await db.content.insert_one(doc)
    await log_audit_event(db, "content.generated", "system", "generate", "content", content_obj.id)
    return content_obj

@router.get("/", response_model=List[ContentPiece])
async def list_content(status: str = None, content_type: str = None, db=Depends(get_db)):
    """List all content pieces"""
    query = {}
    if status:
        query['status'] = status
    if content_type:
        query['content_type'] = content_type
    
    content_list = await db.content.find(query, {"_id": 0}).to_list(1000)
    for content in content_list:
        if isinstance(content.get('created_at'), str):
            content['created_at'] = datetime.fromisoformat(content['created_at'])
        if isinstance(content.get('updated_at'), str):
            content['updated_at'] = datetime.fromisoformat(content['updated_at'])
        if content.get('published_at') and isinstance(content['published_at'], str):
            content['published_at'] = datetime.fromisoformat(content['published_at'])
    return content_list

@router.get("/{content_id}", response_model=ContentPiece)
async def get_content(content_id: str, db=Depends(get_db)):
    """Get a specific content piece"""
    content = await db.content.find_one({"id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    if isinstance(content.get('created_at'), str):
        content['created_at'] = datetime.fromisoformat(content['created_at'])
    if isinstance(content.get('updated_at'), str):
        content['updated_at'] = datetime.fromisoformat(content['updated_at'])
    if content.get('published_at') and isinstance(content['published_at'], str):
        content['published_at'] = datetime.fromisoformat(content['published_at'])
    return content

@router.patch("/{content_id}", response_model=ContentPiece)
async def update_content(content_id: str, updates: ContentUpdateRequest, db=Depends(get_db)):
    """Update a content piece"""
    update_data = {k: v for k, v in updates.model_dump(exclude_unset=True).items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if updates.status == StatusEnum.PUBLISHED:
        update_data['published_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.content.update_one(
        {"id": content_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Content not found")
    
    content = await db.content.find_one({"id": content_id}, {"_id": 0})
    if isinstance(content.get('created_at'), str):
        content['created_at'] = datetime.fromisoformat(content['created_at'])
    if isinstance(content.get('updated_at'), str):
        content['updated_at'] = datetime.fromisoformat(content['updated_at'])
    if content.get('published_at') and isinstance(content['published_at'], str):
        content['published_at'] = datetime.fromisoformat(content['published_at'])
    
    await log_audit_event(db, "content.updated", "system", "update", "content", content_id)
    return content

@router.delete("/{content_id}")
async def delete_content(content_id: str, db=Depends(get_db)):
    """Delete a content piece"""
    result = await db.content.delete_one({"id": content_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Content not found")
    
    await log_audit_event(db, "content.deleted", "system", "delete", "content", content_id)
    return {"message": "Content deleted successfully"}