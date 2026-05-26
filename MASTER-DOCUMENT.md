# Already Here Command OS — Master Document

> Single source of truth. Everything you need to deploy, operate, and extend the
> Already Here Command OS lives here or links from here.

**Last updated:** 2026-05-26
**Maintainer:** alreadyherellc@gmail.com
**Repo:** https://github.com/Quantam101/already-here-dashboard
**Domain:** https://alreadyherellc.com (target)
**Cost target:** $0/month (Oracle Cloud Always Free)

---

## 1. What this is

A two-node, $0/month, free-only-enforced AI ecosystem with:

- **Multi-agent fleet** (Scout, Proposal Writer, Books, AI Advisor, Cycle Scheduler)
- **CapCut-style Content Factory** (ideas → AI-scripted hooks/body/CTA/shot-list → one-click copy-to-platform)
- **Real Stripe Checkout** with UTM share-link attribution
- **eBook + Audiobook generator** (browser SpeechSynthesis = $0 TTS)
- **Bitwarden Secrets Vault** (read-only browser, fail-closed on missing creds)
- **Free-Only Cost Guard** — blocks paid integrations, manual export fallback when APIs cost money
- **Lifelong Catch and Correct** anomaly side-panel
- **Two-node health** — Dashboard on `129.x.x.x` micro, ProfitEngine worker on a bigger node

---

## 2. Architecture

### 2.1 Topology

```
                    ┌─────────────────────┐
GoDaddy DNS         │  alreadyherellc.com │
─────────────────►  │  (A → OCI public IP)│
                    └─────────────────────┘
                              │ 443 HTTPS (Let's Encrypt via Caddy)
                              ▼
┌──────────────────────────────────────────────────┐
│  OCI E2.1.Micro (1 OCPU, 1 GB RAM)               │
│  Hostname: cmdos / DashboardAlways Free          │
│                                                  │
│  ┌──────────┐   ┌──────────┐                    │
│  │  Caddy   │──►│  FastAPI │                    │
│  │  static  │   │  + SQLite│                    │
│  │  React   │   │  (~200MB)│                    │
│  └──────────┘   └──────────┘                    │
│       ▲                                          │
│       │  Volume mount: SQLite DB                 │
└──────────────────────────────────────────────────┘
                              │ Optional: WORKER_BASE_URL
                              ▼
┌──────────────────────────────────────────────────┐
│  profitengine-server (heavier shape)             │
│  Hostname: profitengine-server                   │
│  Role: rendering, distillation, FFmpeg, local AI │
└──────────────────────────────────────────────────┘
```

### 2.2 Storage backend selector

The same codebase runs against EITHER MongoDB or SQLite. Selected by env var:

| Mode | When used | Trigger |
|---|---|---|
| **SQLite** | 1 GB RAM hosts (the Always Free micro) | `STORAGE_BACKEND=sqlite` |
| **MongoDB** | Dev/preview, larger production nodes | (default) |

The `oci-bootstrap.sh` script auto-detects RAM and picks the right one.

### 2.3 Memory budget (SQLite mode, verified)

| Component | RSS |
|---|---|
| FastAPI backend (uvicorn) | ~200 MB |
| Caddy (static + proxy) | ~30 MB |
| OS + Docker overhead | ~200 MB |
| **Total** | **~430 MB / 1024 MB** |

Headroom for daily auto-cycle spikes: ~590 MB.

---

## 3. Repo layout

