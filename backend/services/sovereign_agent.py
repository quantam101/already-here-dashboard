"""
SovereignAgent — The governing AI at the top of the hierarchy.

Architecture (declarative, not imperative):
  ┌─────────────────────────────────────────────────┐
  │              SOVEREIGN (this module)             │
  │  • Reads system snapshot from DB collections    │
  │  • Calls Gemini 2.0 Flash with YAML context     │
  │  • Receives SovereignDecision JSON              │
  │  • Dispatches agent tasks to AgentExecutor      │
  │  • Logs every decision to audit trail           │
  └────────────────────┬────────────────────────────┘
                       │ dispatches
         ┌─────────────┼──────────────┬──────────────┐
         ▼             ▼              ▼              ▼
    GuardAgent   ScoutAgent   ContentAgent  RevenueAgent
    (15 min)     (hourly)     (6 hours)     (30 min)

Decision schema the LLM must return:
  {
    "priority_action": "string",          # human-readable
    "agents_to_run": ["agent-id", ...],   # subset of registered agents
    "reasoning": "string",               # 1-2 sentences
    "risk_level": "low|medium|high",
    "estimated_tokens": 0,
    "skip_reason": null                  # non-null if sovereign decides to skip
  }

The Sovereign's decision is cached for 55 minutes (decision_ttl_seconds from manifest).
Only one active sovereign cycle runs at a time (asyncio.Lock).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime

from services.audit_service import log_audit_event
from services.distillation_service import to_yaml_payload
from services.llm_runner import run_cached

logger = logging.getLogger("sovereign_agent")

SOVEREIGN_COLLECTION = "sovereign_decisions"
AGENT_RUNS_COLLECTION = "agent_runs"
SYSTEM_HEALTH_COLLECTION = "system_health"
SNAPSHOTS_COLLECTION = "revenue_snapshots"

_SOVEREIGN_LOCK = asyncio.Lock()

SOVEREIGN_SYSTEM = """You are Cash, the governing AI of the Already Here Command OS.
Mission: maximize net revenue toward $25,000 while running at $0/month fixed cost.
You receive a YAML system snapshot. Return ONLY a valid JSON SovereignDecision.
Think step by step. Prefer high-leverage, low-cost, reversible actions.
Never exceed safety limits. Protect the operator's interests above all."""

DECISION_PROMPT = """System snapshot:
{snapshot_yaml}

Available agents: {agent_ids}

Return ONLY valid JSON:
{{
  "priority_action": "one sentence describing the most important thing to do now",
  "agents_to_run": ["list", "of", "agent-ids", "to", "dispatch"],
  "reasoning": "1-2 sentences explaining why",
  "risk_level": "low",
  "estimated_tokens": 0,
  "skip_reason": null
}}

Rules:
- always include guard-agent in agents_to_run (safety first)
- skip_reason should be null unless system is in a degraded/overbudget state
- risk_level is low/medium/high based on tokens being spent
- estimated_tokens is your rough estimate of total tokens all chosen agents will use"""


class SovereignDecision:
    __slots__ = (
        "decision_id", "priority_action", "agents_to_run", "reasoning",
        "risk_level", "estimated_tokens", "skip_reason",
        "made_at", "session_id",
    )

    def __init__(self, raw: dict, session_id: str):
        self.decision_id = f"sov-{uuid.uuid4().hex[:10]}"
        self.priority_action = raw.get("priority_action", "")
        self.agents_to_run: list[str] = raw.get("agents_to_run", [])
        self.reasoning = raw.get("reasoning", "")
        self.risk_level = raw.get("risk_level", "low")
        self.estimated_tokens = int(raw.get("estimated_tokens", 0))
        self.skip_reason = raw.get("skip_reason")
        self.made_at = datetime.now(UTC).isoformat()
        self.session_id = session_id

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


