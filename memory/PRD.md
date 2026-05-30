# Already Here Command OS — Product Requirements Document

## Original problem statement
Build the "Already Here Command OS" — a global, enterprise-grade governed
AI ecosystem and dashboard with absolute $0/month operating cost target
(Oracle Cloud Always Free), local-first execution, a CapCut-style Content
Factory, multi-agent management, Cost Guard, and Bitwarden integration.

The user requested an AI Video Generator with **every capability at $0**.
Reference materials: Atlas Cloud "10 best free AI video generators 2026",
email summary of Vidnoz / Invideo / JoggAI / ElevenLabs / Suno / SadTalker,
Google AI blueprint chaining HuggingFace Spaces + Gradio + SadTalker.

## Core requirements
1. **$0/mo** — no recurring fees. Paid integrations opt-in & gated.
2. **Local-first** — every CPU task on the same OCI VM.
3. **Dual database** — MongoDB primary, SQLite portable export.
4. **Governance** — L0-L5 with dual-actor HITL approval gates.
5. **Distillation cache** — semantic compression + cache on every LLM call.
6. **No Emergent dependencies** — pure litellm + standard SDKs.

## What's implemented

### Iteration 12 (2026-05-30) — Real HF Inference + Pollinations TTS + reality-check
- ✅ User's free HuggingFace token wired. Authenticated as `AlreadyHereLLC` (free plan).
- ✅ HF Inference API client rewritten for the new **router.huggingface.co**
  endpoint (the legacy `api-inference.huggingface.co` is dead).
- ✅ **HF FLUX-schnell text-to-image WORKS** — 1024×1024 in ~5 seconds. Used as
  the second AI B-roll provider after Pollinations.
- ✅ Pollinations.ai now also handles **TTS** (6 voices: alloy/echo/fable/onyx/nova/shimmer) via
  the OpenAI-compatible audio endpoint — keyless free. Wired as a TTS choice
  alongside local Piper.
- ✅ Pollinations text-generation via **POST OpenAI-Chat-compatible endpoint** (not
  the deprecated GET URL). Retries on 502/503. Used as the ultimate $0
  text fallback when every Gemini bucket is exhausted.
- ✅ **Reality check**: HF pruned XTTS-v2 voice cloning, MusicGen, and AnimateDiff
  from the free hf-inference tier in 2025. Capability report now honestly
  reports `voice_cloning_available=false`, `ai_music_generation_available=false`,
  `text_to_video_available=false`, and `hf_image_generation_available=true`
  + `pollinations_tts_available=true`.
- ✅ Generative Suite UI updated: ImagePreview gains a provider toggle
  (Pollinations turbo / HF FLUX-schnell), new PollinationsTTSPanel with the
  6 voices, VoiceRefPanel kept for future local-install path.
- ✅ Smoke test: full faceless render with Pollinations TTS nova voice + HF
  FLUX B-roll + adaptive captions + chill bed completes in **~12 seconds**
  end-to-end. Output: stereo AAC 44.1 kHz / H.264 / 14s vertical 1080×1920 MP4.
- ✅ **174 passed, 1 skipped** in the pytest suite.

### Iteration 11 — Pollinations + HF wiring
- Pollinations.ai keyless image gen integrated.
- Hugging Face Inference API client.
- AI B-roll in faceless pipeline (cascade: Pexels → Pollinations → HF → placeholder).
- Voice cloning / AI music / text-to-video stubs (since pruned by HF — see iter12).
- Parallel per-shot fetch (~3x speedup via asyncio.gather).
- Generative Suite UI panel.

### Iteration 10 — Multi-model fallback + adaptive captions + bundled music
- 4-model Gemini fallback chain (2.5-flash → 2.0-flash → 2.5-lite → 2.0-lite).
- Deterministic template fallback for hooks.
- 3 procedural CC0 music beds.
- faster-whisper adaptive captions (tiny.en, int8 CPU).

### Iteration 9 — Video Engine
- Faceless mode, Avatar lipsync (mediapipe), Wav2Lip opt-in, Viral hook generator.

### Earlier — Books / Audiobooks / Proposals / Master Revenue Equation /
Distillation cache / L5 HITL governance / Stripe / Emergent scrub /
OCI one-shot deploy script.

## Roadmap

### P0
- **User verification** — run a render with Pollinations nova voice + HF FLUX
  B-roll + adaptive captions to see the upgrade in action.
- **Rotate the HF token** the user pasted in chat (now in `.env`).

### P1
- Local SadTalker install (open-source) for true photo-to-talking-head
  without depending on HF hosting.
- Local Coqui-TTS install for offline voice cloning (XTTS-v2 model weights
  + pip install).
- OCI deploy execution (push to GitHub → bootstrap on Always Free VM).
- Per-shot voice override in the UI (engine supports it).

### P2
- Roop / InsightFace face-swap mode (license-gated, opt-in).
- Local MusicGen via AudioCraft (CPU, ~1GB model).
- Sidebar "Cost Guard fired N times today" badge.
- Buffer / Hootsuite share chips.
- Wider royalty-free music library via Pixabay / FreePD APIs.

## Tech stack
- **Backend** — FastAPI + Motor (MongoDB) + SQLite fallback.
- **Frontend** — React + Vite + Tailwind + Shadcn UI + react-query.
- **LLM** — litellm with 5-model Gemini free-tier fallback + Pollinations
  text fallback (POST /openai chat format).
- **TTS** — Piper local + Pollinations OpenAI-audio (6 voices, keyless).
- **Captions** — faster-whisper tiny.en int8 CPU.
- **Image gen** — Pollinations (keyless turbo/flux) + HF FLUX-schnell (free token).
- **Music** — 3 bundled CC0 procedural beds.
- **Video** — ffmpeg + Pexels + AI B-roll + mediapipe + Wav2Lip opt-in.
- **Payments** — Stripe (opt-in, test key).
- **Auth** — Operator token (L5).

## Key endpoints
- `GET /api/video/config` — full capability self-report
- `GET /api/video/free-providers` — Pollinations + HF status
- `GET /api/video/music`, `POST /api/video/voice-refs/upload`
- `POST /api/video/generative/image` — Pollinations or HF FLUX preview
- `POST /api/video/render` — script + voice + music + captions + portrait
  + voice_ref_id + ai_music_prompt + **pollinations_voice** + mode
- `POST /api/hooks/`, `POST /api/hooks/ab-test`
- `POST /api/books/{id}/audio/generate` — Piper audiobook
- `GET /api/distillation/stats`, `GET /api/governance/manifest`
