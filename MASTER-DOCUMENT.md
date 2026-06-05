# Already Here Command OS — Master Document v2.0

**Single source of truth.** What this is, what is built, the governance architecture,
how to deploy, how to operate it, and every decision that can be changed declaratively.
**Updated: 2026-05-27 (v2.0 — ASI Governance Layer)**

---

## 1. Mission

A single-operator, declaratively governed AI **revenue automation OS** that runs at
**$0/month** on Oracle Cloud Always Free, generates SEO content + grants + books via
cached LLM calls, collects real money via Stripe, and autonomously tracks net profit
toward a **$25,000 commercialization unlock** — 24 hours a day, 7 days a week, with
zero manual intervention required.

**Domain:** `alreadyherellc.com` | **Repo:** `quantam101/already-here-dashboard`

---

## 2. What Changed in v2.0 (2026-05-27)

| Component | v1 | v2 |
|-----------|----|----|
| Scheduler | Single daily cycle at 07:00 UTC | Multi-frequency sovereign-governed ticks (15/30/60/360 min) |
| Orchestration | Manual `/cycle/run` | Governing AI (Sovereign) makes every dispatch decision |
| Agent model | CRUD records in DB | Executing Python agents with circuit-breakers and audit trails |
| Configuration | Env vars only | Declarative `backend/config/manifest.yaml` + env vars |
| Content publishing | Manual operator step | ContentAgent publishes to GitHub Pages + Dev.to automatically (when `AUTO_PUBLISH=true`) |
| 24/7 cloud trigger | None | GitHub Actions sovereign.yml fires every hour |
| Self-healing | None | GuardAgent detects degradation, drains dead-letter queue every 15 min |
| Revenue tracking | Manual ledger entries | RevenueAgent reconciles + fires milestone alerts every 30 min |

---

## 3. Architecture

```
┌────────────────────────────────────────────────────────────┐
│              GitHub Actions (24/7 heartbeat)               │
│              sovereign.yml — fires every hour              │
└───────────────────────────┬────────────────────────────────┘
                            │ POST /api/sovereign/trigger
                            ▼
┌────────────────────────────────────────────────────────────┐
│                   SOVEREIGN AGENT (v1)                     │
│   • Reads YAML system snapshot (revenue, health, pipeline) │
│   • Calls Gemini 2.0 Flash — returns SovereignDecision     │
│   • Decision cached 55 min (zero token cost on re-use)     │
│   • Dispatches agent list to AgentExecutor                 │
│   • Every decision → audit log → dashboard visible         │
└──────────┬───────────────────┬──────────────┬─────────────┘
           │ sequential first  │              │ parallel batch
           ▼                   ▼              ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
   │ GuardAgent   │  │ ScoutAgent   │  │ContentAgent  │  │RevenueAgent  │
   │ every 15 min │  │ every 1 hour │  │ every 6 hrs  │  │ every 30 min │
   │ 0 LLM tokens │  │ 0 LLM tokens │  │ ≤8K tokens   │  │ ≤200 tokens  │
   │ circuit brkr │  │ dedup 48h    │  │ cached 30d   │  │ milestone    │
   │ dead-letter  │  │ 5 sources    │  │ 5 platforms  │  │ alerts       │
   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
           │                 │                 │                 │
           └─────────────────┴─────────────────┴─────────────────┘
                                     │
                              All results →
                         agent_runs collection
                         sovereign_decisions
                         audit_log (immutable)
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────┐
│              FastAPI Backend + SQLite/MongoDB               │
│  25 route modules  │  7 services  │  4 executing agents    │
└──────────────────────────────┬─────────────────────────────┘
                               │ HTTPS (Caddy reverse proxy)
                               ▼
                     alreadyherellc.com (React SPA)
```

### Memory budget on 1 GB OCI Always Free host

| Component | RAM Usage |
|-----------|-----------|
| Backend container (FastAPI + agents) | ~220 MB |
| Caddy container | ~30 MB |
| SQLite DB file | ~200 KB |
| **Total** | **~250 MB of 1,024 MB** |

---

## 4. Governing AI — The Sovereign

**File:** `backend/services/sovereign_agent.py`

The Sovereign is the only entity that decides which agents run. It cannot be bypassed
(every agent run is gated through AgentExecutor which only runs what the Sovereign approves).

**Decision cycle (every 60 minutes):**
1. Build YAML snapshot: `{revenue, system_health, content_queue, agent_history}`
2. Call `gemini/gemini-2.0-flash` via `run_cached()` — free on cache hit
3. Receive `SovereignDecision` JSON:
   ```json
   {
     "priority_action": "Generate 3 articles from top Reddit trends",
     "agents_to_run": ["guard-agent", "scout-agent", "content-agent"],
     "reasoning": "10 unprocessed opportunities, content queue empty, system healthy",
     "risk_level": "low",
     "estimated_tokens": 5200,
     "skip_reason": null
   }
   ```
