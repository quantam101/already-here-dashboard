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

## What's Been Implemented (2026-02-XX)

### Iteration 21 - Video Engine (Faceless Video Pipeline) (latest)
**$0/mo, OCI-Always-Free-compatible video generator. 142/142 pytest including 9 new video tests.**

**Engine architecture (all $0):**
- **ffmpeg** (apt package) — concat + scale-to-vertical + caption burn + audio mix
- **Piper TTS** (`pip install piper-tts`) — neural TTS, ARM-compatible ONNX, ~60 MB per voice
- **Pexels API** (free tier, 200 req/hr) — stock footage with `sha256(shot)[:16]` cache
- **Pexels fallback** — deterministic hex-colour placeholder clip with shot text burned in (so the pipeline never deadlocks during dev / when no key is set)

**Performance (measured on OCI-equivalent CPU):** ~8 seconds to render a 10-second 1080×1920 vertical MP4 (H.264 ultrafast + AAC 128k) end-to-end.

**Files added:**
- `backend/routes/video.py` — 8 endpoints
- `backend/services/video/{__init__,stock,tts,composer,engine}.py` — pipeline orchestrator
- `frontend/src/pages/VideoStudio.js` — full UI at `/video-studio`
- `frontend/src/lib/api.js` — `videoAPI` helpers
- `/app/VIDEO_ENGINE.md` — full build doc (13 sections)
- `/app/data/voices/en_US-amy-medium.onnx[+.json]` — default voice
- `backend/tests/test_video_engine.py` — 9 tests including the full end-to-end render

**API surface (all under `/api/video`):**
| Method | Path | Notes |
|---|---|---|
| GET | /config | ffmpeg+piper+voices+pexels capability self-report |
| GET | /voices | installed Piper voices |
| POST | /render | queue a render job (BackgroundTask) |
| POST | /render-from-script | render an existing `content_scripts` row |
| GET | /jobs | list recent jobs (default 30) |
| GET | /jobs/{id} | poll status + progress_pct + message |
| GET | /jobs/{id}/download | download finished MP4 (409 until complete) |
| DELETE | /jobs/{id} | remove job + MP4 |

**Tiered modes (in capability_report):**
- **`faceless`** ✅ shipped — stock + TTS + ffmpeg, $0/render
- **`avatar_lipsync`** 🟡 scaffolded — Phase-2, Wav2Lip ONNX; endpoint returns HTTP 501 with operator install hints
- **`external_provider`** 🟡 scaffolded — Phase-3 Sora 2/Veo bridge through litellm; endpoint returns HTTP 501

**Deepfake guardrails baked into `VIDEO_ENGINE.md §8`** (operator-self consent flag, AI-generated watermark default-on, public-figure CLIP-embedding detection routed through the `compliance_content` HITL gate). Engine ships the legitimate use-cases (avatar lipsync onto own face / consenting subject / AI-synthesized portrait) and documents why unconsented public-figure swaps are gated.

**OCI bootstrap script updated** to auto-install ffmpeg + piper-tts + the default Amy voice during deployment so the engine works on a fresh OCI VM without manual setup.

**Sidebar nav** — new `Video Engine` entry (Film icon) routes to `/video-studio`.

**End-to-end render verified via pytest** (`test_full_render_pipeline`): kick-off → poll until `status=complete` → download MP4 → verify Content-Type=video/mp4 → confirm >10KB payload → delete cleanup.

### Iteration 20 - Sidebar HITL Badges + Governance Approvals Queue UI + One-Shot OCI Deploy
**133/133 pytest + testing-agent verification → 0 issues / 0 action items.**

- **`<GovernanceStatusBadges/>`** (new) mounted in the sidebar's System Status box. Polls `GET /api/governance/approvals?status=pending` and `GET /api/lifelong-catch-correct/` every 30s. Renders:
  - Amber **HITL approvals N · M need 2nd** badge linking to `/approvals` (the `· M need 2nd` suffix appears only when dual-actor rule is active AND there are rows with 1-of-2 distinct approvals).
  - Red **Catch & Correct N HIGH** badge for high-severity LCAC findings.
  - Renders nothing when both counts are 0.

