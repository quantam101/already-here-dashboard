from models import ContentGenerateRequest
from emergentintegrations.llm.chat import LlmChat, UserMessage
import os
from dotenv import load_dotenv

load_dotenv()

async def generate_content(request: ContentGenerateRequest) -> str:
    """
    Generate content using AI based on the request parameters.
    Uses Emergent LLM key with Groq for zero-cost generation.
    """
    
    # Build the prompt based on request parameters
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
    
    api_key = os.getenv('EMERGENT_LLM_KEY')
    
    # Initialize LLM Chat with Groq (free tier)
    chat = LlmChat(
        api_key=api_key,
        session_id=f"content_gen_{request.content_type}",
        system_message="You are an expert content creator specializing in business and revenue-focused content. Create high-quality, engaging content that drives results."
    )
    
    # Use Gemini for cost-effective generation
    chat.with_model("gemini", "gemini-3-flash-preview")
    
    # Create user message
    user_message = UserMessage(text=prompt)
    
    # Generate content
    try:
        response = await chat.send_message(user_message)
        return response
    except Exception as e:
        # Fallback to simple template if AI fails
        return f"Content about {request.topic}\n\n[AI generation temporarily unavailable: {str(e)}]\n\nThis is a placeholder for {request.content_type} content. Please edit manually."