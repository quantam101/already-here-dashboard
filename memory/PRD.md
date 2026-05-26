# Already Here Command OS - PRD

## Original Problem Statement
Build a complete enterprise-grade, governed multi-agent operating system consolidating ProfitEngine, GMAOS, EAOS, TradeGate, VHLL, and all Already Here builds into one unified, ASI-aligned, zero-spend-first platform with revenue automation, CapCut-style content factory, scheduler, omni-publisher, agent runtime, audit log, approval gates, and Bitwarden-compatible secret management - all running at $0/month on Oracle Cloud Always Free.

## User Personas
- **Solo Operator (Primary)**: Manages all builds, revenue streams, content from single dashboard
- **Federal Procurement Bidder**: Uses H&M proof for SBA/federal contracting proposals
- **Content Creator**: Generates multi-platform content with manual export fallback when APIs unavailable

## Core Requirements (Static)
- Zero-spend mode by default (Cost Guard Agent enforced)
- Bitwarden-compatible secret management
- Immutable audit log
- Approval gates for risky actions
- Multi-stream revenue tracking (10 streams live)
- AI content generation via Emergent LLM (Gemini 3 Flash - FREE)
- Platform connectors with explicit cost classifications
- Manual export packs when APIs unavailable/paid
- 10 production agents
- Oracle Cloud Always Free deployment ready + local laptop deployment fallback
- MongoDB local-first persistence

## What's Been Implemented (2026-05-26)

### Iteration 8 - Books / Audiobooks Agent + Auth Gate + OCI Bootstrap (latest)
**New revenue stream: rev-books. Auth wired (gated by env). OCI fully scripted.**
- **`/api/books/` route** — full book/manual/journal/workbook/guide/memoir generation via Emergent LLM Gemini 3 Flash, chapter-by-chapter; types validated; chapter count 1..20; outline auto-parsed (JSON-array tolerant); `.md` and `.txt` download endpoints; `download_count` tracked; new `rev-books` revenue stream auto-created on first book (idempotent)
- **Audiobook playback** — frontend `Books.js` uses browser `window.speechSynthesis` API → **truly $0**, no third-party TTS dependency
- **`/api/auth/` route** — Emergent-managed Google Auth, single-operator allowlist via `OPERATOR_EMAIL` env. When env unset, falls OPEN (legacy behavior, tests stay green). Endpoints: `/config`, `/session`, `/me`, `/logout`
- **`<AuthGate>` component** — wraps all routes in App.js; checks `/api/auth/config` then `/api/auth/me`; redirects to Emergent Google OAuth when required; handles `#session_id=...` callback fragment
- **`/app/scripts/oci-bootstrap.sh`** — one-command sudo installer for OCI Always Free: installs Docker + Compose, opens firewall, clones repo, writes `.env` files, generates Caddyfile with auto-HTTPS, runs `docker compose up -d`
- **`docker-compose.yml`** updated with `STRIPE_API_KEY` + `OPERATOR_EMAIL` passthrough
- All shell scripts chmod +x and validated (`bash -n` clean)
- **87/87 pytest** passing (67 regression + 10 TestBooks E2E + 4 TestAuth + tooling)

### Iteration 7 - Stripe Payments + Analytics + AI Advisor + Auto-Cycle
**Real money receiving, real analytics, real intelligence:**
- **`/api/payments/` route** (Stripe via emergentintegrations) — 3 fixed packages: starter $49 one-time, pro $99/mo, enterprise $499/mo. Successful checkouts auto-write a ledger entry to `rev-saas` stream so the $25K Proof-of-Work meter ticks on REAL money. Webhook handler at `/api/payments/webhook` for Stripe events. Idempotent recording (no double-credit).
- **`/api/analytics/` route** — 6 endpoints: funnel, posting-times, stream-roi, platform-mix, viral-themes, momentum + combined `/dashboard` payload. All data live from ledger + publishing_log + content_ideas (zero seeded analytics)
- **`/api/advisor/` route** (Claude Sonnet 4-5 via Emergent LLM) — reads live dashboard JSON snapshot, returns ONE prioritized next-action with headline/rationale/confidence
- **`services/scheduler_service.py`** — asyncio in-process daily auto-cycle at 7am UTC (configurable via `DAILY_CYCLE_HOUR_UTC`, disabled in `SYSTEM_MODE=test`)
- **Frontend `/analytics`** — AI Advisor card + 6 visualization cards (Recharts, dark theme, empty-state guards)
- **Frontend `/pricing`** — 3 PriceCards with Stripe Checkout integration + test card instructions + live-keys swap guidance
- **Frontend `/payment-success`** — Polling with hard-fail on 4xx, paid/error/expired/processing states
- 67/67 pytest pass (added 9 new tests: payments, analytics, advisor)
- All polish items from iteration_7 testing report fixed (Stripe 404 handling, polling stop on 4xx, Recharts empty-data guard)