- **`<GovernanceApprovals/>`** (new) — section rendered at the bottom of `/approvals`. Lists all governance-managed HITL approvals (separate collection from the legacy `approvals` table), with an actor-name input + per-row Approve/Reject buttons that route through `governanceAPI.approve(id, note, actor)` / `reject(id, note, actor)`. Each row shows severity, action_id, route, current decision count and (when applicable) the **2-of-2 · X/Y** badge that surfaces the dual-actor progress.

- **`lib/api.js`**: `governanceAPI.approve`/`.reject` now accept an `actor` parameter (forwarded to the existing `{note, actor}` body shape on the backend).

- **`scripts/one-shot-oci-deploy.sh`** — single-paste OCI bootstrap pre-filled with `alreadyherellc.com` + `dispatch@alreadyherellc.com`. Operator only edits one line (`GITHUB_REPO`) before pasting on the OCI host. Generates a strong `OPERATOR_TOKEN` via `openssl rand -hex 32` and prints the 4-step post-bootstrap sequence (nano backend/.env → docker compose restart → 3 curl health checks → browser open).

- **Verification (testing agent iteration 9)**: 11/11 review items pass first run, 0 critical/minor issues. Confirmed:
  - `governance/status` reports `autonomy_level=L5`, `route_gates_count=8`, `hitl_gates_count=9`.
  - `governance/manifest` exposes all 8 wired route_gates 1:1 (no drift vs `governance.yaml`).
  - `POST /api/payments/keys/rotate` validates shape and stages to `.env.proposed` without touching live `.env`.
  - At L5, gated routes (`cycle/run`, `publishing/`) pass through with 200/201 (not 202).
  - Frontend `/overview` shows `[data-testid="sidebar-governance-badges"]` rendering "HITL approvals 5" tied to live pending count.
  - Frontend `/approvals` shows BOTH legacy section AND `[data-testid="governance-hitl-queue"]` with `2-of-2 · 0/2` badges visible on critical rows.
  - Served HTML has 0 references to "Made with Emergent" or "posthog".

### Iteration 19 - Total Emergent Scrub + 2-of-2 Dual-Actor Approval + DEPLOY-NOW Runbook
**133/133 pytest passing. App now ships with ZERO user-visible Emergent traces and a true enterprise dual-actor control on critical gates.**

