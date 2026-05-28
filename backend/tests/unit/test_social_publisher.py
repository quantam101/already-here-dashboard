"""
Unit tests for SocialPublisher.

All HTTP calls are mocked via pytest-monkeypatch + unittest.mock.
No network. No credentials required. Runs in < 1 second.
"""
from __future__ import annotations

import sys
import os
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.social_publisher import SocialPublisher, PostResult, connector_status, _strip_md, _truncate


# ── helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    """Run an async coroutine in tests. Uses asyncio.run() (Python 3.7+)."""
    return asyncio.run(coro)


SAMPLE_ARTICLE = {
    "title": "Test Article Title",
    "body": "This is the article body. It has **bold** text and *italic* text. [link](https://example.com)",
    "meta_description": "Short meta description",
    "tags": ["ai", "automation", "business"],
    "source_url": "https://example.com/source",
    "slug": "test-article",
}


# ── _strip_md ─────────────────────────────────────────────────────────────────

class TestStripMd:
    def test_removes_bold(self):
        assert _strip_md("**bold text**") == "bold text"

    def test_removes_italic(self):
        assert _strip_md("*italic*") == "italic"

    def test_removes_headings(self):
        assert _strip_md("## Heading") == "Heading"
        assert _strip_md("# H1") == "H1"

    def test_removes_links(self):
        assert _strip_md("[click here](https://example.com)") == "click here"

    def test_removes_inline_code(self):
        assert _strip_md("`code`") == "code"

    def test_passthrough_plain_text(self):
        text = "Plain text with no markdown."
        assert _strip_md(text) == text

    def test_strips_combined(self):
        result = _strip_md("## Title\n**bold** and *italic* with [link](url)")
        assert "##" not in result
        assert "**" not in result
        assert "*italic*" not in result


# ── _truncate ─────────────────────────────────────────────────────────────────

