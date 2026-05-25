from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import ApprovalRequest, ApprovalRequestCreate, ApprovalDecision, StatusEnum
from datetime import datetime, timezone
from services.audit_service import log_audit_event

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=ApprovalRequest)
async def create_approval_request(request: ApprovalRequestCreate, db=Depends(get_db)):
    """Create a new approval request"""
    approval_obj = ApprovalRequest(**request.model_dump())
    doc = approval_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('approved_at'):
        doc['approved_at'] = doc['approved_at'].isoformat()
    
    await db.approvals.insert_one(doc)
    await log_audit_event(db, "approval.requested", request.requested_by, "request", "approval", approval_obj.id)
    return approval_obj

@router.get("/", response_model=List[ApprovalRequest])
async def list_approval_requests(status: str = None, priority: str = None, db=Depends(get_db)):
    """List all approval requests"""
    query = {}
    if status:
        query['status'] = status
    if priority:
        query['priority'] = priority
    
    approvals = await db.approvals.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    for approval in approvals:
        if isinstance(approval.get('created_at'), str):
            approval['created_at'] = datetime.fromisoformat(approval['created_at'])
        if isinstance(approval.get('updated_at'), str):
            approval['updated_at'] = datetime.fromisoformat(approval['updated_at'])
        if approval.get('approved_at') and isinstance(approval['approved_at'], str):
            approval['approved_at'] = datetime.fromisoformat(approval['approved_at'])
    return approvals

@router.get("/{approval_id}", response_model=ApprovalRequest)
async def get_approval_request(approval_id: str, db=Depends(get_db)):
    """Get a specific approval request"""
    approval = await db.approvals.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if isinstance(approval.get('created_at'), str):
        approval['created_at'] = datetime.fromisoformat(approval['created_at'])
    if isinstance(approval.get('updated_at'), str):
        approval['updated_at'] = datetime.fromisoformat(approval['updated_at'])
    if approval.get('approved_at') and isinstance(approval['approved_at'], str):
        approval['approved_at'] = datetime.fromisoformat(approval['approved_at'])
    return approval

@router.post("/{approval_id}/decide", response_model=ApprovalRequest)
async def decide_approval(approval_id: str, decision: ApprovalDecision, db=Depends(get_db)):
    """Approve or reject an approval request"""
    update_data = {
        'status': decision.status.value,
        'approved_by': decision.approved_by,
        'approved_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    if decision.notes:
        update_data['metadata.decision_notes'] = decision.notes
    
    result = await db.approvals.update_one(
        {"id": approval_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    approval = await db.approvals.find_one({"id": approval_id}, {"_id": 0})
    if isinstance(approval.get('created_at'), str):
        approval['created_at'] = datetime.fromisoformat(approval['created_at'])
    if isinstance(approval.get('updated_at'), str):
        approval['updated_at'] = datetime.fromisoformat(approval['updated_at'])
    if approval.get('approved_at') and isinstance(approval['approved_at'], str):
        approval['approved_at'] = datetime.fromisoformat(approval['approved_at'])
    
    event_type = "approval.granted" if decision.status == StatusEnum.APPROVED else "approval.denied"
    await log_audit_event(db, event_type, decision.approved_by, "decide", "approval", approval_id)
    return approval