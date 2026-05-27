# Already Here Command OS — Master Document

**One source of truth.** What this is, what's built, where it lives, how to deploy it, and how to operate it. Updated 2026-05-27.

---

## 1. Mission

A single-operator, governed AI **revenue automation OS** that runs at **$0/month** on Oracle Cloud Always Free, generates content + grants + books via cached LLM calls, collects real money via Stripe, and tracks net profit toward a $25k commercialization unlock.

Domain: **`alreadyherellc.com`**

---

## 2. Current State (snapshot)

| Surface | Status |
|---|---|
| Backend (FastAPI + dual-DB MongoDB/SQLite) | ✅ 116/116 pytest, ruff clean |
| Frontend (React + Recharts + shadcn) | ✅ ESLint clean, smoke-screenshot verified |
| Stripe integration | ✅ Test-mode wired, live-mode safety gate, auto-refunding smoke test |
| LLM Cost Guard | ✅ Distillation cache + daily token cap + on-dashboard chart |
| OCI deploy artifacts | ✅ Cloud-init + bootstrap + backup-cron all syntactically clean |
| GitHub repo | ✅ Public at `Quantam101/already-here-dashboard` (cloud-init on `main` matches local) |
| Production live URL | 🟡 In progress — Phase 1 deploy in flight |

---

## 3. Architecture in 60 seconds

```
                                ┌────────────────────────────────────┐
                                │   alreadyherellc.com  (browser)    │
                                └────────────────┬───────────────────┘
                                                 │ HTTPS (Let's Encrypt)
                                                 ▼
                              ┌──────────────────────────────────────┐
                              │     Caddy reverse proxy (~30 MB)     │
                              └──────────┬───────────────────────────┘
                                         │
                              ┌──────────┴──────────┐
                              ▼                     ▼
                  ┌───────────────────┐  ┌───────────────────────────┐
                  │ React static SPA  │  │ FastAPI backend (~200 MB) │
                  │ (built on host)   │  │  • routes/* (24 modules)  │
                  └───────────────────┘  │  • services/* (incl. LLM  │
                                         │    runner + distillation) │
                                         │  • SQLite on host disk    │
                                         └─────────────┬─────────────┘
                                                       │
                                          ┌────────────┴────────────┐
                                          ▼                         ▼
                                ┌──────────────────┐    ┌──────────────────┐
                                │ Stripe (live)    │    │ Emergent LLM Key │
                                │ + webhook        │    │ (Gemini, Claude) │
                                └──────────────────┘    └──────────────────┘
```

**Memory budget on 1 GB OCI Always Free host:**
- Backend container: 200 MB (400 MB cap)
- Caddy container: 30 MB (100 MB cap)
- SQLite DB file: 200 KB after seed
- **Total ≈ 230 MB. Plenty of headroom.**

---

## 4. Features (what the operator can actually do)

| Feature | Route / API | Notes |
|---|---|---|
| Command Center dashboard | `/overview` | Revenue meter, stream health, cycle controls |
| Content Factory (CapCut-style) | `/studio` + `/api/studio/*` | AI script generation, copy + open platform |
| Books & Audiobooks generator | `/books` + `/api/books/*` | Chapter-by-chapter, MD/TXT downloads, browser TTS |
| Proposal Engine | `/proposals` + `/api/proposals/*` | Grants/contracts/RFPs via Gemini |
| Scout (viral + procurement) | `/scout` + `/api/scout/*` | Reddit, HN, Grants.gov, SAM.gov, Google News |
| Auto-cycle scheduler | `/api/cycle/run` + scheduler_service | Daily 7 UTC by default |
| Proof of Work ledger | `/proof-of-work` + `/api/ledger/*` | Immutable net-revenue tracking → $25k unlock |
| Analytics dashboard | `/analytics` | Funnel, ROI, momentum, UTM attribution, AI Advisor |
| AI Operations Advisor | `/api/advisor/recommend` | Claude Sonnet, cached, YAML-distilled context |
| Stripe payments + smoke runner | `/pricing` + `/api/payments/*` | Live-mode gate, auto-refund $0.50 verifier |
| Secrets vault (Bitwarden-compatible) | `/secrets` + `/api/secrets/*` | Read-only browser, no value leak |
| Cost Guard + Distillation Card | `/analytics` top of page + `/api/distillation/*` | Tokens saved, $ saved, daily cap, hit-rate chart |
| Quickstart Wizard | Auto-opens on first visit | 5-step onboarding |
| Audit log | `/audit` + `/api/audit/*` | Every action immutably logged |