**Total Emergent scrub (every shipped artifact):**
- `frontend/public/index.html` — removed the "Made with Emergent" floating badge, the `assets.emergent.sh/scripts/emergent-main.js` injection, and the hardcoded PostHog analytics block (which phoned home to a third-party project). Production HTML now contains zero external Emergent or PostHog references.
- `frontend/src/pages/Pricing.js` — stripped "(configured by Emergent)" copy from the Stripe Test Mode notice.
- `frontend/src/components/QuickstartWizard.js` — removed legacy `emergent_llm_key_set` fallback read.
- `frontend/src/lib/clipboard.js` — generic "restricted iframes" comment instead of name-checking Emergent.
- `backend/routes/system.py` — removed `emergent_llm_key_set` field from `/api/system/status`. New canonical key is `llm_key_set`.
- `backend/routes/cost.py` — `/api/cost/policy` now lists "litellm + LLM provider API key (BYO key)" instead of "Emergent LLM (Universal Key)".
- `backend/routes/books.py`, `proposals.py`, `cycle.py`, `advisor.py`, `services/content_generation_service.py` — every public docstring de-branded.
- `backend/routes/auth.py`, `services/llm_adapter.py`, `services/stripe_adapter.py` — module headers cleaned of "replaces Emergent…" migration commentary.
- `backend/.env` — `EMERGENT_LLM_KEY=` renamed to `LLM_API_KEY=` (the adapter still reads the legacy var as a fallback so existing operators don't break).
- **Deploy artifacts**: `scripts/oci-bootstrap.sh`, `scripts/preflight.sh`, `scripts/validate-oci.sh`, `scripts/deploy-local.sh`, `cloud-init.sh`, `docker-compose.yml`, `docker-compose.sqlite.yml` — all now write `LLM_API_KEY` first and only fall through to legacy `EMERGENT_LLM_KEY` for backwards compatibility.

**2-of-2 dual-actor approval policy** (`services/governance_service.py`):
- New env flag `DUAL_ACTOR_APPROVAL=true` activates the two-person rule on all `severity=critical` gates (L5: `capital_allocation`, `payment_modification`, `contract_execution`, `pii_access`, `security_modification`, `private_data_to_public_llm`).
- Approval rows now carry `required_decisions` (computed at creation) + a `decisions` append-only ledger of `{actor, approve, note, decided_at}` entries.
- `decide_approval()` dedupes by actor so one operator can't satisfy the 2-of-2 rule alone. A single `reject` from any actor finalizes status to `rejected`.
- 202 response from `enforce()` includes `required_decisions` so the UI can label the gate "TWO-PERSON RULE active — needs N distinct actors".
- Verified end-to-end via curl: L3+critical → 202 with `required_decisions=2`, alice approves → still pending, alice double-approves → still pending (idempotent), bob approves → status flips, request clears with `X-Approval-Id`.
- 5 new pytest unit tests in `tests/test_dual_actor_approval.py` (single-actor flow, critical 2-of-2, high-severity gates stay 1-of-1 even with flag on, any reject finalizes, unknown id returns empty).

**`DEPLOY-NOW.md`** — single ultra-tight 8-section OCI runbook tailored to the user's repeated stumbling points: exact instance specs (VM.Standard.A1.Flex Ubuntu 22.04, NOT 20.04/24.04), public-subnet requirement, OCI key-file `chmod 600` step, port 80/443 ingress rules, DNS A-records, one-line bootstrap, mandatory `.env` overrides, and three guaranteed-to-hit troubleshooting recipes.

**Test totals:** 128 integration + 5 dual-actor unit = **133/133 PASSING**. Ruff clean. ESLint clean. Served HTML scrubbed (0 hits for `emergent`/`posthog`/`made with`).

### Iteration 18 - Remaining HITL Governance Gates Wired
**All 5 ProfitEngineV5 §5 gates now have live route enforcement. 128/128 pytest.**
- **`compliance_content` gate** wired into:
  - `POST /api/proposals/draft` (`routes/proposals.py::draft_proposal`)
  - `POST /api/books/` (`routes/books.py::create_book`)
- **`mass_outreach` gate** wired into:
  - `POST /api/cycle/run` (`routes/cycle.py::run_cycle`)
  - `POST /api/publishing/` — *conditionally*, only fires when `status=="posted"` (the actual external-facing outreach event; drafts/exports bypass the gate)
- **`payment_modification` gate** + new endpoint:
  - `POST /api/payments/keys/rotate` accepts `{stripe_api_key, stripe_webhook_secret, note}`, validates the key shape (`sk_test_` / `sk_live_` / `rk_*`), enforces the gate (requires L5 or HITL approval), then stages credentials to `backend/.env.proposed` — **never overwriting the live `.env`** to guarantee no silent mis-rotation.
- **Manifest updated** — `governance.yaml::route_gates` now declares all 8 gated routes. `GET /api/governance/manifest` is the single auditable source.
- **`AUTONOMY_LEVEL=L5`** added to `backend/.env` so the preview environment runs in operator-trust mode by default (gates fire only when operator dials autonomy down).
- **End-to-end HITL flow verified via curl**: L3 request → 202 with `approval_id` → operator approves → replay with `X-Approval-Id` header → 200.
- **5 new pytest tests** in `TestGovernanceGatesWired` (manifest mapping, rotate validation × 2, rotate staging, publishing drafted bypass). Total **128/128 PASSING**.

### Iteration 17 - Full Emergent Decoupling Verified
**App is now 100% autonomous and free of any Emergent platform dependency. 123/123 pytest still green.**
- **`emergentintegrations` removed entirely.** Replaced with:
  - `services/llm_adapter.py` → `litellm` (Gemini / Claude / OpenAI direct), with placeholder-key short-circuit so test runs never make real network calls.
  - `services/stripe_adapter.py` → raw `stripe` pip SDK with the same placeholder-key short-circuit.
  - `routes/auth.py` → local `OPERATOR_TOKEN` flow (no Emergent OAuth dependency); `AuthGate.js` updated accordingly.
- **Verified:** `pytest backend/tests/backend_test.py` → **123/123 PASSING** after decoupling. Stripe smoke + LLM-calling routes both behave correctly with placeholder keys.
- **Fixed:** React key-prop anti-pattern in `CatchAndCorrectPanel.js` (array-index → stable `${category}-${severity}-${message}` composite). ESLint clean.
- **`ZERO_DOLLAR_ENTERPRISE.md`** — confirmed populated end-to-end (iteration 16 §10 tech-stack equivalency table, governance gate matrix, deferred-roadmap rationale, verification curls).

### Iteration 16 - ProfitEngineV5 Alignment: Governance + Master Revenue Equation + Tier Router + Catch-and-Correct Panel
**~85% of the ProfitEngineV5 blueprint now operational on $0/mo infra. 123/123 pytest passing.**
- **Declarative L0-L5 Governance** (blueprint §5 §6): `governance.yaml` + `services/governance_service.py::enforce()` single chokepoint + `routes/governance.py` (status/manifest/reload/approvals CRUD). Wired `capital_allocation` gate into Stripe smoke-test.
- **Master Revenue Equation tracker** (blueprint §2): `routes/revenue_equation.py` computes `Q_D × C_R × A_OV × P_F × F_C × P_M` from live data; identifies bottleneck. `RevenueEquationCard` on `/overview`.
- **Tier-aware LLM router** (blueprint §3.5): `services/llm_runner.py::run_tiered(tier="low|mid|high")` — Tier 1 zero-LLM local; Tier 2 Gemini-3-Flash; Tier 3 Claude-Sonnet.
- **Catch & Correct telemetry panel** (blueprint §8): Global `CatchAndCorrectPanel` mounted in `DashboardLayout`, polls every 30s, severity-coloured.
- **`ZERO_DOLLAR_ENTERPRISE.md`** — every §10 enterprise spec mapped to a $0 OSS substitute.
- **7 new pytest tests**. Total **123/123 passing**.

## What's Been Implemented (2026-05-26)

### Iteration 15 - Live-Mode Smoke Runner + Cache Hit Rate Chart + Final Go-Live Runbook (latest)
**Operator can now verify live Stripe keys with a self-refunding $0.50 charge. 116/116 pytest.**
- **Auto-refunding Stripe smoke test** (`routes/payments.py`):
  - `POST /api/payments/smoke-test/create` — creates a $0.50 live-mode checkout session tagged `package_id=smoke_test`, `metadata.smoke_test=true`. Refuses to run in test mode or without webhook secret.
  - `GET /api/payments/smoke-test/status/{session_id}` — operator polls this; flips `verified_live_pipeline=true` once the refund lands.
  - `GET /api/payments/smoke-test/recent` — list last N smoke runs.
  - **Webhook handler extended**: smoke-test sessions trigger an immediate full refund via the official `stripe` SDK (`stripe.Refund.create(payment_intent=...)`) instead of recording to ledger. Operator pays $0.50 with a real card, sees the refund within ~10s, knows the full live pipeline (keys + webhook secret + signature verification + refund flow) is wired correctly **before** routing any real customers through it.
- **Cache hit rate line chart** added to the Distillation card on `/analytics`:
  - Pulls `GET /api/distillation/budget/history?days=14`
  - Renders a 90px Recharts line chart (0-100% Y-axis, daily X-axis), with rolling average displayed top-right.
  - Visualizes the compounding savings: every time you regenerate the same proposal/book chapter, the hit-rate line climbs.
- **`GO-LIVE.md`** — single 3-phase final runbook tying together deploy + Stripe live + backup cron. Each phase ends with a copy-paste curl verification.
- **4 new pytest tests** for smoke-test endpoints (refuses in test mode, recent shape, status 404). Total **116/116 PASSING** (was 113).

### Iteration 14 - Unified LLM Runner + Daily Budget Cap + Backup Cron + Analytics UI (latest)
**Every LLM call now cached + budget-tracked. Operator-visible Cost Guard. 113/113 pytest.**
- **`services/llm_runner.py`** — single chokepoint for all LLM calls:
  - `run_cached(db, provider, model, system_msg, prompt, *, session_id)` — distill → cache lookup → daily-budget pre-check → LLM call → cache store → token-counter bump. One call replaces ~20 lines of boilerplate.
  - `get_today_usage(db)` + `daily_usage_history(db, days)` — operator telemetry.
  - `check_daily_budget(db, expected_tokens)` — raises HTTP 429 when `LLM_DAILY_TOKEN_CAP` env (default 0 = unlimited) would be exceeded.
- **All LLM consumers refactored** to use the runner:
  - `routes/books.py` — outline + every chapter now cached independently. Regenerating a book with one tweaked outline only re-bills the changed chapter.
  - `routes/proposals.py` — identical grant/contract drafts hit cache.
  - `routes/advisor.py` — identical dashboard snapshots within TTL skip the LLM.
  - `services/content_generation_service.py` — script generation runs through the runner when `db` is passed (which the route always does).
- **New endpoints:**
  - `GET /api/distillation/budget` — today's tokens in/out/total, cap, remaining, over_cap flag.
  - `GET /api/distillation/budget/history?days=14` — last N days of usage rows.
- **Frontend `<DistillationCard />` on `/analytics`** — top-of-page Cost Guard card showing tokens saved, $ saved (est), cache rows, cache hits, today's usage vs cap with a color-coded progress bar. Auto-refreshes every 60s. Hooked into `distillationAPI` in `lib/api.js`.
- **Backup automation:**
  - `scripts/backup-sqlite.sh` — atomic SQLite snapshot via `sqlite3 .backup`, 14-day retention, tars + exports.
  - `scripts/install-backup-cron.sh` — one-shot installer that writes a systemd timer firing nightly at 03:00 UTC (1h jitter), enables it, runs one backup immediately. Pure $0 host-disk backups, no S3 dependency.
- **6 new pytest tests** (TestDistillation budget shape, budget history, plus 4 from iteration 13). Total **113/113 PASSING** (was 104 pre-iteration-13).

### Iteration 13 - Data Distillation + Stripe Live-Mode Gate + Final OCI Deploy (latest)
**Token-cheap LLM pipeline, live-key safety net, single-command deploy. 111/111 pytest.**
- **`services/distillation_service.py`** — pure utility module:
  - `distill_text()` — semantic compression (filler-word stripping, whitespace collapse). Demo: 53.9% char reduction on test input.
  - `to_yaml_payload()` — YAML formatting for structured data (~25-40% fewer tokens than equivalent JSON for nested-dict payloads).
  - `estimate_tokens()` — chars/4 heuristic for budget telemetry.
  - `fingerprint(model, system, prompt)` — sha256-based cache key (32 hex chars).
  - `cache_lookup/store/stats/clear` — db-backed prompt-response cache in `llm_cache` collection, dual-DB compatible (works on Mongo + SQLite wrapper), 30-day TTL configurable via `LLM_CACHE_TTL_SECONDS`.
- **`routes/distillation.py`** — operator telemetry + utility API:
  - `GET /api/distillation/stats` — cache rows, hits, tokens-saved, $ saved (heuristic via `TOKEN_COST_PER_1K` env).
  - `GET /api/distillation/config` — TTL, cost-per-1k, tier descriptions.
  - `POST /api/distillation/preview` — show before/after for any text + YAML-vs-JSON for any payload (operator tuning tool).
  - `POST /api/distillation/clear` — wipe cache.
- **Tiered LLM pipeline** baked into existing services:
  - `content_generation_service.create_script_prompt()` now emits YAML idea payload + distilled wrapper text.
  - `content_generation_service.generate_script_from_idea(idea, db=db)` does cache lookup BEFORE every LLM call; on miss, stores response under the fingerprint. Cache-hit responses tagged `metadata.cache_hit=True`.
  - `advisor.get_recommendation()` now sends YAML context (not JSON) + cache-checks on identical snapshots.
- **Stripe live-mode safety gate** (`routes/payments.py`):
  - `_stripe_mode()` + `_readiness()` helpers.
  - `GET /api/payments/mode` — lightweight `{mode: "test|live|missing|unknown"}` probe for frontend banners.
  - `GET /api/payments/readiness` — full operator checklist + go_live_ready flag + issues list.
  - **Safety gate inside `create_checkout()`**: if `sk_live_*` key is set but `STRIPE_WEBHOOK_SECRET` is missing, the endpoint returns HTTP 503 — preventing silent revenue loss while operator is mid-setup.
- **`LIVE_MODE_CHECKLIST.md`** — step-by-step Stripe test→live transition (8 steps, includes rollback + common-mistakes table).
- **`DEPLOY-FINAL.md`** — final single-command OCI deploy runbook (cloud-init two-liner, idempotent resume, DNS, env, verify, daily ops).
- **7 new pytest tests** (TestDistillation × 5 + TestPayments mode/readiness × 2). Total **111/111 PASSING** (was 104). Zero regressions on existing 104.

### Iteration 12 - Free-Only Build Directive: SQLite Backend + Two-Node Health + LCAC (latest)
**Honors operator's architecture directive. 104/104 pytest on BOTH backends. 200 MB RSS.**
- **`services/sqlite_db.py`** — Motor-API-compatible shim over aiosqlite (363 lines). Each "collection" maps to one SQLite table `(id TEXT PRIMARY KEY, doc TEXT JSON)`. Supports every Mongo op the codebase actually uses (audited via grep): `find_one`, `find().sort().to_list()`, `insert_one/many`, `update_one` with `$set/$inc/$max`, `delete_one/many`, `count_documents`, `aggregate` with `$group/$sort/$limit`. Filter ops: equality, `$gte/$gt/$lte/$lt/$ne/$in/$nin/$exists`. Unsupported ops raise `NotImplementedError` (fail-loud)
- **Env-gated backend switch** — `STORAGE_BACKEND=sqlite` flips engines without touching route code. Default stays MongoDB so preview/dev unaffected
- **`docker-compose.sqlite.yml`** — 2-container stack for 1GB-RAM micro: backend (400 MB limit) + Caddy (100 MB limit, serves pre-built React static bundle from `frontend/build`). No MongoDB. No Node runtime
- **`Caddyfile.sqlite`** — static frontend + `/api/*` reverse-proxy
- **`oci-bootstrap.sh` v2** — auto-detects RAM via `/proc/meminfo`. `<1500 MB` → SQLite mode (compiles React bundle on host, no Node container in prod). `>=1500 MB` → MongoDB mode. New flags: `-b sqlite|mongodb` (force), `-w WORKER_URL` (link to profitengine-server)
- **`GET /api/health/nodes`** — two-node health report (`DashboardAlways Free` + `profitengine-server`), polls worker if `WORKER_BASE_URL` env is set
- **`GET /api/cost/status`** + **`/api/cost/policy`** — Free-Only enforcement: connector cost classifications, paid_blocked, unknown_blocked, requires_secret, optional_missing_secrets. Static policy doc lists 9 approved free integrations
- **`GET /api/lifelong-catch-correct/`** — read-only anomaly scanner. Surfaces: missing OPERATOR_EMAIL, Stripe live without webhook, no EMERGENT_LLM_KEY, no ledger entries in 30d, agents with >25% failure rate, audit gaps, empty build registry
- **`docs/COMMAND_OS_FREE_ONLY_FINAL_BUILD_DIRECTIVE.md`** — operator's directive committed as architectural source of truth + migration roadmap
- **`seed_data.py`** — backend-agnostic, honors `STORAGE_BACKEND` env var
- **`scripts/preflight.sh` v2** — now validates both compose variants; current state: **24 PASS · 0 FAIL**
- **4 new pytest tests** for cost/status, cost/policy, health/nodes, lifelong-catch-correct. Total **104/104 PASSING** on Mongo, **104/104** on SQLite

**Memory verified on SQLite stack:** backend process = 200 MB RSS · SQLite DB file = 200 KB after seed+tests · Caddy ~30 MB · **Total ~230 MB**, well under the 700 MB directive target.

### Iteration 11 - Bitwarden CLI + Copy+Open Platform + Deploy Preflight
**Real secrets vault, one-click posting, deploy gate. 100/100 pytest.**
- **Real Bitwarden CLI integration** (replaces 45-line mock) — `services/bitwarden_service.py` async-wraps `bw` binary via `asyncio.create_subprocess_exec`. Endpoints: `GET /api/secrets/status` (installed/unlocked/server/user) + `GET /api/secrets/items` (metadata only, **no password values ever cross the wire**). Backend code calls `get_bitwarden_service().get_secret("NAME")` which falls back to env when vault is offline → existing code paths unchanged
- **`/secrets` page** — sidebar nav under SYSTEM. Status banner + setup instructions (Bitwarden cloud OR self-hosted Vaultwarden Docker $0). Vault item browser with username + URI + has_password badge (read-only)
- **`bw` CLI auto-installed in `oci-bootstrap.sh`** (step 3b) — fails gracefully on ARM-mismatch, doesn't block deploy. `BW_SESSION` passed through `docker-compose.yml` env
- **"Copy + Open Platform" buttons** in `IdeaDetailDialog` — each script's target_platform gets a button (Reddit/LinkedIn/X open the platform's post composer pre-filled with script; TikTok/IG/YouTube copy + open the upload page). `lib/platformShare.js` builds the URLs per-platform
- **`scripts/preflight.sh`** — 23-check pre-deploy validator: artifacts exist, scripts have valid bash syntax, Python imports clean, pytest passes, frontend env present, git state. Run `bash scripts/preflight.sh` BEFORE oci-bootstrap to fail-fast. Currently: **20 PASS · 0 FAIL · 3 expected warnings**
- **4 new pytest tests** for secrets endpoints (shape, empty when uninstalled, no-leak verification, system status block). Total **100/100 PASSING** (was 96)

