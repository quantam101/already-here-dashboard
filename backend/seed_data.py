#!/usr/bin/env python3
"""
Seed script to populate the Already Here Command OS with initial ecosystem data.
Refactored into modular functions per entity type.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']


def now_iso():
    return datetime.now(timezone.utc).isoformat()


async def clear_all_data(db):
    """Clear all collections before seeding."""
    collections = [
        "revenue_streams", "content", "agents", "builds",
        "deployments", "audit_log", "approvals", "platform_connectors",
        "content_ideas", "content_scripts", "scheduled_posts"
    ]
    for collection in collections:
        await db[collection].delete_many({})
    print("Cleared existing data")


def get_revenue_streams_data():
    """Return revenue streams seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "rev-001",
            "name": "Content Revenue Automation",
            "type": "content",
            "status": "active",
            "monthly_target": 5000.0,
            "monthly_actual": 1250.0,
            "description": "Automated blog and social media content monetization",
            "metadata": {"platforms": ["blog", "medium", "linkedin"]},
            "created_at": timestamp,
            "updated_at": timestamp
        },
        {
            "id": "rev-002",
            "name": "Federal Contracting",
            "type": "proposal",
            "status": "active",
            "monthly_target": 15000.0,
            "monthly_actual": 3000.0,
            "description": "Federal procurement and SBA proposals",
            "metadata": {"focus": "H&M RFID proof capabilities"},
            "created_at": timestamp,
            "updated_at": timestamp
        },
        {
            "id": "rev-003",
            "name": "Service Automation",
            "type": "service",
            "status": "active",
            "monthly_target": 10000.0,
            "monthly_actual": 2500.0,
            "description": "Automated service delivery and client management",
            "metadata": {},
            "created_at": timestamp,
            "updated_at": timestamp
        }
    ]