4. Validate agent IDs against registry (unknown agents rejected)
5. Force-include `guard-agent` (safety — always runs first)
6. Dispatch to `AgentExecutor`
7. Log decision → `sovereign_decisions` collection + audit trail

**Safety rails (hard-coded, cannot be overridden by LLM output):**
- `guard-agent` always runs first (sequential, not parallel)
- If `system.overall == "degraded"`: skip all non-guard agents, no LLM call
- If LLM call fails: fallback to `[guard-agent, scout-agent]` only
- Agent IDs from LLM response validated against `AGENT_REGISTRY` whitelist

---

## 5. Agent Specifications

### GuardAgent (`agents/guard_agent.py`)
| Property | Value |
|----------|-------|
| Schedule | Every 15 minutes |
| LLM tokens | 0 (pure logic) |
| Timeout | 20 seconds |
| Circuit breaker | 3 failures → 900s reset |

**Outputs:** `system_health` collection snapshot
**Capabilities:** health-check self ping, psutil memory%, dead-letter drain (requeues failed runs), circuit-breaker roll-up

### ScoutAgent (`agents/scout_agent.py`)
| Property | Value |
|----------|-------|
| Schedule | Every 60 minutes |
| LLM tokens | 0 (free HTTP sources only) |
| Timeout | 45 seconds |
| Deduplication | 48-hour URL fingerprint window |

**Sources:** Reddit ×3, HackerNews Algolia, Google News ×2
**Outputs:** `scout_opportunities` collection (deduped by sha256 URL hash)

### ContentAgent (`agents/content_agent.py`)
| Property | Value |
|----------|-------|
| Schedule | Every 6 hours |
| LLM tokens | ≤8,000 per run (~5 articles) |
| Timeout | 120 seconds |
| Cache TTL | 30 days |

**Pipeline per opportunity:**
1. Distill title + summary → compact prompt (saves ~30% tokens)
2. `run_cached()` → Gemini 2.0 Flash → structured JSON article
3. Sanitize slug, sanitize tags (Dev.to compat: lowercase, alphanumeric, ≤20 chars)
4. Save to `content_queue` (status: `ready`)
5. If `AUTO_PUBLISH=true`: push to GitHub Pages + Dev.to with canonical URL

**Auto-publish note:** `AUTO_PUBLISH` defaults to `false` — operator reviews queue and approves. Set to `true` to enable fully autonomous publishing.

### RevenueAgent (`agents/revenue_agent.py`)
| Property | Value |
|----------|-------|
| Schedule | Every 30 minutes |
| LLM tokens | ≤200 (advisor recommendation, cached) |
| Timeout | 30 seconds |

**Capabilities:** sum all `revenue_ledger` entries → net USD, check milestones [100, 500, 1K, 5K, 10K, 25K], fire `revenue.milestone_crossed` audit events, project days-to-unlock at current 7-day velocity

---

## 6. Declarative Configuration

**All system behavior is driven by `backend/config/manifest.yaml`.**
No code changes required for most operational adjustments — edit the YAML, restart backend.

Key knobs:

| YAML path | Default | What it controls |
|-----------|---------|-----------------|
| `sovereign.cycle_interval_minutes` | 60 | How often Sovereign makes a decision |
| `sovereign.safety.max_daily_llm_tokens` | 80,000 | Hard ceiling across all agents |
| `sovereign.safety.max_daily_usd` | $0.10 | Spending limit (429 if exceeded) |
| `agents[*].enabled` | true/false | Toggle any agent on/off |
| `agents[*].budget_tokens` | varies | Per-agent token budget |
| `content.auto_publish` | false | Enable/disable autonomous publishing |
| `content.ideas_per_cycle` | 5 | Articles generated per ContentAgent run |

---

## 7. REST API — New Endpoints

### Sovereign Governance API (`/api/sovereign/*`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sovereign/status` | Last decision + per-agent health |
| `GET` | `/api/sovereign/history?limit=20` | Last N sovereign decisions |
| `POST` | `/api/sovereign/trigger` | Manually fire one full cycle now |
| `GET` | `/api/sovereign/agents` | Registered agent registry |
| `DELETE` | `/api/sovereign/cache` | Force fresh LLM reasoning next tick |

