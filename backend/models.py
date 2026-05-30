import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class StatusEnum(StrEnum):
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

class PriorityEnum(StrEnum):
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
    description: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class RevenueStreamCreate(BaseModel):
    name: str
    type: str
    monthly_target: float = 0.0
    description: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Content Models
class ContentPiece(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content_type: str  # blog, social, email, proposal
    body: str
    status: StatusEnum = StatusEnum.DRAFT
    platform: str | None = None
    revenue_stream_id: str | None = None
    generated_by: str = "ai"
    published_at: datetime | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class ContentGenerateRequest(BaseModel):
    content_type: str
    topic: str
    platform: str | None = None
    tone: str = "professional"
    length: str = "medium"
    keywords: List[str] = Field(default_factory=list)
    revenue_stream_id: str | None = None

class ContentUpdateRequest(BaseModel):
    title: str | None = None
    body: str | None = None
    status: StatusEnum | None = None
    metadata: Dict[str, Any] | None = None

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
    last_run: datetime | None = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
    source_repo: str | None = None
    source_folder: str | None = None
    modules: List[str] = Field(default_factory=list)
    production_gate_score: int = 0
    last_deploy: datetime | None = None
    last_ci_status: str | None = None
    revenue_path: str = "indirect"
    next_action: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class BuildCreate(BaseModel):
    name: str
    type: str
    source_repo: str | None = None
    source_folder: str | None = None
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
    health_check_url: str | None = None
    health_status: str | None = None
    error_log: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class DeploymentCreate(BaseModel):
    build_id: str
    environment: str
    target: str
    version: str
    health_check_url: str | None = None

# Audit Models
class AuditEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    status: StatusEnum = StatusEnum.SUCCESS
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

class AuditEventCreate(BaseModel):
    event_type: str
    actor: str
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Approval Models
class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: str
    agent_id: str
    resource_type: str
    resource_id: str | None = None
    reason: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    status: StatusEnum = StatusEnum.PENDING
    requested_by: str = "system"
    approved_by: str | None = None
    approved_at: datetime | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class ApprovalRequestCreate(BaseModel):
    action: str
    agent_id: str
    resource_type: str
    resource_id: str | None = None
    reason: str
    priority: PriorityEnum = PriorityEnum.MEDIUM
    requested_by: str = "system"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ApprovalDecision(BaseModel):
    status: StatusEnum
    approved_by: str
    notes: str | None = None

# Health Check Models
class HealthCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    service_name: str
    status: StatusEnum = StatusEnum.SUCCESS
    response_time: float | None = None
    error_message: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
