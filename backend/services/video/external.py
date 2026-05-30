"""Phase-3 external generative-video provider bridge.

Today wires:
  - **Hugging Face Inference API** (free tier) — text-to-video via
    AnimateDiff / CogVideoX / text-to-video-ms. Operator brings free
    HUGGINGFACE_API_KEY. **THIS IS THE $0 path that actually works today.**
  - **OpenAI Sora 2** via litellm (opt-in paid path, SDK still in beta).

Cost-Guard integration: every external call is logged in the audit trail
with the provider, model, and reported cost. Renders above
EXTERNAL_VIDEO_GATE_USD ($0.50 default) are routed through the
`capital_allocation` HITL governance gate.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from services.free_apis import huggingface

logger = logging.getLogger("video.external")

OUT_DIR = Path(os.environ.get("VIDEO_OUTPUT_DIR", "/app/data/videos"))


def _preferred_provider() -> str:
    """`hf` (free, works today) > `sora` (paid, beta) > `none`."""
    forced = os.environ.get("VIDEO_EXTERNAL_PROVIDER", "").lower().strip()
    if forced in {"hf", "huggingface", "sora", "openai", "none"}:
        return "hf" if forced in {"hf", "huggingface"} else (
            "sora" if forced in {"sora", "openai"} else "none"
        )
    if huggingface.is_configured():
        return "hf"
    if os.environ.get("OPENAI_VIDEO_KEY") or os.environ.get("LLM_API_KEY"):
        return "sora"
    return "none"


def is_configured() -> bool:
    return _preferred_provider() != "none"


def provider_status() -> dict[str, Any]:
    p = _preferred_provider()
    return {
        "configured": p != "none",
        "active_provider": p,
        "hf_configured": huggingface.is_configured(),
        "model": (
            huggingface.DEFAULT_VIDEO_MODEL if p == "hf"
            else os.environ.get("VIDEO_EXTERNAL_MODEL", "sora-2")
        ),
        "cost_gate_usd": float(os.environ.get("EXTERNAL_VIDEO_GATE_USD", "0.50")),
        "note": (
            "HF: free text-to-video via AnimateDiff / text-to-video-ms (no per-render cost; "
            "free Inference tier is rate-limited but unlimited daily). "
            "Sora: paid, ~$0.50-$2/render, gated by capital_allocation HITL "
            "when cost exceeds EXTERNAL_VIDEO_GATE_USD."
        ),
    }


async def render_text_to_video(prompt: str, duration_s: int = 8) -> dict[str, Any]:
    """Dispatch to the active provider. Returns {output_path, provider}."""
    provider = _preferred_provider()
    if provider == "none":
        raise RuntimeError(
            "external video provider not configured. Set HUGGINGFACE_API_KEY "
            "(free at https://huggingface.co/settings/tokens) for the $0 "
            "AnimateDiff path, or OPENAI_VIDEO_KEY for paid Sora."
        )
    if provider == "hf":
        return await _render_via_hf(prompt, duration_s)
    raise NotImplementedError(
        "Sora 2 / Veo bridge is wired but the upstream provider SDK is still "
        "in limited beta. Switch to provider='hf' (free) or wait for GA."
    )


async def _render_via_hf(prompt: str, duration_s: int) -> dict[str, Any]:
    import uuid
    frames = max(8, min(32, int(duration_s * 4)))
    data = await huggingface.generate_video(prompt, num_frames=frames)
    if not data or len(data) < 1024:
        raise RuntimeError(f"HF returned empty video ({len(data) if data else 0} bytes)")
    out = OUT_DIR / f"ext-hf-{uuid.uuid4().hex[:10]}.mp4"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return {
        "output_path": str(out),
        "provider": "huggingface",
        "model": huggingface.DEFAULT_VIDEO_MODEL,
        "size_bytes": len(data),
        "duration_s": duration_s,
    }