def get_agents_data():
    """Return agents seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "agent-001",
            "name": "Sovereign Orchestrator",
            "type": "orchestrator",
            "mission": "Coordinate multi-agent workflows and enforce governance policies",
            "status": "active",
            "allowed_actions": ["coordinate", "monitor", "route"],
            "forbidden_actions": ["deploy", "delete", "publish"],
            "approval_required_actions": ["deploy", "publish"],
            "cost_ceiling": 0.0,
            "run_count": 15, "success_count": 14, "failure_count": 1,
            "last_run": timestamp, "metadata": {},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "agent-002",
            "name": "Cost Guard Agent",
            "type": "security",
            "mission": "Enforce zero-spend policy and block unauthorized paid actions",
            "status": "active",
            "allowed_actions": ["validate", "block", "audit"],
            "forbidden_actions": ["spend", "authorize_payment"],
            "approval_required_actions": ["approve_paid_action"],
            "cost_ceiling": 0.0,
            "run_count": 47, "success_count": 47, "failure_count": 0,
            "last_run": timestamp, "metadata": {"mode": "zero-spend"},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "agent-003",
            "name": "Content Generation Agent",
            "type": "content",
            "mission": "Generate revenue-focused content using AI for blogs, social, and proposals",
            "status": "active",
            "allowed_actions": ["generate_content", "optimize_seo", "schedule"],
            "forbidden_actions": ["publish_directly"],
            "approval_required_actions": ["publish"],
            "cost_ceiling": 0.0,
            "run_count": 23, "success_count": 21, "failure_count": 2,
            "last_run": timestamp, "metadata": {},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "agent-004",
            "name": "Proposal Engine Agent",
            "type": "revenue",
            "mission": "Generate federal proposals and capability statements using H&M proof data",
            "status": "active",
            "allowed_actions": ["generate_proposal", "analyze_rfp", "compile_evidence"],
            "forbidden_actions": ["submit"],
            "approval_required_actions": ["submit"],
            "cost_ceiling": 0.0,
            "run_count": 8, "success_count": 7, "failure_count": 1,
            "last_run": timestamp, "metadata": {"evidence_source": "H&M US0275"},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "agent-005",
            "name": "Lifelong Catch and Correct",
            "type": "learning",
            "mission": "Track failures, generate fixes, and prevent repeated mistakes",
            "status": "active",
            "allowed_actions": ["analyze_failures", "generate_patches", "update_rules"],
            "forbidden_actions": ["auto_deploy"],
            "approval_required_actions": ["deploy_fix"],
            "cost_ceiling": 0.0,
            "run_count": 12, "success_count": 12, "failure_count": 0,
            "last_run": timestamp, "metadata": {},
            "created_at": timestamp, "updated_at": timestamp
        }
    ]


def get_builds_data():
    """Return builds seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "build-001", "name": "ProfitEngine v5", "type": "command_center",
            "status": "degraded", "source_repo": "quantam101/profitenginev5",
            "source_folder": "ProfitEngine_v5x_Build_20260523",
            "modules": ["agents", "webhooks", "content_pipeline", "distillation", "observability"],
            "production_gate_score": 72, "last_deploy": timestamp, "last_ci_status": "fail",
            "revenue_path": "direct", "next_action": "Fix OCI deployment workflow",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "build-002", "name": "GMAOS", "type": "operating_system",
            "status": "live", "source_repo": None, "source_folder": "GMAOS_Core",
            "modules": ["policy_broker", "governance", "execution_fabric"],
            "production_gate_score": 85, "last_deploy": timestamp, "last_ci_status": "pass",
            "revenue_path": "support", "next_action": None,
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "build-003", "name": "TradeGate", "type": "market_system",
            "status": "live", "source_repo": None, "source_folder": "TradeGate_v2",
            "modules": ["portfolio", "market_data", "simulation"],
            "production_gate_score": 78, "last_deploy": timestamp, "last_ci_status": "pass",
            "revenue_path": "indirect", "next_action": "Add live trading mode flag",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "build-004", "name": "VHLL Distillation Engine", "type": "efficiency_layer",
            "status": "draft", "source_repo": None,
            "source_folder": "ProfitEngine_v5x_Build_20260523/vhll-refactor.zip",
            "modules": ["semantic_compressor", "tiered_router", "logic_offloader"],
            "production_gate_score": 60, "last_deploy": None, "last_ci_status": None,
            "revenue_path": "support", "next_action": "Integrate into ProfitEngine main",
            "metadata": {"test_results": "234/234 passing"},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "build-005", "name": "Command OS Dashboard", "type": "dashboard",
            "status": "live", "source_repo": None, "source_folder": "/app",
            "modules": ["revenue", "content", "agents", "builds", "deployments", "audit"],
            "production_gate_score": 95, "last_deploy": timestamp, "last_ci_status": "pass",
            "revenue_path": "direct", "next_action": None,
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        }
    ]


