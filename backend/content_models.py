import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field

# Content Factory Models

class ContentStatusEnum(StrEnum):
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

class CostClassEnum(StrEnum):
    FREE_LOCAL = "free_local"
    FREE_EXTERNAL = "free_external"
    FREE_WITH_LIMITS = "free_with_limits"
    MANUAL_FREE = "manual_free"
    UNKNOWN_COST_BLOCKED = "unknown_cost_blocked"
    PAID_BLOCKED = "paid_blocked"

class PlatformEnum(StrEnum):
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
    inspiration_source: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# Content Script
class ContentScript(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idea_id: str
    hook: str
    script_body: str
    cta: str | None = None
    duration_seconds: int | None = None
    shot_list: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# Content Asset
class ContentAsset(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    asset_type: str  # video, image, audio, text
    file_path: str | None = None
    file_url: str | None = None
    file_size: int | None = None
    duration: float | None = None
    dimensions: str | None = None  # WxH
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
    app_review_status: str | None = None  # pending, approved, rejected
    credential_status: str = "missing"  # missing, configured, expired
    supported_media_types: List[str] = Field(default_factory=list)
    max_file_size_mb: int | None = None
    max_duration_seconds: int | None = None
    caption_max_length: int | None = None
    supports_scheduling: bool = False
    rate_limit_per_day: int | None = None
    blocked_reason: str | None = None
    setup_instructions: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

# Scheduled Post
class ScheduledPost(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_id: str
    platform: PlatformEnum
    status: ContentStatusEnum = ContentStatusEnum.SCHEDULED
    scheduled_time: datetime
    title: str | None = None
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    thumbnail_url: str | None = None
    publishing_method: str = "direct_api"  # direct_api, manual_export
    export_pack_path: str | None = None
    published_url: str | None = None
    published_at: datetime | None = None
    failure_reason: str | None = None
    retry_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

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
    watch_time_seconds: float | None = None
    engagement_rate: float | None = None
    conversion_events: int = 0
    revenue: float | None = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))
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
    description: str | None = None
    video_path: str | None = None
    thumbnail_path: str | None = None
    subtitle_path: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