**Status response example:**
```json
{
  "sovereign": {
    "decision_id": "sov-a7f3d12c9b",
    "priority_action": "Generate articles from 8 unprocessed Reddit opportunities",
    "agents_to_run": ["guard-agent", "scout-agent", "content-agent"],
    "risk_level": "low",
    "made_at": "2026-05-27T14:05:00Z"
  },
  "agents": {
    "guard-agent":   {"last_success": true, "duration_ms": 340},
    "scout-agent":   {"last_success": true, "duration_ms": 4120},
    "content-agent": {"last_success": true, "duration_ms": 38400},
    "revenue-agent": {"last_success": true, "duration_ms": 210}
  }
}
```

---

## 8. Deploy Playbook (3 Phases)

### Phase 1 — OCI deploy (~15 min)

1. OCI Console → Compute → **Create Instance**
   - Image: **Ubuntu 22.04** (NOT 20.04 — breaks Docker installer)
   - Shape: `VM.Standard.E2.1.Micro` (Always Free)
   - Advanced → Init script:
     ```bash
     #!/bin/bash
     curl -fsSL https://raw.githubusercontent.com/quantam101/already-here-dashboard/main/cloud-init.sh | bash
     ```
2. Security List ingress: TCP 22 (SSH), 80 (HTTP), 443 (HTTPS)
3. GoDaddy DNS: `@` and `www` A-records → instance public IP, TTL 600
4. SSH in:
   ```bash
   ssh -i ~/.ssh/oci_cmdos ubuntu@<IP>
   sudo tail -f /var/log/command-os-bootstrap.log
   ```
5. Wait for `BOOTSTRAP COMPLETE`, then:
   ```bash
   sudo nano /opt/command-os/backend/.env
   ```
   Add:
   ```env
   [removed]
   STRIPE_API_KEY=sk_test_[removed]
   OPERATOR_EMAIL=alreadyherellc@gmail.com
   ```
   ```bash
   cd /opt/command-os && sudo docker compose -f docker-compose.sqlite.yml restart backend
   ```

**Phase 1 gate:** `curl -fsS https://alreadyherellc.com/api/health/` → `{"status":"healthy"}`

### Phase 2 — Sovereign activation (~5 min)

Add to `/opt/command-os/backend/.env`:
```env
# Sovereign governance
GITHUB_CONTENT_OWNER=quantam101
GITHUB_CONTENT_REPO=content
CONTENT_REPO_TOKEN=gho_...
DEVTO_API_KEY=...
AUTO_PUBLISH=false          # set true for fully autonomous publishing
LLM_DAILY_TOKEN_CAP=80000
```

Add GitHub secret `CMDOS_BASE_URL=https://alreadyherellc.com` to enable the
`sovereign.yml` GitHub Actions heartbeat.

**Phase 2 gate:**
```bash
curl -fsS -X POST https://alreadyherellc.com/api/sovereign/trigger | python3 -m json.tool
# → {"status":"completed","decision_id":"sov-...","agents_dispatched":["guard-agent","scout-agent"]}
```

### Phase 3 — Stripe live mode + hardening (~10 min)

Full detail in `LIVE_MODE_CHECKLIST.md`. Summary:
1. Stripe → API keys → `sk_live_...` + webhook `whsec_...` → update `.env` → restart backend
2. Verify: `curl .../api/payments/readiness` → `"go_live_ready": true`
3. Install nightly backup: `sudo bash /opt/command-os/scripts/install-backup-cron.sh`

---

## 9. 24/7 Autonomous Operating Rhythm

| Clock | What happens | Who decides |
|-------|-------------|-------------|
| :00, :15, :30, :45 | GuardAgent health check + dead-letter drain | AgentExecutor (always) |
| :00 of every hour | Sovereign reads snapshot, calls Gemini, decides agent set | Sovereign AI |
| :00, :30 | RevenueAgent: tally ledger, check milestones | Sovereign AI |
| Every hour | ScoutAgent: 5 sources, 48h dedup, new opps → DB | Sovereign AI |
| Every 6 hours | ContentAgent: top 5 opps → articles → queue → publish | Sovereign AI |
| 07:00 UTC | GitHub Actions `sovereign.yml`: external heartbeat trigger | GitHub Cron |
| 03:00 UTC | Nightly SQLite backup to `/var/backups/` | systemd timer |

**The system runs completely unattended.** Revenue accrues, content publishes, and
the ledger tracks progress toward $25K — all while you sleep.

---

## 10. Collections Reference

