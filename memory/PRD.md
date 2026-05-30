# Already Here Command OS — Product Requirements Document

## Original problem statement
Build the "Already Here Command OS" — a global, enterprise-grade governed
AI ecosystem and dashboard with absolute $0/month operating cost target
(Oracle Cloud Always Free), local-first execution, a CapCut-style Content
Factory, multi-agent management, Cost Guard, Bitwarden integration. The
user demanded "the best most advanced AI video generator with all the
functionalities at no cost. dont stop until all objectives are completed".
Then: "no placeholders, everything real, live."

## Core requirements (static)
1. **$0/mo** — no recurring fees. Paid integrations opt-in & gated.
2. **Local-first** — every CPU task on the same OCI VM. No remote
   per-render charges. No silent placeholder fallbacks.
3. **Dual database** — MongoDB primary, SQLite portable export.
4. **Governance** — L0-L5 with dual-actor HITL approval gates.
5. **Distillation cache** — semantic compression + cache on every LLM call.
6. **No Emergent dependencies** — pure litellm + standard SDKs.

## What's implemented

### Iteration 13 (2026-05-30) — Everything real, everything local
- ✅ Installed **Coqui XTTS-v2** locally for real CPU voice cloning. No HF
  hosting required. ~1.8 GB cached after first download; ~47s cold-start.
- ✅ Installed **transformers MusicGen-small** locally for real CPU AI
  music generation. ~300 MB model, ~109s cold-start, ~20s warm.
- ✅ Installed `torch 2.12.0+cpu`, `torchaudio`, `torchcodec 0.13.0+cpu`,
  `coqui-tts[codec]`, plus apt deps `pkg-config` + libav*-dev for PyAV.
- ✅ **Removed silent placeholder fallback** in `stock.py`. When no real
  B-roll source works, the render fails loudly (configurable via
  `VIDEO_ALLOW_PLACEHOLDER=true` for explicit opt-in).
- ✅ Updated `services/video/local_voice.py` (XTTS-v2) and
  `services/video/local_music.py` (MusicGen). Both lazy-load on first use.
- ✅ Compat patch for `transformers.pytorch_utils.isin_mps_friendly` so
  Coqui imports cleanly on transformers 5.x.
- ✅ Wired into engine: `voice_ref_id` → Coqui XTTS-v2; `ai_music_prompt` →
  local MusicGen. Both override Piper/CC0 defaults.
- ✅ Capability report now reports `voice_cloning_available=True` and
  `ai_music_generation_available=True` for real this time.
- ✅ Generative Suite UI: 6 status pills (Pollinations / HF / AI B-roll /
  Voice Clone local / AI Music local / Pollinations TTS) + new "Real local
  stack" panel listing what's running locally.
- ✅ **Verified end-to-end**: full pipeline render with real voice clone
  + real local MusicGen + real AI B-roll + adaptive captions in **132s**
  total wall time. Output 16 MB / 13.6s / H.264 / AAC vertical MP4.
- ✅ **178/178 tests pass** (174 fast + 4 slow real-model integration tests).
- ✅ `requirements.txt` frozen with the full real stack.

### Iteration 12 — HF Inference router + Pollinations TTS
- HF FLUX-schnell text-to-image via the new router.huggingface.co endpoint.
- Pollinations TTS (6 voices, keyless free) wired.
- Pollinations text POST endpoint with 3x retry.
- Honest capability reporting after HF's free-tier pruning.

### Iteration 11 — Generative Suite v1
- Pollinations.ai keyless image gen, HF Inference client, AI B-roll cascade.
- Parallel per-shot fetch (3x speedup), Generative Suite UI panel.

### Iteration 10 — Multi-model fallback + adaptive captions + bundled music
- 4-model Gemini fallback chain + Pollinations text ultimate fallback.
- 3 procedural CC0 music beds, faster-whisper adaptive captions.

### Iteration 9 — Video Engine
- Faceless mode, Avatar lipsync, Wav2Lip opt-in, Viral hook generator.

### Earlier — Books / Audiobooks / Proposals / Master Revenue Equation /
Distillation cache / L5 HITL governance / Stripe / Emergent scrub /
OCI one-shot deploy script.

## Roadmap

### P0
- **User verification** — render with cloned voice + local MusicGen prompt
  to see the real local stack in action.
- **Rotate the leaked HF token** the user pasted in chat earlier.

### P1
- OCI deploy execution (push to GitHub → bootstrap on Always Free VM).
- Pre-warm the local models on backend startup to avoid 47-109s
  cold-start latency on first render.
- Per-shot voice override surfaced in UI (engine supports it).

### P2
- Local AnimateDiff / CogVideoX-2B for true text-to-video at $0
  (requires ~5-10 GB model; CPU inference is slow ~1min/sec output).
- Roop / InsightFace face-swap mode (license-gated, opt-in).
- Cost Guard "fired N times today" sidebar badge.
- Buffer / Hootsuite share chips.

## Tech stack
- **Backend** — FastAPI + Motor (MongoDB) + SQLite fallback.
- **Frontend** — React + Vite + Tailwind + Shadcn UI + react-query.
- **LLM** — litellm with 5-model Gemini fallback chain + Pollinations text fallback.
- **TTS** — Piper local + Pollinations OpenAI-audio (6 voices) + **Coqui XTTS-v2 local (real voice clone)**.
- **Captions** — faster-whisper tiny.en int8 CPU.
- **Image gen** — Pollinations (keyless) + HF FLUX-schnell (free token).
- **Music** — 3 bundled CC0 procedural beds + **transformers MusicGen-small local (real AI gen)**.
- **Video** — ffmpeg + Pexels + AI B-roll + mediapipe + Wav2Lip opt-in.
- **ML stack** — torch 2.12.0+cpu, torchaudio, torchcodec+cpu, transformers 5.9, coqui-tts 0.27.
- **Payments** — Stripe (opt-in, test key).
- **Auth** — Operator token (L5).

## Key endpoints
- `GET /api/video/config` — full capability self-report (incl. voice_cloning_available + ai_music_generation_available)
- `GET /api/video/free-providers` — Pollinations + HF status
- `GET /api/video/music`, `POST /api/video/voice-refs/upload`
- `POST /api/video/generative/image` — Pollinations or HF FLUX preview
- `POST /api/video/render` — script + voice + music + captions + portrait
  + voice_ref_id (real local Coqui XTTS-v2 clone)
  + ai_music_prompt (real local MusicGen)
  + pollinations_voice (6 OpenAI-compat voices) + mode
- `POST /api/hooks/`, `POST /api/hooks/ab-test`
- `POST /api/books/{id}/audio/generate` — Piper audiobook
- `GET /api/distillation/stats`, `GET /api/governance/manifest`
