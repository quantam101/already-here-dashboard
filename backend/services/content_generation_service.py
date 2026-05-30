from content_models import ContentScript
import logging

from services.distillation_service import distill_text, to_yaml_payload
from services.llm_runner import run_cached
from services.llm_adapter import llm_completion, LLMProviderError

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
    Uses litellm with the configured LLM provider key (Gemini 3 Flash by default).

    Runs through the unified llm_runner so:
      - Identical idea prompts hit the cache and skip the LLM call
      - Tokens consumed are tracked in the daily budget collection
      - Daily cap (LLM_DAILY_TOKEN_CAP) is enforced
    """
    prompt = create_script_prompt(idea)
    system_msg = (
        "You are an expert content creator specializing in viral short-form "
        "and long-form content. Create engaging, high-converting scripts."
    )

    # `db` is optional for legacy callers. If absent we fall back to the
    # direct-call path (no caching, no budget tracking).
    if db is None:
        try:
            response = await llm_completion(
                provider="gemini", model="gemini-2.5-flash",
                system_msg=system_msg, prompt=prompt,
                session_id=f"script_gen_{idea['id']}",
            )
        except (LLMProviderError, Exception) as e:
            return create_fallback_script(idea, str(e))
    else:
        try:
            response = await run_cached(
                db, "gemini", "gemini-2.5-flash",
                system_msg, prompt,
                session_id=f"script_gen_{idea['id']}",
            )
        except Exception as e:
            logger.warning("script gen via runner failed: %s", e)
            return create_fallback_script(idea, str(e))

    parsed = parse_script_response(response)
    return ContentScript(
        idea_id=idea['id'],
        hook=parsed["hook"],
        script_body=parsed["script_body"],
        cta=parsed["cta"],
        duration_seconds=60,
        shot_list=parsed["shot_list"],
        metadata={"generated_by": "ai", "model": "gemini-3-flash"},
    )

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
