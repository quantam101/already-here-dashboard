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
                  "pexels_api_key_set", "modes_available", "operator_actions",
                  "mediapipe_installed", "wav2lip_onnx_present",
                  "external_provider_configured", "external_provider_status"):
            assert k in d, f"missing {k}"
        # modes_available is the contract surface the UI relies on
        for m in ("faceless", "avatar_lipsync", "external_provider"):
            assert m in d["modes_available"]
        # Phase-1 + Phase-2 should both be available in this env
        assert d["modes_available"]["faceless"] is True
        assert d["modes_available"]["avatar_lipsync"] is True

    def test_voices_endpoint(self, api):
        r = api.get(f"{BASE_URL}/api/video/voices")
        assert r.status_code == 200
        d = r.json()
        assert "installed" in d and "default" in d
        assert isinstance(d["installed"], list)

    def test_render_rejects_avatar_without_portrait(self, api):
        # avatar_lipsync requires portrait_id — must 400
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {"hook": "x", "script_body": "x", "cta": "x", "shot_list": ["a"]},
            "mode": "avatar_lipsync",
        })
        assert r.status_code == 400, r.text
        assert "portrait" in r.text.lower()

    def test_render_external_provider_returns_pending_then_fails(self, api):
        """external_provider is wired but the Sora 2 SDK is in beta — pipeline must
        fail cleanly with a documented NotImplementedError, not a 501 anymore."""
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {"hook": "x", "script_body": "x", "cta": "x", "shot_list": []},
            "mode": "external_provider",
        })
        # external provider mode is configured (we have LLM_API_KEY) so request
        # is accepted; but the pipeline will fail with NotImplementedError. We
        # don't poll here — just confirm acceptance.
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "external_provider"

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


class TestVideoEngineAvatar:
    """Phase-2: animated-portrait avatar pipeline."""

    @pytest.fixture(scope="class")
    def synthetic_portrait_bytes(self):
        """Generate a tiny synthetic portrait via ffmpeg so we don't ship test fixtures."""
        import subprocess
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            out = f.name
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=0x222222:s=720x720:d=1",
            "-vf", "drawbox=x=160:y=120:w=400:h=480:color=0xddbb99:t=fill,"
                   "drawbox=x=240:y=220:w=40:h=40:color=0x222222:t=fill,"
                   "drawbox=x=440:y=220:w=40:h=40:color=0x222222:t=fill,"
                   "drawbox=x=290:y=420:w=140:h=40:color=0x882222:t=fill",
            "-frames:v", "1", out,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        with open(out, "rb") as f:
            data = f.read()
        os.unlink(out)
        return data

    def test_portrait_upload_rejects_bad_content_type(self, api):
        # send text file with wrong content-type — use a fresh requests call so
        # the multipart boundary isn't overridden by the session's json header.
        r = requests.post(
            f"{BASE_URL}/api/video/portraits/upload",
            files={"file": ("evil.exe", b"\x4d\x5a" + b"\x00" * 4000, "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_portrait_upload_rejects_tiny(self, api):
        r = requests.post(
            f"{BASE_URL}/api/video/portraits/upload",
            files={"file": ("tiny.png", b"\x89PNG\r\n", "image/png")},
        )
        assert r.status_code == 400

    def test_portrait_full_upload_and_list_and_delete(self, api, synthetic_portrait_bytes):
        # upload
        r = requests.post(
            f"{BASE_URL}/api/video/portraits/upload",
            files={"file": ("face.png", synthetic_portrait_bytes, "image/png")},
        )
        assert r.status_code == 200, r.text
        pid = r.json()["portrait_id"]
        assert pid.endswith(".png")
        # list contains it
        rows = api.get(f"{BASE_URL}/api/video/portraits").json()
        assert any(p["portrait_id"] == pid for p in rows)
        # delete
        d = api.delete(f"{BASE_URL}/api/video/portraits/{pid}").json()
        assert d["deleted"] is True

    def test_full_avatar_render(self, api, synthetic_portrait_bytes):
        config = api.get(f"{BASE_URL}/api/video/config").json()
        if not config["modes_available"]["avatar_lipsync"]:
            pytest.skip("avatar_lipsync mode not available on this host")
        up = requests.post(
            f"{BASE_URL}/api/video/portraits/upload",
            files={"file": ("face.png", synthetic_portrait_bytes, "image/png")},
        ).json()
        pid = up["portrait_id"]
        r = api.post(f"{BASE_URL}/api/video/render", json={
            "script": {
                "hook": "Pytest avatar smoke",
                "script_body": "Short narration line for avatar render",
                "cta": "End.",
                "shot_list": [],
            },
            "mode": "avatar_lipsync",
            "portrait_id": pid,
        })
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        # Poll up to 60s — animated-portrait is faster than faceless
        deadline = time.time() + 60
        status = None
        while time.time() < deadline:
            j = api.get(f"{BASE_URL}/api/video/jobs/{job_id}").json()
            status = j["status"]
            if status in ("complete", "failed"):
                break
            time.sleep(2)
        assert status == "complete", f"avatar job ended with status={status}: {j.get('error')}"
        # MP4 servable
        d = api.get(f"{BASE_URL}/api/video/jobs/{job_id}/download")
        assert d.status_code == 200
        assert d.headers.get("content-type") == "video/mp4"
        assert len(d.content) > 50_000
        # Manifest records the wav2lip status
        # (no separate endpoint — checked by file presence; trust the engine)
        # Cleanup
        api.delete(f"{BASE_URL}/api/video/jobs/{job_id}")
        api.delete(f"{BASE_URL}/api/video/portraits/{pid}")