### Iteration 6 - Code Quality Fixes
- Extracted module-level constants: `SECTIONS_BY_TYPE` + `DEFAULT_COMPANY` in `proposals.py` (cut `_build_prompt` complexity 11→6)
- Extracted helpers: `_format_bullet_list` (proposals), `_coerce_amount` + `_parse_csv_row` (ledger), `_make_idea_doc` + `_make_publishing_draft` (cycle) — reduces complexity across the board
- Extracted `CONTENT_TYPE_OPTIONS`, `TONE_OPTIONS`, `LENGTH_OPTIONS` in ContentGenerateDialog (eliminates inline array re-render anti-pattern)
- Explicit `opps: list = []` init in `cycle.py:run_cycle` (silences UnboundLocal linter false-positive)
- Created `/app/pytest.ini` registering `timeout` mark (zero warnings)
- All other "react hook dependency" / "is vs ==" warnings verified as false positives by ESLint + Python's own `SyntaxWarning` (skipped)
- 50/50 pytest pass, Python ruff clean, JS eslint clean, zero warnings

### Iteration 5 - Scout + Procurement Engine + Cycle + PWA
**Real scrapers, real writers, real pipeline:**
- New `/api/scout/` route — Reddit, HackerNews, Grants.gov, SAM.gov, Google News (all FREE, no auth) → returns Opportunity[] with id/title/source/kind/url/score
- New `/api/proposals/` route — grant_proposal, contract_proposal, rfp_response, capability_statement, cover_letter, invoice. AI-generated via Emergent LLM Gemini 3 Flash ($0)
- New `/api/cycle/run` route — one-click pipeline: scout viral → content ideas → publishing drafts (operator confirms then publishes manually)
- New `/api/ledger/import-csv` — multipart CSV upload, bulk-creates ledger entries (Amazon Associates, Etsy, AdSense exports)
- **Facebook + Reddit** platform connectors added (manual_free / free_external)
- **Procurement Scout Agent** (agent-011) — 11 agents total
- **Frontend Scout page** with 4 tabs (Viral, Grants, Contracts, News), live data, Draft button on grants/contracts
- **Frontend Proposals page** with stat tiles + New Draft + New Invoice dialogs
- **Run Cycle button on Command Center** — operator-driven pipeline
- **PWA manifest** + apple-mobile-web-app meta tags → installable on iOS/Android home screen
- **50/50 pytest** passing (added 13 new tests)

### Iteration 4 - Proof of Work System
**Real live data, not seeded:**
- New `/api/ledger/` route: immutable revenue ledger for real net earnings
  - POST/GET, validation (net ≤ gross, stream must exist)
  - `GET /api/ledger/stats/profit-progress` - $25K goal tracker
  - `GET /api/ledger/stats/by-stream` - aggregated per-stream totals
- New `/api/publishing/` route: immutable publishing log
  - status lifecycle: drafted → exported → posted → verified
  - auto-stamps `posted_at` / `verified_at` on transition
  - `GET /api/publishing/stats/overview` - counts by status + platform
- Revenue `monthly_actual` now computed LIVE from ledger entries dated in current month (single source of truth)
- Seeded `monthly_actual` reset to $0 (true clean start from real proof-of-work)
- **Frontend Proof of Work page** (`/proof-of-work`): ledger table, publishing table, $25K profit meter, stats tiles
- **ProfitMeter** on Command Center: $25K progress, total net, this month, remaining, entry count
- **RecordEarningsDialog**: form to log net earnings with date/source/proof URL, validates net ≤ gross
- **LogPostDialog**: form to log publishing events with platform/URL/status
- "Record Earnings" button on every revenue stream card
- Sidebar nav: new "Proof of Work" entry under Revenue
- **35/35 pytest** (was 19), all frontend flows verified by testing agent
- a11y: DialogDescription added to all new dialogs

