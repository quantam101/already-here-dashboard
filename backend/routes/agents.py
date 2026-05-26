from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models import Agent, AgentCreate
from datetime import datetime, timezone
from services.audit_service import log_audit_event

router = APIRouter()

async def get_db():
    from server import db
    return db

@router.post("/", response_model=Agent)
async def create_agent(agent: AgentCreate, db=Depends(get_db)):
    """Create a new agent"""
    agent_obj = Agent(**agent.model_dump())
    doc = agent_obj.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('last_run'):
        doc['last_run'] = doc['last_run'].isoformat()
    
    await db.agents.insert_one(doc)
    await log_audit_event(db, "agent.created", "system", "create", "agent", agent_obj.id)
    return agent_obj

@router.get("/", response_model=List[Agent])
async def list_agents(status: str = None, db=Depends(get_db)):
    """List all agents"""
    query = {}
    if status:
        query['status'] = status
    
    agents = await db.agents.find(query, {"_id": 0}).to_list(1000)
    for agent in agents:
        if isinstance(agent.get('created_at'), str):
            agent['created_at'] = datetime.fromisoformat(agent['created_at'])
        if isinstance(agent.get('updated_at'), str):
            agent['updated_at'] = datetime.fromisoformat(agent['updated_at'])
        if agent.get('last_run') and isinstance(agent['last_run'], str):
            agent['last_run'] = datetime.fromisoformat(agent['last_run'])
    return agents

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str, db=Depends(get_db)):
    """Get a specific agent"""
    agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if isinstance(agent.get('created_at'), str):
        agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    if isinstance(agent.get('updated_at'), str):
        agent['updated_at'] = datetime.fromisoformat(agent['updated_at'])
    if agent.get('last_run') and isinstance(agent['last_run'], str):
        agent['last_run'] = datetime.fromisoformat(agent['last_run'])
    return agent

@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, updates: dict, db=Depends(get_db)):
    """Update an agent"""
    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    result = await db.agents.update_one(
        {"id": agent_id},
        {"$set": updates}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if isinstance(agent.get('created_at'), str):
        agent['created_at'] = datetime.fromisoformat(agent['created_at'])
    if isinstance(agent.get('updated_at'), str):
        agent['updated_at'] = datetime.fromisoformat(agent['updated_at'])
    if agent.get('last_run') and isinstance(agent['last_run'], str):
        agent['last_run'] = datetime.fromisoformat(agent['last_run'])
    
    await log_audit_event(db, "agent.updated", "system", "update", "agent", agent_id)
    return agent

@router.post("/{agent_id}/execute")
async def execute_agent(agent_id: str, db=Depends(get_db)):
    """Execute an agent action"""
    agent = await db.agents.find_one({"id": agent_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Update agent stats
    await db.agents.update_one(
        {"id": agent_id},
        {
            "$set": {
                "last_run": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            },
            "$inc": {"run_count": 1}
        }
    )
    
    await log_audit_event(db, "agent.executed", "system", "execute", "agent", agent_id)
    return {"message": "Agent execution started", "agent_id": agent_id}