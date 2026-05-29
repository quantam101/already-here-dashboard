"""Viral-hook generator — the "first 4 seconds" hooks that the reference doc
calls the actual differentiator.

Single purpose: given a topic + niche + desired tone, return N hook variants
graded by pattern. Operator picks the strongest and ships it into the video
script. Powered by the same litellm-routed LLM that handles books / proposals.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from services.llm_runner import run_cached

router = APIRouter()


async def get_db():
    from server import db
    return db


SYSTEM_MSG = (
    "You are a viral-content strategist who specializes in the first 4 seconds of "
    "vertical short-form video (TikTok, Reels, Shorts). You write hooks that fight "
    "the thumb-swipe. You DO NOT write scripts, only hooks. Each hook MUST be one "
    "sentence, under 12 words, present-tense, and follow one of these 6 proven "
    "patterns: 1) negation hook ('Stop doing X'), 2) curiosity gap ('You'll never "
    "guess what...'), 3) bold claim ('I made $X in Y days'), 4) listicle preview "
    "('Three rules everyone breaks'), 5) controversy ('Everyone is wrong about X'), "
    "6) pattern interrupt (a counterintuitive single-word opener like 'Mistake.')."
    " Never use cliches like 'in this video' or 'today I'll show you'."
)

PATTERNS = {
    "negation": "Tell people to stop doing the dominant common practice in this niche.",
    "curiosity_gap": "Open a question they MUST scroll to answer.",
    "bold_claim": "Make a verifiable-sounding outcome claim with a number.",
    "listicle": "Preview the 3 most counterintuitive points of the video.",
    "controversy": "State that the conventional wisdom in this niche is wrong.",
    "pattern_interrupt": "A single jarring word that recontextualizes the topic.",
}


class HookRequest(BaseModel):
    topic: str = Field(..., description="The core idea / proof of the video")
    niche: str = Field("personal finance", description="Audience niche")
    tone: str = Field("direct", description="conversational / direct / academic / playful")
    count: int = Field(5, ge=1, le=10)


class HookVariant(BaseModel):
    pattern: str
    hook: str


class HookResponse(BaseModel):
    topic: str
    niche: str
    variants: list[HookVariant]


def _format_prompt(req: HookRequest) -> str:
    chosen = list(PATTERNS.items())[: req.count]
    bullets = "\n".join(f"- {name}: {desc}" for name, desc in chosen)
    return (
        f"Topic: {req.topic}\n"
        f"Niche: {req.niche}\n"
        f"Tone: {req.tone}\n\n"
        f"Generate exactly ONE hook for each of these {len(chosen)} patterns "
        f"(one hook per pattern, no duplicates):\n{bullets}\n\n"
        f"Return ONLY the hooks, no explanations. Format strictly as:\n"
        f"PATTERN: <pattern_name>\nHOOK: <one sentence under 12 words>\n\n"
        f"(repeat for each pattern, separated by blank line)"
    )


def _parse_hooks(raw: str) -> list[HookVariant]:
    out: list[HookVariant] = []
    current_pattern: str | None = None
    for raw_line in (raw or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("PATTERN:"):
            current_pattern = line.split(":", 1)[1].strip().lower()
        elif upper.startswith("HOOK:") and current_pattern:
            hook_text = line.split(":", 1)[1].strip().strip('"').strip()
            if hook_text:
                out.append(HookVariant(pattern=current_pattern, hook=hook_text))
                current_pattern = None
    return out


@router.post("/", response_model=HookResponse)
async def generate_hooks(req: HookRequest, db=Depends(get_db)):
    if not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required")
    raw = await run_cached(
        db, "gemini", "gemini-3-flash-preview",
        SYSTEM_MSG, _format_prompt(req),
        session_id=f"hooks-{req.niche[:20]}-{req.topic[:40]}",
        tier=3,
    )
    variants = _parse_hooks(raw)
    if not variants:
        # parser failed — surface the raw LLM output as one variant so the
        # operator can still copy/edit instead of returning empty
        variants = [HookVariant(pattern="raw", hook=raw.strip()[:200])]
    return HookResponse(topic=req.topic, niche=req.niche, variants=variants)
