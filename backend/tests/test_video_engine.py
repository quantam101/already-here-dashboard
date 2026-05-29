"""Integration tests for the Video Engine endpoints.

Render-pipeline runs are short (~8s) but we still don't block the whole test
suite on a full render — we exercise the API surface and verify the engine
correctly reports capabilities, validates inputs, manages job state, and
refuses scaffolded modes (avatar_lipsync, external_provider).
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    yield s


class TestVideoEngine:
    def test_config_shape(self, api):
        r = api.get(f"{BASE_URL}/api/video/config")
        assert r.status_code == 200
        d = r.json()
        for k in ("ffmpeg_installed", "piper_installed", "voices_installed",
                  "pexels_api_key_set", "modes_available", "operator_actions"):
            assert k in d, f"missing {k}"
        # modes_available is the contract surface the UI relies on
        for m in ("faceless", "avatar_lipsync", "external_provider"):
            assert m in d["modes_available"]
        # Phase-2/3 modes are NOT yet implemented — they MUST be false
        assert d["modes_available"]["avatar_lipsync"] is False
        assert d["modes_available"]["external_provider"] is False

    def test_voices_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/video/voices")
        assert r.status_code == 200
        d = r.json()
        assert "installed" in d and "default" in d
        assert isinstance(d["installed"], list)

    def test_render_rejects_avatar_lipsync(self, api):
        # Phase-2 mode is scaffolded — must 501 with operator guidance
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {"hook": "x", "script_body": "x", "cta": "x", "shot_list": ["a"]},
            "mode": "avatar_lipsync",
        })
        assert r.status_code == 501, r.text
        assert "scaffolded" in r.text.lower()

    def test_render_rejects_external_provider(self, api):
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {"hook": "x", "script_body": "x", "cta": "x", "shot_list": ["a"]},
            "mode": "external_provider",
        })
        assert r.status_code == 501, r.text

    def test_render_rejects_unknown_mode(self, api):
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {"hook": "x", "script_body": "x", "cta": "x", "shot_list": ["a"]},
            "mode": "nonexistent",
        })
        assert r.status_code == 400

    def test_jobs_list_returns_array(self, api):
        r = api.get(f"{BASE_URL}/api/video/jobs?limit=5")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_job_404_for_missing_id(self, api):
        r = api.get(f"{BASE_URL}/api/video/jobs/vid-doesnotexist123")
        assert r.status_code == 404

    def test_download_404_for_missing_id(self, api):
        r = api.get(f"{BASE_URL}/api/video/jobs/vid-doesnotexist123/download")
        assert r.status_code == 404

    def test_full_render_pipeline(self, api):
        """End-to-end: kick off a tiny render, poll until complete, verify MP4."""
        config = api.get(f"{BASE_URL}/api/video/config").json()
        if not config["modes_available"]["faceless"]:
            pytest.skip("faceless mode not available on this host")
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {
                "hook": "Hello world",
                "script_body": "Pytest smoke",
                "cta": "Done",
                "shot_list": ["test scene"],
            },
        })
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        # Poll up to 45s
        deadline = time.time() + 45
        status = None
        while time.time() < deadline:
            j = api.get(f"{BASE_URL}/api/video/jobs/{job_id}").json()
            status = j["status"]
            if status in ("complete", "failed"):
                break
            time.sleep(2)
        assert status == "complete", f"job ended with status={status}: {j.get('error')}"

        # Download endpoint must serve the MP4
        d = api.get(f"{BASE_URL}/api/video/jobs/{job_id}/download")
        assert d.status_code == 200
        assert d.headers.get("content-type") == "video/mp4"
        assert len(d.content) > 10_000  # >10KB → at least a real MP4

        # Delete the job
        deleted = api.delete(f"{BASE_URL}/api/video/jobs/{job_id}").json()
        assert deleted["deleted"] is True
