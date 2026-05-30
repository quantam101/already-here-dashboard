"""
Analytics - Drives posting decisions, efficiency, optimization.

Built entirely off live data sources (no synthetic):
  - publishing_log: drafted/exported/posted/verified posts
  - revenue_ledger: real attested earnings
  - audit_log: cycle runs, agent activity
  - content_ideas: scout-sourced topics + scores

Endpoints:
  GET /api/analytics/posting-times  -> when to post based on what got verified
  GET /api/analytics/funnel         -> drafted -> exported -> posted -> verified counts
  GET /api/analytics/stream-roi     -> revenue per stream + revenue/post
  GET /api/analytics/platform-mix   -> posts and revenue per platform
  GET /api/analytics/viral-themes   -> top-scoring scout themes
  GET /api/analytics/momentum       -> last-30-day revenue trend + projection to $25K
"""
import re
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

router = APIRouter()


async def get_db():
    from server import db
    return db


@router.get("/funnel")
async def conversion_funnel(db=Depends(get_db)):
    """Funnel: drafted -> exported -> posted -> verified. Where do posts die?"""
    by_status: dict[str, int] = {"drafted": 0, "exported": 0, "posted": 0, "verified": 0}
    posts = await db.publishing_log.find({}, {"_id": 0}).to_list(10000)
    for p in posts:
        st = p.get("status", "drafted")
        if st in by_status:
            by_status[st] += 1
    total = sum(by_status.values()) or 1
    return {
        "totals": by_status,
        "rates": {
            "drafted_to_exported": round(by_status["exported"] / max(by_status["drafted"], 1) * 100, 1),
            "exported_to_posted": round(by_status["posted"] / max(by_status["exported"], 1) * 100, 1),
            "posted_to_verified": round(by_status["verified"] / max(by_status["posted"], 1) * 100, 1),
            "overall_verified_pct": round(by_status["verified"] / total * 100, 1),
        },
        "sample_size": total,
    }


@router.get("/posting-times")
async def best_posting_times(db=Depends(get_db)):
    """Aggregate posted_at + verified_at timestamps to surface optimal posting hours."""
    posts = await db.publishing_log.find(
        {"posted_at": {"$ne": None}}, {"_id": 0},
    ).to_list(10000)
    hour_counts: Counter = Counter()
    dow_counts: Counter = Counter()
    verified_hour_counts: Counter = Counter()
    for p in posts:
        ts = p.get("posted_at") or p.get("created_at")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            continue
        hour_counts[dt.hour] += 1
        dow_counts[dt.strftime("%a")] += 1
        if p.get("status") == "verified":
            verified_hour_counts[dt.hour] += 1

    best_hours = [h for h, _ in hour_counts.most_common(3)]
    best_verified_hours = [h for h, _ in verified_hour_counts.most_common(3)]
    return {
        "sample_size": len(posts),
        "posts_by_hour_utc": dict(hour_counts),
        "posts_by_day_of_week": dict(dow_counts),
        "best_hours_overall_utc": best_hours,
        "best_hours_verified_utc": best_verified_hours,
        "recommendation": (
            f"Post around hour(s) {best_verified_hours or best_hours} UTC for highest verification rate."
            if posts else
            "Not enough data yet - log 10+ posts to unlock posting-time recommendations."
        ),
    }


@router.get("/stream-roi")
async def stream_roi(db=Depends(get_db)):
    """Revenue per stream + revenue per post -> identify the efficient streams."""
    streams = await db.revenue_streams.find({}, {"_id": 0}).to_list(1000)
    ledger = await db.revenue_ledger.find({}, {"_id": 0}).to_list(20000)
    posts = await db.publishing_log.find({}, {"_id": 0}).to_list(20000)

    net_by_stream: dict[str, float] = {}
    for e in ledger:
        sid = e.get("stream_id", "")
        net_by_stream[sid] = net_by_stream.get(sid, 0.0) + e.get("net_amount", 0.0)

    posts_by_stream: dict[str, int] = {}
    for p in posts:
        sid = p.get("stream_id", "")
        posts_by_stream[sid] = posts_by_stream.get(sid, 0) + 1

    rows = []
    for s in streams:
        net = round(net_by_stream.get(s["id"], 0.0), 2)
        post_count = posts_by_stream.get(s["id"], 0)
        rpp = round(net / post_count, 2) if post_count > 0 else 0.0
        rows.append({
            "stream_id": s["id"],
            "name": s["name"],
            "type": s.get("type"),
            "net_total": net,
            "post_count": post_count,
            "revenue_per_post": rpp,
            "target_monthly": s.get("monthly_target", 0),
        })
    rows.sort(key=lambda r: r["net_total"], reverse=True)
    return {"streams": rows, "top_3_by_revenue": [r["name"] for r in rows[:3]]}


