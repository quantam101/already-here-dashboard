import os
import json
from datetime import datetime
from pathlib import Path

PLATFORM_INSTRUCTIONS = {
    "tiktok": """TIKTOK MANUAL UPLOAD INSTRUCTIONS

1. Open TikTok app or https://www.tiktok.com/creator
2. Click the '+' button to create new post
3. Upload your video file
4. Copy and paste the caption from caption.txt
5. Add hashtags from caption.txt
6. Select privacy settings
7. Schedule post for the specified time or publish immediately
8. Click 'Post'

NOTE: TikTok Content Posting API requires app registration and approval.
Setup instructions: https://developers.tiktok.com/doc/content-posting-api-get-started/
""",
    "youtube": """YOUTUBE MANUAL UPLOAD INSTRUCTIONS

1. Go to https://studio.youtube.com
2. Click 'Create' → 'Upload videos'
3. Select your video file
4. Add title from title.txt
5. Copy description from caption.txt
6. Add hashtags
7. Upload thumbnail if provided
8. Select visibility (Public/Unlisted/Private)
9. Set publish time if scheduling
10. Click 'Publish'

NOTE: YouTube Data API v3 requires OAuth2 setup and app verification.
Setup: https://developers.google.com/youtube/v3/getting-started
""",
    "instagram": """INSTAGRAM MANUAL UPLOAD INSTRUCTIONS

1. Open Instagram app
2. Tap '+' to create new post/reel
3. Select your video/image
4. Add filters or editing
5. Click 'Next'
6. Copy and paste caption from caption.txt
7. Add hashtags
8. Tag location if relevant
9. Tap 'Share'

NOTE: Instagram Graph API requires Facebook App, app review, and approved permissions.
Setup: https://developers.facebook.com/docs/instagram-api
""",
    "linkedin": """LINKEDIN MANUAL UPLOAD INSTRUCTIONS

1. Go to https://www.linkedin.com
2. Click 'Start a post'
3. Click media icon to upload video/image
4. Copy and paste caption from caption.txt
5. Add hashtags
6. Select audience visibility
7. Click 'Post' or schedule

NOTE: LinkedIn API posting requires OAuth2 app setup and permissions.
Setup: https://docs.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/share-api
""",
    "twitter": """TWITTER/X MANUAL UPLOAD INSTRUCTIONS

1. Go to https://twitter.com or open X app
2. Click 'Post' or '+'
3. Attach media (video/image)
4. Copy and paste caption from caption.txt (max 280 chars)
5. Add hashtags within character limit
6. Click 'Post' or schedule

NOTE: Twitter API v2 posting requires Elevated access or Enterprise plan ($$$).
Free tier does not support tweet creation.
Setup: https://developer.twitter.com/en/portal/petition/essential/basic-info
""",
}

def get_platform_upload_instructions(platform: str) -> str:
    """Get detailed manual upload instructions for each platform."""
    return PLATFORM_INSTRUCTIONS.get(platform, f"""MANUAL UPLOAD INSTRUCTIONS FOR {platform.upper()}

1. Log into {platform}
2. Navigate to content creation area
3. Upload media files from export pack
4. Copy caption and hashtags from caption.txt
5. Set schedule time if supported
6. Publish post

API integration not yet configured for this platform.
""")

def create_export_metadata(post: dict) -> dict:
    """Create export package metadata."""
    return {
        "post_id": post['id'],
        "platform": post['platform'],
        "scheduled_time": post.get('scheduled_time', ''),
        "title": post.get('title', ''),
        "caption": post['caption'],
        "hashtags": post.get('hashtags', []),
        "media_urls": post.get('media_urls', []),
        "thumbnail_url": post.get('thumbnail_url'),
        "publishing_method": "manual_upload",
        "created_at": datetime.now().isoformat(),
        "instructions": get_platform_upload_instructions(post['platform'])
    }

def write_export_files(pack_dir: Path, post: dict, metadata: dict):
    """Write all export files to the pack directory."""
    # Write metadata file
    metadata_file = pack_dir / "post_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Write caption file
    caption_file = pack_dir / "caption.txt"
    with open(caption_file, 'w') as f:
        f.write(post['caption'])
        if post.get('hashtags'):
            f.write("\n\n")
            f.write(" ".join(f"#{tag}" for tag in post['hashtags']))
    
    # Write upload instructions
    instructions_file = pack_dir / "UPLOAD_INSTRUCTIONS.txt"
    with open(instructions_file, 'w') as f:
        f.write(get_platform_upload_instructions(post['platform']))
    
    # Write title file if exists
    if post.get('title'):
        title_file = pack_dir / "title.txt"
        with open(title_file, 'w') as f:
            f.write(post['title'])

async def create_export_pack(post: dict) -> str:
    """
    Create a ready-to-post export pack for manual platform upload.
    Generates all necessary files and metadata.
    """
    export_dir = Path("/app/exports")
    export_dir.mkdir(exist_ok=True)
    
    post_id = post['id']
    platform = post['platform']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    pack_dir = export_dir / f"{platform}_{post_id}_{timestamp}"
    pack_dir.mkdir(exist_ok=True)
    
    # Generate export package metadata
    export_metadata = create_export_metadata(post)
    
    # Write all files
    write_export_files(pack_dir, post, export_metadata)
    
    return str(pack_dir)