```
/
├── backend/                          # FastAPI service
│   ├── server.py                     # Entry point, backend selector lives here
│   ├── seed_data.py                  # Idempotent demo seed (backend-agnostic)
│   ├── requirements.txt              # Pinned deps (motor + aiosqlite both included)
│   ├── routes/                       # 22 API modules — one file per domain
│   │   ├── health.py                 # /api/health/, /api/health/nodes (two-node)
│   │   ├── cost.py                   # /api/cost/status, /api/cost/policy
│   │   ├── lcac.py                   # /api/lifelong-catch-correct/
│   │   ├── system.py                 # /api/system/status (powers Quickstart Wizard)
│   │   ├── secrets.py                # /api/secrets/status, /api/secrets/items
│   │   ├── payments.py               # Stripe checkout + webhooks + UTM share-links
│   │   ├── analytics.py              # Funnel, ROI, momentum, UTM attribution
│   │   ├── advisor.py                # AI advisor (Emergent LLM)
│   │   ├── scout.py                  # Reddit + HackerNews + Grants.gov scraping
│   │   ├── proposals.py              # AI-drafted client proposals + grant apps
│   │   ├── books.py                  # eBook generator + audiobook chapters
│   │   ├── cycle.py                  # Daily auto-cycle scheduler
│   │   ├── ledger.py                 # Real-earnings tracking + CSV import
│   │   ├── publishing.py             # Manual ready-to-post export packs
│   │   ├── content_factory.py        # Studio: ideas → scripts → schedule
│   │   ├── audit.py, approvals.py, agents.py, builds.py, deployments.py
│   │   └── ...
│   ├── services/
│   │   ├── sqlite_db.py              # Motor-API-compatible shim over aiosqlite
│   │   ├── bitwarden_service.py      # bw CLI wrapper (read-only metadata)
│   │   ├── scheduler_service.py      # Daily cycle scheduler
│   │   └── content_generation_service.py
│   └── tests/
│       └── backend_test.py           # 104 pytest cases, pass on Mongo OR SQLite
│
├── frontend/                         # React (CRA)
│   ├── src/
│   │   ├── pages/                    # 14 pages: Overview, Scout, Proposals,
│   │   │                             # Pricing, PaymentSuccess, Analytics,
│   │   │                             # Books, Secrets, ContentStudio, Content,
│   │   │                             # ProofOfWork, Agents, Builds, Deployments
│   │   ├── components/               # Reusable: QuickstartWizard, IdeaDetailDialog
│   │   │                             # ContentDetailDialog, AuthGate, ProfitMeter,
│   │   │                             # RecordEarningsDialog, LogPostDialog, etc.
│   │   ├── lib/
│   │   │   ├── api.js                # Centralized axios client
│   │   │   └── platformShare.js      # Reddit/LinkedIn/X share-URL builders
│   │   └── App.js                    # Router
│   └── package.json
│
├── docker-compose.yml                # Mongo stack (preview/dev/larger nodes)
├── docker-compose.sqlite.yml         # SQLite stack (1 GB micro, prod target)
├── Caddyfile                         # Mongo-stack Caddy (proxy /api → backend, / → frontend)
├── Caddyfile.sqlite                  # SQLite-stack Caddy (static + reverse-proxy)
│
├── scripts/
│   ├── oci-bootstrap.sh              # Main installer, RAM auto-detect
│   ├── preflight.sh                  # 27-check pre-deploy validator
│   ├── deploy-local.sh
│   ├── backup.sh
│   └── healthcheck.sh
│
├── cloud-init.sh                     # Top-level wrapper for OCI cloud-init paste
│
├── docs/
│   └── COMMAND_OS_FREE_ONLY_FINAL_BUILD_DIRECTIVE.md
│
├── DEPLOY-TO-OCI.md                  # Original GoDaddy + OCI guide
├── DEPLOY-TO-OCI-CLEAN.md            # Paste-resistant 2-line cloud-init flow ★ START HERE
├── MASTER-DOCUMENT.md                # This file
│
├── memory/                           # Agent memory
│   ├── PRD.md                        # 12 iterations of feature history
│   └── test_credentials.md
│
└── test_reports/
    └── iteration_*.json              # Testing-agent-generated reports
```

---

## 4. Deployment — the 4-step flow

> ⚠️ **`DEPLOY-TO-OCI-CLEAN.md` is the canonical deploy guide.** Follow that, not anything older.

### High-level

| Step | What | Time | Output |
|---|---|---|---|
| 1 | Create OCI Always Free instance with the 2-line cloud-init paste | 5 min | New instance, port 22 open in ~60 sec |
| 2 | Wait for cloud-init to finish (Docker + Node + React build + stack up) | ~10 min | Port 80 + 443 open, SQLite seeded |
| 3 | SSH in once, edit `.env` to add `EMERGENT_LLM_KEY`, `OPERATOR_EMAIL`, `STRIPE_API_KEY` | 2 min | Backend restart picks up secrets |
| 4 | GoDaddy DNS `@` → new IP | 5 min DNS propagation | https://alreadyherellc.com live with Let's Encrypt |

### The 2-line cloud-init paste

```
#!/bin/bash
curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
```

That's the entire OCI user-data field. `cloud-init.sh` on GitHub handles everything else:

1. **Installs the operator SSH public key** (hardcoded — bypasses OCI textbox mangling)
2. Installs base packages (curl, git, ca-certificates)
3. Fetches and runs `scripts/oci-bootstrap.sh`
4. Bootstrap auto-detects RAM: `<1500MB` → SQLite mode
5. Installs Docker, Node, builds React static bundle, starts `docker-compose.sqlite.yml`
6. Logs to `/var/log/command-os-bootstrap.log`

