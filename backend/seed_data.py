#!/usr/bin/env python3
"""
Seed script to populate the Already Here Command OS with initial ecosystem data.
This creates the builds, agents, revenue streams, and other entities mentioned in the requirements.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def seed_database():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🌱 Seeding Already Here Command OS Database...")
    
    # Clear existing data
    print("Clearing existing data...")
    await db.revenue_streams.delete_many({})
    await db.content.delete_many({})
    await db.agents.delete_many({})
    await db.builds.delete_many({})
    await db.deployments.delete_many({})
    await db.audit_log.delete_many({})
    await db.approvals.delete_many({})
    
    # Seed Revenue Streams
    print("Creating revenue streams...")
    revenue_streams = [
        {
            "id": "rev-001",
            "name": "Content Revenue Automation",
            "type": "content",
            "status": "active",
            "monthly_target": 5000.0,
            "monthly_actual": 1250.0,
            "description": "Automated blog and social media content monetization",
            "metadata": {"platforms": ["blog", "medium", "linkedin"]},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.revenue_streams.insert_many(revenue_streams)
    print(f"✓ Created {len(revenue_streams)} revenue streams")
    
    # Seed Agents
    print("Creating agents...")
    agents = [
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
            "run_count": 15,
            "success_count": 14,
            "failure_count": 1,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "run_count": 47,
            "success_count": 47,
            "failure_count": 0,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "metadata": {"mode": "zero-spend"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "run_count": 23,
            "success_count": 21,
            "failure_count": 2,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "run_count": 8,
            "success_count": 7,
            "failure_count": 1,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "metadata": {"evidence_source": "H&M US0275"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
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
            "run_count": 12,
            "success_count": 12,
            "failure_count": 0,
            "last_run": datetime.now(timezone.utc).isoformat(),
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.agents.insert_many(agents)
    print(f"✓ Created {len(agents)} agents")
    
    # Seed Builds
    print("Creating builds...")
    builds = [
        {
            "id": "build-001",
            "name": "ProfitEngine v5",
            "type": "command_center",
            "status": "degraded",
            "source_repo": "quantam101/profitenginev5",
            "source_folder": "ProfitEngine_v5x_Build_20260523",
            "modules": ["agents", "webhooks", "content_pipeline", "distillation", "observability"],
            "production_gate_score": 72,
            "last_deploy": datetime.now(timezone.utc).isoformat(),
            "last_ci_status": "fail",
            "revenue_path": "direct",
            "next_action": "Fix OCI deployment workflow",
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "build-002",
            "name": "GMAOS",
            "type": "operating_system",
            "status": "live",
            "source_repo": None,
            "source_folder": "GMAOS_Core",
            "modules": ["policy_broker", "governance", "execution_fabric"],
            "production_gate_score": 85,
            "last_deploy": datetime.now(timezone.utc).isoformat(),
            "last_ci_status": "pass",
            "revenue_path": "support",
            "next_action": None,
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "build-003",
            "name": "TradeGate",
            "type": "market_system",
            "status": "live",
            "source_repo": None,
            "source_folder": "TradeGate_v2",
            "modules": ["portfolio", "market_data", "simulation"],
            "production_gate_score": 78,
            "last_deploy": datetime.now(timezone.utc).isoformat(),
            "last_ci_status": "pass",
            "revenue_path": "indirect",
            "next_action": "Add live trading mode flag",
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "build-004",
            "name": "VHLL Distillation Engine",
            "type": "efficiency_layer",
            "status": "draft",
            "source_repo": None,
            "source_folder": "ProfitEngine_v5x_Build_20260523/vhll-refactor.zip",
            "modules": ["semantic_compressor", "tiered_router", "logic_offloader"],
            "production_gate_score": 60,
            "last_deploy": None,
            "last_ci_status": None,
            "revenue_path": "support",
            "next_action": "Integrate into ProfitEngine main",
            "metadata": {"test_results": "234/234 passing"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "build-005",
            "name": "Command OS Dashboard",
            "type": "dashboard",
            "status": "live",
            "source_repo": None,
            "source_folder": "/app",
            "modules": ["revenue", "content", "agents", "builds", "deployments", "audit"],
            "production_gate_score": 95,
            "last_deploy": datetime.now(timezone.utc).isoformat(),
            "last_ci_status": "pass",
            "revenue_path": "direct",
            "next_action": None,
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.builds.insert_many(builds)
    print(f"✓ Created {len(builds)} builds")
    
    # Seed Deployments
    print("Creating deployment records...")
    deployments = [
        {
            "id": "deploy-001",
            "build_id": "build-001",
            "environment": "production",
            "status": "failed",
            "target": "oci",
            "version": "v5.0.3",
            "deployed_by": "github-actions",
            "rollback_available": True,
            "health_check_url": None,
            "health_status": None,
            "error_log": "SSH key authentication failed",
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "deploy-002",
            "build_id": "build-005",
            "environment": "production",
            "status": "success",
            "target": "oci",
            "version": "v1.0.0",
            "deployed_by": "system",
            "rollback_available": True,
            "health_check_url": "https://a19cc646-11fd-468b-b5fd-b0d6e6c4db27.preview.emergentagent.com/api/health",
            "health_status": "healthy",
            "error_log": None,
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.deployments.insert_many(deployments)
    print(f"✓ Created {len(deployments)} deployment records")
    
    # Seed Audit Events
    print("Creating audit events...")
    audit_events = [
        {
            "id": "audit-001",
            "event_type": "system.startup",
            "actor": "system",
            "action": "initialize",
            "resource_type": "command_os",
            "resource_id": "build-005",
            "status": "success",
            "metadata": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "audit-002",
            "event_type": "revenue.created",
            "actor": "system",
            "action": "seed",
            "resource_type": "revenue_stream",
            "resource_id": "rev-001",
            "status": "success",
            "metadata": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "audit-003",
            "event_type": "agent.created",
            "actor": "system",
            "action": "seed",
            "resource_type": "agent",
            "resource_id": "agent-001",
            "status": "success",
            "metadata": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.audit_log.insert_many(audit_events)
    print(f"✓ Created {len(audit_events)} audit events")
    
    # Seed Sample Content
    print("Creating sample content...")
    content_pieces = [
        {
            "id": "content-001",
            "title": "Revenue Automation with AI - The Complete Guide",
            "content_type": "blog",
            "body": "Learn how to automate your revenue generation using AI-powered content creation, proposal generation, and autonomous agents...",
            "status": "published",
            "platform": "blog",
            "revenue_stream_id": "rev-001",
            "generated_by": "ai",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"keywords": ["automation", "revenue", "ai"], "tone": "professional", "length": "long"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "content-002",
            "title": "H&M Store US0275 RFID Implementation Success Story",
            "content_type": "proposal",
            "body": "Comprehensive case study showcasing successful RFID deployment at Chandler Fashion Center H&M location with 55 readers, 61 data runs, and 4 new AP installations...",
            "status": "draft",
            "platform": None,
            "revenue_stream_id": "rev-002",
            "generated_by": "ai",
            "published_at": None,
            "metadata": {"keywords": ["rfid", "retail", "h&m"], "tone": "technical", "length": "long"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    await db.content.insert_many(content_pieces)
    print(f"✓ Created {len(content_pieces)} content pieces")
    
    print("\n✨ Database seeded successfully!")
    print(f"Revenue Streams: {len(revenue_streams)}")
    print(f"Agents: {len(agents)}")
    print(f"Builds: {len(builds)}")
    print(f"Deployments: {len(deployments)}")
    print(f"Content Pieces: {len(content_pieces)}")
    print(f"Audit Events: {len(audit_events)}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
