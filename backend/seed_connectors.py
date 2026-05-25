#!/usr/bin/env python3
"""
Seed platform connectors with proper cost classes and setup instructions.
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

load_dotenv()

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def seed_platform_connectors():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    print("🔌 Seeding Platform Connectors...")
    
    await db.platform_connectors.delete_many({})
    
    connectors = [
        {
            "id": "conn-tiktok",
            "platform": "tiktok",
            "name": "TikTok",
            "cost_class": "manual_free",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": True,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["video"],
            "max_file_size_mb": 287,
            "max_duration_seconds": 600,
            "caption_max_length": 2200,
            "supports_scheduling": True,
            "rate_limit_per_day": 1000,
            "blocked_reason": "API requires developer app registration, Direct Post configuration, and Content Posting API approval",
            "setup_instructions": "1. Register app at https://developers.tiktok.com\\n2. Enable Content Posting API\\n3. Complete app review\\n4. Configure OAuth2 credentials in Bitwarden\\n5. Until approved, use manual export packs",
            "metadata": {"api_docs": "https://developers.tiktok.com/doc/content-posting-api-get-started/"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-youtube",
            "platform": "youtube",
            "name": "YouTube",
            "cost_class": "manual_free",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": True,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["video"],
            "max_file_size_mb": 256000,
            "max_duration_seconds": 43200,
            "caption_max_length": 5000,
            "supports_scheduling": True,
            "rate_limit_per_day": 10000,
            "blocked_reason": "YouTube Data API v3 requires OAuth2 setup and app verification for public uploads",
            "setup_instructions": "1. Create project at https://console.cloud.google.com\\n2. Enable YouTube Data API v3\\n3. Configure OAuth2 consent screen\\n4. Complete verification for public uploads\\n5. Store credentials in Bitwarden\\n6. Until verified, use manual export packs",
            "metadata": {"api_docs": "https://developers.google.com/youtube/v3/getting-started"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-instagram",
            "platform": "instagram",
            "name": "Instagram",
            "cost_class": "manual_free",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": True,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["image", "video"],
            "max_file_size_mb": 100,
            "max_duration_seconds": 90,
            "caption_max_length": 2200,
            "supports_scheduling": True,
            "rate_limit_per_day": 25,
            "blocked_reason": "Instagram Graph API requires Facebook App and app review for content publishing permissions",
            "setup_instructions": "1. Create Facebook App\\n2. Add Instagram Graph API product\\n3. Request instagram_content_publish permission\\n4. Complete app review\\n5. Connect Instagram Business account\\n6. Store tokens in Bitwarden\\n7. Until approved, use manual export packs",
            "metadata": {"api_docs": "https://developers.facebook.com/docs/instagram-api"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-linkedin",
            "platform": "linkedin",
            "name": "LinkedIn",
            "cost_class": "manual_free",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": True,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["image", "video", "text"],
            "max_file_size_mb": 200,
            "max_duration_seconds": 600,
            "caption_max_length": 3000,
            "supports_scheduling": False,
            "rate_limit_per_day": 100,
            "blocked_reason": "LinkedIn Share API requires OAuth2 app with w_member_social permission",
            "setup_instructions": "1. Create LinkedIn App at https://www.linkedin.com/developers\\n2. Request w_member_social permission\\n3. Configure OAuth2 redirect\\n4. Store credentials in Bitwarden\\n5. Until configured, use manual export packs",
            "metadata": {"api_docs": "https://docs.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/share-api"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-twitter",
            "platform": "twitter",
            "name": "Twitter / X",
            "cost_class": "paid_blocked",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": False,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["image", "video", "text"],
            "max_file_size_mb": 512,
            "max_duration_seconds": 140,
            "caption_max_length": 280,
            "supports_scheduling": False,
            "rate_limit_per_day": None,
            "blocked_reason": "Twitter API v2 requires Elevated ($100/month) or Enterprise ($$$) for tweet creation. Free Basic tier cannot create tweets.",
            "setup_instructions": "Twitter API posting is PAID ONLY. Cost Guard blocks this connector. Use manual export packs for free posting.",
            "metadata": {"api_docs": "https://developer.twitter.com/en/docs/twitter-api", "cost": "minimum $100/month"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-blog",
            "platform": "blog",
            "name": "Website Blog",
            "cost_class": "free_local",
            "has_api": False,
            "api_authenticated": False,
            "requires_app_review": False,
            "app_review_status": None,
            "credential_status": "configured",
            "supported_media_types": ["text", "image"],
            "max_file_size_mb": None,
            "max_duration_seconds": None,
            "caption_max_length": None,
            "supports_scheduling": True,
            "rate_limit_per_day": None,
            "blocked_reason": None,
            "setup_instructions": "Internal blog publishing - no external API required",
            "metadata": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": "conn-medium",
            "platform": "medium",
            "name": "Medium",
            "cost_class": "free_external",
            "has_api": True,
            "api_authenticated": False,
            "requires_app_review": False,
            "app_review_status": None,
            "credential_status": "missing",
            "supported_media_types": ["text", "image"],
            "max_file_size_mb": 25,
            "max_duration_seconds": None,
            "caption_max_length": None,
            "supports_scheduling": False,
            "rate_limit_per_day": None,
            "blocked_reason": "Integration token not configured",
            "setup_instructions": "1. Get integration token from https://medium.com/me/settings/security\\n2. Store in Bitwarden under MEDIUM_INTEGRATION_TOKEN\\n3. Integration is free for personal publishing",
            "metadata": {"api_docs": "https://github.com/Medium/medium-api-docs"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.platform_connectors.insert_many(connectors)
    print(f"Created {len(connectors)} platform connectors")
    
    print("Connector Status Summary:")
    for conn in connectors:
        cost_class = conn['cost_class']
        print(f"{conn['name']}: {cost_class} - {conn.get('blocked_reason', 'Ready')}")
    
    client.close()\n\nif __name__ == \"__main__\":\n    asyncio.run(seed_platform_connectors())