| Collection | Written by | Purpose |
|------------|------------|---------|
| `sovereign_decisions` | SovereignAgent | Every AI governance decision |
| `agent_runs` | BaseAgent (all agents) | Per-run result with success/error/duration |
| `system_health` | GuardAgent | 15-min health snapshots |
| `scout_opportunities` | ScoutAgent | Viral trends + news (deduped 48h) |
| `content_queue` | ContentAgent | Articles ready for review/publish |
| `revenue_ledger` | Manual / Stripe | Immutable revenue entries |
| `revenue_snapshots` | RevenueAgent | 30-min net revenue roll-ups |
| `revenue_milestones` | RevenueAgent | Crossed milestones (idempotent) |
| `llm_cache` | distillation_service | 30-day prompt-response cache |
| `llm_budget` | llm_runner | Daily token usage counters |
| `audit_log` | audit_service | Every action, immutable |

---

## 11. Environment Variables

| Var | Required | Default | Purpose |
|-----|----------|---------|---------|
| `STORAGE_BACKEND` | Yes | `mongodb` | `sqlite` or `mongodb` |
| `SQLITE_PATH` | SQLite only | `/app/backend/data/command_os.db` | DB file |
| `[removed] | Yes | — | Gemini + Claude unified key |
| `STRIPE_API_KEY` | Payments | `sk_test_[removed] | Test or live key |
| `STRIPE_WEBHOOK_SECRET` | Live mode | — | Required for live checkout |
| `OPERATOR_EMAIL` | Auth gate | open | Lock dashboard to one Google account |
| `[removed] | All LLM | — | Universal key (Gemini, Claude) |
| `LLM_DAILY_TOKEN_CAP` | Optional | `0` (∞) | Hard daily token ceiling |
| `AUTO_PUBLISH` | Optional | `false` | Set `true` for autonomous publishing |
| `CONTENT_REPO_TOKEN` | Publishing | — | GitHub PAT for content repo |
| `GITHUB_CONTENT_OWNER` | Publishing | `quantam101` | GitHub Pages owner |
| `GITHUB_CONTENT_REPO` | Publishing | `content` | GitHub Pages repo |
| `DEVTO_API_KEY` | Publishing | — | Dev.to API key |
| `MEDIUM_API_KEY` | Publishing | — | Medium (pending approval) |
| `LEGACY_CYCLE_ONLY` | Optional | `false` | Revert to old single-daily scheduler |
| `AUTO_CYCLE_ENABLED` | Optional | `true` | Set `false` to disable scheduler |
| `DAILY_CYCLE_HOUR_UTC` | Legacy only | `7` | Hour for legacy daily run |
| `SELF_BASE_URL` | GuardAgent | `http://localhost:8001` | Self health-check URL |
| `SYSTEM_MODE` | Tests | — | Set `test` to disable scheduler |
| `CORS_ORIGINS` | Optional | `*` | CORS allowlist |

---

## 12. Cost Ledger

| Item | Monthly |
|------|---------|
| OCI VM.Standard.E2.1.Micro (Always Free) | $0 |
| Let's Encrypt via Caddy | $0 |
| SQLite on-disk | $0 |
| GitHub Actions (2,000 min/mo free) | $0 |
| GoDaddy domain (~$18/yr) | ~$1.50 |
| Stripe fees | 2.9% + $0.30/txn (no base) |
| Gemini 2.0 Flash (distillation cache, ~80K tokens/day cap) | ~$0.05/day max |
| **Fixed monthly cost** | **~$1.50 + Stripe fees** |

---

## 13. Ops Cheat Sheet

```bash
# Trigger sovereign cycle manually
curl -X POST https://alreadyherellc.com/api/sovereign/trigger

# Sovereign status + agent health
curl https://alreadyherellc.com/api/sovereign/status | python3 -m json.tool

# Revenue progress toward $25K unlock
curl https://alreadyherellc.com/api/ledger/stats/profit-progress | python3 -m json.tool

# Force fresh sovereign reasoning (clear LLM cache)
curl -X DELETE https://alreadyherellc.com/api/sovereign/cache

# Token usage today
curl https://alreadyherellc.com/api/distillation/budget | python3 -m json.tool

# SSH health check
ssh ubuntu@<IP> "curl -fsS http://localhost:8001/api/health/"

# Restart all containers
ssh ubuntu@<IP> "cd /opt/command-os && sudo docker compose -f docker-compose.sqlite.yml restart"

# Tail sovereign decisions in real-time
ssh ubuntu@<IP> "sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f backend 2>&1 | grep -i sovereign"

# Pull latest code + rebuild
ssh ubuntu@<IP> "cd /opt/command-os && sudo git pull && sudo docker compose -f docker-compose.sqlite.yml up -d --build"
```

---

## 14. Troubleshooting