async def _build_snapshot(db) -> dict:
    """Collect a lightweight system state snapshot for the Sovereign's context."""
    now = datetime.now(UTC).isoformat()

    # Recent agent run summary
    try:
        recent_runs = await db[AGENT_RUNS_COLLECTION].find(
            {}, {"_id": 0, "agent_id": 1, "success": 1, "started_at": 1}
        ).sort("started_at", -1).to_list(20)
    except Exception:
        recent_runs = []

    # Revenue snapshot
    try:
        rev = await db[SNAPSHOTS_COLLECTION].find_one(
            {}, {"_id": 0}, sort=[("timestamp", -1)]
        )
    except Exception:
        rev = {}

    # System health
    try:
        health = await db[SYSTEM_HEALTH_COLLECTION].find_one(
            {}, {"_id": 0}, sort=[("timestamp", -1)]
        )
    except Exception:
        health = {}

    # Content queue depth
    try:
        queue_depth = await db["content_queue"].count_documents({"status": "ready"})
    except Exception:
        queue_depth = 0

    # Opportunities unprocessed
    try:
        opp_count = await db["scout_opportunities"].count_documents(
            {"processed": {"$ne": True}}
        )
    except Exception:
        opp_count = 0

    return {
        "timestamp": now,
        "revenue": {
            "net_usd": (rev or {}).get("net_usd", 0.0),
            "unlock_pct": (rev or {}).get("unlock_pct", 0.0),
            "last_7d_usd": (rev or {}).get("revenue_last_7d_usd", 0.0),
        },
        "system": {
            "overall": (health or {}).get("overall", "unknown"),
            "memory_pct": (health or {}).get("memory_pct", 0.0),
            "backend_alive": (health or {}).get("backend_alive", True),
        },
        "pipeline": {
            "content_queue_ready": queue_depth,
            "opportunities_unprocessed": opp_count,
            "recent_agent_runs": [
                {"agent_id": r.get("agent_id"), "success": r.get("success")}
                for r in recent_runs[:10]
            ],
        },
    }