def get_deployments_data():
    """Return deployments seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "deploy-001", "build_id": "build-001", "environment": "production",
            "status": "failed", "target": "oci", "version": "v5.0.3",
            "deployed_by": "github-actions", "rollback_available": True,
            "health_check_url": None, "health_status": None,
            "error_log": "SSH key authentication failed", "metadata": {},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "deploy-002", "build_id": "build-005", "environment": "production",
            "status": "success", "target": "oci", "version": "v1.0.0",
            "deployed_by": "system", "rollback_available": True,
            "health_check_url": "https://app.example.com/api/health",
            "health_status": "healthy", "error_log": None, "metadata": {},
            "created_at": timestamp, "updated_at": timestamp
        }
    ]


def get_platform_connectors_data():
    """Return platform connectors with cost classifications."""
    timestamp = now_iso()
    return [
        {
            "id": "conn-tiktok", "platform": "tiktok", "name": "TikTok",
            "cost_class": "manual_free", "has_api": True, "api_authenticated": False,
            "requires_app_review": True, "app_review_status": None,
            "credential_status": "missing", "supported_media_types": ["video"],
            "max_file_size_mb": 287, "max_duration_seconds": 600,
            "caption_max_length": 2200, "supports_scheduling": True,
            "rate_limit_per_day": 1000,
            "blocked_reason": "API requires developer app registration and Content Posting API approval",
            "setup_instructions": "Register at developers.tiktok.com, complete app review, configure OAuth2",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-youtube", "platform": "youtube", "name": "YouTube",
            "cost_class": "manual_free", "has_api": True, "api_authenticated": False,
            "requires_app_review": True, "app_review_status": None,
            "credential_status": "missing", "supported_media_types": ["video"],
            "max_file_size_mb": 256000, "max_duration_seconds": 43200,
            "caption_max_length": 5000, "supports_scheduling": True,
            "rate_limit_per_day": 10000,
            "blocked_reason": "YouTube Data API v3 requires OAuth2 setup and app verification",
            "setup_instructions": "Create project at Google Cloud Console, enable YouTube Data API v3",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-instagram", "platform": "instagram", "name": "Instagram",
            "cost_class": "manual_free", "has_api": True, "api_authenticated": False,
            "requires_app_review": True, "credential_status": "missing",
            "supported_media_types": ["image", "video"],
            "max_file_size_mb": 100, "max_duration_seconds": 90,
            "caption_max_length": 2200, "supports_scheduling": True,
            "rate_limit_per_day": 25,
            "blocked_reason": "Instagram Graph API requires Facebook App review",
            "setup_instructions": "Create Facebook App, request instagram_content_publish permission",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-linkedin", "platform": "linkedin", "name": "LinkedIn",
            "cost_class": "manual_free", "has_api": True, "api_authenticated": False,
            "requires_app_review": True, "credential_status": "missing",
            "supported_media_types": ["image", "video", "text"],
            "max_file_size_mb": 200, "max_duration_seconds": 600,
            "caption_max_length": 3000, "supports_scheduling": False,
            "blocked_reason": "LinkedIn Share API requires OAuth2 app with w_member_social permission",
            "setup_instructions": "Create LinkedIn App at linkedin.com/developers",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-twitter", "platform": "twitter", "name": "Twitter / X",
            "cost_class": "paid_blocked", "has_api": True, "api_authenticated": False,
            "requires_app_review": False, "credential_status": "missing",
            "supported_media_types": ["image", "video", "text"],
            "max_file_size_mb": 512, "max_duration_seconds": 140,
            "caption_max_length": 280, "supports_scheduling": False,
            "blocked_reason": "API requires PAID Elevated access ($100/month minimum)",
            "setup_instructions": "BLOCKED by Cost Guard - manual export only",
            "metadata": {"cost": "min $100/month"},
            "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-blog", "platform": "blog", "name": "Website Blog",
            "cost_class": "free_local", "has_api": False, "api_authenticated": False,
            "requires_app_review": False, "credential_status": "configured",
            "supported_media_types": ["text", "image"],
            "supports_scheduling": True, "blocked_reason": None,
            "setup_instructions": "Internal blog publishing - no external API required",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        },
        {
            "id": "conn-medium", "platform": "medium", "name": "Medium",
            "cost_class": "free_external", "has_api": True, "api_authenticated": False,
            "requires_app_review": False, "credential_status": "missing",
            "supported_media_types": ["text", "image"],
            "max_file_size_mb": 25, "supports_scheduling": False,
            "blocked_reason": "Integration token not configured",
            "setup_instructions": "Get integration token from medium.com/me/settings/security",
            "metadata": {}, "created_at": timestamp, "updated_at": timestamp
        }
    ]


def get_audit_events_data():
    """Return audit events seed data."""
    timestamp = now_iso()
    return [
        {
            "id": "audit-001", "event_type": "system.startup", "actor": "system",
            "action": "initialize", "resource_type": "command_os",
            "resource_id": "build-005", "status": "success", "metadata": {},
            "timestamp": timestamp
        },
        {
            "id": "audit-002", "event_type": "revenue.created", "actor": "system",
            "action": "seed", "resource_type": "revenue_stream",
            "resource_id": "rev-001", "status": "success", "metadata": {},
            "timestamp": timestamp
        },
        {
            "id": "audit-003", "event_type": "agent.created", "actor": "system",
            "action": "seed", "resource_type": "agent",
            "resource_id": "agent-001", "status": "success", "metadata": {},
            "timestamp": timestamp
        }
    ]


def get_content_data():
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
            "created_at": timestamp, "updated_at": timestamp
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
            "created_at": timestamp, "updated_at": timestamp
        }
    ]


async def seed_collection(db, collection_name, data, label):
    """Generic helper to seed a collection."""
    if data:
        await db[collection_name].insert_many(data)
    print(f"  Created {len(data)} {label}")


async def seed_database():
    """Main seeding orchestrator."""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("Seeding Already Here Command OS Database...")
    
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
