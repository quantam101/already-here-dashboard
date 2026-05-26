#!/usr/bin/env python3
"""
Seed script to populate the Already Here Command OS with initial ecosystem data.
Refactored into modular functions with builder pattern for entities.

Backend-agnostic: honors STORAGE_BACKEND=sqlite if set, otherwise uses MongoDB.
"""
import asyncio
from typing import Any
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "mongodb").lower()


def _make_client():
    if STORAGE_BACKEND == "sqlite":
        from services.sqlite_db import SqliteClient
        path = os.environ.get("SQLITE_PATH", "./data/command_os.db")
        return SqliteClient(path), path
    from motor.motor_asyncio import AsyncIOMotorClient
    return AsyncIOMotorClient(os.environ["MONGO_URL"]), os.environ["MONGO_URL"]


db_name = os.environ.get("DB_NAME", "command_os")


def now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


async def clear_all_data(db) -> None:
    """Clear all collections before seeding."""
    collections = [
        "revenue_streams", "content", "agents", "builds",
        "deployments", "audit_log", "approvals", "platform_connectors",
        "content_ideas", "content_scripts", "scheduled_posts",
        "revenue_ledger", "publishing_log",
    ]
    for collection in collections:
        await db[collection].delete_many({})
    print("Cleared existing data")


