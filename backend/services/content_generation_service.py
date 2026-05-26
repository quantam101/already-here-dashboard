from content_models import ContentScript
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
import logging

from services.distillation_service import (
    cache_lookup, cache_store, distill_text, to_yaml_payload,
)

logger = logging.getLogger(__name__)

SECTION_MARKERS = {
    "HOOK:": "hook",
    "SCRIPT:": "script",
    "CTA:": "cta",
    "SHOTS:": "shots",
}

DEFAULT_HOOK = "Stop scrolling! This is important."
DEFAULT_CTA = "Follow for more content like this!"
DEFAULT_SHOTS = ["Opening shot", "Main content", "B-roll", "CTA visual"]


def _extract_section(line: str) -> tuple[str | None, str]:
    """Return (section_name, content) if line starts with a known marker, else (None, '')."""
    for marker, name in SECTION_MARKERS.items():
        if line.startswith(marker):
            return name, line.replace(marker, "").strip()
    return None, ""


def parse_script_response(response: str) -> dict:
    """Parse AI response into script components."""
    sections = {"hook": "", "script_body": "", "cta": "", "shot_list": []}
    current_section = None

    for line in response.split('\n'):
        section_name, content = _extract_section(line)

        if section_name:
            current_section = section_name
            if section_name == "shots":
                sections["shot_list"] = [s.strip() for s in content.split(',') if s.strip()]
            elif section_name == "script":
                sections["script_body"] = content
            else:
                sections[section_name] = content
        elif current_section == "script" and line.strip():
            sections["script_body"] += " " + line.strip()

    return {
        "hook": sections["hook"] or DEFAULT_HOOK,
        "script_body": sections["script_body"] or response,
        "cta": sections["cta"] or DEFAULT_CTA,
        "shot_list": sections["shot_list"] or DEFAULT_SHOTS,
    }

def create_script_prompt(idea: dict) -> str:
    """Create the AI prompt for script generation.

    Uses YAML for the idea payload (token-cheaper than embedding fields inline
    in prose) and applies semantic compression to the wrapper text.
    """
    payload = to_yaml_payload({
        "title": idea.get("title", ""),
        "description": idea.get("description", ""),
        "topic": idea.get("topic", ""),
        "platforms": idea.get("target_platforms", []),
    })
    raw = f"""Create a compelling content script for this idea.

IDEA (YAML):
{payload}

Produce:
1. Hook (first 3 seconds, stop-the-scroll)
2. Script body (engaging, concise, value-driven)
3. CTA (call to action)
4. Shot list (5-7 visual scenes)

Format exactly:
HOOK: [hook text]
SCRIPT: [script body]
CTA: [call to action]
SHOTS: [shot 1], [shot 2], [shot 3], ...
"""
    return distill_text(raw)

def create_fallback_script(idea: dict, error: str) -> ContentScript:
    """Create a template script when AI generation fails."""
    return ContentScript(
        idea_id=idea['id'],
        hook=f"Discover the secret to {idea['title']}",
        script_body=f"{idea['description']}\n\n[AI generation temporarily unavailable: {error}]\n\nThis is a template script. Edit to customize.",
        cta="Follow for more valuable content!",
        duration_seconds=60,
        shot_list=["Opening hook", "Main point 1", "Main point 2", "Proof/example", "Call to action"],
        metadata={"generated_by": "template", "error": error}
    )

async def generate_script_from_idea(idea: dict, db=None) -> ContentScript:
    """
    Generate a content script from an idea using AI.
    Uses Emergent LLM key with Gemini for zero-cost generation.

    Tier-2 distillation: cache lookup on a fingerprint of
    (model, system_msg, distilled_prompt). On cache hit we skip the LLM
    entirely and reconstruct the ContentScript from the cached response.
    """
    prompt = create_script_prompt(idea)
    api_key = os.getenv('EMERGENT_LLM_KEY')
    model_id = "gemini/gemini-3-flash-preview"
    system_msg = (
        "You are an expert content creator specializing in viral short-form "
        "and long-form content. Create engaging, high-converting scripts."
    )

    # Cache lookup (best-effort — never fails the request)
    cached_response: str | None = None
    if db is not None:
        try:
            hit = await cache_lookup(db, model_id, system_msg, prompt)
            if hit and hit.get("response"):
                cached_response = hit["response"]
                logger.info("distillation: cache HIT idea=%s tokens_saved≈%s",
                            idea.get("id"), hit.get("tokens_out_est", 0))
        except Exception as e:
            logger.warning("distillation cache lookup failed: %s", e)

    if cached_response is not None:
        parsed = parse_script_response(cached_response)
        return ContentScript(
            idea_id=idea['id'],
            hook=parsed["hook"],
            script_body=parsed["script_body"],
            cta=parsed["cta"],
            duration_seconds=60,
            shot_list=parsed["shot_list"],
            metadata={"generated_by": "ai_cached", "model": "gemini-3-flash", "cache_hit": True}
        )

    chat = LlmChat(
        api_key=api_key,
        session_id=f"script_gen_{idea['id']}",
        system_message=system_msg,
    )

    chat.with_model("gemini", "gemini-3-flash-preview")
    user_message = UserMessage(text=prompt)

    try:
        response = await chat.send_message(user_message)
        parsed = parse_script_response(response)

        # Best-effort cache store
        if db is not None:
            try:
                await cache_store(db, model_id, system_msg, prompt, response, tier=3)
            except Exception as e:
                logger.warning("distillation cache store failed: %s", e)

        script = ContentScript(
            idea_id=idea['id'],
            hook=parsed["hook"],
            script_body=parsed["script_body"],
            cta=parsed["cta"],
            duration_seconds=60,
            shot_list=parsed["shot_list"],
            metadata={"generated_by": "ai", "model": "gemini-3-flash", "cache_hit": False}
        )

        return script

    except Exception as e:
        return create_fallback_script(idea, str(e))

async def generate_captions_for_platform(script: dict, platform: str) -> str:
    """Generate platform-specific captions with hashtags."""
    platform_limits = {
        "tiktok": 2200,
        "youtube_shorts": 100,
        "instagram": 2200,
        "twitter": 280,
        "linkedin": 3000,
    }
    
    max_length = platform_limits.get(platform, 2000)
    caption = f"{script['hook']}\n\n{script['script_body'][:max_length - 200]}\n\n{script['cta']}"
    
    return caption

def get_base_hashtags(topic: str) -> list:
    """Generate base hashtags for any topic."""
    return [
        f"#{topic.replace(' ', '')}",
        "#content",
        "#viral",
        "#fyp",
        "#trending"
    ]

def get_platform_hashtags(platform: str) -> list:
    """Get platform-specific hashtags."""
    platform_tags = {
        "tiktok": ["#tiktok", "#foryou", "#foryoupage"],
        "instagram": ["#instagram", "#reels", "#instagood"],
        "youtube": ["#youtube", "#shorts", "#viral"],
        "twitter": ["#twitter", "#thread"],
        "linkedin": ["#linkedin", "#professional", "#business"],
    }
    return platform_tags.get(platform, [])

async def generate_hashtags(topic: str, platform: str) -> list:
    """Generate relevant hashtags for the topic and platform."""
    base_tags = get_base_hashtags(topic)
    platform_tags = get_platform_hashtags(platform)
    tags = base_tags + platform_tags
    return tags[:10]  # Limit to 10 hashtags