---

## 5. Cost Guard (the distillation pipeline)

Every LLM call goes through one chokepoint: **`services/llm_runner.py::run_cached()`**

```
prompt → distill_text (semantic compression)
       → cache_lookup (sha256 fingerprint of model+system+prompt)
       → HIT?  →  serve cached response (0 tokens billed)
       → MISS? →  check daily budget (LLM_DAILY_TOKEN_CAP env)
                →  call LLM (Gemini or Claude)
                →  cache_store (30-day TTL)
                →  bump tokens-in/out counter in `llm_budget` collection
```

**Visible in the UI**: top of `/analytics` shows live tokens saved, $ saved (est), cache hit rate (last 14 days, line chart), today's usage vs cap.

**Hard ceiling**: set `LLM_DAILY_TOKEN_CAP=50000` in `.env` and every LLM-calling route returns HTTP 429 when exceeded.

---

## 6. Deploy from zero — the 3 phases

This is the canonical playbook. Each phase ends with a verification curl that must succeed before moving on.

### Phase 1 — OCI deploy (~15 min)

Full detail in `DEPLOY-FINAL.md`. Skeleton:

1. OCI Console → Compute → Instances → **Create instance**
   - Name: `cmdos`
   - Image: **Canonical Ubuntu 22.04** ⚠️ NOT 20.04 (EOL, breaks Docker installer)
   - Shape: `VM.Standard.E2.1.Micro` (Always Free)
   - SSH keys: **Paste public keys** → your `~/.ssh/oci_cmdos.pub`
   - Networking: assign public IPv4
   - Advanced → Management → Initialization script:
     ```bash
     #!/bin/bash
     curl -fsSL https://raw.githubusercontent.com/Quantam101/already-here-dashboard/main/cloud-init.sh | bash
     ```
2. **Security List** ingress (the VCN default usually has SSH but always verify):

   | Source | Protocol | Port | Purpose |
   |---|---|---|---|
   | `0.0.0.0/0` | TCP | 22 | SSH |
   | `0.0.0.0/0` | TCP | 80 | HTTP / Let's Encrypt challenge |
   | `0.0.0.0/0` | TCP | 443 | HTTPS |

3. GoDaddy DNS → `alreadyherellc.com` A-records `@` and `www` → instance public IP, TTL 600.

4. SSH from your laptop:
   ```powershell
   ssh -i $HOME\.ssh\oci_cmdos ubuntu@<actual-ip-digits>
   sudo tail -f /var/log/command-os-bootstrap.log
   ```
5. Wait for `BOOTSTRAP COMPLETE` (~10 min). Then drop in secrets:
   ```bash
   sudo nano /opt/command-os/backend/.env
   ```
   ```env
   EMERGENT_LLM_KEY="sk-emergent-..."
   STRIPE_API_KEY="sk_test_emergent"
   OPERATOR_EMAIL="alreadyherellc@gmail.com"
   ```
   Save → restart:
   ```bash
   cd /opt/command-os && sudo docker compose -f docker-compose.sqlite.yml restart backend
   ```

**Phase 1 verification (must pass before Phase 2):**
```bash
curl -fsS https://alreadyherellc.com/api/health/
# → {"status":"healthy","timestamp":"..."}
```

### Phase 2 — Stripe live mode (~10 min)

Full detail in `LIVE_MODE_CHECKLIST.md`. Skeleton:

1. Stripe dashboard → Developers → API keys → reveal `sk_live_...`
2. Stripe → Developers → Webhooks → Add endpoint:
   - URL: `https://alreadyherellc.com/api/payments/webhook`
   - Events: `checkout.session.completed`
   - Reveal signing secret `whsec_...`
3. SSH in, edit `.env`:
   ```env
   STRIPE_API_KEY="sk_live_..."
   STRIPE_WEBHOOK_SECRET="whsec_..."
   ```
   Restart backend.
4. Verify readiness:
   ```bash
   curl -fsS https://alreadyherellc.com/api/payments/readiness | python3 -m json.tool
   # → "go_live_ready": true, "issues": []
   ```
5. **Auto-refunding smoke test** (charges $0.50 with a real card, refunds within 10s):
   ```bash
   SMOKE=$(curl -fsS -X POST https://alreadyherellc.com/api/payments/smoke-test/create)
   echo "$SMOKE" | python3 -m json.tool
   ```
   Open the returned `url` in a browser → pay $0.50 → then:
   ```bash
   SID=$(echo "$SMOKE" | python3 -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
   curl -fsS https://alreadyherellc.com/api/payments/smoke-test/status/$SID | python3 -m json.tool
   # → "verified_live_pipeline": true
   ```

If `verified_live_pipeline: true` → live Stripe integration is wired correctly end-to-end.

### Phase 3 — Operational hardening (~5 min)

1. **Nightly backups** (idempotent):
   ```bash
   sudo bash /opt/command-os/scripts/install-backup-cron.sh
   ```
   Verify: `systemctl list-timers cmdos-backup.timer` shows next 03:00 UTC fire.

2. **(Optional) Daily LLM token cap** — gives the Cost Guard real teeth:
   ```bash
   echo 'LLM_DAILY_TOKEN_CAP=50000' | sudo tee -a /opt/command-os/backend/.env
   cd /opt/command-os && sudo docker compose -f docker-compose.sqlite.yml restart backend
   ```
   Verify in browser: `/analytics` → Distillation card now shows `50,000 cap`.

---

## 7. Daily ops cheat sheet

```bash
# Health probe
curl -fsS https://alreadyherellc.com/api/health/

# Today's LLM token usage + savings
curl -fsS https://alreadyherellc.com/api/distillation/budget | python3 -m json.tool

# Progress toward $25k unlock
curl -fsS https://alreadyherellc.com/api/ledger/stats/profit-progress | python3 -m json.tool

# Manual backup
ssh ubuntu@<ip>; sudo bash /opt/command-os/scripts/backup-sqlite.sh

# Restart all containers
ssh ubuntu@<ip>; sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml restart

# Tail logs
ssh ubuntu@<ip>; sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs -f --tail 100

# Update to latest code from GitHub
ssh ubuntu@<ip>; cd /opt/command-os && sudo git pull && sudo docker compose -f docker-compose.sqlite.yml up -d --build
```

---

## 8. Files of record