def make_agent(
    agent_id: str,
    name: str,
    agent_type: str,
    mission: str,
    allowed: list[str],
    forbidden: list[str],
    approval_required: list[str],
    runs: int,
    successes: int,
    failures: int,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builder for agent records to reduce repetition."""
    timestamp = now_iso()
    return {
        "id": agent_id, "name": name, "type": agent_type, "mission": mission,
        "status": "active",
        "allowed_actions": allowed,
        "forbidden_actions": forbidden,
        "approval_required_actions": approval_required,
        "cost_ceiling": 0.0,
        "run_count": runs, "success_count": successes, "failure_count": failures,
        "last_run": timestamp, "metadata": metadata or {},
        "created_at": timestamp, "updated_at": timestamp,
    }


def make_connector(
    connector_id: str,
    platform: str,
    name: str,
    cost_class: str,
    has_api: bool,
    credential_status: str,
    blocked_reason: str | None = None,
    setup: str | None = None,
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Builder for platform connector records to reduce repetition."""
    timestamp = now_iso()
    base = {
        "id": connector_id, "platform": platform, "name": name,
        "cost_class": cost_class, "has_api": has_api, "api_authenticated": False,
        "requires_app_review": cost_class == "manual_free",
        "credential_status": credential_status,
        "blocked_reason": blocked_reason, "setup_instructions": setup or "",
        "metadata": {}, "created_at": timestamp, "updated_at": timestamp,
    }
    if extras:
        base.update(extras)
    return base


def get_revenue_streams_data() -> list[dict[str, Any]]:
    """Return revenue streams seed data - the 10 active streams of Already Here."""
    timestamp = now_iso()
    base = {"created_at": timestamp, "updated_at": timestamp, "status": "active"}
    return [
        {**base, "id": "rev-001", "name": "AI Blog Network", "type": "content",
         "monthly_target": 4000.0, "monthly_actual": 0.0,
         "description": "Multi-niche SEO blog network monetized with display ads and affiliates",
         "metadata": {"platforms": ["blog", "medium"], "cost_class": "free_local", "sites": 6}},
        {**base, "id": "rev-002", "name": "Faceless Videos", "type": "content",
         "monthly_target": 6000.0, "monthly_actual": 0.0,
         "description": "Faceless YouTube/TikTok automation with AI scripts + stock footage",
         "metadata": {"platforms": ["youtube", "tiktok"], "cost_class": "manual_free"}},
        {**base, "id": "rev-003", "name": "Print-on-Demand A", "type": "ecommerce",
         "monthly_target": 3500.0, "monthly_actual": 0.0,
         "description": "POD apparel store (RedBubble + Teespring) - design-led niches",
         "metadata": {"platforms": ["redbubble", "teespring"], "cost_class": "free_external"}},
        {**base, "id": "rev-004", "name": "Print-on-Demand B", "type": "ecommerce",
         "monthly_target": 3500.0, "monthly_actual": 0.0,
         "description": "POD home goods (Printify + Etsy) - automated bulk uploader",
         "metadata": {"platforms": ["printify", "etsy"], "cost_class": "free_external"}},
        {**base, "id": "rev-005", "name": "Affiliate Links", "type": "affiliate",
         "monthly_target": 5000.0, "monthly_actual": 0.0,
         "description": "Amazon Associates + niche affiliate programs wired across blog/video",
         "metadata": {"networks": ["amazon", "impact", "shareasale"], "cost_class": "free_external"}},
        {**base, "id": "rev-006", "name": "Social Automation", "type": "content",
         "monthly_target": 2500.0, "monthly_actual": 0.0,
         "description": "Cross-posted social content via manual export packs (Cost Guard compliant)",
         "metadata": {"platforms": ["linkedin", "instagram", "tiktok"], "cost_class": "manual_free"}},
        {**base, "id": "rev-007", "name": "SEO Content Farm", "type": "content",
         "monthly_target": 4500.0, "monthly_actual": 0.0,
         "description": "Programmatic SEO pages targeting long-tail keywords at scale",
         "metadata": {"pages": 1240, "cost_class": "free_local"}},
        {**base, "id": "rev-008", "name": "Federal Contracting", "type": "proposal",
         "monthly_target": 15000.0, "monthly_actual": 0.0,
         "description": "Federal procurement and SBA proposals - H&M RFID proof leveraged",
         "metadata": {"focus": "H&M RFID US0275", "cost_class": "free_local"}},
        {**base, "id": "rev-009", "name": "Service Automation", "type": "service",
         "monthly_target": 10000.0, "monthly_actual": 0.0,
         "description": "Automated service delivery, client onboarding and retainer management",
         "metadata": {"cost_class": "free_local"}},
        {**base, "id": "rev-010", "name": "Newsletter Sponsorships", "type": "subscription",
         "monthly_target": 2000.0, "monthly_actual": 0.0,
         "description": "Owned newsletter monetized via direct sponsorships (no paid ESP)",
         "metadata": {"subscribers": 4120, "cost_class": "free_local"}},
    ]


def get_agents_data() -> list[dict[str, Any]]:
    """Return agents seed data using builder - 10 production agents."""
    return [
        make_agent("agent-001", "Sovereign Orchestrator", "orchestrator",
                   "Coordinate multi-agent workflows and enforce governance policies",
                   ["coordinate", "monitor", "route"],
                   ["deploy", "delete", "publish"],
                   ["deploy", "publish"], 152, 148, 4),
        make_agent("agent-002", "Cost Guard Agent", "security",
                   "Enforce zero-spend policy and block unauthorized paid actions",
                   ["validate", "block", "audit"],
                   ["spend", "authorize_payment"],
                   ["approve_paid_action"], 487, 487, 0,
                   metadata={"mode": "zero-spend"}),
        make_agent("agent-003", "Content Generation Agent", "content",
                   "Generate revenue-focused content using AI for blogs, social, and proposals",
                   ["generate_content", "optimize_seo", "schedule"],
                   ["publish_directly"],
                   ["publish"], 234, 221, 13),
        make_agent("agent-004", "Proposal Engine Agent", "revenue",
                   "Generate federal proposals and capability statements using H&M proof data",
                   ["generate_proposal", "analyze_rfp", "compile_evidence"],
                   ["submit"],
                   ["submit"], 81, 76, 5,
                   metadata={"evidence_source": "H&M US0275"}),
        make_agent("agent-005", "Lifelong Catch and Correct", "learning",
                   "Track failures, generate fixes, and prevent repeated mistakes",
                   ["analyze_failures", "generate_patches", "update_rules"],
                   ["auto_deploy"],
                   ["deploy_fix"], 124, 121, 3),
        make_agent("agent-006", "SEO Scout Agent", "content",
                   "Discover trending niches, run keyword research, and queue topics",
                   ["scrape_trends", "rank_keywords", "queue_topics"],
                   ["pay_for_data"],
                   [], 312, 305, 7,
                   metadata={"sources": ["google_trends", "reddit", "youtube"]}),
        make_agent("agent-007", "Faceless Video Agent", "content",
                   "Assemble faceless videos from AI script + free stock footage + TTS",
                   ["compose_video", "render_ffmpeg", "package_export"],
                   ["upload_paid"],
                   ["publish"], 96, 91, 5,
                   metadata={"renderer": "ffmpeg", "tts": "free_local"}),
        make_agent("agent-008", "POD Designer Agent", "revenue",
                   "Generate print-on-demand designs and push to RedBubble/Printify/Etsy",
                   ["generate_design", "format_mockup", "queue_upload"],
                   ["pay_for_design_tool"],
                   ["publish_listing"], 178, 169, 9),
        make_agent("agent-009", "Affiliate Link Agent", "revenue",
                   "Manage affiliate link injection across content and track conversions",
                   ["inject_links", "rotate_offers", "track_clicks"],
                   ["paid_redirect"],
                   [], 421, 419, 2,
                   metadata={"networks": ["amazon", "impact", "shareasale"]}),
        make_agent("agent-010", "Health Oracle Agent", "security",
                   "Continuous health checks, circuit-breakers, and self-improve hooks",
                   ["health_check", "trip_breaker", "report"],
                   ["restart_paid_service"],
                   ["restart_service"], 1043, 1041, 2,
                   metadata={"checks_per_hour": 60}),
        make_agent("agent-011", "Procurement Scout Agent", "revenue",
                   "Scan SAM.gov + Grants.gov for matching opportunities, queue proposals",
                   ["scrape_sam_gov", "scrape_grants_gov", "match_naics", "queue_proposal"],
                   ["pay_for_data", "submit_unverified"],
                   ["queue_proposal"], 62, 58, 4,
                   metadata={"sources": ["sam.gov", "grants.gov", "google_news"]}),
    ]


def get_builds_data() -> list[dict[str, Any]]:
    """Return builds seed data."""
    timestamp = now_iso()
    common = {"metadata": {}, "created_at": timestamp, "updated_at": timestamp}
    return [
        {**common, "id": "build-001", "name": "ProfitEngine v5", "type": "command_center",
         "status": "live", "source_repo": "quantam101/profitenginev5",
         "source_folder": "ProfitEngine_v5x_Build_20260523",
         "modules": ["agents", "webhooks", "content_pipeline", "distillation", "observability"],
         "production_gate_score": 94, "last_deploy": timestamp, "last_ci_status": "pass",
         "revenue_path": "direct", "next_action": None},
        {**common, "id": "build-002", "name": "GMAOS", "type": "operating_system",
         "status": "live", "source_repo": None, "source_folder": "GMAOS_Core",
         "modules": ["policy_broker", "governance", "execution_fabric"],
         "production_gate_score": 85, "last_deploy": timestamp, "last_ci_status": "pass",
         "revenue_path": "support", "next_action": None},
        {**common, "id": "build-003", "name": "TradeGate", "type": "market_system",
         "status": "live", "source_repo": None, "source_folder": "TradeGate_v2",
         "modules": ["portfolio", "market_data", "simulation"],
         "production_gate_score": 78, "last_deploy": timestamp, "last_ci_status": "pass",
         "revenue_path": "indirect", "next_action": "Add live trading mode flag"},
        {**common, "id": "build-004", "name": "VHLL Distillation Engine", "type": "efficiency_layer",
         "status": "live", "source_repo": None,
         "source_folder": "ProfitEngine_v5x_Build_20260523/vhll-refactor.zip",
         "modules": ["semantic_compressor", "tiered_router", "logic_offloader"],
         "production_gate_score": 92, "last_deploy": timestamp, "last_ci_status": "pass",
         "revenue_path": "support", "next_action": None,
         "metadata": {"test_results": "234/234 passing", "tokens_saved_pct": 47}},
        {**common, "id": "build-005", "name": "Command OS Dashboard", "type": "dashboard",
         "status": "live", "source_repo": None, "source_folder": "/app",
         "modules": ["revenue", "content", "agents", "builds", "deployments", "audit"],
         "production_gate_score": 95, "last_deploy": timestamp, "last_ci_status": "pass",
         "revenue_path": "direct", "next_action": None},
    ]


def get_deployments_data() -> list[dict[str, Any]]:
    """Return deployments seed data - all healthy after OCI fix + local fallback."""
    timestamp = now_iso()
    return [
        {
            "id": "deploy-001", "build_id": "build-001", "environment": "production",
            "status": "success", "target": "oci", "version": "v5.0.4",
            "deployed_by": "github-actions", "rollback_available": True,
            "health_check_url": "https://app.alreadyhere.local/api/health",
            "health_status": "healthy",
            "error_log": None, "metadata": {"resolution": "Migrated SSH key + Caddyfile auto-HTTPS"},
            "created_at": timestamp, "updated_at": timestamp,
        },
        {
            "id": "deploy-002", "build_id": "build-005", "environment": "production",
            "status": "success", "target": "oci", "version": "v1.0.0",
            "deployed_by": "system", "rollback_available": True,
            "health_check_url": "https://app.alreadyhere.local/api/health",
            "health_status": "healthy", "error_log": None, "metadata": {},
            "created_at": timestamp, "updated_at": timestamp,
        },
        {
            "id": "deploy-003", "build_id": "build-001", "environment": "local",
            "status": "success", "target": "laptop", "version": "v5.0.4",
            "deployed_by": "operator", "rollback_available": True,
            "health_check_url": "http://localhost:8001/api/health",
            "health_status": "healthy", "error_log": None,
            "metadata": {"script": "/app/scripts/deploy-local.sh"},
            "created_at": timestamp, "updated_at": timestamp,
        },
        {
            "id": "deploy-004", "build_id": "build-004", "environment": "production",
            "status": "success", "target": "oci", "version": "vhll-1.0.0",
            "deployed_by": "github-actions", "rollback_available": True,
            "health_check_url": "https://app.alreadyhere.local/api/health",
            "health_status": "healthy", "error_log": None,
            "metadata": {"tokens_saved_pct": 47},
            "created_at": timestamp, "updated_at": timestamp,
        },
    ]


def get_platform_connectors_data() -> list[dict[str, Any]]:
    """Return platform connectors with cost classifications using builder."""
    return [
        make_connector("conn-tiktok", "tiktok", "TikTok", "manual_free", True, "missing",
                       blocked_reason="API requires developer app registration and Content Posting API approval",
                       setup="Register at developers.tiktok.com, complete app review, configure OAuth2",
                       extras={"supported_media_types": ["video"], "max_file_size_mb": 287,
                               "max_duration_seconds": 600, "caption_max_length": 2200,
                               "supports_scheduling": True}),
        make_connector("conn-youtube", "youtube", "YouTube", "manual_free", True, "missing",
                       blocked_reason="YouTube Data API v3 requires OAuth2 setup and app verification",
                       setup="Create project at Google Cloud Console, enable YouTube Data API v3",
                       extras={"supported_media_types": ["video"], "max_file_size_mb": 256000,
                               "max_duration_seconds": 43200, "caption_max_length": 5000,
                               "supports_scheduling": True}),
        make_connector("conn-instagram", "instagram", "Instagram", "manual_free", True, "missing",
                       blocked_reason="Instagram Graph API requires Facebook App review",
                       setup="Create Facebook App, request instagram_content_publish permission",
                       extras={"supported_media_types": ["image", "video"], "max_file_size_mb": 100,
                               "max_duration_seconds": 90, "caption_max_length": 2200,
                               "supports_scheduling": True}),
        make_connector("conn-linkedin", "linkedin", "LinkedIn", "manual_free", True, "missing",
                       blocked_reason="LinkedIn Share API requires OAuth2 app with w_member_social permission",
                       setup="Create LinkedIn App at linkedin.com/developers",
                       extras={"supported_media_types": ["image", "video", "text"], "max_file_size_mb": 200,
                               "max_duration_seconds": 600, "caption_max_length": 3000,
                               "supports_scheduling": False}),
        make_connector("conn-twitter", "twitter", "Twitter / X", "paid_blocked", True, "missing",
                       blocked_reason="API requires PAID Elevated access ($100/month minimum)",
                       setup="BLOCKED by Cost Guard - manual export only",
                       extras={"supported_media_types": ["image", "video", "text"], "max_file_size_mb": 512,
                               "max_duration_seconds": 140, "caption_max_length": 280,
                               "supports_scheduling": False, "metadata": {"cost": "min $100/month"}}),
        make_connector("conn-facebook", "facebook", "Facebook", "manual_free", True, "missing",
                       blocked_reason="Facebook Graph API requires Business Verification + App Review",
                       setup="Create Facebook App, request pages_manage_posts + publish_pages permissions",
                       extras={"supported_media_types": ["image", "video", "text", "link"], "max_file_size_mb": 100,
                               "max_duration_seconds": 240, "caption_max_length": 63206,
                               "supports_scheduling": True}),
        make_connector("conn-reddit", "reddit", "Reddit", "free_external", True, "missing",
                       blocked_reason="Reddit API requires OAuth2 app + script-style auth (free tier available)",
                       setup="Register a 'script' app at reddit.com/prefs/apps - free, no review needed for personal use",
                       extras={"supported_media_types": ["text", "link", "image"], "max_file_size_mb": 20,
                               "caption_max_length": 40000, "supports_scheduling": False,
                               "metadata": {"read_api": "free no auth", "write_api": "free oauth"}}),
        make_connector("conn-blog", "blog", "Website Blog", "free_local", False, "configured",
                       setup="Internal blog publishing - no external API required",
                       extras={"supported_media_types": ["text", "image"], "supports_scheduling": True}),
        make_connector("conn-medium", "medium", "Medium", "free_external", True, "missing",
                       blocked_reason="Integration token not configured",
                       setup="Get integration token from medium.com/me/settings/security",
                       extras={"supported_media_types": ["text", "image"], "max_file_size_mb": 25,
                               "supports_scheduling": False}),
    ]


def get_audit_events_data() -> list[dict[str, Any]]:
    """Return audit events seed data."""
    timestamp = now_iso()
    return [
        {"id": "audit-001", "event_type": "system.startup", "actor": "system",
         "action": "initialize", "resource_type": "command_os", "resource_id": "build-005",
         "status": "success", "metadata": {}, "timestamp": timestamp},
        {"id": "audit-002", "event_type": "revenue.created", "actor": "system",
         "action": "seed", "resource_type": "revenue_stream", "resource_id": "rev-001",
         "status": "success", "metadata": {}, "timestamp": timestamp},
        {"id": "audit-003", "event_type": "agent.created", "actor": "system",
         "action": "seed", "resource_type": "agent", "resource_id": "agent-001",
         "status": "success", "metadata": {}, "timestamp": timestamp},
    ]


def get_content_data() -> list[dict[str, Any]]:
    """Return content pieces seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "content-001",
            "title": "Revenue Automation with AI - The Complete Guide",
            "content_type": "blog",
            "body": "Learn how to automate your revenue generation using AI-powered content creation, proposal generation, and autonomous agents...",
            "status": "published", "platform": "blog",
            "revenue_stream_id": "rev-001", "generated_by": "ai",
            "published_at": timestamp,
            "metadata": {"keywords": ["automation", "revenue", "ai"], "tone": "professional"},
            "created_at": timestamp, "updated_at": timestamp,
        },
        {
            "id": "content-002",
            "title": "H&M Store US0275 RFID Implementation Success Story",
            "content_type": "proposal",
            "body": "Comprehensive case study showcasing successful RFID deployment at Chandler Fashion Center H&M location with 55 readers, 61 data runs, and 4 new AP installations...",
            "status": "draft", "platform": None,
            "revenue_stream_id": "rev-002", "generated_by": "ai",
            "published_at": None,
            "metadata": {"keywords": ["rfid", "retail", "h&m"]},
            "created_at": timestamp, "updated_at": timestamp,
        },
    ]


async def seed_collection(db, collection_name: str, data: list[dict[str, Any]], label: str) -> None:
    """Generic helper to seed a collection."""
    if data:
        await db[collection_name].insert_many(data)
    print(f"  Created {len(data)} {label}")


async def seed_database() -> None:
    """Main seeding orchestrator."""
    client, _ = _make_client()
    db = client[db_name]

    print(f"Seeding Already Here Command OS Database ({STORAGE_BACKEND})...")
    await clear_all_data(db)

    print("Seeding entities:")
    await seed_collection(db, "revenue_streams", get_revenue_streams_data(), "revenue streams")
    await seed_collection(db, "agents", get_agents_data(), "agents")
    await seed_collection(db, "builds", get_builds_data(), "builds")
    await seed_collection(db, "deployments", get_deployments_data(), "deployments")
    await seed_collection(db, "platform_connectors", get_platform_connectors_data(), "platform connectors")
    await seed_collection(db, "audit_log", get_audit_events_data(), "audit events")
    await seed_collection(db, "content", get_content_data(), "content pieces")

    print("\nDatabase seeded successfully!")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_database())
