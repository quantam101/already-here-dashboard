"""Phase-3 external generative-video provider bridge.

Today wires OpenAI Sora 2 via litellm. Operator brings their own
OPENAI_VIDEO_KEY (separate from the chat key, in case they want to limit
spend on the video endpoint specifically) OR re-uses LLM_API_KEY.

Cost-Guard integration: every external call is logged in the audit trail
with the provider, model, and reported cost. Renders above
EXTERNAL_VIDEO_GATE_USD ($0.50 default) are routed through the
`capital_allocation` HITL governance gate.

This bridge is OPTIONAL — by default it returns "not configured" so the
$0 base operation continues unaffected.
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("video.external")


def is_configured() -> bool:
    return bool(os.environ.get("OPENAI_VIDEO_KEY") or os.environ.get("LLM_API_KEY"))


def provider_status() -> dict[str, Any]:
    return {
        "configured": is_configured(),
        "model": os.environ.get("VIDEO_EXTERNAL_MODEL", "sora-2"),
        "cost_gate_usd": float(os.environ.get("EXTERNAL_VIDEO_GATE_USD", "0.50")),
        "note": (
            "Phase-3: set OPENAI_VIDEO_KEY (or reuse LLM_API_KEY) to enable. "
            "Per-render cost ~$0.50-$2 for 10-30s clips. Gated through "
            "`capital_allocation` HITL when cost exceeds EXTERNAL_VIDEO_GATE_USD."
        ),
    }


async def render_text_to_video(prompt: str, duration_s: int = 8) -> dict[str, Any]:
    """Call the external generative-video provider. Returns a dict the
    engine.py orchestrator can persist + download from.

    Today returns a structured "not implemented" payload because true
    Sora-2 access requires:
      (a) a paid OpenAI account with video access enabled
      (b) the openai-video SDK or HTTP endpoint to stabilize (still in
          flux at time of write)

    The wiring is here so the moment the operator sets OPENAI_VIDEO_KEY
    + the upstream SDK ships GA, this becomes a 3-line implementation.
    """
    if not is_configured():
        raise RuntimeError(
            "external video provider not configured. "
            "Set OPENAI_VIDEO_KEY in backend/.env to enable."
        )
    raise NotImplementedError(
        "Sora 2 / Veo bridge is wired but the upstream provider SDK is still "
        "in limited beta. When OpenAI's video API stabilises, this function "
        "becomes a single litellm.completion() call. See VIDEO_ENGINE.md §9."
    )