@router.get("/platform-mix")
async def platform_mix(db=Depends(get_db)):
    """Distribution of posts + revenue per platform."""
    posts = await db.publishing_log.find({}, {"_id": 0}).to_list(20000)
    by_platform: dict[str, dict] = {}
    for p in posts:
        plat = p.get("platform", "unknown")
        bucket = by_platform.setdefault(plat, {"posts": 0, "verified": 0})
        bucket["posts"] += 1
        if p.get("status") == "verified":
            bucket["verified"] += 1
    rows = [
        {
            "platform": plat,
            "posts": d["posts"],
            "verified": d["verified"],
            "verification_rate": round(d["verified"] / d["posts"] * 100, 1) if d["posts"] else 0,
        }
        for plat, d in by_platform.items()
    ]
    rows.sort(key=lambda r: r["posts"], reverse=True)
    return {"platforms": rows, "total_posts": sum(r["posts"] for r in rows)}


_STOP = {
    "the","and","for","with","from","this","that","what","why","when","how",
    "are","you","your","but","not","they","their","have","has","was","will",
    "more","into","than","then","just","like","about","over","one","two","new",
    "make","made","get","got","can","still","most","much","really","very","every",
}


def _tokenize_titles(titles: list[str]) -> Counter:
    bag: Counter = Counter()
    for t in titles:
        for w in re.findall(r"[a-zA-Z][a-zA-Z\-]+", (t or "").lower()):
            if len(w) >= 4 and w not in _STOP:
                bag[w] += 1
    return bag


@router.get("/viral-themes")
async def viral_themes(db=Depends(get_db)):
    """Extract top keywords from high-engagement content_ideas (sourced from scout)."""
    ideas = await db.content_ideas.find({}, {"_id": 0}).sort("created_at", -1).limit(500).to_list(500)
    titles = [i.get("title", "") for i in ideas]
    bag = _tokenize_titles(titles)
    return {
        "sample_size": len(titles),
        "top_themes": [{"word": w, "count": c} for w, c in bag.most_common(20)],
        "recommendation": (
            f"Top viral themes from {len(titles)} recent scout pulls: " +
            ", ".join(w for w, _ in bag.most_common(5))
        ) if titles else "Run /api/cycle/run to populate viral themes.",
    }


@router.get("/momentum")
async def momentum(db=Depends(get_db)):
    """30-day revenue trend, 7-day rolling avg, projected days to $25K at current rate."""
    today = datetime.now(UTC).date()
    start = (today - timedelta(days=30)).isoformat()
    entries = await db.revenue_ledger.find({"occurred_on": {"$gte": start}}, {"_id": 0}).to_list(10000)

    by_day: dict[str, float] = {}
    total = 0.0
    for e in entries:
        d = e.get("occurred_on", "")
        amt = e.get("net_amount", 0.0)
        by_day[d] = by_day.get(d, 0.0) + amt
        total += amt

    # 7-day rolling
    last7 = (today - timedelta(days=7)).isoformat()
    last7_net = sum(amt for d, amt in by_day.items() if d >= last7)
    daily_avg = last7_net / 7.0

    # Cumulative net from all entries (not just last 30) for the goal projection
    all_entries = await db.revenue_ledger.find({}, {"_id": 0}).to_list(20000)
    cumulative_net = sum(e.get("net_amount", 0.0) for e in all_entries)
    remaining = max(0.0, 25000.0 - cumulative_net)
    days_to_goal = (remaining / daily_avg) if daily_avg > 0 else None

    return {
        "cumulative_net": round(cumulative_net, 2),
        "last_30_days_net": round(total, 2),
        "last_7_days_net": round(last7_net, 2),
        "daily_avg_last_7d": round(daily_avg, 2),
        "remaining_to_25k": round(remaining, 2),
        "projected_days_to_25k": round(days_to_goal, 1) if days_to_goal else None,
        "trend_by_day": [{"date": d, "net": round(v, 2)} for d, v in sorted(by_day.items())],
        "recommendation": (
            f"At ${daily_avg:.2f}/day average, you reach $25K in ~{round(days_to_goal)} days." if days_to_goal else
            "Need at least one ledger entry in the last 7 days to project."
        ),
    }


@router.get("/dashboard")
async def analytics_dashboard(db=Depends(get_db)):
    """Single-call payload for the Analytics page - everything at once."""
    return {
        "funnel": await conversion_funnel(db),
        "posting_times": await best_posting_times(db),
        "stream_roi": await stream_roi(db),
        "platform_mix": await platform_mix(db),
        "viral_themes": await viral_themes(db),
        "momentum": await momentum(db),
    }
