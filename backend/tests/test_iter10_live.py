"""Iteration 10 live-API checks against the public REACT_APP_BACKEND_URL.

Covers:
- /api/video/config exposes music_tracks_available + adaptive_captions_available
- /api/video/music returns 3 CC0 beds with default_volume
- /api/video/render accepts music + adaptive_captions and completes
- /api/hooks/ falls back to deterministic template on quota exhaustion (or returns LLM)
- /api/hooks/ab-test returns used_fallback and never 502 on quota
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gmaos-control.preview.emergentagent.com").rstrip("/")


# ---------- Video config / music catalogue ----------
class TestVideoConfig:
    def test_config_exposes_new_fields(self):
        r = requests.get(f"{BASE_URL}/api/video/config", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "music_tracks_available" in data
        assert "adaptive_captions_available" in data
        assert isinstance(data["music_tracks_available"], list)
        ids = {t if isinstance(t, str) else t.get("id") for t in data["music_tracks_available"]}
        assert {"cinematic", "upbeat", "chill"}.issubset(ids), data["music_tracks_available"]
        assert data["adaptive_captions_available"] is True

    def test_music_endpoint(self):
        r = requests.get(f"{BASE_URL}/api/video/music", timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "available" in data and "default_volume" in data
        assert isinstance(data["default_volume"], (int, float))
        avail = data["available"]
        assert len(avail) == 3
        for t in avail:
            assert "id" in t and "label" in t and "size_kb" in t
            # size_kb may be str or int — coerce
            assert int(t["size_kb"]) > 0
        ids = {t["id"] for t in avail}
        assert ids == {"cinematic", "upbeat", "chill"}


# ---------- Video render with music + adaptive captions ----------
class TestVideoRender:
    def test_render_with_music_and_adaptive_captions(self):
        payload = {
            "script": {
                "hook": "Stop wasting money today.",
                "script_body": "Welcome to the test render. This validates music and adaptive captions.",
                "cta": "Subscribe for more.",
                "shot_list": [],
            },
            "voice_id": None,
            "music_id": "cinematic",
            "music_volume": 0.2,
            "adaptive_captions": True,
        }
        r = requests.post(f"{BASE_URL}/api/video/render", json=payload, timeout=30)
        assert r.status_code in (200, 201, 202), r.text
        job = r.json()
        job_id = job.get("id") or job.get("job_id")
        assert job_id, job

        # Poll for completion (faster-whisper ~10-15s)
        complete = None
        for _ in range(40):
            time.sleep(2)
            s = requests.get(f"{BASE_URL}/api/video/jobs/{job_id}", timeout=15)
            if s.status_code != 200:
                continue
            jd = s.json()
            if jd.get("status") in ("complete", "completed", "failed", "error"):
                complete = jd
                break
        assert complete is not None, f"Render never finished: last poll {s.text}"
        assert complete["status"] in ("complete", "completed"), complete
        assert complete.get("output_path"), complete
        # Job response exposes music_id + adaptive_captions directly; manifest file
        # is persisted on disk alongside the MP4 (see engine.py write_manifest).
        assert complete.get("music_id") == "cinematic", complete
        assert complete.get("adaptive_captions") is True, complete
        # Verify the on-disk manifest matches if exposed
        manifest = complete.get("manifest") or {}
        if manifest:
            assert manifest.get("music_id") == "cinematic", manifest
            assert manifest.get("adaptive_captions_used") is True, manifest


# ---------- Hooks: LLM or deterministic fallback ----------
class TestHooks:
    def test_hooks_returns_variants_or_fallback(self):
        r = requests.post(
            f"{BASE_URL}/api/hooks/",
            json={"topic": "Free productivity tips", "count": 3},
            timeout=60,
        )
        # Must return 200 either via real LLM or fallback template
        assert r.status_code == 200, r.text
        data = r.json()
        variants = data.get("variants") or data.get("hooks") or []
        assert isinstance(variants, list) and len(variants) >= 1, data

    def test_ab_test_never_502_and_reports_fallback(self):
        r = requests.post(
            f"{BASE_URL}/api/hooks/ab-test",
            json={"topic": "Free productivity tips", "count": 3},
            timeout=120,
        )
        assert r.status_code != 502, r.text
        assert r.status_code == 200, r.text
        data = r.json()
        assert "used_fallback" in data, data
        assert isinstance(data["used_fallback"], bool)
        # Should kick off `count` video jobs (field name: job_ids)
        jobs = data.get("job_ids") or data.get("jobs") or data.get("video_jobs") or data.get("renders") or []
        assert isinstance(jobs, list)
        assert len(jobs) == 3, data
