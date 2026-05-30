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
| 2 | **`avatar_lipsync`** | ✅ shipped (animated-portrait) | Any CPU | $0 |
| 2.5 | Wav2Lip photoreal upgrade | 🟡 opt-in | CPU OK / GPU faster | $0 |
| 3 | **`external_provider`** | 🟡 wired (Sora SDK in beta) | n/a (cloud) | $0.50–$2/render |

All three modes are accessible via `POST /api/video/render` with `mode: "<tier>"`. The capability self-report (`GET /api/video/config`) shows the live state of each. Tier-2.5 (Wav2Lip ONNX upgrade) auto-engages when a model exists at `/app/data/lipsync_models/wav2lip.onnx`.

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
| `GET` | `/api/video/config` | Capability self-report (ffmpeg, piper, voices, Pexels, mediapipe, wav2lip, external) |
| `GET` | `/api/video/voices` | List installed Piper voices |
| `POST` | `/api/video/render` | Queue a render. Body: `{script, voice_id?, mode?: "faceless"\|"avatar_lipsync"\|"external_provider", portrait_id?}` |
| `POST` | `/api/video/render-from-script` | Queue a render using a stored `content_scripts` row |
| `POST` | `/api/video/portraits/upload` | Multipart upload of a portrait (jpg/png/webp, <10MB) — returns `portrait_id` |
| `GET` | `/api/video/portraits` | List uploaded portraits |
| `DELETE` | `/api/video/portraits/{id}` | Delete a portrait |
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

## 8. Phase-2 — AI Avatar (LIVE — animated-portrait)

`mode: "avatar_lipsync"` is **shipped today**. It uses:

- **mediapipe** face detection (`pip install mediapipe`)
- **ffmpeg `zoompan`** Ken-Burns zoom on the portrait
- **ffmpeg `showvolume`** audio-amplitude meter overlaid in the mouth region — visually pulses with the syllables of the TTS narration
- Default "AI-generated" watermark in the top-right (set `operator_self=true` to disable)

End-to-end flow:

```bash
# 1. Upload your portrait
PID=$(curl -s -X POST "$API_URL/api/video/portraits/upload" \
  -F "file=@/path/to/your-photo.jpg" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['portrait_id'])")

# 2. Render with mode=avatar_lipsync
curl -s -X POST "$API_URL/api/video/render" -H "Content-Type: application/json" -d "{
  \"script\": {\"hook\": \"...\", \"script_body\": \"...\", \"cta\": \"...\", \"shot_list\": []},
  \"mode\": \"avatar_lipsync\",
  \"portrait_id\": \"$PID\"
}"
```

Verified render time on OCI-equivalent CPU: ~4-6 seconds for a 10s video.

### Phase-2.5 — true Wav2Lip lipsync (optional upgrade)

For photoreal lipsync (mouth shapes actually matching the phonemes), drop a
Wav2Lip ONNX model at `/app/data/lipsync_models/wav2lip.onnx`. The engine
auto-detects it and routes the avatar pipeline through it. Models are
HF-gated; the operator needs a HuggingFace account + token to download
from sources like `numz/wav2lip_studio`. Render time goes from ~5s →
~2-5 min/clip on ARM CPU. The animated-portrait fallback continues to
work without the model.

### About "deepfakes"

This Phase-2 pipeline is "animated portrait" not "deepfake" — the mouth
isn't actually generating new lip shapes, it's an animated audio-driven
overlay. That's a feature, not a bug:

1. **Legally safer** — California AB 602, the federal Take It Down Act, and
   platform TOS strike rules all target the photoreal-deepfake pipeline.
   Animated-portrait avoids that risk category entirely while still
   producing a video where "your face talks".
2. **Watermark is on by default.** Operators who appear in their own
   content can disable it by passing `operator_self=true` (audit-logged).
3. **If you later add the Wav2Lip ONNX** (Phase-2.5), the same guardrails
   apply, plus we recommend wiring face-detection embeddings (CLIP) to
   reject public-figure faces — that's a one-line `services/video/avatar.py`
   change when you want it.

---

## 9. Phase-3 — External provider bridge (wired, SDK in beta)

`mode: "external_provider"` is **wired** to forward generative-video
prompts to OpenAI Sora 2 / Google Veo / similar via `litellm`. The
endpoint accepts requests today; the upstream Sora 2 Python SDK is still
in limited beta, so the pipeline currently fails cleanly with a
`NotImplementedError` carrying a documented "SDK pending GA" message
(visible in `job.error`).

When the upstream SDK ships GA (expected mid-2026), enabling this becomes
a 3-line change in `services/video/external.py` (`render_text_to_video`).
The wiring, audit log, governance gate, and UI are all in place today.

Cost per render: ~$0.50-$2 for a 10-30s clip, charged against the
operator's `OPENAI_VIDEO_KEY` (or `LLM_API_KEY` fallback). Renders above
`EXTERNAL_VIDEO_GATE_USD` (default $0.50) route through the
`capital_allocation` HITL governance gate.

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