| Symptom | Check first | Resolution |
|---------|-------------|-----------|
| Sovereign returns 503 | `[removed] not set | Add to `.env`, restart backend |
| GuardAgent failing | Container not self-reachable | Set `SELF_BASE_URL=http://backend:8001` in docker env |
| ScoutAgent 0 new results | All URLs already seen in 48h window | Normal behavior — try after 48h or add new sources to manifest |
| ContentAgent timeout | Gemini slow under load | Increase `agents[content-agent].timeout_seconds` in manifest |
| `/api/sovereign/trigger` 429 | Daily token cap reached | `curl -X DELETE .../api/sovereign/cache` or bump `LLM_DAILY_TOKEN_CAP` |
| Bootstrap `docker-model-plugin` error | Ubuntu 20.04 image | Terminate, recreate with Ubuntu 22.04 |
| `Permission denied (publickey)` | Wrong SSH key | Verify `~/.ssh/oci_cmdos.pub` was pasted into OCI |
| Caddy cert won't issue | DNS not propagated | `dig +short alreadyherellc.com @1.1.1.1` must match instance IP |
| `Connection timed out` port 22 | Security List | Add TCP 22 from `0.0.0.0/0` |

---

## 15. Files of Record

```
already-here-dashboard/
├── backend/
│   ├── server.py                      ← ⭐ FastAPI app (v2.0) + sovereign router
│   ├── agents/
│   │   ├── base_agent.py              ← ⭐ Circuit-breaker base (all agents extend this)
│   │   ├── guard_agent.py             ← Self-healing infrastructure monitor
│   │   ├── scout_agent.py             ← 24/7 multi-source trend scanner
│   │   ├── content_agent.py           ← LLM article generator + publisher
│   │   └── revenue_agent.py           ← Revenue tracker + milestone alerts
│   ├── services/
│   │   ├── sovereign_agent.py         ← ⭐ Governing AI orchestrator
│   │   ├── agent_executor.py          ← ⭐ Parallel dispatcher + circuit-breaker runner
│   │   ├── scheduler_service.py       ← ⭐ Multi-frequency sovereign-aware scheduler
│   │   ├── llm_runner.py              ← Single LLM chokepoint (cache + budget)
│   │   └── distillation_service.py    ← Semantic compression + 30d cache
│   ├── routes/
│   │   ├── sovereign.py               ← ⭐ /api/sovereign/* REST endpoints
│   │   └── [24 other route modules]
│   └── config/
│       └── manifest.yaml              ← ⭐ Declarative agent configuration
├── .github/workflows/
│   ├── sovereign.yml                  ← ⭐ 24/7 hourly GitHub Actions heartbeat
│   └── [existing CI/deploy workflows]
├── MASTER-DOCUMENT.md                 ← ⭐ THIS FILE
├── GO-LIVE.md                         ← 3-phase deploy runbook
├── LIVE_MODE_CHECKLIST.md             ← Stripe live-mode steps
└── cloud-init.sh                      ← OCI bootstrap (installs everything)
```

---

## 16. Quick Links

| Resource | URL |
|----------|-----|
| Repo | https://github.com/quantam101/already-here-dashboard |
| Production | https://alreadyherellc.com |
| Sovereign status | https://alreadyherellc.com/api/sovereign/status |
| API docs | https://alreadyherellc.com/api/docs |
| Stripe | https://dashboard.stripe.com |
| [removed] LLM key | https://app.[removed] → Profile → Universal Key |
| GoDaddy DNS | https://goto.godaddy.com → My Products → DNS |
| OCI console | https://cloud.oracle.com |
| Dev.to settings | https://dev.to/settings/extensions |
| GitHub Actions | https://github.com/quantam101/already-here-dashboard/actions |

---

## 17. If You Only Read One Section

**The system is autonomous.** After Phase 1-3 deploy:

1. The Sovereign fires every 60 minutes, reads system state, decides what to run
2. GuardAgent checks health every 15 min — self-heals dead runs
3. ScoutAgent pulls viral trends hourly — no tokens spent
4. ContentAgent generates 5 articles every 6 hours — cached prompts cost pennies
5. RevenueAgent reconciles ledger every 30 min — fires alerts at each milestone
6. GitHub Actions pings `/api/sovereign/trigger` every hour as external watchdog

**Nothing requires your input once deployed.** Revenue accrues. Content publishes.
The meter climbs toward $25,000. You review the content queue at `/studio` and
mark publishing records as `posted` when you verify they went live. That is all.

**To go fully hands-free:** Set `AUTO_PUBLISH=true` in `.env`. ContentAgent will
publish directly to GitHub Pages and Dev.to without asking. You can review published
articles at https://dev.to/already_herellc_c954583f after the fact.