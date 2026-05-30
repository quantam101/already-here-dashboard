"""Top-level video render orchestrator + job store.

The pipeline:
  1. Build the narration script (HOOK + SCRIPT + CTA, joined).
  2. TTS → narration.wav  (Piper, local, free)
  3. For each SHOT description → fetch_clip_for_shot (Pexels free tier, falls
     back to a placeholder clip when no API key is set so the pipeline
     never deadlocks during $0 dev).
  4. ffmpeg concat + scale-to-vertical + burn-in captions + audio mix.
  5. Write a manifest JSON next to the MP4 (full provenance).

Jobs are tracked in the `video_jobs` collection so the operator can poll
status from the UI.
"""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.video import avatar, captions, composer, external, gen_assets, local_music, local_voice, music, stock, tts

logger = logging.getLogger("video.engine")

JOB_COLLECTION = "video_jobs"
WORK_ROOT = Path(os.environ.get("VIDEO_OUTPUT_DIR", "/app/data/videos"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return f"vid-{uuid.uuid4().hex[:10]}"


async def create_job(db, *, script: dict, voice_id: str | None, mode: str = "faceless", portrait_path: str | None = None, music_id: str | None = None, music_volume: float = 0.15, adaptive_captions: bool = False, voice_ref_id: str | None = None, ai_music_prompt: str | None = None, pollinations_voice: str | None = None) -> dict:
    """Insert a `pending` job row and return it. Operator polls /status."""
    row = {
        "id": new_job_id(),
        "mode": mode,
        "status": "pending",
        "script": {
            "hook": script.get("hook", ""),
            "script_body": script.get("script_body") or script.get("body", ""),
            "cta": script.get("cta", ""),
            "shots": script.get("shot_list") or script.get("shots") or [],
        },
        "voice_id": voice_id,
        "portrait_path": portrait_path,
        "music_id": music_id,
        "music_volume": float(music_volume),
        "adaptive_captions": bool(adaptive_captions),
        "voice_ref_id": voice_ref_id,
        "ai_music_prompt": ai_music_prompt,
        "pollinations_voice": pollinations_voice,
        "progress_pct": 0,
        "message": "queued",
        "output_path": None,
        "error": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    await db[JOB_COLLECTION].insert_one(row)
    return row


async def get_job(db, job_id: str) -> dict | None:
    return await db[JOB_COLLECTION].find_one({"id": job_id}, {"_id": 0})


async def list_jobs(db, limit: int = 30) -> list[dict]:
    return await db[JOB_COLLECTION].find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)


async def _update(db, job_id: str, **changes) -> None:
    changes["updated_at"] = _now()
    await db[JOB_COLLECTION].update_one({"id": job_id}, {"$set": changes})


async def run_pipeline(db, job_id: str) -> None:
    """Run the configured render. Dispatches by job.mode."""
    job = await get_job(db, job_id)
    if not job:
        logger.error("run_pipeline: job %s missing", job_id)
        return

    mode = job.get("mode", "faceless")
    if mode == "avatar_lipsync":
        return await _run_avatar_pipeline(db, job)
    if mode == "external_provider":
        return await _run_external_pipeline(db, job)
    return await _run_faceless_pipeline(db, job)


async def _run_faceless_pipeline(db, job: dict) -> None:
    """Stock-footage faceless render (Phase-1 — the $0 default)."""
    job_id = job["id"]
    script = job["script"]
    shots = [s for s in (script.get("shots") or []) if s and s.strip()]
    if not shots:
        shots = ["Opening", "Main idea", "Detail", "Proof", "Call to action"]

    narration = " ".join([
        script.get("hook", ""), script.get("script_body", ""), script.get("cta", ""),
    ]).strip()

    if not narration:
        await _update(db, job_id, status="failed", error="empty narration script")
        return

    try:
        await _update(db, job_id, status="running", progress_pct=5, message="generating narration")
        wav_path = WORK_ROOT / f"{job_id}.wav"
        voice_ref_id = job.get("voice_ref_id")
        pollinations_voice = job.get("pollinations_voice")
        if voice_ref_id:
            # Real local voice cloning via Coqui XTTS-v2 ($0, runs on CPU).
            ref = gen_assets.voice_ref_path(voice_ref_id)
            if not ref:
                raise RuntimeError(f"voice reference {voice_ref_id!r} not found")
            try:
                await _update(db, job_id, progress_pct=8, message=f"local voice clone (Coqui XTTS-v2 ref={voice_ref_id})")
                await local_voice.synthesize_cloned(narration, ref, wav_path)
            except Exception as e:
                logger.warning("local voice clone failed, falling back to Piper: %s", str(e)[:200])
                await tts.synthesize(narration, wav_path, voice_id=job.get("voice_id"))
        elif pollinations_voice:
            try:
                await _update(db, job_id, progress_pct=8, message=f"pollinations TTS ({pollinations_voice})")
                await gen_assets.synthesize_pollinations_voice(narration, pollinations_voice, wav_path)
            except Exception as e:
                logger.warning("pollinations TTS failed, falling back to Piper: %s", str(e)[:200])
                await tts.synthesize(narration, wav_path, voice_id=job.get("voice_id"))
        else:
            await tts.synthesize(narration, wav_path, voice_id=job.get("voice_id"))

        await _update(db, job_id, progress_pct=25, message=f"fetching {len(shots)} stock clips in parallel")
        # Fetch all shots concurrently — huge speedup when AI B-roll is active
        # (Pollinations ~10-20s per image; serial 3 shots = 30-60s, parallel = ~20s).
        async def _fetch(idx: int, shot: str):
            clip = await stock.fetch_clip_for_shot(shot)
            pct = 25 + int(50 * (idx + 1) / len(shots))
            await _update(db, job_id, progress_pct=pct, message=f"clip {idx+1}/{len(shots)}: {shot[:40]}")
            return clip
        clip_paths_results = await asyncio.gather(
            *[_fetch(i, s) for i, s in enumerate(shots)],
            return_exceptions=False,
        )
        clip_paths: list[Path] = list(clip_paths_results)

        await _update(db, job_id, progress_pct=80, message="composing final MP4")
        caption_lines = _caption_lines(script)
        adaptive_srt_text: str | None = None
        if job.get("adaptive_captions"):
            try:
                await _update(db, job_id, progress_pct=82, message="transcribing for adaptive captions")
                adaptive_srt_text = captions.build_adaptive_srt(wav_path)
            except Exception as ex:
                logger.warning("adaptive caption transcription failed, falling back to uniform: %s", ex)
                adaptive_srt_text = None
        music_path = music.resolve(job.get("music_id"))
        # AI music override — if the operator supplied a prompt and HF is
        # configured, generate a fresh bed via MusicGen.
        ai_music_prompt = job.get("ai_music_prompt")
        if ai_music_prompt:
            try:
                ai_path = await gen_assets.generate_music_track(ai_music_prompt, duration_s=30)
                if ai_path and ai_path.exists():
                    music_path = ai_path
            except Exception as e:
                logger.warning("AI music gen failed, keeping bundled bed: %s", str(e)[:160])
        out_mp4 = await composer.compose(
            clips=clip_paths,
            narration_wav=wav_path,
            caption_lines=caption_lines,
            output_filename=job_id,
            music_path=music_path,
            music_volume=float(job.get("music_volume") or 0.15),
            adaptive_srt_text=adaptive_srt_text,
        )

        await composer.write_manifest(job_id, {
            "job_id": job_id, "mode": job["mode"], "shots": shots,
            "voice_id": job.get("voice_id"), "clip_count": len(clip_paths),
            "music_id": job.get("music_id"),
            "adaptive_captions_used": bool(adaptive_srt_text),
            "size_bytes": out_mp4.stat().st_size, "created_at": _now(),
        })

        await _update(
            db, job_id,
            status="complete", progress_pct=100,
            message=f"render complete ({out_mp4.stat().st_size // 1024} KB)",
            output_path=str(out_mp4),
        )
    except Exception as e:
        logger.exception("faceless pipeline failed: %s", e)
        await _update(db, job["id"], status="failed", error=str(e)[:500], message="render failed")


async def _run_avatar_pipeline(db, job: dict) -> None:
    """Phase-2: Animated-portrait avatar render.

    Uses mediapipe face detection + ffmpeg zoompan + audio-driven mouth-area
    overlay. NOT photoreal Wav2Lip (those models are HF-gated); IS a free
    $0 alternative that ships today. Operator can drop a Wav2Lip ONNX
    model into /app/data/lipsync_models/ to upgrade later — see VIDEO_ENGINE.md.
    """
    job_id = job["id"]
    script = job["script"]
    portrait_path = job.get("portrait_path")
    if not portrait_path or not Path(portrait_path).exists():
        await _update(db, job_id, status="failed", error="portrait image missing or invalid path")
        return

    narration = " ".join([
        script.get("hook", ""), script.get("script_body", ""), script.get("cta", ""),
    ]).strip()
    if not narration:
        await _update(db, job_id, status="failed", error="empty narration script")
        return

    try:
        await _update(db, job_id, status="running", progress_pct=10, message="generating narration")
        wav_path = WORK_ROOT / f"{job_id}.wav"
        await tts.synthesize(narration, wav_path, voice_id=job.get("voice_id"))

        await _update(db, job_id, progress_pct=40, message="detecting face + rendering portrait animation")

        # caption SRT
        from services.video.composer import _build_caption_srt  # internal helper
        caption_lines = _caption_lines(script)
        from services.video import composer as _comp
        duration = await _comp.probe_duration(wav_path)
        srt_text = _build_caption_srt(caption_lines, duration)
        srt_path = WORK_ROOT / f"{job_id}.srt"
        srt_path.write_text(srt_text or "1\n00:00:00,000 --> 00:00:01,000\n \n")

        out_mp4 = WORK_ROOT / f"{job_id}.mp4"
        # Watermark default: "AI-generated". Operator-self flag disables.
        watermark = "" if job.get("operator_self") else "AI-generated"
        await avatar.render_animated_portrait(
            portrait=Path(portrait_path),
            narration_wav=wav_path,
            output_mp4=out_mp4,
            caption_srt=srt_path,
            watermark=watermark,
        )

        await composer.write_manifest(job_id, {
            "job_id": job_id, "mode": job["mode"],
            "portrait": str(portrait_path), "voice_id": job.get("voice_id"),
            "watermark": watermark, "size_bytes": out_mp4.stat().st_size,
            "wav2lip_used": avatar.has_wav2lip_onnx(),
            "created_at": _now(),
        })

        await _update(
            db, job_id, status="complete", progress_pct=100,
            message=f"avatar render complete ({out_mp4.stat().st_size // 1024} KB)",
            output_path=str(out_mp4),
        )
    except Exception as e:
        logger.exception("avatar pipeline failed: %s", e)
        await _update(db, job["id"], status="failed", error=str(e)[:500], message="avatar render failed")


async def _run_external_pipeline(db, job: dict) -> None:
    """Phase-3: external generative-AI bridge (Sora 2 / Veo). Operator pays per render."""
    job_id = job["id"]
    if not external.is_configured():
        await _update(db, job_id, status="failed",
                      error="external provider not configured (set OPENAI_VIDEO_KEY)")
        return
    try:
        await _update(db, job_id, status="running", progress_pct=10,
                      message="dispatching to external provider")
        prompt = " ".join([
            job["script"].get("hook", ""), job["script"].get("script_body", ""),
        ]).strip()
        # This raises NotImplementedError today — the bridge is wired,
        # the upstream Sora 2 SDK is still in limited beta.
        result = await external.render_text_to_video(prompt)
        await _update(db, job_id, status="complete", progress_pct=100,
                      message="external render complete",
                      output_path=result.get("output_path"))
    except NotImplementedError as e:
        await _update(db, job_id, status="failed", error=str(e)[:500],
                      message="external provider sdk in beta")
    except Exception as e:
        logger.exception("external pipeline failed: %s", e)
        await _update(db, job["id"], status="failed", error=str(e)[:500],
                      message="external render failed")


def _caption_lines(script: dict) -> list[str]:
    return [
        line.strip()
        for chunk in [script.get("hook"), script.get("script_body"), script.get("cta")]
        for line in (chunk or "").split(". ")
        if line and line.strip()
    ]


def kickoff(db, job_id: str) -> asyncio.Task:
    """Spawn the pipeline as a background task and return it."""
    return asyncio.create_task(run_pipeline(db, job_id))


# ---------------------------------------------------------------------------
# Capability self-report — used by /api/video/config
# ---------------------------------------------------------------------------

def capability_report() -> dict[str, Any]:
    """What the engine can do RIGHT NOW on this host."""
    import shutil
    from services.free_apis import huggingface as _hf, pollinations as _poll
    ffmpeg = shutil.which("ffmpeg") is not None
    # piper ships as both a script ("piper") AND an importable Python module.
    # Check both — supervisor PATH may not include the venv bin dir even when
    # the venv module is importable.
    piper = shutil.which("piper") is not None
    if not piper:
        try:
            import piper as _piper_mod  # noqa: F401
            piper = True
        except ImportError:
            piper = False
    voices = tts.list_installed_voices()
    music_tracks = music.list_tracks()
    voice_refs = gen_assets.list_voice_refs()
    pexels_key = bool(os.environ.get("PEXELS_API_KEY", "").strip())
    mediapipe_ok = avatar.has_mediapipe()
    wav2lip_ok = avatar.has_wav2lip_onnx()
    whisper_ok = captions.is_available()
    hf_ok = _hf.is_configured()
    pollinations_ok = _poll.is_available()
    external_provider_ok = external.is_configured()
    # Local Coqui XTTS-v2 + transformers MusicGen — REAL $0 implementations
    # that run on CPU, no external API needed. Cold-start ~30-60s, then cached.
    local_voice_ok = local_voice.is_available()
    local_music_ok = local_music.is_available()
    return {
        "ffmpeg_installed": ffmpeg,
        "piper_installed": piper,
        "voices_installed": [v["id"] for v in voices],
        "music_tracks_available": [t["id"] for t in music_tracks],
        "adaptive_captions_available": whisper_ok,
        "pexels_api_key_set": pexels_key,
        "mediapipe_installed": mediapipe_ok,
        "wav2lip_onnx_present": wav2lip_ok,
        "external_provider_configured": external_provider_ok,
        # NEW: $0 free-provider features
        "free_providers": {
            "pollinations_ai": pollinations_ok,
            "huggingface": hf_ok,
        },
        "ai_b_roll_available": pollinations_ok or hf_ok,
        # Local CPU-only implementations — TRULY $0 with no external dependencies.
        "voice_cloning_available": local_voice_ok,  # Coqui XTTS-v2 local
        "ai_music_generation_available": local_music_ok,  # transformers MusicGen local
        "text_to_video_available": False,  # still requires GPU; not viable on CPU
        "hf_image_generation_available": hf_ok,
        "pollinations_tts_available": pollinations_ok,
        "pollinations_tts_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
        "voice_refs_uploaded": [r["voice_ref_id"] for r in voice_refs],
        "modes_available": {
            "faceless": ffmpeg and piper and bool(voices),
            "avatar_lipsync": ffmpeg and piper and bool(voices),
            "external_provider": external_provider_ok,
        },
        "external_provider_status": external.provider_status(),
        "operator_actions": _operator_hints(ffmpeg, piper, voices, pexels_key, mediapipe_ok, wav2lip_ok, hf_ok),
    }


def _operator_hints(
    ffmpeg: bool, piper: bool, voices: list, pexels: bool,
    mediapipe: bool, wav2lip: bool, hf: bool,
) -> list[str]:
    hints: list[str] = []
    if not ffmpeg:
        hints.append("Install ffmpeg: `sudo apt-get install -y ffmpeg`")
    if not piper:
        hints.append("Install Piper TTS: `pip install piper-tts`")
    if not voices:
        hints.append(
            "Download at least one voice into /app/data/voices/ — e.g. "
            "`curl -L https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx -o /app/data/voices/en_US-amy-medium.onnx` (plus the .json file)"
        )
    if not pexels:
        hints.append(
            "Add a PEXELS_API_KEY env var for real stock footage (free at "
            "https://www.pexels.com/api/). Without it the engine still renders, "
            "but uses solid-colour placeholder clips."
        )
    if not mediapipe:
        hints.append(
            "Optional: `pip install mediapipe` for face-aware avatar rendering. "
            "Without it, avatar mode falls back to centred Ken-Burns + audio meter."
        )
    if not wav2lip:
        hints.append(
            "Optional: drop a Wav2Lip ONNX model into /app/data/lipsync_models/wav2lip.onnx "
            "for photoreal lipsync. The free animated-portrait pipeline runs without it."
        )
    if not hf:
        hints.append(
            "Optional: set HUGGINGFACE_API_KEY (free at https://huggingface.co/settings/tokens) "
            "to unlock voice cloning (XTTS-v2), AI music (MusicGen), and text-to-video (AnimateDiff). "
            "All at $0/mo via the free Inference tier."
        )
    return hints
