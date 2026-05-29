from models import ContentGenerateRequest
from dotenv import load_dotenv
from services.llm_adapter import llm_completion

load_dotenv()


async def generate_content(request: ContentGenerateRequest) -> str:
    """
    Generate content using the configured LLM provider (vendor-neutral via litellm).
    Uses Gemini 3 Flash by default for cost-effective generation. The buyer can
    swap providers/models via the LLM_TIER_MID_* env vars.
    """
    prompt = f"""Generate {request.content_type} content about: {request.topic}

Tone: {request.tone}
Length: {request.length}
Keywords to include: {', '.join(request.keywords) if request.keywords else 'None'}
"""
    if request.platform:
        prompt += f"\nPlatform: {request.platform}\n"

    if request.content_type == "blog":
        prompt += "\nCreate an engaging blog post with introduction, main points, and conclusion."
    elif request.content_type == "social":
        prompt += "\nCreate concise, engaging social media content."
    elif request.content_type == "email":
        prompt += "\nCreate professional email content with subject line."
    elif request.content_type == "proposal":
        prompt += "\nCreate a professional business proposal with clear value proposition."

    try:
        return await llm_completion(
            provider="gemini",
            model="gemini-3-flash-preview",
            system_msg=(
                "You are an expert content creator specializing in business and "
                "revenue-focused content. Create high-quality, engaging content "
                "that drives results."
            ),
            prompt=prompt,
            session_id=f"content_gen_{request.content_type}",
        )
    except Exception as e:
        return (
            f"Content about {request.topic}\n\n[AI generation temporarily "
            f"unavailable: {str(e)}]\n\nThis is a placeholder for "
            f"{request.content_type} content. Please edit manually."
        )
