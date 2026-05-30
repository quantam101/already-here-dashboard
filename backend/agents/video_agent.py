"""
VideoScriptAgent — generates production-ready faceless video scripts.

For each trending opportunity, produces:
  • Hook (first 3 seconds — pattern-interrupt opening line)
  • Narration sections (5–8 bullet points, each ~15s of speech)
  • B-roll notes (what stock footage/visuals to show per section)
  • CTA (call-to-action for last 5 seconds)
  • CapCut export pack (ready to paste into CapCut text-to-speech)
  • Caption + hashtags for TikTok / YouTube Shorts / Instagram Reels

Output is stored in content_ideas.video_script and in a new video_scripts collection.

Cost: $0 — uses LLM from the 11-provider free failover chain.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from agents.base_agent import AgentResult, BaseAgent
from services.llm_runner import llm_complete

logger = logging.getLogger("video_agent")

_SYSTEM_PROMPT = """You are a viral short-form video scriptwriter for faceless YouTube / TikTok content.
Your scripts use the PAS (Problem → Agitate → Solution) framework. Voice: punchy, direct, no filler words.
Output ONLY valid JSON — no markdown fences, no explanation."""

_USER_PROMPT_TEMPLATE = """Write a faceless video script for the following topic.

Topic: {title}
Summary: {summary}
Target platforms: TikTok, YouTube Shorts, Instagram Reels (60–90 seconds)

Return EXACTLY this JSON structure:
{{
  "hook": "Opening line (max 15 words) — must create curiosity or shock",
  "narration": [
    {{"text": "Section 1 narration (1–2 sentences)", "broll": "what stock footage to show"}},
    {{"text": "Section 2 narration", "broll": "suggested b-roll"}},
    {{"text": "Section 3 narration", "broll": "suggested b-roll"}},
    {{"text": "Section 4 narration", "broll": "suggested b-roll"}},
    {{"text": "Section 5 narration", "broll": "suggested b-roll"}}
  ],
  "cta": "Final 5-second call to action (max 20 words)",
  "caption": "TikTok/IG caption (max 200 chars)",
  "hashtags": ["hashtag1", "hashtag2", "hashtag3", "hashtag4", "hashtag5"],
  "capcut_script": "Full script joined into one block for CapCut TTS paste"
}}"""


def _build_capcut_script(hook: str, narration: list[dict], cta: str) -> str:
    """Assemble the full narration as a single paste-able block for CapCut TTS."""
    parts = [hook]
    for section in narration:
        parts.append(section.get("text", ""))
    parts.append(cta)
    return "\n\n".join(p.strip() for p in parts if p.strip())


def _parse_llm_json(raw: str) -> dict:
    """Extract JSON from LLM response, tolerating minor formatting issues."""
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw, flags=re.I).strip().rstrip("`").strip()
    import json
    return json.loads(raw)


async def generate_video_script(title: str, summary: str) -> dict:
    """
    Standalone coroutine — can be called from routes or other agents.
    Returns a dict with keys: hook, narration, cta, caption, hashtags, capcut_script.
    """
    prompt = _USER_PROMPT_TEMPLATE.format(
        title=title,
        summary=summary[:600] if summary else title,
    )
    raw = await llm_complete(
        system=_SYSTEM_PROMPT,
        user=prompt,
        max_tokens=1200,
        temperature=0.7,
    )

    try:
        script = _parse_llm_json(raw)
        # Ensure capcut_script is present even if LLM omitted it
        if not script.get("capcut_script"):
            script["capcut_script"] = _build_capcut_script(
                script.get("hook", title),
                script.get("narration", []),
                script.get("cta", "Follow for more."),
            )
        return script
    except Exception as e:
        logger.warning("video_agent: JSON parse failed, building fallback. raw=%s err=%s", raw[:200], e)
        # Fallback: construct a minimal script from the raw text
        sentences = [s.strip() for s in re.split(r"[.!?]+", summary or title) if len(s.strip()) > 15]
        hook = sentences[0] if sentences else title[:100]
        narration_sections = [
            {"text": s, "broll": "relevant stock footage"} for s in sentences[1:6]
        ]
        cta = "Follow for daily insights on this topic."
        return {
            "hook": hook,
            "narration": narration_sections or [{"text": summary or title, "broll": "stock footage"}],
            "cta": cta,
            "caption": f"{title[:150]} #viral #trending #ai",
            "hashtags": ["viral", "trending", "ai", "contentcreator", "faceless"],
            "capcut_script": _build_capcut_script(hook, narration_sections, cta),
        }


class VideoScriptAgent(BaseAgent):
    """
    Picks up content_ideas that have status=drafted but no video_script,
    generates a production-ready faceless video script for each,
    and stores it back in the idea document.

    Registers as 'video-agent' in the agent executor.
    """
    agent_id = "video-agent"
    agent_name = "Faceless Video Script Agent"
    description = "Generates TikTok/YouTube Shorts/Reels scripts for trending ideas"
    cost_class = "free_local"

    async def execute(self, db, ctx: dict) -> AgentResult:
        ts = datetime.now(UTC).isoformat()
        ideas_processed = 0
        scripts_generated = 0
        errors = []

        try:
            # Find ideas that need video scripts
            all_ideas = await db.content_ideas.find(
                {"status": {"$in": ["drafted", "scripted"]}, "video_script": {"$exists": False}},
                {"_id": 0},
                limit=5,
            )
            ideas = list(all_ideas) if not isinstance(all_ideas, list) else all_ideas
        except Exception as e:
            return AgentResult(
                self.agent_id, f"run-{ts}",
                success=False, error=f"DB query failed: {e}",
            )

        for idea in ideas:
            idea_id = idea.get("id", "unknown")
            title = idea.get("title", "")
            summary = idea.get("description", "")
            ideas_processed += 1

            try:
                script = await generate_video_script(title, summary)
                script["generated_at"] = ts
                script["idea_id"] = idea_id

                # Store in idea document
                await db.content_ideas.update_one(
                    {"id": idea_id},
                    {"$set": {
                        "video_script": script,
                        "status": "scripted",
                        "updated_at": ts,
                    }},
                )

                # Also store in video_scripts collection for independent querying
                script_doc = {
                    "id": f"vs-{idea_id}",
                    "idea_id": idea_id,
                    "title": title,
                    **script,
                    "created_at": ts,
                }
                # Upsert so re-runs don't duplicate
                try:
                    await db.video_scripts.update_one(
                        {"idea_id": idea_id},
                        {"$set": script_doc},
                        upsert=True,
                    )
                except Exception:
                    pass  # Collection may not exist; non-fatal

                scripts_generated += 1
                logger.info("video_agent: script generated for idea=%s", idea_id)

            except Exception as e:
                errors.append(f"{idea_id}: {e}")
                logger.warning("video_agent: script failed for %s: %s", idea_id, e)

        return AgentResult(
            self.agent_id, f"run-{ts}",
            success=True,
            data={
                "ideas_processed": ideas_processed,
                "scripts_generated": scripts_generated,
                "errors": errors,
            },
            tokens_used=0,
        )
