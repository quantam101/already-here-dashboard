"""
Regression test suite — Already Here Command OS.

Purpose: catch regressions introduced by changes to existing functionality.
These tests run the SAME assertions as the integration suite but are grouped
separately so they can be re-run independently as a smoke check before deploys.

Strategy:
  • Start all regression tests with an exact expected value / contract
  • Any deviation = a regression that needs investigation
  • Keep tests small and targeted — one behaviour per test

This file is the "before/after snapshot" layer in the test pyramid.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# ── Social Publisher — regression contracts ────────────────────────────────────

class TestSocialPublisherRegression:
    """
    Exact behaviour contracts for SocialPublisher.
    If any of these change, a regression has occurred.
    """

    def test_export_pack_has_exactly_five_top_level_content_keys(self):
        from services.social_publisher import SocialPublisher
        pub = SocialPublisher()
        pack = pub.export_pack({
            "title": "Test", "body": "Body text.", "tags": ["a"],
        })
        content_keys = {"facebook_groups", "quora", "forum", "video_script", "instagram_caption"}
        actual_keys = set(pack.keys()) - {"generated_at", "article_title"}
        assert actual_keys == content_keys, f"Pack keys changed: {actual_keys}"

    def test_video_script_note_always_mentions_capcut(self):
        from services.social_publisher import SocialPublisher
        pub = SocialPublisher()
        pack = pub.export_pack({"title": "Test", "body": "Body", "tags": []})
        assert "CapCut" in pack["video_script"]["note"]

    def test_export_pack_article_title_is_preserved(self):
        from services.social_publisher import SocialPublisher
        pub = SocialPublisher()
        title = "Exact Title — Regression Check"
        pack = pub.export_pack({"title": title, "body": "B", "tags": []})
        assert pack["article_title"] == title

    def test_connector_status_keys_are_stable(self):
        """
        The set of connector keys must remain stable across releases.
        If a new platform is added it must appear here too.
        """
        from services.social_publisher import connector_status
        status = connector_status()
        required_keys = {
            "medium", "devto", "reddit", "facebook", "threads",
            "linkedin", "youtube", "tiktok", "instagram", "discourse",
        }
        missing = required_keys - set(status.keys())
        assert not missing, f"Connector keys removed: {missing}"

    def test_post_result_to_dict_has_stable_schema(self):
        from services.social_publisher import PostResult
        r = PostResult("medium", True, url="https://medium.com/test", skipped=False)
        d = r.to_dict()
        assert set(d.keys()) == {"platform", "success", "url", "error", "skipped"}


# ── Cycle constants — regression contracts ────────────────────────────────────

class TestCycleConstantsRegression:
    def test_all_platforms_count_is_13(self):
        from routes.cycle import ALL_PLATFORMS
        assert len(ALL_PLATFORMS) == 13, (
            f"ALL_PLATFORMS count changed (expected 13, got {len(ALL_PLATFORMS)}): {ALL_PLATFORMS}"
        )

    def test_text_platforms_count_is_7(self):
        from routes.cycle import TEXT_PLATFORMS
        assert len(TEXT_PLATFORMS) == 7

    def test_video_platforms_count_is_3(self):
        from routes.cycle import VIDEO_PLATFORMS
        assert len(VIDEO_PLATFORMS) == 3

    def test_manual_platforms_count_is_3(self):
        from routes.cycle import MANUAL_PLATFORMS
        assert len(MANUAL_PLATFORMS) == 3


# ── PlatformEnum — regression contracts ──────────────────────────────────────

class TestPlatformEnumRegression:
    def test_enum_value_count_is_19(self):
        """
        PlatformEnum must have exactly 19 values.
        Update this assertion when adding new platforms (with explanation in commit).
        """
        from content_models import PlatformEnum
        count = len(list(PlatformEnum))
        assert count == 19, f"PlatformEnum count changed (expected 19, got {count})"

    def test_four_new_platforms_present(self):
        """Regression: facebook_groups, discourse, quora, forum added in v2.0."""
        from content_models import PlatformEnum
        values = {e.value for e in PlatformEnum}
        for p in ("facebook_groups", "discourse", "quora", "forum"):
            assert p in values, f"Regression: '{p}' was removed from PlatformEnum"


# ── ContentStatusEnum — regression contracts ──────────────────────────────────

class TestContentStatusEnumRegression:
    def test_manual_upload_required_not_removed(self):
        """This status is critical for the export-pack workflow."""
        from content_models import ContentStatusEnum
        assert ContentStatusEnum.MANUAL_UPLOAD_REQUIRED.value == "manual_upload_required"

    def test_repurpose_candidate_present(self):
        from content_models import ContentStatusEnum
        assert ContentStatusEnum.REPURPOSE_CANDIDATE.value == "repurpose_candidate"


# ── Strip Markdown — regression contracts ────────────────────────────────────

class TestStripMdRegression:
    """Exact output contracts — any change breaks quora/forum export packs."""

    def test_bold_stripped_exactly(self):
        from services.social_publisher import _strip_md
        assert _strip_md("**hello world**") == "hello world"

    def test_h2_stripped(self):
        from services.social_publisher import _strip_md
        assert _strip_md("## Section Title") == "Section Title"

    def test_plain_text_unchanged(self):
        from services.social_publisher import _strip_md
        text = "This is plain text with no markdown whatsoever."
        assert _strip_md(text) == text

    def test_link_text_preserved_url_removed(self):
        from services.social_publisher import _strip_md
        assert _strip_md("[click here](https://example.com)") == "click here"


# ── Truncate — regression contracts ──────────────────────────────────────────

class TestTruncateRegression:
    def test_truncated_text_ends_with_ellipsis(self):
        from services.social_publisher import _truncate
        result = _truncate("a" * 100, 50)
        assert result.endswith("...")

    def test_truncated_length_is_exactly_limit(self):
        from services.social_publisher import _truncate
        result = _truncate("a" * 100, 50)
        assert len(result) == 50

    def test_short_text_not_modified(self):
        from services.social_publisher import _truncate
        text = "short"
        assert _truncate(text, 100) == text


# ── AgentExecutor registry — regression contracts ─────────────────────────────

class TestAgentRegistryRegression:
    def test_all_six_agents_registered(self):
        """
        The agent registry must always contain all 6 agents.
        Add to this list when registering new agents.
        """
        from services.agent_executor import AGENT_REGISTRY
        required = {
            "guard-agent", "scout-agent", "content-agent",
            "revenue-agent", "social-agent", "video-agent",
        }
        missing = required - set(AGENT_REGISTRY.keys())
        assert not missing, f"Agents removed from registry: {missing}"

    def test_guard_agent_is_first_sequential(self):
        from services.agent_executor import SEQUENTIAL_PRIORITY_AGENTS
        assert SEQUENTIAL_PRIORITY_AGENTS[0] == "guard-agent"
