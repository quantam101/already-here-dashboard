from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
from enum import Enum

# Content Factory Models

class ContentStatusEnum(str, Enum):
    IDEA = "idea"
    DRAFTED = "drafted"
    SCRIPTED = "scripted"
    STORYBOARDED = "storyboarded"
    ASSETS_READY = "assets_ready"
    RENDERED = "rendered"
    CAPTIONED = "captioned"
    VARIANT_READY = "variant_ready"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    BLOCKED = "blocked"
    MANUAL_UPLOAD_REQUIRED = "manual_upload_required"
    ARCHIVED = "archived"
    REPURPOSE_CANDIDATE = "repurpose_candidate"

class CostClassEnum(str, Enum):
    FREE_LOCAL = "free_local"
    FREE_EXTERNAL = "free_external"
    FREE_WITH_LIMITS = "free_with_limits"
    MANUAL_FREE = "manual_free"
    UNKNOWN_COST_BLOCKED = "unknown_cost_blocked"
    PAID_BLOCKED = "paid_blocked"

class PlatformEnum(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    YOUTUBE_SHORTS = "youtube_shorts"
    INSTAGRAM = "instagram"
    INSTAGRAM_REELS = "instagram_reels"
    FACEBOOK = "facebook"
    FACEBOOK_GROUPS = "facebook_groups"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    THREADS = "threads"
    PINTEREST = "pinterest"
    REDDIT = "reddit"
    MEDIUM = "medium"
    DEVTO = "devto"
    HASHNODE = "hashnode"
    BLOG = "blog"
    DISCOURSE = "discourse"
    QUORA = "quora"
    FORUM = "forum"

# Content Idea
class ContentIdea(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    topic: str
    target_platforms: List[PlatformEnum] = Field(default_factory=list)
    status: ContentStatusEnum = ContentStatusEnum.IDEA
    priority: str = "medium"  # low, medium, high, critical
    tags: List[str] = Field(default_factory=list)
    inspiration_source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Content Script
class ContentScript(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idea_id: str
    hook: str
    script_body: str
    cta: Optional[str] = None
    duration_seconds: Optional[int] = None
    shot_list: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Content Asset
class ContentAsset(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    asset_type: str  # video, image, audio, text
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    dimensions: Optional[str] = None  # WxH
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Platform Connector
class PlatformConnector(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    platform: PlatformEnum
    name: str
    cost_class: CostClassEnum
    has_api: bool = False
    api_authenticated: bool = False
    requires_app_review: bool = False
    app_review_status: Optional[str] = None  # pending, approved, rejected
    credential_status: str = "missing"  # missing, configured, expired
    supported_media_types: List[str] = Field(default_factory=list)
    max_file_size_mb: Optional[int] = None
    max_duration_seconds: Optional[int] = None
    caption_max_length: Optional[int] = None
    supports_scheduling: bool = False
    rate_limit_per_day: Optional[int] = None
    blocked_reason: Optional[str] = None
    setup_instructions: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Scheduled Post
class ScheduledPost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str
    platform: PlatformEnum
    status: ContentStatusEnum = ContentStatusEnum.SCHEDULED
    scheduled_time: datetime
    title: Optional[str] = None
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    thumbnail_url: Optional[str] = None
    publishing_method: str = "direct_api"  # direct_api, manual_export
    export_pack_path: Optional[str] = None
    published_url: Optional[str] = None
    published_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Content Analytics
class ContentAnalytics(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    post_id: str
    platform: PlatformEnum
    post_url: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    watch_time_seconds: Optional[float] = None
    engagement_rate: Optional[float] = None
    conversion_events: int = 0
    revenue: Optional[float] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Platform Variant
class PlatformVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str
    platform: PlatformEnum
    aspect_ratio: str  # 9:16, 1:1, 4:5, 16:9
    title: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))