### Post-deploy secrets (Step 3)

Once SSH works:

```bash
ssh -i ~/.ssh/cmdos -o StrictHostKeyChecking=no ubuntu@<NEW_IP>

sudo nano /opt/command-os/backend/.env
# Set these three lines:
#   EMERGENT_LLM_KEY="sk-emergent-..."
#   STRIPE_API_KEY="sk_test_emergent"  (or sk_live_... when ready)
#   OPERATOR_EMAIL="your@gmail.com"

cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

---

## 5. API surface

Every endpoint is prefixed `/api`.

### 5.1 Core

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/` | Basic liveness |
| GET | `/health/nodes` | Two-node health (dashboard + worker) |
| GET | `/system/status` | Operator dashboard snapshot (Stripe mode, secrets, counts) |
| GET | `/cost/status` | Free-only enforcement: blocked paid, blocked unknown, missing secrets |
| GET | `/cost/policy` | Static policy doc + 9 approved free integrations |
| GET | `/lifelong-catch-correct/` | Anomaly side-panel findings |
| GET | `/secrets/status` | Bitwarden vault status (no values) |
| GET | `/secrets/items` | Vault metadata browser (no values) |

### 5.2 Money

| Method | Path | Purpose |
|---|---|---|
| POST | `/payments/checkout` | Create Stripe Checkout session |
| GET | `/payments/status/{session_id}` | Poll session result |
| POST | `/payments/webhook` | Stripe → server (signature verified when secret set) |
| POST | `/payments/share-link` | Generate UTM-tagged share URL |
| GET | `/payments/stats` | Revenue + `by_utm_source` attribution |

### 5.3 Engine

| Method | Path | Purpose |
|---|---|---|
| GET | `/scout/sources` | Reddit + HackerNews + Grants opportunities |
| POST | `/proposals/draft` | AI-write client proposal / grant application |
| POST | `/cycle/run` | One-off run of the daily cycle |
| POST | `/studio/ideas/` | Create content idea |
| POST | `/studio/ideas/{id}/script` | Gemini-3-Flash drafts hook/body/CTA/shot list |
| GET | `/studio/scripts/` | All generated scripts (operator browse) |
| GET | `/ledger/` | Real-money entries |
| POST | `/ledger/` | Record an earning |
| POST | `/books/` | Generate eBook chapters |
| GET | `/audit/` | Audit log |

### 5.4 Registry

| Method | Path | Purpose |
|---|---|---|
| GET | `/agents/` | All agents + run counts + success rate |
| POST | `/agents/{id}/execute` | Manually invoke an agent |
| GET | `/builds/` | Build registry |
| GET | `/deployments/` | Deployment registry |
| GET | `/content/` | Content library |
| GET | `/publishing/` | Published posts with status |

---

## 6. Free-Only Build Directive

Hard rules baked into the cost guard (`routes/cost.py`):

1. **Block paid** — any connector with `cost_class=paid_blocked` is rejected
2. **Block unknown-cost** — `cost_class=unknown` is also blocked (fail-closed)
3. **Manual export pack** for any platform where the publish API costs money (TikTok, IG, YouTube Shorts)
4. **Fail-closed on missing secret** — endpoints requiring `EMERGENT_LLM_KEY` return 503 with `requires_secret` if not set
5. **Approved free integrations only** (9 total):
   - Emergent LLM (Universal Key) — Gemini/Claude/GPT text + Nano Banana images
   - Stripe Checkout (test mode default)
   - Reddit JSON API (no auth)
   - HackerNews API (no auth)
   - Grants.gov API (no auth)
   - Browser SpeechSynthesis (audiobooks, $0 TTS)
   - Vaultwarden self-hosted (or Bitwarden free tier)
   - Caddy + Let's Encrypt (free HTTPS)
   - Oracle Cloud Always Free (compute + bandwidth)

Full directive: `docs/COMMAND_OS_FREE_ONLY_FINAL_BUILD_DIRECTIVE.md`

---

## 7. Operations runbook

### Daily

```bash
# Check stack health
curl -fsS https://alreadyherellc.com/api/health/
curl -fsS https://alreadyherellc.com/api/lifelong-catch-correct/
```

### Weekly

```bash
ssh ubuntu@<your-ip>

# Container health
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml ps

# Disk usage (SQLite + Caddy data + logs)
df -h
sudo du -sh /opt/command-os /var/lib/docker

# Auto-cycle ran on schedule?
curl -fsS http://localhost:8001/api/audit/ | jq '.[] | select(.event_type=="cycle.run.success")' | head
```

