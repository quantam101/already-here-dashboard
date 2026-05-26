"""
AI Operations Advisor - reads the live dashboard (ledger + analytics + scout)
and asks Claude Sonnet for the single best next action.

Cost Guard: uses Emergent LLM Key ($0 to operator).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage  # noqa: F401
from routes.analytics import (
    conversion_funnel, stream_roi, momentum, viral_themes, platform_mix,
)
from services.distillation_service import to_yaml_payload
from services.llm_runner import run_cached

router = APIRouter()


class AdvisorRecommendation(BaseModel):
    id: str
    generated_at: str
    headline: str
    next_action: str
    rationale: str
    confidence: str  # low | medium | high
    cost: str = "$0"
    raw_context: dict


async def get_db():
    from server import db
    return db


SYSTEM_MSG = (
    "You are the AI Operations Advisor for the Already Here Command OS, a zero-spend "
    "($0/month) governed AI revenue operating system. Read the live dashboard JSON "
    "context and return ONE prioritized next action that maximises progress toward "
    "the $25,000 net-profit unlock goal. Be specific, evidence-driven, brutally honest. "
    "Always reply in this exact JSON shape:\n"
    "{ \"headline\": \"<one-line summary>\","
    " \"next_action\": \"<specific actionable instruction the operator can do RIGHT NOW>\","
    " \"rationale\": \"<2-3 sentence why, citing the data>\","
    " \"confidence\": \"low|medium|high\" }"
)


@router.post("/recommend", response_model=AdvisorRecommendation)
async def get_recommendation(db=Depends(get_db)):
    """Pull live context, ask Claude, return a single next-action."""
    # Gather live snapshot
    context = {
        "funnel": await conversion_funnel(db),
        "stream_roi": await stream_roi(db),
        "momentum": await momentum(db),
        "viral_themes": await viral_themes(db),
        "platform_mix": await platform_mix(db),
    }

    # YAML payload is ~25-40% fewer tokens than the equivalent indented JSON.
    yaml_ctx = to_yaml_payload(context)
    prompt = (
        "Live dashboard snapshot below (YAML). Return ONE prioritized next "
        "action as JSON.\n\n```yaml\n" + yaml_ctx[:5000] + "\n```"
    )

    raw = await run_cached(
        db, "anthropic", "claude-sonnet-4-5-20250929",
        SYSTEM_MSG, prompt,
        session_id=f"adv_{uuid.uuid4().hex[:8]}",
    )

    # Extract first JSON object from response
    parsed: dict = {}
    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
    except Exception:
        parsed = {
            "headline": "Advisor returned unstructured text",
            "next_action": raw[:300],
            "rationale": "Raw LLM output - could not parse JSON",
            "confidence": "low",
        }

    rec = AdvisorRecommendation(
        id=f"adv-{uuid.uuid4().hex[:10]}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        headline=parsed.get("headline", "")[:240],
        next_action=parsed.get("next_action", "")[:1000],
        rationale=parsed.get("rationale", "")[:1000],
        confidence=parsed.get("confidence", "medium"),
        raw_context=context,
    )
    await db.advisor_recommendations.insert_one(rec.model_dump())
    return rec


@router.get("/recent")
async def recent_recommendations(limit: int = 10, db=Depends(get_db)):
    rows = await db.advisor_recommendations.find({}, {"_id": 0, "raw_context": 0}).sort("generated_at", -1).to_list(limit)
    return rows