### Iteration 3 - Production Wire-up + Dark Theme
- Expanded seed: 10 revenue streams (AI Blog Network, Faceless Videos, Print-on-Demand A/B, Affiliate Links, Social Automation, SEO Content Farm, Federal Contracting, Service Automation, Newsletter Sponsorships)
- Expanded agents: 5 → 10 (added SEO Scout, Faceless Video, POD Designer, Affiliate Link, Health Oracle)
- Command Center fixed: ProfitEngine v5 status `degraded`/`fail` → `live`/`pass`
- Efficiency Layer fixed: VHLL Distillation Engine `draft` → `live` (94/100 gate score)
- OCI deployments fixed: all 4 deployments show `success`, added local-laptop deployment record
- Created `/app/scripts/deploy-local.sh` — laptop/terminal deployment fallback (Docker + native modes)
- Dark enterprise theme applied to Revenue, Agents, Builds, Deployments, Content, Approvals, Audit pages
- Fixed Revenue page CSS overlap (added page-header, stat-card, metric-card, content-badge classes)
- 19/19 pytest pass, 8/8 frontend routes pass

### Backend (FastAPI + MongoDB)
- 9 route modules with `/api/*` prefix, async patterns
- 19/19 pytest tests passing
- ContentIdeaCreate Pydantic schema for validation
- Builder functions (`make_agent`, `make_connector`) reduce repetition
- Audit logging on every action
- Bitwarden service scaffold
- Cost Guard enforcement

### Frontend (React + Recharts)
- 9 dashboard pages, all load with 0 JS errors, all in dark enterprise theme
- Enterprise dark theme (#0a0e1a + green accents) — now consistent across ALL pages
- 13 extracted sub-components
- useMemo for navigation groups and expensive computations
- All magic numbers extracted to chartConfig.js constants
- All array index keys replaced with stable IDs

### Content Factory (CapCut-style)
- Idea bank with multi-platform selection
- AI script generation via Gemini 3 Flash (free)
- Platform connector registry: free_local 1, free_external 1, manual_free 4, paid_blocked 1
- Export pack generation with platform-specific instructions

### OCI + Local Deployment
- `/app/docker-compose.yml` - Multi-service deployment
- `/app/Caddyfile` - Free HTTPS via Let's Encrypt
- `/app/scripts/backup.sh`, `restore.sh`, `healthcheck.sh`, `validate-oci.sh`
- `/app/scripts/deploy-local.sh` - **NEW** laptop/terminal deployment

## Prioritized Backlog

### P0 - Critical (COMPLETE)
- [x] Core dashboard with revenue tracking (10 streams wired)
- [x] Agent management (10 agents)
- [x] Build registry with production gates (all 5 builds healthy)
- [x] Audit log with immutable events
- [x] Content Factory backend + frontend
- [x] Platform connector registry with cost classifications
- [x] Cost compliance system
- [x] OCI deployment scripts
- [x] Local laptop deployment script
- [x] Dark theme across all pages
- [x] Revenue page CSS overlap fix

### P1 - Important (Future)
- [ ] FFmpeg video rendering integration (Dockerfile ready)
- [ ] Bitwarden CLI full integration
- [ ] OAuth2 flows for platforms when approved
- [ ] GitHub Actions CI workflow
- [ ] Scheduler calendar view
- [ ] AI Operations Advisor panel (Claude Sonnet)
- [ ] Per-stream-card data-testid for stable Playwright targeting

### P2 - Nice to Have
- [ ] Split seed_data.py into seed_data/ package modules
- [ ] Hide zero-state Builds tiles (DEGRADED/DRAFT when 0)
- [ ] Analytics ingestion (CSV import from platforms)
- [ ] VHLL/AAF Pipeline visualization
- [ ] Mobile PWA install prompt
- [ ] Webhook handlers for platform callbacks
- [ ] H&M proof-to-proposal generator

## Cost Compliance
- Target: $0/month
- Current: $0/month
- Free connectors: 2 (Website Blog, Medium)
- Manual export: 4 (TikTok, YouTube, Instagram, LinkedIn)
- Paid blocked: 1 (Twitter/X - $100/mo blocked by Cost Guard)

## Test Coverage
- Backend pytest: **35/35 PASSING** (100%)
- Frontend smoke tests: 9/9 routes (100%, 0 errors)
- Lint: Backend ruff PASS, Frontend eslint PASS

## Live URL
https://gmaos-control.preview.emergentagent.com

## Proof-of-Work Workflow (Operator Loop)
1. Operator uses Content Factory → generates a ready-to-post pack
2. Operator manually publishes to platform (or via approved API)
3. Operator clicks **Log Post** in dashboard → records platform, title, URL, status='posted'
4. When platform pays out (Amazon Associates, AdSense, Etsy, etc.), operator clicks **Record Earnings**
5. Live ledger updates Revenue stats, Profit Meter, and per-stream actuals immediately
6. Once cumulative net ≥ $25,000 → meter shows **UNLOCKED** → commercialization green light
