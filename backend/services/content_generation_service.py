from content_models import ContentScript, ContentIdea
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
import uuid
from datetime import datetime, timezone

def parse_script_response(response: str) -> dict:
    """Parse AI response into script components."""
    lines = response.split('\n')
    hook = ""
    script_body = ""
    cta = ""
    shot_list = []
    
    current_section = None
    for line in lines:
        if line.startswith("HOOK:"):
            hook = line.replace("HOOK:", "").strip()
            current_section = "hook"
        elif line.startswith("SCRIPT:"):
            script_body = line.replace("SCRIPT:", "").strip()
            current_section = "script"
        elif line.startswith("CTA:"):
            cta = line.replace("CTA:", "").strip()
            current_section = "cta"
        elif line.startswith("SHOTS:"):
            shots_text = line.replace("SHOTS:", "").strip()
            shot_list = [s.strip() for s in shots_text.split(',')]
            current_section = "shots"
        elif current_section == "script" and line.strip():
            script_body += " " + line.strip()
    
    return {
        "hook": hook or "Stop scrolling! This is important.",
        "script_body": script_body or response,
        "cta": cta or "Follow for more content like this!",
        "shot_list": shot_list or ["Opening shot", "Main content", "B-roll", "CTA visual"]
    }

def create_script_prompt(idea: dict) -> str:
    """Create the AI prompt for script generation."""
    return f"""Create a compelling content script for the following idea:

Title: {idea['title']}
Description: {idea['description']}
Topic: {idea['topic']}
Target Platforms: {', '.join(idea.get('target_platforms', []))}

Generate:
1. A powerful hook (first 3 seconds that stops the scroll)
2. Main script body (engaging, concise, value-driven)
3. Strong call-to-action
4. Shot list (5-7 visual scenes)

Format as:
HOOK: [hook text]
SCRIPT: [script body]
CTA: [call to action]
SHOTS: [shot 1], [shot 2], [shot 3], etc.
"""

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

async def generate_script_from_idea(idea: dict) -> ContentScript:
    """
    Generate a content script from an idea using AI.
    Uses Emergent LLM key with Gemini for zero-cost generation.
    """
    prompt = create_script_prompt(idea)
    api_key = os.getenv('EMERGENT_LLM_KEY')
    
    chat = LlmChat(
        api_key=api_key,
        session_id=f"script_gen_{idea['id']}",
        system_message="You are an expert content creator specializing in viral short-form and long-form content. Create engaging, high-converting scripts."
    )
    
    chat.with_model("gemini", "gemini-3-flash-preview")
    user_message = UserMessage(text=prompt)
    
    try:
        response = await chat.send_message(user_message)
        parsed = parse_script_response(response)
        
        script = ContentScript(
            idea_id=idea['id'],
            hook=parsed["hook"],
            script_body=parsed["script_body"],
            cta=parsed["cta"],
            duration_seconds=60,
            shot_list=parsed["shot_list"],
            metadata={"generated_by": "ai", "model": "gemini-3-flash"}
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