### Backup (do this monthly minimum)

```bash
sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml exec backend \
  sqlite3 /app/data/command_os.db ".backup '/app/data/backup-$(date +%F).db'"

# Then scp it off-box:
scp ubuntu@<ip>:/var/lib/docker/volumes/*/sqlite_data/_data/backup-*.db ~/backups/
```

### Code update

```bash
cd /opt/command-os
sudo git pull
sudo docker compose -f docker-compose.sqlite.yml up -d --build
```

### Switch Stripe to LIVE mode

```bash
# 1. Stripe Dashboard → API Keys → reveal live key (sk_live_...)
# 2. Stripe Dashboard → Webhooks → Add endpoint:
#    URL:    https://alreadyherellc.com/api/payments/webhook
#    Events: checkout.session.completed, checkout.session.expired
#    Copy the signing secret (whsec_...)

sudo nano /opt/command-os/backend/.env
# Update:
#   STRIPE_API_KEY="sk_live_..."
#   STRIPE_WEBHOOK_SECRET="whsec_..."

cd /opt/command-os
sudo docker compose -f docker-compose.sqlite.yml restart backend
```

---

## 8. Test coverage

**104 backend tests in `backend/tests/backend_test.py`. Both backends pass 104/104.**

Run locally:

```bash
cd /app
python -m pytest backend/tests/backend_test.py -v
```

CI guarantees:

- Every route module has at least 1 test
- Free-only directive endpoints (`/cost/*`, `/health/nodes`, `/lifelong-catch-correct/`) have shape + no-secret-leak tests
- Stripe payment flow has happy-path + UTM-attribution test
- Books AI generation tests gated behind LLM key presence

---

## 9. Known gaps and roadmap

| Item | Status | Priority |
|---|---|---|
| Worker bridge (dashboard → profitengine-server task queue) | Pending | P1 |
| Self-hosted Vaultwarden Docker service | Optional | P2 |
| Auto-publish via free platform APIs (Reddit, LinkedIn UGC) | Currently manual | P2 |
| Email digest of daily ledger + LCAC findings | Pending | P3 |
| Crash/error tracking (Sentry free tier) | Pending | P3 |
| Backup automation via cron | Manual | P2 |
| Stripe live-mode swap helper script | Manual | P3 |

---

## 10. Emergency contacts / when things break

| Symptom | First check | Fix |
|---|---|---|
| `https://...` won't load | DNS via `dig +short alreadyherellc.com @1.1.1.1` | Wait propagation or fix GoDaddy A-record |
| Site loads but Caddy shows 502 | `docker compose -f docker-compose.sqlite.yml logs backend --tail 50` | Restart backend |
| Backend boots but APIs return 500 | Inside backend container: `cat /app/.env` | Check `EMERGENT_LLM_KEY` is set |
| Google login rejects your email | Operator email mismatch | Update `OPERATOR_EMAIL` in `.env`, restart backend |
| Out of disk | `df -h` | Trim Docker: `sudo docker system prune -af` |
| Out of RAM | `free -h` then `sudo docker stats` | Restart whichever container is hot |

Full deployment-recovery procedures in `DEPLOY-TO-OCI-CLEAN.md` Section "If something still breaks".

---

## 11. Cost ledger (verify monthly)

| Resource | Expected $/mo | Actual |
|---|---|---|
| Oracle Cloud E2.1.Micro | $0 (Always Free) | $0 |
| Outbound bandwidth (10 TB/mo cap) | $0 | $0 |
| GoDaddy domain renewal (annual) | ~$1/mo amortized | — |
| Let's Encrypt cert | $0 | $0 |
| Stripe fees | 2.9% + $0.30 per txn | (only on real sales) |
| Emergent LLM (Universal Key) | included in plan | — |
| **TOTAL infrastructure** | **$0/month** | — |

---

## 12. Quick-reference URLs

- **Live site:** https://alreadyherellc.com
- **Health:** https://alreadyherellc.com/api/health/
- **Cost status:** https://alreadyherellc.com/api/cost/status
- **Repo:** https://github.com/Quantam101/already-here-dashboard
- **Emergent Universal Key:** https://app.emergent.sh → Profile → Universal Key
- **Stripe Dashboard:** https://dashboard.stripe.com
- **OCI Console:** https://cloud.oracle.com
- **GoDaddy DNS:** https://dcc.godaddy.com → My Products → DNS for alreadyherellc.com

---

*End of master document. Iterations recorded in `memory/PRD.md`.*
