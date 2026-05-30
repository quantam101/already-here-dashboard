"""
Master Revenue Equation tracker — operationalizes blueprint §2.

  Daily Revenue Capacity = Q_D * C_R * A_OV * P_F * F_C * P_M

  Q_D  Qualified Demand     (leads/day)
  C_R  Conversion Rate       (paid / total leads)
  A_OV Average Order Value   ($ per txn)
  P_F  Purchase Frequency    (txns/customer/month, normalized to /day)
  F_C  Fulfillment Capacity  (txns/day ceiling)
  P_M  Profit Margin         (net / gross)

This route is **pure analytics** — no LLM, no external calls. It reads from the
existing collections (`payment_transactions`, `revenue_ledger`, `analytics_events`,
`publishing_log`) and projects the path to north_star_usd_per_day from governance.yaml.

GET /api/revenue/equation     -> current snapshot + projection to $1M/day
GET /api/revenue/bottleneck   -> which of the 6 variables is the limiter
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta
from collections import Counter

from services import governance_service as gov

router = APIRouter()


async def get_db():
    from server import db
    return db


def _safe(numerator: float, denominator: float, *, default: float = 0.0) -> float:
    if denominator <= 0:
        return default
    return numerator / denominator


async def _compute_variables(db) -> dict:
    """Compute the 6 variables from real live data."""
    now = datetime.now(timezone.utc)
    cutoff_30 = (now - timedelta(days=30)).isoformat()

    # --- Q_D: Qualified Demand (leads/day from analytics_events) ---
    qd_events = await db.analytics_events.find(
        {"event_name": {"$in": ["lead", "signup", "intent"]}, "ts": {"$gte": cutoff_30}},
        {"_id": 0, "ts": 1},
    ).to_list(5000)
    Q_D = len(qd_events) / 30.0

    # --- C_R: Conversion Rate (paid/leads) ---
    paid_txns = await db.payment_transactions.find(
        {"payment_status": "paid", "created_at": {"$gte": cutoff_30}}, {"_id": 0},
    ).to_list(5000)
    paid_count = len(paid_txns)
    C_R = _safe(paid_count, len(qd_events) or paid_count or 1, default=0.0)

    # --- A_OV: Average Order Value ($) ---
    if paid_txns:
        gross = sum(float(t.get("amount") or 0) for t in paid_txns)
        A_OV = gross / max(1, paid_count)
    else:
        A_OV = 0.0

    # --- P_F: Purchase Frequency (txns per customer per day, normalized) ---
    customers = Counter()
    for t in paid_txns:
        cid = t.get("customer_email") or t.get("metadata", {}).get("customer_email") or t.get("session_id")
        if cid:
            customers[cid] += 1
    if customers:
        avg_txns_per_customer_30d = sum(customers.values()) / len(customers)
        P_F = avg_txns_per_customer_30d / 30.0
    else:
        P_F = 0.0

    # --- F_C: Fulfillment Capacity (system-defined ceiling) ---
    # Pulled from manifest (operator-tunable) OR a hard floor of paid+50 txns/day.
    manifest = gov.load_manifest()
    F_C = float(
        (manifest.get("revenue_equation", {}) or {}).get("fulfillment_capacity_per_day")
        or max(paid_count / 30.0 + 50.0, 100.0)
    )

    # --- P_M: Profit Margin (net/gross from ledger) ---
    ledger_rows = await db.revenue_ledger.find(
        {"created_at": {"$gte": cutoff_30}},
        {"_id": 0, "gross_amount": 1, "net_amount": 1},
    ).to_list(5000)
    if ledger_rows:
        g_total = sum(float(r.get("gross_amount") or 0) for r in ledger_rows)
        n_total = sum(float(r.get("net_amount") or 0) for r in ledger_rows)
        P_M = _safe(n_total, g_total, default=0.0)
    else:
        P_M = 0.0

    return {
        "Q_D": round(Q_D, 4),
        "C_R": round(C_R, 6),
        "A_OV": round(A_OV, 2),
        "P_F": round(P_F, 6),
        "F_C": round(F_C, 2),
        "P_M": round(P_M, 6),
    }


def _daily_capacity(vars_: dict) -> float:
    """Compute Q_D * C_R * A_OV * P_F * F_C * P_M, clamping nonsense values to 0."""
    product = 1.0
    for k in ("Q_D", "C_R", "A_OV", "P_F", "F_C", "P_M"):
        v = float(vars_.get(k) or 0)
        if v <= 0:
            return 0.0
        product *= v
    return round(product, 2)


def _identify_bottleneck(vars_: dict, target_per_var: dict) -> dict:
    """Return the variable whose ratio-to-target is the smallest (the worst lever)."""
    ratios = []
    for k, target in target_per_var.items():
        v = float(vars_.get(k) or 0)
        if target > 0:
            ratios.append((k, _safe(v, target)))
    if not ratios:
        return {}
    ratios.sort(key=lambda x: x[1])
    bn_var, bn_ratio = ratios[0]
    return {
        "variable": bn_var,
        "ratio_of_target": round(bn_ratio, 4),
        "current": float(vars_.get(bn_var) or 0),
        "target": target_per_var[bn_var],
        "gap_percent": round((1.0 - bn_ratio) * 100, 1),
    }


@router.get("/equation")
async def equation(db=Depends(get_db)):
    """Compute the live Master Revenue Equation + projection to north-star target."""
    manifest = gov.load_manifest()
    north_star = float(
        (manifest.get("system", {}) or {}).get("north_star_usd_per_day") or 1_000_000
    )
    unlock = float(
        (manifest.get("system", {}) or {}).get("unlock_threshold_usd") or 25_000
    )

    vars_ = await _compute_variables(db)
    today_capacity = _daily_capacity(vars_)

    # Target each variable holds equal weight to the geometric mean; aim each ~target_root
    # so multiplied product = north_star.
    if today_capacity > 0:
        target_root = (north_star) ** (1.0 / 6.0)
    else:
        target_root = (north_star) ** (1.0 / 6.0)
    target_per_var = {k: round(target_root, 4) for k in vars_.keys()}

    # If A_OV/F_C/P_M have natural ceilings (margin can't exceed 1), pin those.
    target_per_var["P_M"] = min(target_per_var["P_M"], 0.85)
    target_per_var["C_R"] = min(target_per_var["C_R"], 0.40)
    target_per_var["A_OV"] = max(target_per_var["A_OV"], 49.0)

    bottleneck = _identify_bottleneck(vars_, target_per_var)
    gap_to_target = round(max(0, north_star - today_capacity), 2)
    pct_of_target = round(_safe(today_capacity, north_star) * 100, 4)

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "formula": "Q_D * C_R * A_OV * P_F * F_C * P_M",
        "variables": vars_,
        "variable_targets": target_per_var,
        "daily_capacity_usd": today_capacity,
        "north_star_usd_per_day": north_star,
        "gap_to_north_star_usd": gap_to_target,
        "percent_of_north_star": pct_of_target,
        "unlock_threshold_usd": unlock,
        "bottleneck": bottleneck,
        "note": (
            "Q_D and P_F may be 0 in cold-start. The bottleneck variable "
            "is your highest-leverage focus next."
        ),
    }


@router.get("/bottleneck")
async def bottleneck(db=Depends(get_db)):
    """Just the bottleneck variable. Useful for badges/widgets."""
    data = await equation(db=db)
    return {
        "bottleneck": data["bottleneck"],
        "current_capacity_usd_per_day": data["daily_capacity_usd"],
    }