async def make_decision(db, registered_agent_ids: list[str]) -> SovereignDecision:
    """One sovereign decision cycle. Safe to call from scheduler."""
    async with _SOVEREIGN_LOCK:
        session_id = f"sov-sess-{uuid.uuid4().hex[:8]}"
        snapshot = await _build_snapshot(db)
        snapshot_yaml = to_yaml_payload(snapshot)
        agent_ids_str = ", ".join(registered_agent_ids)

        # Safety guard: if system is degraded, skip non-essential agents
        if snapshot.get("system", {}).get("overall") == "degraded":
            logger.warning("Sovereign: system degraded — forcing guard-only run")
            decision = SovereignDecision(
                {
                    "priority_action": "System degraded — run guard-agent only",
                    "agents_to_run": ["guard-agent"],
                    "reasoning": "Backend health check failed. No content or revenue work until system recovers.",
                    "risk_level": "high",
                    "estimated_tokens": 0,
                    "skip_reason": None,
                },
                session_id,
            )
        else:
            # Provider priority: Groq (always free) → Gemini (if key set) → fallback
            _lm_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
            _gr_key = os.environ.get("GROQ_API_KEY", "").strip()

            # ── Provider resolution — ordered by speed/cost/reliability ──────
            # Keys from environment (set in .env or docker-compose)
            _ds_key  = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            _or_key  = os.environ.get("OPENROUTER_API_KEY", "").strip()
            _ms_key  = os.environ.get("MISTRAL_API_KEY", "").strip()
            _qw_key  = os.environ.get("QWEN_API_KEY", "").strip()
            _ol_url  = os.environ.get("OLLAMA_BASE_URL", "").strip()   # e.g. http://localhost:11434
            _kb_url  = os.environ.get("KOBOLD_BASE_URL", "").strip()   # e.g. http://localhost:5001
            _ol_model = os.environ.get("OLLAMA_MODEL", "llama3.2").strip()
            _kb_model = os.environ.get("KOBOLD_MODEL", "koboldcpp").strip()

            _providers_to_try: list[tuple[str, str, str]] = []

            # Tier 1 — fast free cloud APIs
            if _gr_key:
                _providers_to_try.append(("groq",      "llama-3.3-70b-versatile", _gr_key))
            if _lm_key:
                _providers_to_try.append(("gemini",    "gemini-2.5-flash",         _lm_key))
            if _ms_key:
                _providers_to_try.append(("mistral",   "mistral-small-latest",     _ms_key))
            if _ms_key:
                _providers_to_try.append(("codestral", "codestral-latest",         _ms_key))

            # Tier 2 — local inference (zero cost, requires running instance)
            if _ol_url:
                _providers_to_try.append(("ollama",    _ol_model,                  "nokey"))
            if _kb_url:
                _providers_to_try.append(("koboldcpp", _kb_model,                  "nokey"))

            # Tier 3 — paid/BYOK cloud fallbacks
            if _qw_key:
                _providers_to_try.append(("qwen",       "qwen-plus",               _qw_key))
            if _ds_key:
                _providers_to_try.append(("deepseek",   "deepseek-chat",           _ds_key))
            if _or_key:
                _providers_to_try.append(("openrouter", "openai/gpt-4o-mini",      _or_key))
                _providers_to_try.append(("openrouter", "openai/gpt-4o",           _or_key))

            # Tier 4 — last-resort Gemini fallback
            if _lm_key:
                _providers_to_try.append(("gemini",    "gemini-1.5-flash",         _lm_key))

            if not _providers_to_try:
                raise RuntimeError("No LLM API key configured (set GROQ_API_KEY or EMERGENT_LLM_KEY)")

            last_error: Exception | None = None
            raw_response: str | None = None
            for _cash_provider, _cash_model, _api_key in _providers_to_try:
                try:
                    # Temporarily set EMERGENT_LLM_KEY so llm_runner picks up the right key
                    os.environ["EMERGENT_LLM_KEY"] = _api_key
                    logger.info("Cash AI trying provider=%s model=%s", _cash_provider, _cash_model)
                    raw_response = await run_cached(
                        db,
                        provider=_cash_provider,
                        model=_cash_model,
                        system_msg=SOVEREIGN_SYSTEM,
                        prompt=DECISION_PROMPT.format(
                            snapshot_yaml=snapshot_yaml,
                            agent_ids=agent_ids_str,
                        ),
                        session_id=session_id,
                        tier=3,
                    )
                    logger.info("Cash AI succeeded with provider=%s", _cash_provider)
                    break  # success — stop trying
                except Exception as exc:
                    last_error = exc
                    logger.warning("Cash AI provider=%s failed: %s — trying next", _cash_provider, exc)

            try:
                if raw_response is None:
                    raise last_error or RuntimeError("All LLM providers failed")
                raw_json = raw_response.strip()
                raw_json = __import__("re").sub(r"^```(?:json)?\s*", "", raw_json)
                raw_json = __import__("re").sub(r"\s*```$", "", raw_json)
                parsed = json.loads(raw_json)
                # Validate agents_to_run are all registered
                parsed["agents_to_run"] = [
                    a for a in parsed.get("agents_to_run", [])
                    if a in registered_agent_ids
                ]
                if "guard-agent" in registered_agent_ids:
                    if "guard-agent" not in parsed["agents_to_run"]:
                        parsed["agents_to_run"].insert(0, "guard-agent")
                decision = SovereignDecision(parsed, session_id)
            except Exception as e:
                logger.exception("Sovereign LLM call failed: %s — falling back to default", e)
                decision = SovereignDecision(
                    {
                        "priority_action": "LLM unavailable — run guard and scout agents",
                        "agents_to_run": [a for a in ["guard-agent", "scout-agent"] if a in registered_agent_ids],
                        "reasoning": f"Sovereign LLM failed ({e}). Conservative fallback.",
                        "risk_level": "low",
                        "estimated_tokens": 0,
                        "skip_reason": None,
                    },
                    session_id,
                )

        # Persist decision
        try:
            await db[SOVEREIGN_COLLECTION].insert_one(decision.to_dict())
        except Exception:
            pass

        # Audit
        try:
            await log_audit_event(
                db, "sovereign.decision", "sovereign-v1", "decide",
                "system", decision.decision_id,
                metadata={
                    "priority_action": decision.priority_action,
                    "agents_to_run": decision.agents_to_run,
                    "risk_level": decision.risk_level,
                },
            )
        except Exception:
            pass

        logger.info(
            "Sovereign decision %s: action='%s' agents=%s risk=%s",
            decision.decision_id, decision.priority_action,
            decision.agents_to_run, decision.risk_level,
        )
        return decision
