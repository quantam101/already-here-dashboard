# Social Media Credential Setup — Already Here Command OS

All credentials go in `/opt/command-os/.env` on the server.
After adding any credential, run: `cd /opt/command-os && sudo docker compose -f docker-compose.sqlite.yml up -d backend`

---

## ✅ TIER 1 — Works Today (5–15 minutes each)

### Medium
1. Go to https://medium.com/me/settings/security
2. Scroll to "Integration Tokens" → click "Get integration token"
3. Name it "AlreadyHereOS", copy the token
4. Add to server `.env`:
   ```
   MEDIUM_INTEGRATION_TOKEN=your_token_here
   ```

### Dev.to
1. Go to https://dev.to/settings/extensions
2. Scroll to "DEV Community API Keys" → Generate API key
3. Add to server `.env`:
   ```
   DEVTO_API_KEY=your_key_here
   ```

### Reddit
1. Go to https://www.reddit.com/prefs/apps
2. Click "Create another app..." at the bottom
3. Name: `AlreadyHereOS`, Type: **script**, Redirect URI: `http://localhost`
4. Copy the client_id (under the app name) and secret
5. Add to server `.env`:
   ```
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_secret
   REDDIT_USERNAME=your_reddit_username
   REDDIT_PASSWORD=your_reddit_password
   REDDIT_SUBREDDITS=entrepreneur,passive_income,sidehustle,AItools
   ```

---

## 🟡 TIER 2 — Requires App Registration (1–4 hours)

### LinkedIn
1. Go to https://www.linkedin.com/developers/apps → New App
2. App Name: `Already Here LLC`, Company: your LinkedIn Company Page
3. In "Products" tab → Request access to "Share on LinkedIn"
4. Get OAuth 2.0 tokens via: https://www.linkedin.com/developers/tools/oauth/token-generator
5. Select scopes: `w_member_social`, `r_liteprofile`
6. Add to server `.env`:
   ```
   LINKEDIN_ACCESS_TOKEN=your_access_token
   LINKEDIN_PERSON_URN=urn:li:person:YOUR_PERSON_ID
   ```
   (Get your Person URN from: GET https://api.linkedin.com/v2/me)

### YouTube (for video uploads)
1. Go to https://console.cloud.google.com
2. Create a new project → Enable "YouTube Data API v3"
3. Credentials → Create OAuth 2.0 Client ID (Desktop application)
4. Download the credentials JSON
5. Run the one-time auth script on your local machine:
   ```bash
   cd /opt/command-os && python3 backend/scripts/youtube_auth.py
   ```
6. Add to server `.env`:
   ```
   YOUTUBE_CLIENT_ID=your_client_id
   YOUTUBE_CLIENT_SECRET=your_client_secret
   YOUTUBE_REFRESH_TOKEN=your_refresh_token
   ```

### Discourse / Niche Forums
For any forum running Discourse software (many tech/business forums):
1. Go to your forum → Admin → API → Generate a Master API Key
2. Add to server `.env`:
   ```
   DISCOURSE_BASE_URL=https://yourforum.com
   DISCOURSE_API_KEY=your_api_key
   DISCOURSE_API_USERNAME=your_username
   DISCOURSE_CATEGORY_ID=1
   ```

---

## 🔴 TIER 3 — Requires Platform App Review (days to weeks)

### Facebook Pages + Instagram + Threads (all one Meta App)
These all share one Meta Developer App.

**Step 1: Create Meta Developer App**
1. Go to https://developers.facebook.com/apps → Create App
2. Use case: "Other" → App type: "Business"
3. App Name: `Already Here LLC`

**Step 2: Connect your Facebook Page**
1. Dashboard → Add Product → "Facebook Login"
2. Dashboard → Add Product → "Instagram Graph API"
3. Dashboard → Add Product → "Threads API"

**Step 3: Request permissions (App Review)**
- `pages_manage_posts` — post to your Facebook Page
- `pages_read_engagement` — read page metrics
- `instagram_content_publish` — post to Instagram
- `threads_content_publish` — post to Threads

**Step 4: Generate Page Access Token**
1. Graph API Explorer → select your app → select your page
2. Generate a long-lived Page Access Token (60 days)
3. Exchange for a permanent token via:
   ```
   GET https://graph.facebook.com/v19.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id={app_id}&
     client_secret={app_secret}&
     fb_exchange_token={short_lived_token}
   ```

**Step 5: Add to server `.env`:**
```
FB_PAGE_ID=your_page_id
FB_PAGE_ACCESS_TOKEN=your_permanent_page_token
IG_USER_ID=your_instagram_business_account_id
IG_ACCESS_TOKEN=same_page_access_token
THREADS_USER_ID=your_threads_user_id
THREADS_ACCESS_TOKEN=your_threads_token
```

**Get your Page ID:** https://www.facebook.com/your-page-name/about → scroll down
**Get Instagram Business Account ID:** Graph API Explorer → `me?fields=instagram_business_account`
**Get Threads User ID:** Graph API Explorer → `me?fields=threads_user_id`

---

### TikTok (Content Posting API — requires business approval)
1. Go to https://developers.tiktok.com → My Apps → Create App
2. Add Product: "Content Posting API"
3. Submit for review with business use case description
4. Once approved, complete OAuth flow to get access token
5. Add to server `.env`:
   ```
   TIKTOK_ACCESS_TOKEN=your_access_token
   ```

**TikTok Review Tips:**
- Business name: Already Here LLC
- Use case: "Automated content distribution for digital marketing agency"
- Website: https://alreadyherellc.com

---

## 📦 EXPORT PACK — No API Needed (Works Immediately)

For platforms without APIs or while awaiting app review, the system generates
**Export Packs** automatically after each cycle.

**How to use:**
1. Go to https://app.alreadyherellc.com → **Publishing** tab
2. Click any draft → **Export Pack**
3. Copy the formatted content for each platform:
   - `video_script` → Film in CapCut, post to TikTok/YouTube Shorts/Instagram Reels
   - `facebook_groups` → Paste into your Facebook Groups
   - `quora` → Find a matching question on Quora, paste as your answer
   - `forum` → Post to niche forums, Reddit, Hacker News
   - `instagram_caption` → Use with your image/video in Instagram

**Or via API:**
```bash
curl https://app.alreadyherellc.com/api/cycle/export-pack/{idea_id}
```

---

## Trigger a Full Cycle (After Adding Credentials)
```bash
curl -X POST https://app.alreadyherellc.com/api/cycle/run
```

Check which connectors are live:
```bash
curl https://app.alreadyherellc.com/api/cycle/connectors
```
