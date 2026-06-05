from __future__ import annotations

import re
from typing import Any


def match_technicians(
    work_order: dict[str, Any],
    technicians: list[dict[str, Any]],
    min_skill_ratio: float = 0.55,
) -> list[dict[str, Any]]:
    required_skills = _normalize_set(work_order.get("required_skills", []))
    work_city = str(work_order.get("city", "")).strip().lower()
    work_state = str(work_order.get("state", "")).strip().lower()
    pay_rate = _safe_float(work_order.get("pay_rate"), default=0.0)
    dispatch_minimum = _safe_float(work_order.get("minimum_hours"), default=0.0)
    work_type = str(work_order.get("work_type", "field_service")).strip().lower()

    matches: list[dict[str, Any]] = []
    for technician in technicians:
        tech_skills = _normalize_set(technician.get("skills", []))
        skill_ratio = 1.0 if not required_skills else len(required_skills & tech_skills) / len(required_skills)
        accepts_1099 = bool(technician.get("accepts_1099", True))
        tech_min_rate = _safe_float(technician.get("minimum_effective_rate"), default=65.0)
        tech_min_hours = _safe_float(technician.get("minimum_hours"), default=2.0)
        tech_city = str(technician.get("city", "")).strip().lower()
        tech_state = str(technician.get("state", "")).strip().lower()
        availability = str(technician.get("availability", "available")).strip().lower()

        rate_ok = pay_rate >= tech_min_rate if pay_rate else True
        minimum_ok = dispatch_minimum >= tech_min_hours if dispatch_minimum else True
        state_ok = not work_state or not tech_state or work_state == tech_state
        city_bonus = 1.0 if work_city and tech_city and work_city == tech_city else 0.0
        state_bonus = 1.0 if state_ok else 0.0
        availability_bonus = 1.0 if availability in {"available", "active", "on_call", "priority"} else 0.0
        model_bonus = 1.0 if accepts_1099 else 0.0

        score = round(
            (skill_ratio * 55.0)
            + (20.0 if rate_ok and minimum_ok else 0.0)
            + (state_bonus * 10.0)
            + (city_bonus * 10.0)
            + (availability_bonus * 3.0)
            + (model_bonus * 2.0),
            2,
        )
        eligible = bool(
            skill_ratio >= min_skill_ratio
            and accepts_1099
            and rate_ok
            and minimum_ok
            and state_ok
        )
        matches.append(
            {
                "technician_id": technician.get("id") or technician.get("email") or technician.get("name"),
                "name": technician.get("name", "Unknown technician"),
                "score": score,
                "eligible": eligible,
                "skill_match_ratio": round(skill_ratio, 4),
                "matched_skills": sorted(required_skills & tech_skills),
                "missing_skills": sorted(required_skills - tech_skills),
                "rate_ok": rate_ok,
                "minimum_ok": minimum_ok,
                "state_ok": state_ok,
                "work_type": work_type,
            }
        )

    return sorted(matches, key=lambda item: (item["eligible"], item["score"]), reverse=True)


def _normalize_set(value: Any) -> set[str]:
    if isinstance(value, str):
        values = re.split(r"[,|]", value)
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = []
    return {str(item).strip().lower() for item in values if str(item).strip()}


def _safe_float(value: Any, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
