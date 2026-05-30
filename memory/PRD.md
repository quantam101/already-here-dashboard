# Already Here Command OS — Product Requirements Document

## Original problem statement
Build the "Already Here Command OS" — a global, enterprise-grade governed
AI ecosystem and dashboard with absolute $0/month operating cost target
(Oracle Cloud Always Free), local-first execution, a CapCut-style Content
Factory, multi-agent management, Cost Guard, and Bitwarden integration.
The application must be completely stripped of Emergent platform
dependencies so it can be deployed autonomously and freely anywhere.

The user requested an AI Video Generator with **every capability at $0**:
faceless, avatars, deepfakes, generative video, voice cloning, AI music,
AI B-roll, talking-heads, face-swap. Reference materials supplied:
Atlas Cloud "10 best free AI video generators 2026", an email summary
of Vidnoz / Invideo / JoggAI / ElevenLabs / Suno / SadTalker, and a
Google AI blueprint chaining HuggingFace Spaces + Gradio + Llama + TTS
+ SadTalker + face-swap.

## Personas
- **Operator** — single-tenant power user. Owns Operator Token + LLM key.
- **Audience** — TikTok/Reels/Shorts viewers of operator's videos.
- **Buyers** — operators who clone the repo, plug their own free keys,
  and run $0/mo on Oracle Cloud Always Free.

## Core requirements (static)
1. **$0/mo** — no recurring fees. Paid integrations opt-in & gated.
2. **Local-first** — every CPU task runs on the same OCI VM.
3. **Dual database** — MongoDB primary, SQLite portable export.
4. **Governance** — L0-L5 with dual-actor HITL approval gates.
5. **Distillation cache** — semantic compression + cache on every LLM call.
6. **No Emergent dependencies** — pure litellm + standard SDKs.

## What's implemented

### Iteration 11 (2026-05-30) — Generative Suite at $0
- ✅ **Pollinations.ai** keyless image gen integrated. Powers AI B-roll
  (replaces Pexels placeholder cards with real AI images per shot).
- ✅ **Hugging Face Inference API** client wired for voice cloning
  (XTTS-v2), AI music (MusicGen), and text-to-video (AnimateDiff /
  text-to-video-ms-1.7b). Free tier — operator provides HF token.
- ✅ **AI B-roll** in faceless pipeline. Cascade: Pexels → Pollinations
  → HF FLUX → solid-colour placeholder. ~3x faster via parallel
  `asyncio.gather` per shot.
- ✅ **Voice cloning** — upload reference WAV/MP3 → narration in operator's voice.
- ✅ **AI music** — operator prompt → MusicGen bed overrides bundled CC0 beds.
- ✅ **External provider** (Phase-3) now dispatches to HF AnimateDiff
  ($0 free) when HUGGINGFACE_API_KEY is set; Sora 2 path still wired
  for paid GA.
- ✅ Fallback chain pruned: dropped deprecated `gemini-1.5-flash` /
  `1.5-flash-8b` (404 NOT_FOUND); current chain = 2.5-flash → 2.0-flash
  → 2.5-flash-lite → 2.0-flash-lite. 404 NOT_FOUND now treated like
  quota (skip + try next).
- ✅ New routes: `GET /api/video/free-providers`, `POST/GET/DELETE /api/video/voice-refs`,
  `POST /api/video/generative/image`.
- ✅ Generative Suite UI panel in Video Studio with image preview,
  voice-ref upload, AI music prompt, provider status pills.
- ✅ `tests/test_free_apis.py` 6 tests; suite **170/170 PASS**.
- ✅ Testing agent: ALL PASS end-to-end (no retests).

### Iteration 10 — Multi-model fallback + adaptive captions + bundled music
- 6-model Gemini fallback chain + deterministic template fallback for hooks.
- 3 procedural CC0 music beds (cinematic/upbeat/chill).
- `faster-whisper` adaptive captions (tiny.en, int8 CPU).
- UI controls in Video Studio.

### Iteration 9 — Video Engine
- Faceless mode (ffmpeg + Piper + Pexels).
- Avatar lipsync (mediapipe animated portrait).
- Wav2Lip Phase 2.5 opt-in.
- Viral hook generator + A/B test endpoint.

### Earlier — Books / Audiobooks / Proposals / Master Revenue Equation /
Distillation cache / L5 HITL governance / Stripe / Emergent scrub /
OCI one-shot deploy script.

## Roadmap

### P0
- **User verification of Generative Suite** — run a render with AI
  B-roll on, optional voice-clone, optional AI music.
- **Drop a free Hugging Face token** into `backend/.env` to unlock
  voice cloning + AI music + text-to-video.

### P1
- OCI deploy execution (push to GitHub → bootstrap on Always Free VM).
- Sidebar "Cost Guard fired N times today" badge.
- Per-shot voice override in the UI (engine supports it).
- Per-route LLM cost breakdown in `/api/distillation/stats`.

### P2
- SadTalker direct (open-source local install) instead of HF-hosted.
- Roop / InsightFace face-swap mode (license-gated, opt-in).
- Suno-style song generation (different endpoint, longer outputs).
- Buffer / Hootsuite share chips.
- Wider royalty-free music library via Pixabay/FreePD API.

## Tech stack
- **Backend** — FastAPI + Motor (MongoDB) + SQLite fallback.
- **Frontend** — React + Vite + Tailwind + Shadcn UI + react-query.
- **LLM** — `litellm` with 4-model Gemini free-tier fallback.
- **TTS** — Piper local OR XTTS-v2 (HF) for voice cloning.
- **Captions** — `faster-whisper` tiny.en int8 CPU.
- **Image gen** — Pollinations.ai (keyless) + HF FLUX (free tier).
- **Music** — 3 bundled CC0 procedural beds + MusicGen (HF).
- **Video** — ffmpeg + Pexels + AI B-roll + mediapipe + Wav2Lip + HF AnimateDiff.
- **Payments** — Stripe (opt-in, test key).
- **Auth** — Operator token (L5).

## Key endpoints
- `GET /api/video/config` — full capability self-report
- `GET /api/video/free-providers` — Pollinations + HF status
- `GET /api/video/music`, `POST /api/video/voice-refs/upload`
- `POST /api/video/generative/image` — keyless Pollinations preview
- `POST /api/video/render` — script + voice + music + captions + portrait
  + voice_ref_id (clone) + ai_music_prompt (MusicGen) + mode
- `POST /api/hooks/`, `POST /api/hooks/ab-test`
- `POST /api/books/{id}/audio/generate` — Piper audiobook
- `GET /api/distillation/stats`, `GET /api/governance/manifest`
