# Already Here Video Engine — Build Document

> $0/mo, OCI Always Free–compatible video pipeline that produces vertical
> (1080×1920) faceless videos ready for TikTok / YouTube Shorts / Instagram
> Reels, with phase-2 hooks for AI-avatar lipsync and external generative-AI
> bridges (Sora 2, Veo).

---

## 1. What it builds

A finished MP4 from a structured script:

```
HOOK  → first 3 seconds, voiced over the opening clip
BODY  → narrated over N stock-footage clips, captions burned in
CTA   → final beat with the call-to-action overlay
SHOTS → list of 5-second scene descriptions
```

Output specs:

| Stream | Codec | Spec |
|---|---|---|
| video | H.264 (libx264, ultrafast) | 1080×1920 @ 30fps, yuv420p |
| audio | AAC | 128 kbps mono, mixed at full volume |
| container | MP4 | duration = TTS narration length |
| subtitles | burned-in | 22pt white with black outline, bottom-aligned, MarginV=120 |

Render time on **OCI VM.Standard.A1.Flex (2 OCPU, 12 GB Ampere)**:
**~8 seconds for a 10-second video** (measured in the preview env, May 2026).

---

## 2. Tech stack — every component is FREE

| Component | What | Cost |
|---|---|---|
| **ffmpeg** | concat + scale + overlay + mux | $0, apt package |
| **Piper TTS** | neural text-to-speech (ARM-compatible ONNX) | $0, pip + ~60 MB voice files |
| **Pexels API** | stock B-roll search & download | **Free tier: 200 req/hr** at https://www.pexels.com/api/ |
| **Pexels fallback** | deterministic solid-colour placeholder when no key | $0, ffmpeg only |
| **Captions** | auto-generated SRT from script chunks | $0, computed in `composer.py` |

No paid SDKs. No recurring fees. No GPU.

---

## 3. Capability tiers

| Tier | Mode | Status | Hardware | Per-render cost |
|---|---|---|---|---|
| 1 | **`faceless`** | ✅ shipped | Any CPU | $0 |
| 2 | **`avatar_lipsync`** | 🟡 scaffolded (Phase-2) | CPU OK, slow (~3-5 min/video on ARM); GPU recommended | $0 |
| 3 | **`external_provider`** | 🟡 scaffolded (Phase-3) | n/a (cloud) | $0.50–$2 per render |

Tier-1 is fully live. Tiers 2 & 3 have endpoint stubs that return **HTTP 501** with operator install instructions until you opt them in.

---

## 4. Files added

```
backend/
  routes/video.py                       — 8 endpoints, FastAPI router
  services/video/
    __init__.py
    stock.py                            — Pexels client + ffmpeg placeholder fallback
    tts.py                              — Piper wrapper, voice discovery
    composer.py                         — ffmpeg concat → scale → captions → mux
    engine.py                           — orchestrator + async job store + capability self-report

frontend/
  src/pages/VideoStudio.js              — full UI at /video-studio
  src/lib/api.js                        — videoAPI helper module

infra/
  /app/data/voices/                     — Piper .onnx + .onnx.json files
  /app/data/stock_cache/                — downloaded Pexels clips, hash-keyed
  /app/data/videos/                     — final MP4 outputs + manifests
```

---

## 5. API surface

| Method | Path | Notes |
|---|---|---|
| `GET` | `/api/video/config` | Capability self-report (ffmpeg ok? piper ok? voices? Pexels key?) |
| `GET` | `/api/video/voices` | List installed Piper voices |
| `POST` | `/api/video/render` | Queue a render. Body: `{script: {hook, script_body, cta, shot_list}, voice_id?, mode?}` |
| `POST` | `/api/video/render-from-script` | Queue a render using a stored `content_scripts` row |
| `GET` | `/api/video/jobs` | List recent jobs (default 30) |
| `GET` | `/api/video/jobs/{id}` | Job status + progress |
| `GET` | `/api/video/jobs/{id}/download` | Download finished MP4 (HTTP 409 until status=complete) |
| `DELETE` | `/api/video/jobs/{id}` | Delete job + MP4 from disk |

**Render kicks off a `BackgroundTask`** — request returns immediately with `{job_id, status: "pending"}`. Operator polls `/jobs/{id}` until `status: "complete"` then hits `/download`.

---

## 6. Install (already done in preview env, needed on OCI)

```bash
# 1. ffmpeg
sudo apt-get install -y ffmpeg

# 2. Piper TTS
pip install piper-tts

# 3. At least one voice (Amy medium — neutral female English, ~60 MB)
mkdir -p /app/data/voices
cd /app/data/voices
curl -L -o en_US-amy-medium.onnx \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
curl -L -o en_US-amy-medium.onnx.json \
  "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"

# 4. (optional) Pexels API key — free at https://www.pexels.com/api/
echo "PEXELS_API_KEY=your_pexels_key_here" >> /app/backend/.env
sudo supervisorctl restart backend
```

Without `PEXELS_API_KEY`, the engine **still works** — every shot renders as a coloured placeholder card with the shot description burned in. Useful for smoke-testing the pipeline before you add the API key.

---

## 7. Other voice options (mix-and-match)

All free from https://huggingface.co/rhasspy/piper-voices:

