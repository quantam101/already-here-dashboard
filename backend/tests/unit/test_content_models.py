"""
Unit tests for Pydantic content models.

Validates that model validation, defaults, and enum enforcement work correctly.
No network. No DB. Zero external dependencies.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from content_models import (
    ContentAnalytics,
    ContentIdea,
    ContentScript,
    ContentStatusEnum,
    CostClassEnum,
    PlatformConnector,
    PlatformEnum,
    ScheduledPost,
)

# ── ContentIdea ───────────────────────────────────────────────────────────────

class TestContentIdea:
    def _valid(self, **kwargs):
        defaults = {"title": "Test Idea", "description": "A description", "topic": "AI"}
        defaults.update(kwargs)
        return ContentIdea(**defaults)

    def test_default_status_is_idea(self):
        idea = self._valid()
        assert idea.status == ContentStatusEnum.IDEA

    def test_auto_uuid_id(self):
        idea = self._valid()
        assert len(idea.id) == 36  # UUID4 string length
        try:
            uuid.UUID(idea.id)
        except ValueError:
            pytest.fail("id is not a valid UUID")

    def test_default_priority_is_medium(self):
        assert self._valid().priority == "medium"

    def test_target_platforms_default_empty_list(self):
        assert self._valid().target_platforms == []

    def test_accepts_valid_platforms(self):
        idea = self._valid(target_platforms=["tiktok", "youtube", "instagram"])
        assert PlatformEnum.TIKTOK in idea.target_platforms

    def test_rejects_invalid_platform(self):
        with pytest.raises(Exception):
            self._valid(target_platforms=["not_a_real_platform"])

    def test_extra_fields_ignored(self):
        """model_config extra='ignore' — unknown fields must not raise."""
        idea = self._valid(unknown_field="should_be_ignored")
        assert not hasattr(idea, "unknown_field")

    def test_timestamps_are_datetime(self):
        idea = self._valid()
        assert isinstance(idea.created_at, datetime)
        assert isinstance(idea.updated_at, datetime)


# ── ContentScript ─────────────────────────────────────────────────────────────

class TestContentScript:
    def test_required_fields(self):
        script = ContentScript(
            idea_id="idea-001",
            hook="Did you know?",
            script_body="Here is the full script.",
        )
        assert script.idea_id == "idea-001"
        assert script.hook == "Did you know?"

    def test_shot_list_defaults_empty(self):
        script = ContentScript(idea_id="idea-001", hook="H", script_body="B")
        assert script.shot_list == []

    def test_optional_cta_defaults_none(self):
        script = ContentScript(idea_id="idea-001", hook="H", script_body="B")
        assert script.cta is None


# ── PlatformEnum ──────────────────────────────────────────────────────────────

class TestPlatformEnum:
    def test_all_expected_values_present(self):
        expected = {
            "tiktok", "youtube", "youtube_shorts", "instagram", "instagram_reels",
            "facebook", "facebook_groups", "linkedin", "twitter", "threads",
            "pinterest", "reddit", "medium", "devto", "hashnode", "blog",
            "discourse", "quora", "forum",
        }
        actual = {e.value for e in PlatformEnum}
        missing = expected - actual
        assert not missing, f"Missing platform values: {missing}"

    def test_string_value_matches_enum_name_lowercase(self):
        assert PlatformEnum.TIKTOK.value == "tiktok"
        assert PlatformEnum.YOUTUBE.value == "youtube"
        assert PlatformEnum.FACEBOOK_GROUPS.value == "facebook_groups"
        assert PlatformEnum.DISCOURSE.value == "discourse"
        assert PlatformEnum.QUORA.value == "quora"
        assert PlatformEnum.FORUM.value == "forum"


# ── ContentStatusEnum ─────────────────────────────────────────────────────────

class TestContentStatusEnum:
    def test_all_lifecycle_states_present(self):
        values = {e.value for e in ContentStatusEnum}
        for state in ("idea", "drafted", "scripted", "published", "failed", "archived"):
            assert state in values, f"Missing status: {state}"

    def test_manual_upload_required_present(self):
        assert ContentStatusEnum.MANUAL_UPLOAD_REQUIRED.value == "manual_upload_required"


# ── CostClassEnum ─────────────────────────────────────────────────────────────

class TestCostClassEnum:
    def test_free_local_exists(self):
        assert CostClassEnum.FREE_LOCAL.value == "free_local"

    def test_paid_blocked_exists(self):
        assert CostClassEnum.PAID_BLOCKED.value == "paid_blocked"


# ── ContentAnalytics ──────────────────────────────────────────────────────────

class TestContentAnalytics:
    def test_default_counts_are_zero(self):
        a = ContentAnalytics(
            post_id="post-001",
            platform=PlatformEnum.TIKTOK,
            post_url="https://tiktok.com/@user/video/123",
        )
        assert a.views == 0
        assert a.likes == 0
        assert a.comments == 0
        assert a.shares == 0

    def test_engagement_rate_defaults_none(self):
        a = ContentAnalytics(
            post_id="post-001",
            platform=PlatformEnum.YOUTUBE,
            post_url="https://youtube.com/watch?v=abc",
        )
        assert a.engagement_rate is None


# ── PlatformConnector ─────────────────────────────────────────────────────────

class TestPlatformConnector:
    def test_default_credential_status(self):
        c = PlatformConnector(
            platform=PlatformEnum.MEDIUM,
            name="Medium",
            cost_class=CostClassEnum.FREE_EXTERNAL,
        )
        assert c.credential_status == "missing"

    def test_has_api_defaults_false(self):
        c = PlatformConnector(
            platform=PlatformEnum.REDDIT,
            name="Reddit",
            cost_class=CostClassEnum.FREE_EXTERNAL,
        )
        assert c.has_api is False


# ── ScheduledPost ─────────────────────────────────────────────────────────────

class TestScheduledPost:
    def test_status_defaults_to_scheduled(self):
        post = ScheduledPost(
            content_id="idea-001",
            platform=PlatformEnum.TIKTOK,
            scheduled_time=datetime.now(UTC),
            caption="Test caption",
        )
        assert post.status == ContentStatusEnum.SCHEDULED

    def test_retry_count_defaults_zero(self):
        post = ScheduledPost(
            content_id="idea-001",
            platform=PlatformEnum.YOUTUBE,
            scheduled_time=datetime.now(UTC),
            caption="Caption",
        )
        assert post.retry_count == 0