class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 100) == "hello"

    def test_long_text_truncated(self):
        result = _truncate("a" * 200, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        text = "a" * 50
        assert _truncate(text, 50) == text


# ── export_pack ───────────────────────────────────────────────────────────────

class TestExportPack:
    def setup_method(self):
        self.pub = SocialPublisher()

    def test_contains_all_keys(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        assert "facebook_groups" in pack
        assert "quora" in pack
        assert "forum" in pack
        assert "video_script" in pack
        assert "instagram_caption" in pack
        assert "generated_at" in pack
        assert "article_title" in pack

    def test_facebook_groups_body_contains_title(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        assert SAMPLE_ARTICLE["title"] in pack["facebook_groups"]["body"]

    def test_video_script_has_hook(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        assert pack["video_script"]["hook"]

    def test_video_script_has_capcut_note(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        note = pack["video_script"]["note"]
        assert "CapCut" in note

    def test_quora_body_has_intro(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        assert "Great question" in pack["quora"]["body"]

    def test_instagram_caption_has_hashtags(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE)
        caption = pack["instagram_caption"]["caption"]
        assert "#" in caption

    def test_platform_filter(self):
        pack = self.pub.export_pack(SAMPLE_ARTICLE, platforms=["facebook_groups"])
        assert "facebook_groups" in pack
        assert "quora" not in pack
        assert "forum" not in pack

    def test_empty_body_safe(self):
        """export_pack must not crash on minimal article."""
        pack = self.pub.export_pack({"title": "T", "body": "", "tags": []})
        assert pack["article_title"] == "T"

    def test_long_body_truncated_per_platform(self):
        long_body = "word " * 2000
        pack = self.pub.export_pack({"title": "T", "body": long_body, "tags": []})
        assert len(pack["facebook_groups"]["body"]) <= 2000


# ── connector_status ──────────────────────────────────────────────────────────

class TestConnectorStatus:
    def test_returns_dict(self, clean_env):
        status = connector_status()
        assert isinstance(status, dict)

    def test_medium_not_configured_when_no_token(self, clean_env):
        status = connector_status()
        assert status.get("medium", {}).get("configured") is False

    def test_medium_configured_when_token_set(self, clean_env, monkeypatch):
        monkeypatch.setenv("MEDIUM_INTEGRATION_TOKEN", "test-token-123")
        status = connector_status()
        assert status.get("medium", {}).get("configured") is True

    def test_reddit_requires_all_four_vars(self, clean_env, monkeypatch):
        # Only client_id set — should NOT be configured
        monkeypatch.setenv("REDDIT_CLIENT_ID", "abc")
        status = connector_status()
        assert status.get("reddit", {}).get("configured") is False

    def test_reddit_configured_when_all_vars_set(self, clean_env, monkeypatch):
        monkeypatch.setenv("REDDIT_CLIENT_ID", "abc")
        monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
        monkeypatch.setenv("REDDIT_USERNAME", "user")
        monkeypatch.setenv("REDDIT_PASSWORD", "pass")
        status = connector_status()
        assert status.get("reddit", {}).get("configured") is True

    def test_all_platforms_present(self, clean_env):
        status = connector_status()
        expected = {"medium", "devto", "reddit", "facebook", "threads", "linkedin",
                    "youtube", "tiktok", "instagram", "discourse"}
        assert expected.issubset(set(status.keys()))


# ── _medium (mocked HTTP) ─────────────────────────────────────────────────────

class TestMediumPost:
    def setup_method(self):
        self.pub = SocialPublisher()

    def test_skips_when_no_token(self, clean_env):
        result = run(self.pub._medium(SAMPLE_ARTICLE))
        assert result.skipped is True
        assert result.success is False
        assert "MEDIUM_INTEGRATION_TOKEN" in result.error

    def test_posts_successfully_with_valid_token(self, clean_env, monkeypatch):
        monkeypatch.setenv("MEDIUM_INTEGRATION_TOKEN", "tok-123")

        # Mock httpx.AsyncClient
        mock_me_response = MagicMock()
        mock_me_response.raise_for_status = MagicMock()
        mock_me_response.json.return_value = {"data": {"id": "user-abc"}}

        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json.return_value = {"data": {"url": "https://medium.com/@user/test-post"}}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_me_response)
        mock_client.post = AsyncMock(return_value=mock_post_response)

        with patch("services.social_publisher.httpx.AsyncClient", return_value=mock_client):
            result = run(self.pub._medium(SAMPLE_ARTICLE))

        assert result.success is True
        assert "medium.com" in result.url
        assert result.skipped is False

    def test_returns_error_on_http_failure(self, clean_env, monkeypatch):
        monkeypatch.setenv("MEDIUM_INTEGRATION_TOKEN", "tok-bad")

        import httpx as _httpx

        mock_me_response = MagicMock()
        mock_me_response.raise_for_status.side_effect = _httpx.HTTPStatusError(
            "401", request=MagicMock(), response=MagicMock()
        )

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_me_response)

        with patch("services.social_publisher.httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(Exception):
                run(self.pub._medium(SAMPLE_ARTICLE))


# ── _devto (mocked HTTP) ──────────────────────────────────────────────────────

class TestDevtoPost:
    def setup_method(self):
        self.pub = SocialPublisher()

    def test_skips_when_no_key(self, clean_env):
        result = run(self.pub._devto(SAMPLE_ARTICLE))
        assert result.skipped is True
        assert "DEVTO_API_KEY" in result.error

    def test_posts_successfully(self, clean_env, monkeypatch):
        monkeypatch.setenv("DEVTO_API_KEY", "devto-key-123")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"url": "https://dev.to/user/test-post"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("services.social_publisher.httpx.AsyncClient", return_value=mock_client):
            result = run(self.pub._devto(SAMPLE_ARTICLE))

        assert result.success is True
        assert "dev.to" in result.url


# ── _facebook_page (mocked HTTP) ─────────────────────────────────────────────

class TestFacebookPagePost:
    def setup_method(self):
        self.pub = SocialPublisher()

    def test_skips_when_no_credentials(self, clean_env):
        result = run(self.pub._facebook_page(SAMPLE_ARTICLE))
        assert result.skipped is True

    def test_posts_successfully(self, clean_env, monkeypatch):
        monkeypatch.setenv("FB_PAGE_ID", "123456")
        monkeypatch.setenv("FB_PAGE_ACCESS_TOKEN", "page-token-abc")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"id": "123456_7890"}

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("services.social_publisher.httpx.AsyncClient", return_value=mock_client):
            result = run(self.pub._facebook_page(SAMPLE_ARTICLE))

        assert result.success is True
        assert "facebook.com" in result.url


# ── post_article dispatcher ───────────────────────────────────────────────────

class TestPostArticleDispatcher:
    def setup_method(self):
        self.pub = SocialPublisher()

    def test_video_platforms_are_skipped(self, clean_env):
        """TikTok / YouTube / Instagram skip gracefully in post_article()."""
        results = run(self.pub.post_article(SAMPLE_ARTICLE, ["tiktok", "youtube", "instagram"]))
        for r in results:
            assert r.skipped is True, f"{r.platform} should be skipped in post_article"

    def test_unknown_platform_skipped(self, clean_env):
        results = run(self.pub.post_article(SAMPLE_ARTICLE, ["unknown_platform"]))
        assert results[0].skipped is True

    def test_all_platforms_skipped_when_no_creds(self, clean_env):
        platforms = ["medium", "devto", "reddit", "facebook", "threads", "linkedin", "discourse"]
        results = run(self.pub.post_article(SAMPLE_ARTICLE, platforms))
        skipped = [r for r in results if r.skipped]
        # All should be skipped (no credentials in clean_env)
        assert len(skipped) == len(results)

    def test_empty_platform_list_returns_empty(self, clean_env):
        results = run(self.pub.post_article(SAMPLE_ARTICLE, []))
        assert results == []
