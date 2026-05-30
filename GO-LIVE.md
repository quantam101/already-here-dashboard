# 🚀 Go Live — Final Runbook

This is the **single document** for taking the Command OS from "running in preview" to "live at `https://alreadyherellc.com` collecting real Stripe revenue, with nightly backups and a Cost Guard."

> **Time budget:** 30–60 minutes  
> **Cost:** $0/month (OCI Always Free + Let's Encrypt + SQLite)

Three phases. Do them in order. Each phase ends with a verification curl that **must** return success before moving on.

---

## Phase 1 — Deploy the app to OCI

Follow `DEPLOY-FINAL.md`. Total time ≈ 15 min once you have the SSH key.

**Verification before phase 2:**

```bash
curl -fsS https://alreadyherellc.com/api/health/
# → {"status":"healthy","timestamp":"..."}
curl -fsS https://alreadyherellc.com/api/system/status | python3 -m json.tool
# → returns counts + flags, no errors
```

If both work, the app is live. Browser-open `https://alreadyherellc.com` → Quickstart Wizard should appear.

---

## Phase 2 — Switch Stripe to live mode

Follow `LIVE_MODE_CHECKLIST.md`. Total time ≈ 10 min.

**Verification before phase 3:**

```bash
# (a) Readiness — should be all green
curl -fsS https://alreadyherellc.com/api/payments/readiness | python3 -m json.tool
# look for: "go_live_ready": true, "issues": []

# (b) End-to-end smoke test (charges $0.50, auto-refunds)
SMOKE=$(curl -fsS -X POST https://alreadyherellc.com/api/payments/smoke-test/create)
echo "$SMOKE" | python3 -m json.tool
URL=$(echo "$SMOKE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["url"])')
SID=$(echo "$SMOKE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')

# Open $URL in browser → pay $0.50 with real card → wait 15 sec → then:
curl -fsS https://alreadyherellc.com/api/payments/smoke-test/status/$SID | python3 -m json.tool
# look for: "verified_live_pipeline": true, "smoke_refund_status": "succeeded"
```

If `verified_live_pipeline` is `true` → live keys + webhook + auto-refund all work. You're ready to take real money.

---

## Phase 3 — Operational hardening

These are one-time SSH commands on the OCI box. Each is idempotent.

### 3a. Enable automated nightly backups

```bash
sudo bash /opt/command-os/scripts/install-backup-cron.sh
```

Confirms with:
```bash
systemctl list-timers cmdos-backup.timer
ls -lh /opt/command-os/backups/
```

You should see one backup file already created and a timer showing the next 03:00 UTC fire time.

### 3b. (Optional) Enforce daily LLM token cap

Default: unlimited. To put a hard ceiling on LLM spend (per the Cost Guard):

```bash
sudo nano /opt/command-os/backend/.env
# Add (pick any number — 50k is a generous daily ceiling for solo use):
LLM_DAILY_TOKEN_CAP=50000
```

Save → restart:

```bash
cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

Verify:
```bash
curl -fsS https://alreadyherellc.com/api/distillation/budget | python3 -m json.tool
# look for: "daily_cap": 50000, "remaining": <some number>, "over_cap": false
```

Once exceeded, all LLM-calling routes (`/api/studio/ideas/{id}/script`, `/api/proposals/draft`, `/api/books/`, `/api/advisor/recommend`) will return HTTP 429 until UTC midnight rolls over. The Analytics page's **Data Distillation** card visualizes this in real time.

### 3c. Test the Cost Guard end-to-end

Browser → `https://alreadyherellc.com/analytics` → the top card is **Data Distillation**. After a few days you'll see:
- Tokens saved (from cache hits)
- $ saved (estimated)
- Cache hit-rate line chart (last 14 days)
- Today's usage vs cap (with color-coded progress bar)

---

## You're done

The app is now:
- ✅ Live at `https://alreadyher ellc.com`on a $0/month OCI host
- ✅ Collecting real Stripe revenue
- ✅ Auto-refunding smoke-test charges so you can re-verify any time
- ✅ Backed up nightly to host disk (14-day retention)
- ✅ Cost-guarded: every LLM call is cached; daily token cap enforced if set
- ✅ Audit-logged: every payment, refund, ledger entry, and LLM call goes to `audit_log`

---

## Daily ops cheat sheet

```bash
# health
curl -fsS https://alreadyherellc.com/api/health/

# today's $ + token usage
curl -fsS https://alreadyherellc.com/api/distillation/budget | python3 -m json.tool
curl -fsS https://alreadyherellc.com/api/ledger/stats/profit-progress | python3 -m json.tool

# manual backup
ssh ubuntu@<ip>; sudo bash /opt/command-os/scripts/backup-sqlite.sh

# manual restart
ssh ubuntu@<ip>; sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml restart

# logs
ssh ubuntu@<ip>; sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f --tail 100
```

## Rollback

If anything goes sideways post-go-live:

```bash
# Revert Stripe to test mode (live charges already collected unaffected)
ssh ubuntu@<ip>
sudo sed -i 's|^STRIPE_API_KEY=.*|STRIPE_API_KEY="sk_test_emergent"|' /opt/command-os/backend/.env
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml restart backend
```

## When something breaks

- `LIVE_MODE_CHECKLIST.md` § "Common mistakes" — quick fixes for the top 5 failure modes
- `HANDOFF.md` — full handoff doc for a DevOps freelancer if you want to outsource further changes
- All scripts are in `/opt/command-os/scripts/` — plain bash, error messages tell you exactly where they died

## What it cost to build

| Service | Monthly cost |
|---|---|
| OCI VM.Standard.E2.1.Micro (Always Free) | $0 |
| Let's Encrypt (HTTPS) | $0 |
| SQLite (on host disk) | $0 |
| Caddy reverse proxy | $0 |
| GoDaddy domain (paid annually) | $1.50 |
| Stripe (pay-per-transaction only) | $0 base |
| Emergent LLM Key (Cost Guard enforced) | depends on `LLM_DAILY_TOKEN_CAP` |
| **Total fixed cost** | **~$1.50/month** |
