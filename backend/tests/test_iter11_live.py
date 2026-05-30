"""Iteration 11 live regression tests for Generative Suite endpoints.

Targets the public REACT_APP_BACKEND_URL. Validates:
  - GET /api/video/config new fields
  - GET /api/video/free-providers structure
  - POST /api/video/generative/image (Pollinations live)
  - Voice-refs upload/list/delete
  - POST /api/video/render with unique shot list (AI B-roll path)
"""
from __future__ import annotations

import io
import os
import time

import pytest
import requests


def _read_env_var(name: str) -> str:
    v = os.environ.get(name, "")
    if v:
        return v
    for p in ("/app/frontend/.env",):
        try:
            for line in open(p):
                if line.strip().startswith(f"{name}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return ""


BASE_URL = _read_env_var("REACT_APP_BACKEND_URL").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set in frontend/.env"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---------- /api/video/config ----------
def test_video_config_exposes_new_free_provider_fields(s):
    r = s.get(f"{BASE_URL}/api/video/config", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in (
        "free_providers", "ai_b_roll_available", "voice_cloning_available",
        "ai_music_generation_available", "text_to_video_available",
        "voice_refs_uploaded",
    ):
        assert key in data, f"missing field {key}: {list(data.keys())}"
    assert "pollinations_ai" in data["free_providers"]
    assert "huggingface" in data["free_providers"]
    assert data["free_providers"]["pollinations_ai"] is True
    # HF token not configured by default — but allow either state since
    # the operator may have plugged in a real token. Just assert it's bool.
    assert isinstance(data["free_providers"]["huggingface"], bool)
    assert data["ai_b_roll_available"] is True
    # Iter12: voice cloning now runs locally via Coqui XTTS-v2 — accept either
    # state so the test is portable to envs without the local model installed.
    assert isinstance(data["voice_cloning_available"], bool)


# ---------- /api/video/free-providers ----------
def test_free_providers_catalogue(s):
    r = s.get(f"{BASE_URL}/api/video/free-providers", timeout=20)
    assert r.status_code == 200, r.text
    data = r.json()
    # Accept either dict or list-style catalogue but must mention pollinations + huggingface
    txt = str(data).lower()
    assert "pollinations" in txt
    assert "huggingface" in txt or "hugging_face" in txt or "hugging face" in txt


# ---------- /api/video/generative/image ----------
def test_generative_image_pollinations_live(s):
    payload = {
        "prompt": "vibrant minimalist gradient abstract test",
        "provider": "pollinations",
        "width": 1080,
        "height": 1920,
    }
    r = s.post(f"{BASE_URL}/api/video/generative/image", json=payload, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("size_bytes", 0) > 1024
    assert isinstance(data.get("data_url", ""), str)
    assert data["data_url"].startswith("data:image/") and "base64," in data["data_url"]
    assert data.get("provider", "").lower().startswith("pollin")


# ---------- voice refs lifecycle ----------
def test_voice_ref_upload_list_delete():
    # multipart upload using requests (no Content-Type override)
    fake_wav = b"RIFF" + b"\x00" * 4096
    files = {"file": ("test.wav", io.BytesIO(fake_wav), "audio/wav")}
    r = requests.post(f"{BASE_URL}/api/video/voice-refs/upload", files=files, timeout=30)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "voice_ref_id" in body
    assert body.get("size_bytes", 0) > 0
    vid = body["voice_ref_id"]

    # list
    r2 = requests.get(f"{BASE_URL}/api/video/voice-refs", timeout=20)
    assert r2.status_code == 200
    lst = r2.json()
    ids = [v.get("voice_ref_id") for v in (lst if isinstance(lst, list) else lst.get("voice_refs", []))]
    assert vid in ids

    # delete
    r3 = requests.delete(f"{BASE_URL}/api/video/voice-refs/{vid}", timeout=20)
    assert r3.status_code in (200, 204)


# ---------- /api/video/render with AI B-roll path ----------
def test_render_ai_broll_completes(s):
    unique = f"iter11-{int(time.time())}"
    payload = {
        "script": {
            "hook": f"Hello world {unique}.",
            "script_body": "This is an iteration eleven AI B-roll regression test.",
            "cta": "Subscribe now.",
            "shot_list": [
                f"unique scene {unique} pyramid night sky stars",
                f"unique scene {unique} ocean sunset waves",
                f"unique scene {unique} forest mist morning",
            ],
        },
        "voice_id": None,
        "music_id": None,
        "adaptive_captions": False,
    }
    r = s.post(f"{BASE_URL}/api/video/render", json=payload, timeout=60)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") in ("complete", "completed", "done", "rendered", "queued", "running", "pending"), data
    job_id = data.get("job_id")
    assert job_id, "render response missing job_id"

    # Poll job until terminal (up to 180s for AI B-roll path)
    final = None
    for _ in range(60):
        time.sleep(3)
        jr = s.get(f"{BASE_URL}/api/video/jobs/{job_id}", timeout=20)
        if jr.status_code != 200:
            continue
        jd = jr.json()
        st = jd.get("status")
        if st in ("complete", "completed", "done", "rendered", "failed", "error"):
            final = jd
            break
    assert final is not None, "render never reached terminal state in 180s"
    assert final.get("status") in ("complete", "completed", "done", "rendered"), final
    assert final.get("output_path"), final
    # File size check via reported size if available
    sz = final.get("size_bytes") or final.get("output_size") or 0
    if sz:
        assert sz > 200 * 1024, f"output too small: {sz}"