```
/app/
├── cloud-init.sh                          # 2-line OCI user-data target (on GitHub)
├── scripts/
│   ├── oci-bootstrap.sh                   # RAM-aware (SQLite for <1500 MB)
│   ├── install-backup-cron.sh             # systemd timer installer (nightly 03:00 UTC)
│   ├── backup-sqlite.sh                   # atomic sqlite3 .backup + tar + 14-day retention
│   ├── backup.sh                          # legacy MongoDB backup (kept for non-SQLite hosts)
│   ├── deploy-local.sh                    # laptop fallback (Docker or native)
│   ├── healthcheck.sh
│   ├── preflight.sh
│   ├── restore.sh
│   └── validate-oci.sh
├── docker-compose.sqlite.yml              # 2-container stack for 1 GB RAM
├── docker-compose.yml                     # MongoDB stack (preview/dev)
├── Caddyfile.sqlite                       # production reverse proxy
├── Caddyfile                              # preview proxy
├── GO-LIVE.md                             # ⭐ 3-phase final runbook
├── DEPLOY-FINAL.md                        # Phase 1 detail
├── LIVE_MODE_CHECKLIST.md                 # Phase 2 detail
├── HANDOFF.md                             # For a DevOps freelancer if needed
├── MASTER-DOCUMENT.md                     # ⭐ THIS FILE
├── memory/PRD.md                          # Product spec + iteration log
├── backend/
│   ├── server.py                          # dual-DB switching logic
│   ├── seed_data.py                       # backend-agnostic seed
│   ├── routes/                            # 24 route modules
│   ├── services/
│   │   ├── llm_runner.py                  # ⭐ single chokepoint for LLM calls
│   │   ├── distillation_service.py        # cache + compression + YAML payloads
│   │   ├── sqlite_db.py                   # Motor-API-compatible SQLite wrapper
│   │   ├── bitwarden_service.py
│   │   ├── content_generation_service.py
│   │   ├── scheduler_service.py
│   │   ├── audit_service.py
│   │   └── export_service.py
│   ├── tests/backend_test.py              # 116 tests, dual-DB safe
│   └── requirements.txt
└── frontend/
    ├── public/manifest.json               # PWA installable
    └── src/
        ├── App.js
        ├── lib/
        │   ├── api.js                     # all axios endpoints
        │   ├── clipboard.js                # ⭐ iframe-safe copy + open helpers
        │   └── platformShare.js           # share-link builders per platform
        ├── pages/                          # Overview, Analytics, ContentStudio, ...
        └── components/                     # AuthGate, DashboardLayout, ...
```

---

## 9. Environment variables (every one explained)