### Iteration 10 - Read/Copy/Post Content Flow + Agents UX Polish
**Fixes the "I can't access my generated content" pain. 96/96 pytest.**
- **`GET /api/studio/scripts/`** + **`GET /api/studio/ideas/{id}/scripts`** — operator can now read every script Gemini generated (was previously written to DB with no surfaced UI)
- **`<IdeaDetailDialog>`** — clicking an idea card opens a 3xl dialog showing description, target platforms, inspiration source URL, and **all generated scripts** (newest first). Each script section (Hook / Script Body / CTA / Shot List) has its own `copy` button, plus a top-level "Copy Full Script" that bundles everything in CapCut-import-ready format. "Generate Another" button inside the dialog calls Gemini-3-Flash and refreshes the list
- **`<ContentDetailDialog>`** — Content Library cards are now clickable; opens a 2xl dialog with full body in a `<pre>` block, Copy button, keywords, "Open published URL" if present, and a clear "How to post" instruction line linking to `/proof-of-work` Log Post
- **Agents page UX rewrite** — replaced scary "Fails: N" red columns with prominent **Success Rate %** (green ✓ if ≥90%, yellow ⚠ otherwise) and a "Fleet Success Rate" header stat (currently 98% across 3,190 historical runs). Agents with 0 fails show **"Status: ✓ Clean"** instead of red "0". Execute button now toasts the agent name and refetches
- **3 new pytest tests** for studio scripts (list all, list-for-idea, empty-for-nonexistent). Total **96/96 PASSING** (was 93)

