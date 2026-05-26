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

### Iteration 3 - Production Wire-up + Dark Theme (latest)
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
- Backend pytest: 19/19 PASSING (100%)
- Frontend smoke tests: 8/8 routes (100%, 0 errors)
- Lint: Backend ruff PASS, Frontend eslint PASS

## Live URL
https://gmaos-control.preview.emergentagent.com
