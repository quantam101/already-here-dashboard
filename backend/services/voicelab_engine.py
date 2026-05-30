"""
Voice Lab Multi-Channel Matrix Engine.

Parallel TTS extraction from the Pollinations Unified Gateway API across
N voice channels (default: all 6 — alloy, echo, fable, onyx, nova, shimmer),
followed by a single ffmpeg pass that assembles them into a 2×3 diagnostic
grid MP4 with mixed audio.

Job states:
  pending → extracting → compiling → complete
                                    → failed

Output directory layout:
  /app/data/voicelab/{job_id}/
      voice_channel_alloy.mp3
      voice_channel_echo.mp3
      … (one per voice)
      voicelab_matrix_6up.mp4  ← final deliverable
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiohttp

logger = logging.getLogger("voicelab.engine")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VOICES: tuple[str, ...] = ("alloy", "echo", "fable", "onyx", "nova", "shimmer")
POLLINATIONS_TTS_URL = "https://gen.pollinations.ai/v1/audio/speech"
JOB_COLLECTION = "voicelab_jobs"
WORK_ROOT = Path(os.environ.get("VOICELAB_OUTPUT_DIR", "/app/data/voicelab"))
CONCURRENCY_LIMIT = 6

# Distinct dark-navy palette per voice (visible difference even without drawtext)
_VOICE_COLORS: dict[str, str] = {
    "alloy":   "0x0B132B",
    "echo":    "0x0D1B35",
    "fable":   "0x0A1A30",
    "onyx":    "0x071520",
    "nova":    "0x0C1E38",
    "shimmer": "0x091827",
}


# ---------------------------------------------------------------------------
# Job CRUD helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_job_id() -> str:
    return f"vlab-{uuid.uuid4().hex[:10]}"


async def create_job(db, *, script: str, selected_voices: list[str] | None = None) -> dict:
    """Create a pending job row in the DB and return it."""
    voices = list(selected_voices) if selected_voices else list(VOICES)
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    row: dict = {
        "id": new_job_id(),
        "script": script,
        "voices": voices,
        "status": "pending",
        "progress_pct": 0,
        "message": "queued — awaiting worker",
        "voice_results": {},   # voice → {path, size_bytes, status}
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
    return (
        await db[JOB_COLLECTION]
        .find({}, {"_id": 0})
        .sort("created_at", -1)
        .to_list(limit)
    )


async def _update(db, job_id: str, **changes) -> None:
    changes["updated_at"] = _now()
    await db[JOB_COLLECTION].update_one({"id": job_id}, {"$set": changes})


# ---------------------------------------------------------------------------
# Main pipeline  (called from BackgroundTasks)
# ---------------------------------------------------------------------------

async def run_pipeline(db, job_id: str) -> None:
    """Orchestrate the full extraction → compilation pipeline for one job."""
    job = await get_job(db, job_id)
    if not job:
        logger.error("voicelab run_pipeline: job %s not found", job_id)
        return

    voices: list[str] = job.get("voices") or list(VOICES)
    script: str = job["script"]
    work_dir = WORK_ROOT / job_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # ── Phase 1: concurrent TTS extraction ───────────────────────────────
    await _update(
        db, job_id,
        status="extracting",
        progress_pct=5,
        message=f"Dispatching {len(voices)} concurrent voice extraction workers…",
    )

    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    manifest: dict[str, Path] = {}
    extraction_errors: list[str] = []

    async with aiohttp.ClientSession() as session:
        tasks = [
            _extract_voice(session, script, voice, work_dir, semaphore)
            for voice in voices
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for voice, result in zip(voices, results):
        if isinstance(result, Exception):
            logger.error("voicelab: extraction failed for %s: %s", voice, result)
            extraction_errors.append(f"{voice}: {result}")
        else:
            manifest[voice] = result

    # Partial success: allow compilation if at least one voice extracted (grid
    # adapts to however many channels are available).
    if not manifest:
        await _update(
            db, job_id,
            status="failed",
            progress_pct=0,
            error=(
                f"All voice extractions failed. Errors: {'; '.join(extraction_errors[:4])}"
            ),
            message="Voice extraction failed — no channels available",
        )
        return

    if extraction_errors:
        logger.warning(
            "voicelab: partial extraction failure (%d/%d voices ok). Proceeding with available channels.",
            len(manifest), len(voices),
        )

    voice_results = {
        v: {"path": str(p), "size_bytes": p.stat().st_size, "status": "ok"}
        for v, p in manifest.items()
    }
    # Record any skipped voices
    for v in voices:
        if v not in manifest:
            voice_results[v] = {"status": "failed", "path": None, "size_bytes": 0}

    await _update(
        db, job_id,
        voice_results=voice_results,
        progress_pct=70,
        message=f"Extracted {len(manifest)}/{len(voices)} voice channels. Starting matrix compilation…",
    )

    # ── Phase 2: ffmpeg matrix compilation ───────────────────────────────
    await _update(
        db, job_id,
        status="compiling",
        progress_pct=75,
        message="Building 6-up analytical matrix via hardware-accelerated ffmpeg filtergraph…",
    )

    # Use only the successfully extracted voices
    available_voices = [v for v in voices if v in manifest]

    try:
        output_mp4 = _compile_matrix(manifest, available_voices, work_dir)
    except Exception as exc:
        logger.exception("voicelab: matrix compilation failed for job %s", job_id)
        await _update(
            db, job_id,
            status="failed",
            error=str(exc)[:500],
            message="ffmpeg compilation failed",
        )
        return

    await _update(
        db, job_id,
        status="complete",
        output_path=str(output_mp4),
        progress_pct=100,
        message=f"Matrix compilation complete — {len(available_voices)} voice channels rendered.",
    )
    logger.info("voicelab job %s complete → %s", job_id, output_mp4)


# ---------------------------------------------------------------------------
# TTS extraction worker
# ---------------------------------------------------------------------------

async def _extract_voice(
    session: aiohttp.ClientSession,
    script: str,
    voice: str,
    work_dir: Path,
    semaphore: asyncio.Semaphore,
    max_retries: int = 4,
    initial_backoff: float = 1.0,
) -> Path:
    """Download one voice channel MP3 from Pollinations TTS API.

    Uses exponential back-off on transient failures and validates the
    downloaded payload size before atomically renaming the temp file.
    """
    payload = {
        "input": script,
        "voice": voice,
        "model": "openai",
        "response_format": "mp3",
    }
    headers = {"Content-Type": "application/json"}
    api_key = os.environ.get("POLLINATIONS_API_KEY", "").strip()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    target_file = work_dir / f"voice_channel_{voice}.mp3"
    temp_file = target_file.with_suffix(".tmp")
    timeout = aiohttp.ClientTimeout(total=60)

    async with semaphore:
        backoff = initial_backoff
        last_err: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "voicelab: POST voice='%s' attempt=%d/%d",
                    voice, attempt, max_retries,
                )
                async with session.post(
                    POLLINATIONS_TTS_URL,
                    json=payload,
                    headers=headers,
                    timeout=timeout,
                ) as resp:
                    if resp.status == 200:
                        # Stream-write in 64 KB page blocks (memory-mapped chunk drain)
                        with open(temp_file, "wb") as fd:
                            async for chunk in resp.content.iter_chunked(65536):
                                fd.write(chunk)

                        size = temp_file.stat().st_size
                        if size < 1024:
                            raise ValueError(
                                f"Payload footprint ({size} B) below minimum validation "
                                f"threshold for voice='{voice}'"
                            )

                        # Atomic replacement — guarantees no partial files
                        temp_file.rename(target_file)
                        logger.info(
                            "voicelab: voice='%s' verified → %s (%d bytes)",
                            voice, target_file.name, target_file.stat().st_size,
                        )
                        return target_file

                    else:
                        body = await resp.text()
                        logger.warning(
                            "voicelab: HTTP %d for voice='%s': %.200s",
                            resp.status, voice, body,
                        )
                        last_err = RuntimeError(f"HTTP {resp.status}: {body[:120]}")

            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
                logger.error(
                    "voicelab: voice='%s' attempt %d error: %s",
                    voice, attempt, exc,
                )
                last_err = exc
            except Exception as exc:
                logger.error(
                    "voicelab: voice='%s' unexpected error: %s", voice, exc,
                )
                last_err = exc
            finally:
                # Always clean up temp file on error/retry
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except OSError:
                        pass

            if attempt < max_retries:
                logger.info(
                    "voicelab: backoff %.1fs before retry for voice='%s'",
                    backoff, voice,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30.0)

        raise RuntimeError(
            f"All {max_retries} extraction attempts failed for voice='{voice}'"
        ) from last_err


# ---------------------------------------------------------------------------
# ffmpeg matrix compilation
# ---------------------------------------------------------------------------

def _compile_matrix(
    manifest: dict[str, Path],
    voices: list[str],
    work_dir: Path,
) -> Path:
    """Build the N-up diagnostic grid MP4 using a single ffmpeg filtergraph pass.

    Architecture:
      Inputs 0..(n-1)  — lavfi color panels with centred voice label (video only)
      Inputs n..(2n-1) — MP3 audio files (audio only)

    The filter graph stacks inputs into a 2-row grid, scales to 1920×1080 at
    24 fps, and mixes all audio channels with equal weights.
    """
    if not shutil.which("ffmpeg"):
        raise FileNotFoundError(
            "ffmpeg binary not found in PATH — cannot compile matrix"
        )

    output_mp4 = work_dir / "voicelab_matrix_6up.mp4"
    n = len(voices)

    # Build a balanced grid: top row = first half, bottom row = second half
    top = voices[: (n + 1) // 2]
    bottom = voices[(n + 1) // 2 :]

    cmd = _build_ffmpeg_cmd(manifest, voices, top, bottom, output_mp4, use_drawtext=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        logger.warning(
            "voicelab: ffmpeg with drawtext failed (likely missing libfreetype). "
            "Retrying without text overlay. stderr: %.300s",
            proc.stderr,
        )
        cmd_no_text = _build_ffmpeg_cmd(
            manifest, voices, top, bottom, output_mp4, use_drawtext=False
        )
        proc2 = subprocess.run(cmd_no_text, capture_output=True, text=True)
        if proc2.returncode != 0:
            raise RuntimeError(
                f"ffmpeg matrix compilation failed:\n{proc2.stderr[:600]}"
            )

    return output_mp4


def _hstack_expr(indices: list[int]) -> str:
    """Build an hstack filter expression for the given stream indices."""
    if len(indices) == 1:
        return f"[{indices[0]}:v]copy"
    streams = "".join(f"[{i}:v]" for i in indices)
    return f"{streams}hstack=inputs={len(indices)}"


def _build_ffmpeg_cmd(
    manifest: dict[str, Path],
    voices: list[str],
    top: list[str],
    bottom: list[str],
    output_mp4: Path,
    use_drawtext: bool = True,
) -> list[str]:
    """Assemble the complete ffmpeg command list."""
    n = len(voices)
    top_idx = list(range(len(top)))
    bottom_idx = list(range(len(top), len(top) + len(bottom)))

    filter_parts: list[str] = []

    # Row stacking
    top_expr = _hstack_expr(top_idx)
    filter_parts.append(f"{top_expr}[top_row]")

    if bottom:
        bottom_expr = _hstack_expr(bottom_idx)
        filter_parts.append(f"{bottom_expr}[bottom_row]")
        filter_parts.append("[top_row][bottom_row]vstack=inputs=2[raw_grid]")
    else:
        filter_parts.append("[top_row]copy[raw_grid]")

    filter_parts.append("[raw_grid]scale=1920:1080,fps=24[v_compiled]")

    # Audio mix
    audio_in = "".join(f"[{n + i}:a]" for i in range(n))
    weights = " ".join("1" for _ in range(n))
    filter_parts.append(
        f"{audio_in}amix=inputs={n}:duration=longest:weights={weights}[a_mixed]"
    )

    cmd: list[str] = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]

    # Inputs 0..(n-1): lavfi video panels
    for voice in voices:
        color = _VOICE_COLORS.get(voice, "0x0B132B")
        if use_drawtext:
            label = voice.upper()
            video_filter = (
                f"color=c={color}:s=640x360:r=24,"
                f"drawtext=text='{label}'"
                f":fontcolor=0x48CAE4:fontsize=54"
                f":x=(w-tw)/2:y=(h-th)/2"
            )
        else:
            video_filter = f"color=c={color}:s=640x360:r=24"
        cmd += ["-f", "lavfi", "-i", video_filter]

    # Inputs n..(2n-1): MP3 audio files
    for voice in voices:
        cmd += ["-i", str(manifest[voice])]

    # Filters + output
    cmd += [
        "-filter_complex", "; ".join(filter_parts),
        "-map", "[v_compiled]",
        "-map", "[a_mixed]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "256k",
        "-shortest",           # stop when the shortest input (audio) ends
        str(output_mp4),
    ]
    return cmd