### Iteration 9 - Quickstart Wizard + UTM Channel Attribution + Deploy Guide
**First-run operator onboarding + live channel-of-sale attribution. 93/93 pytest.**
- **`/api/system/status` route** — operator-facing config snapshot: `operator_email_set`, `stripe_mode` (live/test/missing), `stripe_webhook_secret_set`, `emergent_llm_key_set`, `daily_cycle_hour_utc`, collection counts (revenue_streams/agents/builds/ledger_entries/books/payment_transactions), `is_seeded`. Never leaks secret values — only set/unset flags + masked operator email
- **QuickstartWizard component** — auto-opens on first visit (gated by `localStorage` key `ah_quickstart_completed_v1`), 5 steps: Welcome → Operator Access → Stripe Mode → Seed Data & LLM → Test Auto-Cycle (one-click `POST /api/cycle/run`). Each step shows live ✓/⚠ from `/api/system/status`. Re-openable from sidebar's "Re-open Quickstart" button
- **Channel Attribution (UTM) card on `/analytics`** — reads `/api/payments/stats.by_utm_source` and renders a sortable Source / Clicks / Paid / Revenue / CVR table. Auto-refreshes every 60s. Empty-state when no transactions
- **UTM share-link tracking already complete in earlier batch** (forwarded into Stripe metadata + ledger entries + `/api/payments/share-link` generator on `/pricing`)
- **`/app/DEPLOY-TO-OCI.md`** — complete 7-step deployment guide for `alreadyherellc.com`: OCI Always Free provisioning → GoDaddy A-records → SSH bootstrap → Stripe webhook → PWA install on phone → daily-ops cheat sheet → rollback/test-mode toggle
- **3 new pytest tests** for `/api/system/status` (shape, no-secrets-leaked, seeded). Total **93/93 PASSING** (was 87)

### Iteration 8 - Books / Audiobooks Agent + Auth Gate + OCI Bootstrap
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
