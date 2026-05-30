# Already Here Command OS — Product Requirements Document

## Original problem statement
Build the "Already Here Command OS" — a global, enterprise-grade governed
AI ecosystem and dashboard with absolute $0/month operating cost target
(Oracle Cloud Always Free), local-first execution, a CapCut-style Content
Factory, multi-agent management, Cost Guard, and Bitwarden integration.
The application must be completely stripped of Emergent platform
dependencies so it can be deployed autonomously and freely anywhere.

Recently the user requested an AI Video Generator (Faceless, Avatars,
Deepfakes, Generative Video) at $0 cost.

## Personas
- **Operator (you)** — single-tenant power user. Has the Operator Token,
  approves HITL gates, owns the LLM provider key.
- **Audience** — TikTok/Reels/Shorts viewers who consume the videos the
  operator publishes.
- **Optional buyers** — operators who clone the repo, point it at their
  own LLM key, and run the same dashboard $0/mo on Oracle.

## Core requirements (static)
1. **$0/mo** — no recurring fees. Every paid integration is opt-in and
   gated.
2. **Local-first** — every CPU-bound task (TTS, captions, ffmpeg) runs on
   the same OCI VM. No external worker queues, no SaaS dependencies.
3. **Dual database** — MongoDB for the dashboard, SQLite for portable
   offline export.
4. **Governance** — L0-L5 with dual-actor HITL approval gates on
   high-risk autonomous actions (capital_allocation, mass_outreach).
5. **Distillation cache** — every LLM call goes through semantic
   compression + cache lookup before hitting the provider.
6. **No Emergent dependencies** — pure litellm + standard SDKs.

## What's implemented (current state — May 2026)

### Iteration 10 (2026-05-29) — Free upgrade pack
- ✅ Multi-model Gemini fallback chain in `services/llm_adapter.py`:
  primary `gemini-3-flash-preview` → `gemini-2.5-flash` →
  `gemini-2.0-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash` →
  `gemini-1.5-flash-8b`. Each fallback bucket has its own free-tier
  daily quota so the operator gets ~3500+ free requests/day combined.
- ✅ Deterministic template fallback for hook generation when every
  Gemini bucket is exhausted (`routes/hooks._deterministic_hooks`).
- ✅ Three bundled CC0 royalty-free music beds at `/app/data/music/`
  (cinematic / upbeat / chill), procedurally synthesized via ffmpeg
  `aevalsrc`. Mixed under TTS via a 3-input ffmpeg filter graph.
- ✅ Adaptive captions via `faster-whisper` (tiny.en, int8 CPU). Real
  word-aligned SRT replaces uniform per-line timing.
- ✅ Per-shot voice override (already supported in engine, surfaced in
  UI via Voice select).
- ✅ Video Studio UI: music dropdown, adaptive-captions toggle, expanded
  CapabilityCard with 8 pills.
- ✅ New tests: `tests/test_llm_fallback.py` (6) + `tests/test_video_extras.py` (4).
- ✅ **158/158 pytest PASS. All API + frontend regression PASS.**

### Iteration 9 — Video Engine
- Phase 1 faceless: ffmpeg + Piper TTS + Pexels stock + burned-in
  captions, vertical 1080×1920 MP4.
- Phase 2 avatar lipsync: mediapipe + ffmpeg zoompan + audio meter.
- Phase 2.5 Wav2Lip opt-in (ONNX model auto-detected).
- Phase 3 external generative bridge wired (Sora 2 SDK pending GA).
- Viral hook generator (`POST /api/hooks/` + `/api/hooks/ab-test`).

### Earlier iterations
- Books / audiobooks (Piper TTS for audio).
- Proposals generator.
- Master Revenue Equation tracker.
- Data Distillation Framework (semantic compression + cache).
- L5 dual-actor HITL governance.
- Stripe payments (test key).
- Complete Emergent scrub.
- One-shot OCI deploy script (`scripts/one-shot-oci-deploy.sh`).

## Roadmap

### P0 (next)
- **User verification** — operator confirms A/B test + music + adaptive
  captions work in the UI after this fix lands.

### P1
- OCI deploy execution — user pushes to GitHub + runs the bootstrap.
- Per-shot voice overrides surfaced in the UI (engine supports it).
- Per-route LLM cost breakdown in `/api/distillation/stats`.

### P2
- Sidebar "Cost Guard fired N times today" badge.
- Buffer/Hootsuite fallback share chips.
- Switch unbounded `find().to_list()` queries to MongoDB aggregations.
- Royalty-free music: ingest a wider library (Pixabay/FreePD API)
  instead of bundled procedural beds.
- Multi-voice scripts: per-shot voice_id override surfaced in UI.

## Tech stack
- **Backend** — FastAPI + Motor (MongoDB) + SQLite fallback.
- **Frontend** — React + Vite + Tailwind + Shadcn UI + react-query.
- **LLM** — `litellm` over BYO key (default chain: Gemini 3 Flash w/
  6-model free-tier fallback).
- **TTS** — Piper TTS local (`pip install piper-tts`).
- **Video** — ffmpeg + Pexels free tier (200 req/hr) + mediapipe + faster-whisper.
- **Music** — 3 bundled CC0 procedural beds (1.9 MB each).
- **Payments** — Stripe (opt-in, test key).
- **Auth** — Operator token (L5), no public auth surface.

## API endpoints (key)
- `GET /api/video/config` — full capability self-report
- `GET /api/video/music` — bundled music catalogue
- `GET /api/video/voices` — installed Piper voices
- `POST /api/video/render` — kick off a render (script + voice + music + captions + portrait + mode)
- `POST /api/video/portraits/upload` — upload avatar portrait
- `POST /api/hooks/` — generate 5 hook variants (with fallback chain)
- `POST /api/hooks/ab-test` — generate N hooks + fire N parallel renders
- `POST /api/books/{id}/audio/generate` — Piper-driven audiobook
- `GET /api/distillation/stats` — cache + cost breakdown
- `GET /api/governance/manifest` — L0-L5 governance manifest
