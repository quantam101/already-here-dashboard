from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from enum import Enum

class StatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    PUBLISHED = "published"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    SUCCESS = "success"
    DEGRADED = "degraded"
    LIVE = "live"
    ARCHIVED = "archived"

class PriorityEnum(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

# Revenue Models
class RevenueStream(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # affiliate, service, content, proposal
    status: StatusEnum = StatusEnum.ACTIVE
    monthly_target: float = 0.0
    monthly_actual: float = 0.0
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RevenueStreamCreate(BaseModel):
    name: str
    type: str
    monthly_target: float = 0.0
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Content Models
class ContentPiece(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content_type: str  # blog, social, email, proposal
    body: str
    status: StatusEnum = StatusEnum.DRAFT
    platform: Optional[str] = None
    revenue_stream_id: Optional[str] = None
    generated_by: str = "ai"
    published_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ContentGenerateRequest(BaseModel):
    content_type: str
    topic: str
    platform: Optional[str] = None
    tone: str = "professional"
    length: str = "medium"
    keywords: List[str] = Field(default_factory=list)
    revenue_stream_id: Optional[str] = None

class ContentUpdateRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    status: Optional[StatusEnum] = None
    metadata: Optional[Dict[str, Any]] = None

# Agent Models
class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str
    mission: str
    status: StatusEnum = StatusEnum.ACTIVE
    allowed_actions: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    approval_required_actions: List[str] = Field(default_factory=list)
    cost_ceiling: float = 0.0
    last_run: Optional[datetime] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentCreate(BaseModel):
    name: str
    type: str
    mission: str
    allowed_actions: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    approval_required_actions: List[str] = Field(default_factory=list)
    cost_ceiling: float = 0.0

# Build Models
class Build(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str
    status: StatusEnum = StatusEnum.DRAFT
    source_repo: Optional[str] = None
    source_folder: Optional[str] = None
    modules: List[str] = Field(default_factory=list)
    production_gate_score: int = 0
    last_deploy: Optional[datetime] = None
    last_ci_status: Optional[str] = None
    revenue_path: str = "indirect"
    next_action: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BuildCreate(BaseModel):
    name: str
    type: str
    source_repo: Optional[str] = None
    source_folder: Optional[str] = None
    modules: List[str] = Field(default_factory=list)
    revenue_path: str = "indirect"

# Deployment Models
class Deployment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    build_id: str
    environment: str  # production, staging, development
    status: StatusEnum = StatusEnum.PENDING
    target: str  # oci, vercel, local
    version: str
    deployed_by: str = "system"
    rollback_available: bool = False
    health_check_url: Optional[str] = None
    health_status: Optional[str] = None
    error_log: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class DeploymentCreate(BaseModel):
    build_id: str
    environment: str
    target: str
    version: str
    health_check_url: Optional[str] = None

# Audit Models
class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    actor: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    status: StatusEnum = StatusEnum.SUCCESS
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditEventCreate(BaseModel):
    event_type: str
    actor: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Approval Models
class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    agent_id: str
    resource_type: str
    resource_id: Optional[str] = None
    reason: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    status: StatusEnum = StatusEnum.PENDING
    requested_by: str = "system"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ApprovalRequestCreate(BaseModel):
    action: str
    agent_id: str
    resource_type: str
    resource_id: Optional[str] = None
    reason: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    requested_by: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ApprovalDecision(BaseModel):
    status: StatusEnum
    approved_by: str
    notes: Optional[str] = None

# Health Check Models
class HealthCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str
    status: StatusEnum = StatusEnum.SUCCESS
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))