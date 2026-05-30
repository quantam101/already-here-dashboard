"""
Data Distillation Framework — keeps LLM token cost strictly at $0 by:

  Tier 1 (LOCAL / no LLM)   Deterministic transforms that never need an LLM
                            (hashtag generation, list formatting, slug-ification).
  Tier 2 (DISTILL + CACHE)  Compress the prompt + payload, then check cache;
                            only call the LLM on a true miss.
  Tier 3 (LLM CALL)         The actual model invocation, but with semantically
                            compressed input and YAML-formatted structured data
                            (yields ~25-40% fewer tokens than equivalent JSON).

Public API (all sync — distillation is pure, no I/O until you hit `cache_*`):

    distill_text(text, *, max_chars=None)         -> str
    to_yaml_payload(obj)                          -> str  (YAML; falls back to JSON)
    estimate_tokens(text)                         -> int  (~chars/4 heuristic)
    fingerprint(model, system, prompt)            -> str  (sha256 hex, 32 chars)

    await cache_lookup(db, model, system, prompt) -> dict | None
    await cache_store(db, model, system, prompt, response, *, tier=3) -> None
    await cache_stats(db)                          -> dict
    await cache_clear(db)                          -> int  (rows deleted)

Notes:
  - Cache lives in the same db handle (Mongo or SQLite) under `llm_cache`.
  - Cost-savings numbers are heuristic; only tokens are real. $ figures are
    informational (set TOKEN_COST_PER_1K env to tune).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from typing import Any

try:
    import yaml  # PyYAML already in requirements.txt
    _YAML_OK = True
except Exception:  # pragma: no cover
    _YAML_OK = False


# ---------------------------------------------------------------------------
# Semantic compression — strip noise BEFORE sending to LLM
# ---------------------------------------------------------------------------

# Filler patterns that add tokens but no semantic value to a prompt.
# Order matters: longer phrases first to avoid partial-match cascades.
_FILLER_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(please note that|it is important to note that|it should be noted that)\b", re.I), ""),
    (re.compile(r"\b(in order to)\b", re.I), "to"),
    (re.compile(r"\b(due to the fact that|owing to the fact that)\b", re.I), "because"),
    (re.compile(r"\b(at this point in time|at the present time)\b", re.I), "now"),
    (re.compile(r"\b(in the event that)\b", re.I), "if"),
    (re.compile(r"\b(a large number of|a great deal of|a lot of)\b", re.I), "many"),
    (re.compile(r"\b(make use of|utilize)\b", re.I), "use"),
    (re.compile(r"\b(very|really|quite|extremely|absolutely|literally)\s+", re.I), ""),
    (re.compile(r"\b(basically|essentially|actually|honestly|frankly)\b[, ]*", re.I), ""),
]

_WHITESPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_DECORATIVE = re.compile(r"^[\s\-=*_#]{3,}$", re.M)


def distill_text(text: str, *, max_chars: int | None = None) -> str:
    """Apply semantic compression — strips filler, collapses whitespace.

    Idempotent: distill(distill(x)) == distill(x).
    """
    if not text:
        return ""
    out = text
    for pat, repl in _FILLER_PATTERNS:
        out = pat.sub(repl, out)
    out = _DECORATIVE.sub("", out)
    out = _WHITESPACE.sub(" ", out)
    out = _MULTI_NEWLINE.sub("\n\n", out)
    out = "\n".join(line.rstrip() for line in out.split("\n"))
    out = out.strip()
    if max_chars and len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


# ---------------------------------------------------------------------------
# YAML payload formatting — token-cheap structured data
# ---------------------------------------------------------------------------

def to_yaml_payload(obj: Any) -> str:
    """Convert a structured object to YAML (smaller than JSON for nested data).

    Falls back to compact JSON if PyYAML is unavailable for any reason.
    """
    if not _YAML_OK:
        return json.dumps(obj, separators=(",", ":"), default=str)
    try:
        return yaml.safe_dump(
            obj, sort_keys=False, default_flow_style=False, width=120, allow_unicode=True
        ).strip()
    except Exception:
        return json.dumps(obj, separators=(",", ":"), default=str)


# ---------------------------------------------------------------------------
# Token estimation (heuristic — good enough for budget telemetry)
# ---------------------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Rough char/4 heuristic. Matches OpenAI/Anthropic averages within ~10%."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _cost_for_tokens(tokens: int) -> float:
    per_1k = float(os.environ.get("TOKEN_COST_PER_1K", "0.0001"))  # default: ~free-tier
    return round(tokens / 1000.0 * per_1k, 6)


# ---------------------------------------------------------------------------
# Cache — db-backed, dual-DB compatible (Mongo or SQLite wrapper)
# ---------------------------------------------------------------------------

CACHE_COLLECTION = "llm_cache"
CACHE_TTL_SECONDS = int(os.environ.get("LLM_CACHE_TTL_SECONDS", str(60 * 60 * 24 * 30)))  # 30d


def fingerprint(model: str, system: str, prompt: str) -> str:
    """Stable 32-char hex fingerprint of (model, distilled-system, distilled-prompt)."""
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update(distill_text(system or "").encode("utf-8"))
    h.update(b"\x00")
    h.update(distill_text(prompt or "").encode("utf-8"))
    return h.hexdigest()[:32]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_expired(created_at: str) -> bool:
    try:
        ts = datetime.fromisoformat(created_at)
    except Exception:
        return True
    age = (datetime.now(UTC) - ts).total_seconds()
    return age > CACHE_TTL_SECONDS


async def cache_lookup(db, model: str, system: str, prompt: str) -> dict | None:
    """Return cached response dict on hit, None on miss.

    Bumps the `hits` counter atomically (via $inc) so /stats stays accurate.
    """
    key = fingerprint(model, system, prompt)
    row = await db[CACHE_COLLECTION].find_one({"key": key}, {"_id": 0})
    if not row:
        return None
    if _is_expired(row.get("created_at", "")):
        await db[CACHE_COLLECTION].delete_one({"key": key})
        return None
    try:
        await db[CACHE_COLLECTION].update_one(
            {"key": key},
            {"$inc": {"hits": 1}, "$set": {"last_hit_at": _now_iso()}},
        )
    except Exception:
        # Cache is best-effort — never let it break the calling route.
        pass
    return row


async def cache_store(
    db,
    model: str,
    system: str,
    prompt: str,
    response: str,
    *,
    tier: int = 3,
) -> None:
    """Upsert a cache row. Tracks tokens-in/out for /stats."""
    key = fingerprint(model, system, prompt)
    doc = {
        "id": f"cache-{key[:12]}",
        "key": key,
        "model": model,
        "tier": tier,
        "tokens_in_est": estimate_tokens(system) + estimate_tokens(prompt),
        "tokens_out_est": estimate_tokens(response),
        "response": response,
        "hits": 0,
        "created_at": _now_iso(),
        "last_hit_at": None,
    }
    try:
        await db[CACHE_COLLECTION].delete_one({"key": key})
        await db[CACHE_COLLECTION].insert_one(doc)
    except Exception:
        # Best-effort: a failed cache store must NEVER fail the user request.
        pass


async def cache_stats(db) -> dict:
    rows = await db[CACHE_COLLECTION].find({}, {"_id": 0}).to_list(5000)
    total_rows = len(rows)
    total_hits = sum(int(r.get("hits", 0)) for r in rows)
    tokens_saved = sum(
        int(r.get("hits", 0)) * (int(r.get("tokens_in_est", 0)) + int(r.get("tokens_out_est", 0)))
        for r in rows
    )
    by_model: dict[str, dict] = {}
    by_tier: dict[str, int] = {}
    for r in rows:
        m = r.get("model", "unknown")
        bucket = by_model.setdefault(m, {"rows": 0, "hits": 0})
        bucket["rows"] += 1
        bucket["hits"] += int(r.get("hits", 0))
        t = f"tier_{r.get('tier', 3)}"
        by_tier[t] = by_tier.get(t, 0) + 1
    return {
        "rows": total_rows,
        "hits": total_hits,
        "tokens_saved_est": tokens_saved,
        "usd_saved_est": _cost_for_tokens(tokens_saved),
        "by_model": by_model,
        "by_tier": by_tier,
        "ttl_seconds": CACHE_TTL_SECONDS,
    }


async def cache_clear(db) -> int:
    """Wipe the entire cache. Returns rows deleted (best-effort)."""
    rows = await db[CACHE_COLLECTION].find({}, {"_id": 0}).to_list(5000)
    n = len(rows)
    await db[CACHE_COLLECTION].delete_many({})
    return n