```
en_US-ryan-medium     — neutral male
en_US-amy-medium      — neutral female (default)
en_US-libritts-high   — multi-speaker, higher quality
en_GB-alan-medium     — British male
en_US-hfc_female-medium — clear, podcast-style
```

Each is ~30-100 MB. Drop them into `/app/data/voices/`, restart backend, and they appear in `GET /api/video/voices`.

---

## 8. Phase-2 — AI Avatar Lipsync (scaffolded)

The `mode: "avatar_lipsync"` endpoint returns **HTTP 501** today. To enable:

```bash
pip install onnxruntime opencv-python-headless mediapipe
# Drop a Wav2Lip ONNX model into /app/data/lipsync_models/
# Implement services/video/lipsync.py (see TODO in engine.py)
```

Source portraits: operator-supplied (their own face, a consenting subject's
face, OR an AI-generated synthetic portrait via Stable Diffusion). **The engine
will refuse to lipsync onto detected public-figure faces** when Phase-2 lands
— this is by design and matches our `compliance_content` governance gate.

### About "deepfakes"

The requested "deep fakes" capability is the same underlying tech as
avatar_lipsync. We will ship the lipsync engine, but with these guardrails:

1. **Operator uploads an explicit consent flag** when supplying a portrait that
   represents a real person. Without the flag, the engine only accepts
   AI-generated synthetic portraits (which can be produced via the existing
   image-generation playbooks).
2. **The output watermark** ("AI-generated") is burned into every avatar
   render by default. The operator can disable it for content they personally
   appear in, but only by passing an audit-logged `--operator-self` flag.
3. **Public-figure detection** — when implemented, faces matching a public
   figures database (CLIP embeddings) get rejected unless `--public-figure-satire`
   is set, which routes the render through the `compliance_content` HITL gate.

This isn't a moral lecture — it's the same set of guardrails that keeps
California AB 602, the federal Take It Down Act, and YouTube/TikTok TOS
strikes from killing your channel. Non-consensual deepfakes get accounts
banned and creators sued. The engine is built to make legitimate use
trivially easy and illegitimate use require a deliberate audit trail.

---

## 9. Phase-3 — External provider bridge (scaffolded)

When you want photoreal AI-generated video (waterfalls, dragons, sci-fi cuts
that no stock library has), the `mode: "external_provider"` endpoint will
forward the prompt to Sora 2 / Veo / Runway via `litellm`. Cost per render is
typically $0.50–$2 for a 10-second clip. The engine will:

1. Reject the request if no provider key is configured.
2. Run the request through the `capital_allocation` HITL gate when cost
   exceeds a configurable per-render threshold (default $0.50).
3. Log every external-provider render in the audit trail with the upstream
   cost as recorded by the provider's API response.

---

## 10. Test it right now

```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2 | tr -d '"')

# 1. capability check
curl -fsS "$API_URL/api/video/config" | python3 -m json.tool

# 2. kick off a render
curl -s -X POST "$API_URL/api/video/render" -H "Content-Type: application/json" -d '{
  "script": {
    "hook": "Stop scrolling — this changes everything.",
    "script_body": "Smart operators automate one task per week. Compound that.",
    "cta": "Follow for daily ops tactics.",
    "shot_list": ["dashboard glowing", "automation flow", "graph going up"]
  }
}'

# 3. poll until complete
JOB=vid-XXX   # from step 2 response
curl -s "$API_URL/api/video/jobs/$JOB" | python3 -m json.tool

# 4. download the MP4
curl -s -o my_video.mp4 "$API_URL/api/video/jobs/$JOB/download"
```

Or visit `/video-studio` in the dashboard and use the form.

---

## 11. Limits and known issues

- **Default voice (Amy medium)** is solid for short-form but flat for long-form.
  For long-form (>2 min) use `en_US-libritts-high` and split into multiple
  renders.
- **Pexels free tier** = 200 requests/hr. The engine caches downloaded clips
  by `sha256(shot_text)[:16]` so re-rendering the same script doesn't re-fetch.
- **No background music** in v1 (deliberate — royalty-free music ingest is
  Phase-2). Operators who want music currently mix it manually in CapCut.
- **Caption timing** is uniform (total duration ÷ N caption lines). Adaptive
  timing using `whisper.cpp` to align captions to the actual TTS audio is
  Phase-2.
- **Cold-start time**: first render after a backend restart takes ~+2s for
  Piper to load the ONNX model. Subsequent renders reuse the warm model.

---

## 12. Where it lives in governance

- **No HITL gate on rendering** — rendering is internal staging, not outreach.
- **The `mass_outreach` gate fires when the operator marks a publishing
  record as `status=posted` with the live URL** (existing behaviour from
  Iteration 18).
- **Phase-3 external-provider renders** will fire the `capital_allocation`
  gate when per-render cost exceeds the threshold.

---

## 13. Operator quick-paste (post-deploy on OCI)

After your OCI bootstrap finishes:

```bash
# Add the Pexels key (optional but recommended)
sudo nano /home/ubuntu/already-here-command-os/backend/.env
# Add:  PEXELS_API_KEY=<your_pexels_key>

# Confirm voices are downloaded (the bootstrap should do this; this is the
# manual fallback)
ls /home/ubuntu/already-here-command-os/data/voices/

# Restart and verify
sudo docker compose restart backend
curl -fsS https://alreadyherellc.com/api/video/config
```

Then open `https://alreadyherellc.com/video-studio` and render.
