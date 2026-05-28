"""
Unit tests for cycle route helper logic.

Tests _make_idea_doc() and _make_publishing_draft() in isolation — no DB, no HTTP.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from routes.cycle import (
    _make_idea_doc,
    _make_publishing_draft,
    ALL_PLATFORMS,
    TEXT_PLATFORMS,
    VIDEO_PLATFORMS,
    MANUAL_PLATFORMS,
)


class _FakeOpp:
    """Minimal stand-in for a Scout Opportunity."""
    def __init__(
        self,
        title="Test Opportunity",
        summary="A summary",
        source="reddit",
        kind="post",
        score=95,
        url="https://reddit.com/r/test/1",
        opp_id="opp-abc123",
        metadata=None,
    ):
        self.id = opp_id
        self.title = title
        self.summary = summary
        self.source = source
        self.kind = kind
        self.score = score
        self.url = url
        self.metadata = metadata or {}


TS = datetime.now(timezone.utc).isoformat()
CYCLE_ID = "cyc-test001"


class TestMakeIdeaDoc:
    def test_returns_dict_with_required_keys(self):
        opp = _FakeOpp()
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        for key in ("id", "title", "description", "topic", "target_platforms", "status", "tags"):
            assert key in doc, f"Missing key: {key}"

    def test_id_has_idea_prefix(self):
        opp = _FakeOpp()
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["id"].startswith("idea-")

    def test_title_truncated_to_200_chars(self):
        opp = _FakeOpp(title="x" * 300)
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert len(doc["title"]) <= 200

    def test_target_platforms_matches_input(self):
        platforms = ["medium", "devto"]
        opp = _FakeOpp()
        doc = _make_idea_doc(opp, platforms, CYCLE_ID, TS)
        assert doc["target_platforms"] == platforms

    def test_status_is_drafted(self):
        opp = _FakeOpp()
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["status"] == "drafted"

    def test_metadata_has_opp_score_and_cycle_id(self):
        opp = _FakeOpp(score=42)
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["metadata"]["opp_score"] == 42
        assert doc["metadata"]["cycle_id"] == CYCLE_ID

    def test_tags_include_source_and_kind(self):
        opp = _FakeOpp(source="hackernews", kind="story")
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert "hackernews" in doc["tags"]
        assert "story" in doc["tags"]

    def test_subreddit_metadata_used_as_topic(self):
        opp = _FakeOpp(source="reddit", metadata={"subreddit": "entrepreneur"})
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["topic"] == "entrepreneur"

    def test_source_used_as_topic_when_no_subreddit(self):
        opp = _FakeOpp(source="hackernews", metadata={})
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["topic"] == "hackernews"

    def test_inspiration_source_is_opp_url(self):
        opp = _FakeOpp(url="https://news.ycombinator.com/item?id=123")
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert doc["inspiration_source"] == "https://news.ycombinator.com/item?id=123"

    def test_description_falls_back_to_source(self):
        opp = _FakeOpp(summary=None)
        doc = _make_idea_doc(opp, ALL_PLATFORMS, CYCLE_ID, TS)
        assert opp.source in doc["description"]


class TestMakePublishingDraft:
    def test_returns_dict_with_required_keys(self):
        doc = _make_publishing_draft(
            idea_id="idea-001", title="Test", stream_id="rev-001",
            platform="medium", cycle_id=CYCLE_ID,
            source="reddit", timestamp_iso=TS,
        )
        for key in ("id", "stream_id", "platform", "title", "idea_id", "status"):
            assert key in doc, f"Missing key: {key}"

    def test_id_has_pub_prefix(self):
        doc = _make_publishing_draft(
            "idea-001", "Test", "rev-001", "medium", CYCLE_ID, "reddit", TS
        )
        assert doc["id"].startswith("pub-")

    def test_status_is_drafted(self):
        doc = _make_publishing_draft(
            "idea-001", "Test", "rev-001", "medium", CYCLE_ID, "reddit", TS
        )
        assert doc["status"] == "drafted"

    def test_title_truncated_to_200_chars(self):
        doc = _make_publishing_draft(
            "idea-001", "T" * 300, "rev-001", "medium", CYCLE_ID, "reddit", TS
        )
        assert len(doc["title"]) <= 200

    def test_platform_is_correct(self):
        doc = _make_publishing_draft(
            "idea-001", "Test", "rev-001", "tiktok", CYCLE_ID, "reddit", TS
        )
        assert doc["platform"] == "tiktok"

    def test_idea_id_is_correct(self):
        doc = _make_publishing_draft(
            "idea-test-001", "Test", "rev-001", "medium", CYCLE_ID, "reddit", TS
        )
        assert doc["idea_id"] == "idea-test-001"

    def test_notes_contains_cycle_id(self):
        doc = _make_publishing_draft(
            "idea-001", "Test", "rev-001", "medium", CYCLE_ID, "reddit", TS
        )
        assert CYCLE_ID in doc["notes"]


class TestPlatformConstants:
    def test_all_platforms_is_union(self):
        combined = set(TEXT_PLATFORMS + VIDEO_PLATFORMS + MANUAL_PLATFORMS)
        for p in combined:
            assert p in ALL_PLATFORMS, f"Platform '{p}' missing from ALL_PLATFORMS"

    def test_no_duplicates_in_all_platforms(self):
        assert len(ALL_PLATFORMS) == len(set(ALL_PLATFORMS)), "Duplicate platforms in ALL_PLATFORMS"

    def test_expected_text_platforms_present(self):
        for p in ("medium", "devto", "reddit", "facebook", "threads", "linkedin", "discourse"):
            assert p in TEXT_PLATFORMS, f"'{p}' missing from TEXT_PLATFORMS"

    def test_expected_video_platforms_present(self):
        for p in ("youtube", "tiktok", "instagram"):
            assert p in VIDEO_PLATFORMS, f"'{p}' missing from VIDEO_PLATFORMS"

    def test_expected_manual_platforms_present(self):
        for p in ("facebook_groups", "quora", "forum"):
            assert p in MANUAL_PLATFORMS, f"'{p}' missing from MANUAL_PLATFORMS"
