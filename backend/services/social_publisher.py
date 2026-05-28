"""
SocialPublisher — Multi-platform autonomous content distribution.

TEXT / ARTICLE platforms (fully auto when credentials set):
  Medium       MEDIUM_INTEGRATION_TOKEN
  Dev.to       DEVTO_API_KEY
  Reddit       REDDIT_CLIENT_ID + REDDIT_CLIENT_SECRET + REDDIT_USERNAME + REDDIT_PASSWORD
               REDDIT_SUBREDDITS  (comma-sep, e.g. "entrepreneur,passive_income")
  Facebook     FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN
  Threads      THREADS_USER_ID + THREADS_ACCESS_TOKEN
  LinkedIn     LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN
  Discourse    DISCOURSE_BASE_URL + DISCOURSE_API_KEY + DISCOURSE_API_USERNAME
               DISCOURSE_CATEGORY_ID  (int, default 1)

VIDEO platforms (auto-post when credentials + video file provided):
  YouTube      YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN
  TikTok       TIKTOK_ACCESS_TOKEN
  Instagram    IG_USER_ID + IG_ACCESS_TOKEN  (also used for image posts)

EXPORT PACK (no API — copy-paste ready text returned):
  Facebook Groups, Quora, niche forums — call export_pack()

Cost Guard: $0. All free-tier APIs.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger("social_publisher")

# ── helpers ────────────────────────────────────────────────────────────────────

def _env(key: str) -> str:
    return (os.environ.get(key) or "").strip()

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def _strip_md(text: str) -> str:
    """Remove Markdown headings/bold/italic for plain-text platforms."""
    text = re.sub(r"#{1,6}\s+", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.S)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text.strip()


# ── result schema ──────────────────────────────────────────────────────────────

class PostResult:
    def __init__(self, platform: str, success: bool, url: str = "", error: str = "", skipped: bool = False):
        self.platform = platform
        self.success = success
        self.url = url
        self.error = error
        self.skipped = skipped   # credentials not configured

    def to_dict(self) -> dict:
        return {
            "platform": self.platform,
            "success": self.success,
            "url": self.url,
            "error": self.error,
            "skipped": self.skipped,
        }


# ── SocialPublisher ────────────────────────────────────────────────────────────

class SocialPublisher:
    """
    Call post_article() for text content (articles, blog posts).
    Call post_video()   for video content (TikTok, YouTube, Reels).
    Call export_pack()  to get formatted copy-paste text for manual platforms.
    """

    # ── TEXT POST DISPATCHER ──────────────────────────────────────────────────

    async def post_article(self, article: dict, platforms: list[str]) -> list[PostResult]:
        """
        article keys: title, body (markdown), slug, meta_description, tags (list[str]),
                      source_url (optional)
        """
        results: list[PostResult] = []
        for platform in platforms:
            try:
                if platform == "medium":
                    results.append(await self._medium(article))
                elif platform == "devto":
                    results.append(await self._devto(article))
                elif platform == "reddit":
                    results.extend(await self._reddit(article))
                elif platform == "facebook":
                    results.append(await self._facebook_page(article))
                elif platform == "threads":
                    results.append(await self._threads(article))
                elif platform == "linkedin":
                    results.append(await self._linkedin(article))
                elif platform in ("discourse", "forum"):
                    results.append(await self._discourse(article))
                elif platform == "instagram":
                    results.append(PostResult("instagram", False, skipped=True,
                                              error="Instagram requires image/video. Use post_video() or export_pack()."))
                elif platform == "tiktok":
                    results.append(PostResult("tiktok", False, skipped=True,
                                              error="TikTok requires video file. Use post_video() or export_pack()."))
                elif platform == "youtube":
                    results.append(PostResult("youtube", False, skipped=True,
                                              error="YouTube requires video file. Use post_video() or export_pack()."))
                else:
                    results.append(PostResult(platform, False, skipped=True,
                                              error=f"Platform '{platform}' not supported for text posts."))
            except Exception as exc:
                logger.exception("social_publisher: %s failed", platform)
                results.append(PostResult(platform, False, error=str(exc)))
        return results

    # ── VIDEO POST DISPATCHER ─────────────────────────────────────────────────

    async def post_video(self, video_path: str, meta: dict, platforms: list[str]) -> list[PostResult]:
        """
        meta keys: title, description, tags (list[str]), privacy (public/private),
                   made_for_kids (bool), category_id (YouTube int)
        """
        results: list[PostResult] = []
        for platform in platforms:
            try:
                if platform == "youtube":
                    results.append(await self._youtube(video_path, meta))
                elif platform == "tiktok":
                    results.append(await self._tiktok(video_path, meta))
                elif platform == "instagram":
                    results.append(await self._instagram_video(video_path, meta))
                else:
                    results.append(PostResult(platform, False, skipped=True,
                                              error=f"'{platform}' is not a video platform."))
            except Exception as exc:
                logger.exception("social_publisher video: %s failed", platform)
                results.append(PostResult(platform, False, error=str(exc)))
        return results

    # ── EXPORT PACK (no API required) ─────────────────────────────────────────

    def export_pack(self, article: dict, platforms: list[str] | None = None) -> dict:
        """
        Returns formatted copy-paste text for every manual platform.
        Use for: Facebook Groups, Quora, niche forums, any platform without API.
        """
        title = article.get("title", "")
        body  = _strip_md(article.get("body", ""))
        tags  = article.get("tags", [])
        url   = article.get("source_url", "")
        desc  = article.get("meta_description", "")
        hashtags = " ".join(f"#{t}" for t in tags[:5])

        pack: dict[str, Any] = {}

        # Facebook Groups — conversational, no hashtags
        if not platforms or "facebook_groups" in platforms:
            pack["facebook_groups"] = {
                "title": title,
                "body": f"{title}\n\n{body[:1500]}\n\n{url}".strip(),
                "note": "Paste as a post in your Facebook Group. Remove the URL if group rules require it.",
            }

        # Quora — answer-format, authoritative
        if not platforms or "quora" in platforms:
            intro = f"Great question. Here's what I've found:\n\n"
            pack["quora"] = {
                "title": f"Answer about: {title}",
                "body": f"{intro}{body[:2000]}\n\n{hashtags}",
                "note": "Find a related Quora question and paste as your answer. Add your credentials in your profile.",
            }

        # Niche forums / Discourse — structured post
        if not platforms or "forum" in platforms:
            pack["forum"] = {
                "title": title,
                "body": f"{desc}\n\n{body[:3000]}\n\n---\n{hashtags}",
                "note": "Works for Reddit, Discourse forums, niche community boards.",
            }

        # TikTok / YouTube Shorts script pack
        if not platforms or "tiktok_script" in platforms:
            sentences = [s.strip() for s in re.split(r"[.!?]+", body) if len(s.strip()) > 20]
            hook = sentences[0] if sentences else title
            pack["video_script"] = {
                "hook": hook[:100],
                "title": title,
                "caption": f"{title}\n\n{desc}\n\n{hashtags}",
                "hashtags": hashtags,
                "script_outline": "\n".join(f"• {s}" for s in sentences[:8]),
                "note": (
                    "1. Film/edit in CapCut using this script.\n"
                    "2. Save as vertical 9:16 video.\n"
                    "3. Upload via dashboard → Publishing → mark as posted."
                ),
            }

        # Instagram caption
        if not platforms or "instagram_caption" in platforms:
            pack["instagram_caption"] = {
                "caption": f"{title}\n\n{desc}\n\n{hashtags}",
                "note": "Create an image or short video in CapCut. Use this as the caption.",
            }

        pack["generated_at"] = _now()
        pack["article_title"] = title
        return pack

    # ─────────────────────────────────────────────────────────────────────────
    # PLATFORM IMPLEMENTATIONS
    # ─────────────────────────────────────────────────────────────────────────

    # ── Medium ────────────────────────────────────────────────────────────────
    async def _medium(self, article: dict) -> PostResult:
        token = _env("MEDIUM_INTEGRATION_TOKEN")
        if not token:
            return PostResult("medium", False, skipped=True, error="MEDIUM_INTEGRATION_TOKEN not set")

        async with httpx.AsyncClient(timeout=20) as c:
            # Get user ID
            me = await c.get(
                "https://api.medium.com/v1/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            me.raise_for_status()
            user_id = me.json()["data"]["id"]

            body_md = article.get("body", "")
            meta = article.get("meta_description", "")
            if meta:
                body_md = f"> {meta}\n\n{body_md}"

            payload = {
                "title": article.get("title", ""),
                "contentFormat": "markdown",
                "content": body_md,
                "tags": article.get("tags", [])[:5],
                "publishStatus": "public",
            }
            src_url = article.get("source_url")
            if src_url:
                payload["canonicalUrl"] = src_url

            r = await c.post(
                f"https://api.medium.com/v1/users/{user_id}/posts",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            data = r.json()["data"]
            url = data.get("url", "")
            logger.info("Medium posted: %s", url)
            return PostResult("medium", True, url=url)

    # ── Dev.to ────────────────────────────────────────────────────────────────
    async def _devto(self, article: dict) -> PostResult:
        key = _env("DEVTO_API_KEY")
        if not key:
            return PostResult("devto", False, skipped=True, error="DEVTO_API_KEY not set")

        body_md = article.get("body", "")
        meta = article.get("meta_description", "")
        if meta:
            body_md = f"> {meta}\n\n{body_md}"

        payload: dict[str, Any] = {
            "article": {
                "title": article.get("title", ""),
                "published": True,
                "body_markdown": body_md,
                "tags": article.get("tags", [])[:4],
            }
        }
        src_url = article.get("source_url")
        if src_url:
            payload["article"]["canonical_url"] = src_url

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://dev.to/api/articles",
                headers={"api-key": key, "Content-Type": "application/json"},
                json=payload,
            )
            r.raise_for_status()
            url = r.json().get("url", "")
            logger.info("Dev.to posted: %s", url)
            return PostResult("devto", True, url=url)

    # ── Reddit ────────────────────────────────────────────────────────────────
    async def _reddit(self, article: dict) -> list[PostResult]:
        client_id     = _env("REDDIT_CLIENT_ID")
        client_secret = _env("REDDIT_CLIENT_SECRET")
        username      = _env("REDDIT_USERNAME")
        password      = _env("REDDIT_PASSWORD")
        subreddits    = [s.strip() for s in _env("REDDIT_SUBREDDITS").split(",") if s.strip()]

        if not (client_id and client_secret and username and password):
            return [PostResult("reddit", False, skipped=True,
                               error="REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD not set")]
        if not subreddits:
            subreddits = ["test"]

        # Get OAuth token
        async with httpx.AsyncClient(timeout=20) as c:
            tok_r = await c.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=(client_id, client_secret),
                data={"grant_type": "password", "username": username, "password": password},
                headers={"User-Agent": "AlreadyHereCmdOS/1.0"},
            )
            tok_r.raise_for_status()
            access_token = tok_r.json()["access_token"]

            results = []
            for sub in subreddits[:3]:  # max 3 subreddits per run
                try:
                    body_text = _strip_md(article.get("body", ""))[:40000]
                    r = await c.post(
                        "https://oauth.reddit.com/api/submit",
                        headers={
                            "Authorization": f"bearer {access_token}",
                            "User-Agent": "AlreadyHereCmdOS/1.0",
                        },
                        data={
                            "api_type": "json",
                            "kind": "self",
                            "sr": sub,
                            "title": article.get("title", "")[:300],
                            "text": body_text,
                            "resubmit": "true",
                        },
                    )
                    r.raise_for_status()
                    resp = r.json()
                    errors = resp.get("json", {}).get("errors", [])
                    if errors:
                        results.append(PostResult(f"reddit/{sub}", False, error=str(errors)))
                    else:
                        post_url = resp.get("json", {}).get("data", {}).get("url", "")
                        logger.info("Reddit r/%s posted: %s", sub, post_url)
                        results.append(PostResult(f"reddit/{sub}", True, url=post_url))
                except Exception as e:
                    results.append(PostResult(f"reddit/{sub}", False, error=str(e)))
            return results

    # ── Facebook Page ─────────────────────────────────────────────────────────
    async def _facebook_page(self, article: dict) -> PostResult:
        page_id    = _env("FB_PAGE_ID")
        page_token = _env("FB_PAGE_ACCESS_TOKEN")
        if not (page_id and page_token):
            return PostResult("facebook", False, skipped=True,
                              error="FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN not set. See setup guide.")

        title  = article.get("title", "")
        desc   = article.get("meta_description", "")
        tags   = article.get("tags", [])
        src    = article.get("source_url", "")
        body   = _strip_md(article.get("body", ""))[:500]
        hashtags = " ".join(f"#{t}" for t in tags[:5])
        message  = f"{title}\n\n{desc or body}\n\n{hashtags}".strip()

        payload: dict[str, Any] = {"message": message, "access_token": page_token}
        if src:
            payload["link"] = src

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                f"https://graph.facebook.com/v19.0/{page_id}/feed",
                json=payload,
            )
            r.raise_for_status()
            post_id = r.json().get("id", "")
            url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}" if post_id else ""
            logger.info("Facebook Page posted: %s", url)
            return PostResult("facebook", True, url=url)

    # ── Threads ───────────────────────────────────────────────────────────────
    async def _threads(self, article: dict) -> PostResult:
        user_id = _env("THREADS_USER_ID")
        token   = _env("THREADS_ACCESS_TOKEN")
        if not (user_id and token):
            return PostResult("threads", False, skipped=True,
                              error="THREADS_USER_ID + THREADS_ACCESS_TOKEN not set. See setup guide.")

        title = article.get("title", "")
        desc  = article.get("meta_description", "")
        tags  = article.get("tags", [])
        src   = article.get("source_url", "")
        hashtags = " ".join(f"#{t}" for t in tags[:5])
        text = _truncate(f"{title}\n\n{desc}\n\n{hashtags}", 500)

        async with httpx.AsyncClient(timeout=20) as c:
            # Step 1: create container
            create_r = await c.post(
                f"https://graph.threads.net/v1.0/{user_id}/threads",
                params={
                    "media_type": "TEXT",
                    "text": text,
                    "access_token": token,
                },
            )
            create_r.raise_for_status()
            creation_id = create_r.json()["id"]

            # Step 2: publish
            pub_r = await c.post(
                f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
                params={"creation_id": creation_id, "access_token": token},
            )
            pub_r.raise_for_status()
            thread_id = pub_r.json().get("id", "")
            url = f"https://www.threads.net/t/{thread_id}" if thread_id else ""
            logger.info("Threads posted: %s", url)
            return PostResult("threads", True, url=url)

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    async def _linkedin(self, article: dict) -> PostResult:
        token      = _env("LINKEDIN_ACCESS_TOKEN")
        author_urn = _env("LINKEDIN_PERSON_URN")   # e.g. urn:li:person:ABC123
        if not (token and author_urn):
            return PostResult("linkedin", False, skipped=True,
                              error="LINKEDIN_ACCESS_TOKEN + LINKEDIN_PERSON_URN not set. See setup guide.")

        title = article.get("title", "")
        desc  = article.get("meta_description", "")
        src   = article.get("source_url", "")
        tags  = article.get("tags", [])
        hashtags = " ".join(f"#{t}" for t in tags[:5])
        text = f"{title}\n\n{desc}\n\n{hashtags}".strip()

        payload: dict[str, Any] = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": _truncate(text, 3000)},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        if src:
            payload["specificContent"]["com.linkedin.ugc.ShareContent"].update({
                "shareMediaCategory": "ARTICLE",
                "media": [{"status": "READY", "originalUrl": src,
                           "title": {"text": title}, "description": {"text": desc or title}}],
            })

        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                json=payload,
            )
            r.raise_for_status()
            post_id = r.headers.get("x-restli-id", "")
            url = f"https://www.linkedin.com/feed/update/{post_id}" if post_id else ""
            logger.info("LinkedIn posted: %s", url)
            return PostResult("linkedin", True, url=url)

    # ── Discourse (niche forums) ───────────────────────────────────────────────
    async def _discourse(self, article: dict) -> PostResult:
        base     = _env("DISCOURSE_BASE_URL").rstrip("/")
        api_key  = _env("DISCOURSE_API_KEY")
        api_user = _env("DISCOURSE_API_USERNAME")
        cat_id   = int(_env("DISCOURSE_CATEGORY_ID") or "1")
        if not (base and api_key and api_user):
            return PostResult("discourse", False, skipped=True,
                              error="DISCOURSE_BASE_URL + DISCOURSE_API_KEY + DISCOURSE_API_USERNAME not set.")

        body_raw = article.get("body", "")[:32000]
        payload = {
            "title": article.get("title", "")[:255],
            "raw": body_raw,
            "category": cat_id,
        }

        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"{base}/posts.json",
                headers={
                    "Api-Key": api_key,
                    "Api-Username": api_user,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
            topic_slug = data.get("topic_slug", "")
            topic_id   = data.get("topic_id", "")
            url = f"{base}/t/{topic_slug}/{topic_id}" if topic_slug else f"{base}/t/{topic_id}"
            logger.info("Discourse posted: %s", url)
            return PostResult("discourse", True, url=url)

    # ─────────────────────────────────────────────────────────────────────────
    # VIDEO PLATFORMS
    # ─────────────────────────────────────────────────────────────────────────

    # ── YouTube ───────────────────────────────────────────────────────────────
    async def _youtube(self, video_path: str, meta: dict) -> PostResult:
        client_id     = _env("YOUTUBE_CLIENT_ID")
        client_secret = _env("YOUTUBE_CLIENT_SECRET")
        refresh_token = _env("YOUTUBE_REFRESH_TOKEN")
        if not (client_id and client_secret and refresh_token):
            return PostResult("youtube", False, skipped=True,
                              error="YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN not set.")

        # Exchange refresh token for access token
        async with httpx.AsyncClient(timeout=30) as c:
            tok_r = await c.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            tok_r.raise_for_status()
            access_token = tok_r.json()["access_token"]

            # Resumable upload
            title       = meta.get("title", "")[:100]
            description = meta.get("description", "")[:5000]
            tags        = meta.get("tags", [])[:500]
            category_id = str(meta.get("category_id", "22"))  # 22 = People & Blogs
            privacy     = meta.get("privacy", "public")

            snippet = {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            }
            status = {"privacyStatus": privacy, "madeForKids": meta.get("made_for_kids", False)}

            # Initiate resumable upload
            init_r = await c.post(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "X-Upload-Content-Type": "video/*",
                },
                json={"snippet": snippet, "status": status},
            )
            init_r.raise_for_status()
            upload_url = init_r.headers["Location"]

            # Upload video file
            with open(video_path, "rb") as f:
                video_data = f.read()

            up_r = await c.put(
                upload_url,
                headers={"Content-Type": "video/*"},
                content=video_data,
                timeout=300,
            )
            up_r.raise_for_status()
            video_id = up_r.json().get("id", "")
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            logger.info("YouTube uploaded: %s", url)
            return PostResult("youtube", True, url=url)

    # ── TikTok ────────────────────────────────────────────────────────────────
    async def _tiktok(self, video_path: str, meta: dict) -> PostResult:
        access_token = _env("TIKTOK_ACCESS_TOKEN")
        if not access_token:
            return PostResult("tiktok", False, skipped=True,
                              error="TIKTOK_ACCESS_TOKEN not set. See setup guide.")

        title = meta.get("title", "")[:150]
        caption = meta.get("description", title)[:2200]
        tags = meta.get("tags", [])
        hashtags = " ".join(f"#{t}" for t in tags[:5])
        full_caption = f"{caption}\n\n{hashtags}".strip()

        async with httpx.AsyncClient(timeout=60) as c:
            # Step 1: Init upload
            init_r = await c.post(
                "https://open.tiktokapis.com/v2/post/publish/video/init/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json={
                    "post_info": {
                        "title": full_caption,
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": os.path.getsize(video_path),
                        "chunk_size": os.path.getsize(video_path),
                        "total_chunk_count": 1,
                    },
                },
            )
            init_r.raise_for_status()
            data = init_r.json().get("data", {})
            publish_id  = data.get("publish_id", "")
            upload_url  = data.get("upload_url", "")

            if not upload_url:
                return PostResult("tiktok", False, error="TikTok did not return upload_url")

            # Step 2: Upload video
            with open(video_path, "rb") as f:
                video_bytes = f.read()

            up_r = await c.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes 0-{len(video_bytes)-1}/{len(video_bytes)}",
                },
                content=video_bytes,
                timeout=300,
            )
            up_r.raise_for_status()
            logger.info("TikTok uploaded publish_id=%s", publish_id)
            return PostResult("tiktok", True, url=f"https://www.tiktok.com/ (publish_id={publish_id})")

    # ── Instagram video/image ─────────────────────────────────────────────────
    async def _instagram_video(self, video_path: str, meta: dict) -> PostResult:
        ig_user_id   = _env("IG_USER_ID")
        access_token = _env("IG_ACCESS_TOKEN")
        if not (ig_user_id and access_token):
            return PostResult("instagram", False, skipped=True,
                              error="IG_USER_ID + IG_ACCESS_TOKEN not set. See setup guide.")

        caption = meta.get("description", meta.get("title", ""))
        tags    = meta.get("tags", [])
        hashtags = " ".join(f"#{t}" for t in tags[:30])
        full_caption = f"{caption}\n\n{hashtags}".strip()[:2200]

        # Instagram requires a publicly accessible video URL, not a file upload
        video_url = meta.get("video_url", "")
        if not video_url:
            return PostResult("instagram", False,
                              error="Instagram requires a public video URL (video_url in meta). Upload video to your server first.")

        async with httpx.AsyncClient(timeout=60) as c:
            # Step 1: create media container (Reels)
            create_r = await c.post(
                f"https://graph.facebook.com/v19.0/{ig_user_id}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": full_caption,
                    "access_token": access_token,
                },
            )
            create_r.raise_for_status()
            creation_id = create_r.json()["id"]

            # Wait for processing (poll up to 60s)
            import asyncio
            for _ in range(12):
                await asyncio.sleep(5)
                status_r = await c.get(
                    f"https://graph.facebook.com/v19.0/{creation_id}",
                    params={"fields": "status_code", "access_token": access_token},
                )
                status_code = status_r.json().get("status_code", "")
                if status_code == "FINISHED":
                    break
                if status_code == "ERROR":
                    return PostResult("instagram", False, error="Instagram media processing failed")

            # Step 2: publish
            pub_r = await c.post(
                f"https://graph.facebook.com/v19.0/{ig_user_id}/media_publish",
                params={"creation_id": creation_id, "access_token": access_token},
            )
            pub_r.raise_for_status()
            media_id = pub_r.json().get("id", "")
            url = f"https://www.instagram.com/p/{media_id}/" if media_id else ""
            logger.info("Instagram Reel posted: %s", url)
            return PostResult("instagram", True, url=url)


# ── Singleton ─────────────────────────────────────────────────────────────────
_publisher: SocialPublisher | None = None

def get_publisher() -> SocialPublisher:
    global _publisher
    if _publisher is None:
        _publisher = SocialPublisher()
    return _publisher


# ── Credential checker (for dashboard status) ─────────────────────────────────
def connector_status() -> dict:
    """Returns which connectors are configured. Safe to call anytime."""
    def chk(*keys: str) -> bool:
        return all(bool(_env(k)) for k in keys)

    return {
        "medium":     {"configured": chk("MEDIUM_INTEGRATION_TOKEN"),      "type": "text"},
        "devto":      {"configured": chk("DEVTO_API_KEY"),                  "type": "text"},
        "reddit":     {"configured": chk("REDDIT_CLIENT_ID","REDDIT_CLIENT_SECRET","REDDIT_USERNAME","REDDIT_PASSWORD"), "type": "text"},
        "facebook":   {"configured": chk("FB_PAGE_ID","FB_PAGE_ACCESS_TOKEN"), "type": "text"},
        "threads":    {"configured": chk("THREADS_USER_ID","THREADS_ACCESS_TOKEN"), "type": "text"},
        "linkedin":   {"configured": chk("LINKEDIN_ACCESS_TOKEN","LINKEDIN_PERSON_URN"), "type": "text"},
        "discourse":  {"configured": chk("DISCOURSE_BASE_URL","DISCOURSE_API_KEY","DISCOURSE_API_USERNAME"), "type": "text"},
        "youtube":    {"configured": chk("YOUTUBE_CLIENT_ID","YOUTUBE_CLIENT_SECRET","YOUTUBE_REFRESH_TOKEN"), "type": "video"},
        "tiktok":     {"configured": chk("TIKTOK_ACCESS_TOKEN"),            "type": "video"},
        "instagram":  {"configured": chk("IG_USER_ID","IG_ACCESS_TOKEN"),   "type": "video"},
    }