| Var | Required? | Default | Purpose |
|---|---|---|---|
| `MONGO_URL` | Only if `STORAGE_BACKEND=mongodb` | (preview only) | MongoDB connection |
| `DB_NAME` | Always | `command_os` | Mongo db name or SQLite logical name |
| `STORAGE_BACKEND` | Production | `mongodb` (preview) / `sqlite` (OCI) | Switches engine |
| `SQLITE_PATH` | SQLite mode only | `/app/backend/data/command_os.db` | DB file location |
| `EMERGENT_LLM_KEY` | For any LLM feature | — | Universal key (Gemini + Claude) |
| `STRIPE_API_KEY` | For payments | `sk_test_emergent` placeholder | `sk_test_...` or `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | **Required in live mode** | — | Without it, live-mode checkout returns 503 |
| `OPERATOR_EMAIL` | Auth gate | (open if unset) | Locks dashboard to one Google account |
| `SYSTEM_MODE` | Tests | `production` | `test` disables scheduler |
| `DAILY_CYCLE_HOUR_UTC` | — | `7` | Auto-cycle daily fire hour |
| `LLM_DAILY_TOKEN_CAP` | Optional | `0` (unlimited) | Hard ceiling; 429 when hit |
| `LLM_CACHE_TTL_SECONDS` | — | `2592000` (30d) | Distillation cache TTL |
| `TOKEN_COST_PER_1K` | Telemetry | `0.0001` | Used for $ saved estimate |
| `WORKER_BASE_URL` | Optional | — | Two-node health link to `profitengine-server` |
| `BW_SESSION` | Only if Bitwarden CLI installed | — | Vault unlock token |
| `CORS_ORIGINS` | — | `*` | Comma-separated allowlist |
| `AUTO_CYCLE_ENABLED` | — | `true` | Disable to silence the scheduler |

**Reading rule:** every backend env read uses `os.environ.get(...)` with no string default fallback for required values — missing config fails fast.

---

## 10. Where to find what's broken

| Symptom | First check | Then |
|---|---|---|
| `/api/health/` returns 5xx | `sudo docker compose -f /opt/command-os/docker-compose.sqlite.yml logs backend --tail 100` | If module import error, missing dep in `requirements.txt` |
| 404 on every API call | Frontend hitting wrong host | Verify `REACT_APP_BACKEND_URL` baked into the bundle (rebuild required if changed) |
| Stripe checkout silently fails | `/api/payments/readiness` | Issues list tells you exactly what's missing |
| LLM calls return 429 | `/api/distillation/budget` | `over_cap: true` → bump `LLM_DAILY_TOKEN_CAP` or wait for UTC midnight |
| Dashboard shows "Loading…" forever | Auth gate stuck | Check `OPERATOR_EMAIL` matches the Google account you logged in with |
| Caddy HTTPS cert won't issue | DNS not propagated | `dig +short alreadyherellc.com @1.1.1.1` should match instance IP |
| Bootstrap log shows `docker-model-plugin` error | Ubuntu 20.04 image | Terminate, recreate with **Ubuntu 22.04** |
| `Permission denied (publickey)` from SSH | Wrong key | Verify the public key pasted into OCI matches the private key on your laptop |
| `Connection timed out` on port 22 | Security List | Add ingress TCP 22 from `0.0.0.0/0` |

---

## 11. The 25k unlock loop

This is the operator's daily flow:

1. **Generate** content via `/studio` (or wait for the daily auto-cycle at 07:00 UTC)
2. **Post** to platforms with the Copy + Open buttons (or use exported pack for TikTok/IG/YT)
3. **Log post** in dashboard → `publishing_log` updates
4. **Collect revenue** when platforms pay out
5. **Record earnings** in dashboard → `revenue_ledger` updates
6. **Watch the meter** at `/overview` → cumulative net climbs toward $25k
7. **At $25k cumulative net** → meter shows `UNLOCKED` → commercialization green light

The AI Advisor on `/analytics` reads the live snapshot every 60s and recommends the single highest-leverage next action.

---

## 12. Cost ledger

| Item | Monthly |
|---|---|
| OCI VM.Standard.E2.1.Micro (Always Free) | $0 |
| Let's Encrypt (HTTPS via Caddy) | $0 |
| SQLite on host disk | $0 |
| GoDaddy domain (annually $18 / 12) | $1.50 |
| Stripe transaction fees | 2.9% + $0.30 per sale (no base) |
| Emergent LLM Key | Cost-Guarded (cap-enforced) |
| **Fixed monthly cost** | **~$1.50** |

---

## 13. Roadmap (post-go-live)

P0 (next sprint):
- [ ] Land Phase 1-3 of `GO-LIVE.md` (in progress)
- [ ] First share-link campaign with UTM tracking on one channel

P1:
- [ ] Per-route LLM cost breakdown in `/distillation/stats` (books vs proposals vs advisor)
- [ ] Sidebar "Cost Guard fired N times today" badge
- [ ] Buffer/Hootsuite share fallback chips

P2:
- [ ] Switch unbounded `find().to_list()` queries to MongoDB `aggregate()` pipelines (deployment-agent finding)
- [ ] Stripe Connect / Tax when expanding beyond solo use
- [ ] Public-facing pricing page rebuild with testimonials

---

## 14. Quick links

- Repo: https://github.com/Quantam101/already-here-dashboard
- Preview (dev): https://gmaos-control.preview.emergentagent.com
- Production (target): https://alreadyherellc.com
- Stripe dashboard: https://dashboard.stripe.com
- Emergent Universal Key: app.emergent.sh → Profile → Universal Key
- GoDaddy DNS: goto.godaddy.com → My Products → DNS
- OCI console: https://cloud.oracle.com

---

## 15. If you only read one section

**You are mid-Phase-1 deploy.** Three things will get you live:

1. SSH in to the OCI box. If you're seeing `Connection timed out`, open port 22 in the VCN Security List (see § 6 Phase 1 step 2).
2. Run `sudo tail -f /var/log/command-os-bootstrap.log` and wait for `BOOTSTRAP COMPLETE`.
3. Edit `/opt/command-os/backend/.env` to add `EMERGENT_LLM_KEY`, `STRIPE_API_KEY`, `OPERATOR_EMAIL` → restart backend.

Then run the Phase-1 verification curl. Paste me the output and we move to Phase 2.
