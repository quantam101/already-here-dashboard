# Already Here Command OS — Free-Only Final Build Directive

> Architectural source of truth for the two-node free-tier deployment.
> Approved by operator on 2026-05-26.

## Final server target map

| Node | Role | Public IP | Private IP | Shape | Use |
|---|---|---|---|---|---|
| **`DashboardAlways Free`** | Command OS dashboard / control plane | `129.153.192.229` | `10.0.0.58` | `VM.Standard.E2.1.Micro`, 1 OCPU, 1 GB RAM | Dashboard, SQLite, scheduler, audit, manifests, approval queue |
| **`profitengine-server`** | Runtime / worker / ProfitEngine node | `129.146.167.73` | `10.0.0.160` | not fully provided | Agents, rendering, heavier jobs, ProfitEngine runtime |

## Dashboard host (`129.153.192.229`) constraints

- Public dashboard, build registry, agent registry, connector registry, cost dashboard, approval queue, audit log, scheduler, SQLite database, free-only policy enforcement, Lifelong Catch and Correct side panel, content schedule dashboard, ready-to-post export manager
- **Do NOT run MongoDB by default** on this host
- **Do NOT run heavy model inference**
- **Do NOT run heavy video rendering** unless the job is small
- Use **SQLite-first persistence**
- Use **local JSONL audit logs**
- Use **nginx or Caddy** for HTTPS
- Use **PM2 or lightweight Docker Compose**
- **Keep memory usage under 700 MB steady-state**

## Worker host (`129.146.167.73`) responsibilities

- ProfitEngine runtime, agent worker execution, heavier automation jobs, FFmpeg/Remotion rendering, content processing, distillation/VHLL jobs, health checks, optional local AI if resources allow, API worker for dashboard host

## Required dashboard API surface

The dashboard host MUST expose:

- `/api/health`
- `/api/cost/status`
- `/api/builds`
- `/api/agents`
- `/api/connectors`
- `/api/approvals`
- `/api/audit`
- `/api/content`
- `/api/scheduler`
- `/api/lifelong-catch-correct`

## Required dashboard UI surface

The dashboard MUST show:

- DashboardAlways Free health
- profitengine-server health
- current monthly estimated cost
- target monthly cost: **$0**
- blocked paid connectors
- unknown-cost blocked connectors
- missing credentials
- Bitwarden/Vaultwarden secret status
- build registry
- agent registry
- deployment registry
- content scheduler
- CapCut-style content factory
- manual ready-to-post packs
- production gate score
- audit log
- repair recommendations

## Free-only deployment rule

1. If a service exceeds the 1 GB dashboard host limit → move it to `profitengine-server` or disable it
2. If it costs money → **block**
3. If cost is unknown → **block**
4. If direct API publishing costs money → generate manual ready-to-post export packs
5. If AI costs money → use deterministic code, local model, or manual fallback
6. If a credential is missing → **fail closed** and show `requires_secret`

## Hard budget constraints

- Both servers must remain under **$0/month**
- No paid OCI resources
- No paid APIs required to boot
- No paid schedulers
- No paid database
- No paid storage
- No paid analytics
- No paid model required
- Unknown-cost actions block by default

## Migration roadmap (current state → directive-compliant)

| Phase | Work | Status |
|---|---|---|
| **Phase 1: Capture directive** | Save this file as architectural source of truth | ✅ DONE 2026-05-26 |
| **Phase 2: Cost gate API** | `/api/cost/status` reading the existing `connectors` collection cost_class field; `/api/system/status.bitwarden` already returns secret status | ✅ DONE 2026-05-26 |
| **Phase 3: Two-node health** | Add `WORKER_BASE_URL` env to dashboard; `/api/health` probes both nodes | 🟡 PENDING |
| **Phase 4: SQLite migration** | Replace motor/MongoDB with `aiosqlite` + lightweight ORM; refactor all 18 route files; tests | 🔴 MAJOR — multi-iteration effort |
| **Phase 5: Worker bridge** | Dashboard pushes approved jobs to `profitengine-server`; worker reports back via webhook into audit log | 🔴 PENDING |
| **Phase 6: Manual export packs** | Already implemented (`/studio/schedule/{id}/export`) — verify covers all platforms without free APIs | 🟡 PARTIAL |

## Tactical deploy decision

Until Phase 4 (SQLite migration) is complete, the current MongoDB-coupled stack **cannot run on the 1 GB micro instance** without OOM risk. Two pragmatic options exist for "go-live now":

- **(A) Deploy current MongoDB stack to `profitengine-server`** (the worker host, presumed larger). Use the 1 GB micro as a static reverse proxy or leave dark. Re-architect to the directive in V2.
- **(B) Pause launch, complete SQLite migration first** (~4–6 hours of refactoring). Then deploy to the dashboard host per the directive.

Operator chose: _to be confirmed_.
