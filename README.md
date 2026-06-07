# Already Here Field Network OS

Owned by Already Here LLC.

This repository contains the production PWA foundation for the Already Here LLC technician network, dispatch command center, retainer tracker, compliant opportunity mesh, deterministic matching engine, prime-network readiness system, automated-income planner, offline queue, and audit workflow.

## Current Capabilities

- Mobile-first Next.js PWA shell.
- Technician opt-in intake workflow.
- Local IndexedDB persistence for field network state.
- Local browser persistence for revenue opportunity decisions.
- Offline failover state indicator.
- Deterministic technician matching engine.
- Work order creation and match ranking.
- Compliant opportunity mesh for break/fix, retainer, teaming, dispatch, hauling, and procurement targets.
- A/B/C/Avoid opportunity grading against Already Here LLC rate floors and dispatch minimums.
- Proceed / Counter / Discard decision states for lead suppression and follow-through.
- Owner/company monthly income floor targeting $25,000 before technician-network upside.
- Negotiable technician contribution model estimating Already Here LLC income lift based on location, demand, negotiated payout, client price, skill level, reliability, and routed work volume.
- Automated and semi-passive productized income queue.
- Prime contractor readiness panel for vendor packet, compliance, coverage, and national capacity milestones.
- Audit event capture.
- Sync queue capture for future Oracle backend sync.
- Strict TypeScript configuration.
- Node test coverage for the revenue model.
- CI verification workflow.
- Vercel production configuration.
- Hardened HTTP response headers.

## Revenue Model

The $25,000 target is the Already Here LLC owner/company income floor. It is not the ceiling and it is not dependent on adding technicians.

Technician expansion is tracked as estimated company-income upside, not a fixed pay rate or fixed promise. Technician pay is negotiable per tech, per market, per job, and per scope.

| Contribution profile | Estimated Already Here LLC income lift per tech/month | When it applies |
|---|---:|---|
| Low-volume / developing market | $500–$1,500 | Secondary markets, rural routes, limited demand, or early-market testing |
| Standard metro / reliable coverage | $1,500–$4,000 | Normal planning range when enough profitable work can be routed consistently |
| High-demand / specialized market | $4,000–$8,000 | Dense metros, urgent coverage lanes, specialized skills, and strong client pricing |

Actual income lift depends on client bill rate, negotiated tech payout, route density, location, urgency premium, repeat volume, QA quality, closeout reliability, and how much work Already Here LLC can push through the technician.

## Commands

```bash
npm install
npm run dev
npm run verify
```

## Deployment

Primary frontend target: Vercel.

Primary backend target: Oracle Cloud.

DNS authority: GoDaddy.

The Vercel build command is configured as:

```bash
npm run verify
```

This means deployment must pass typecheck, lint, revenue-model tests, and the production Next.js build.

See `docs/deployment.md` and `docs/oracle-schema.md`.

## Security Rule

No private API keys, credentials, payment secrets, cloud credentials, or tokens belong in client-side code or committed files. Use Vercel environment variables and Oracle secret storage.

## Lead Mesh Compliance Rule

This system does not bypass logins, CAPTCHAs, robots policies, account terms, or platform access controls. Opportunity intake must come from authorized email, official portals, public procurement notices, partner channels, or manual review of public listings. High-risk actions such as bid submission, counter submission, email outreach, credential changes, payments, and contract acceptance require manual approval.

## Operating Model

Morning work funds the system. The system removes Stephen as the bottleneck by capturing technician capacity, QA evidence, repeat clients, and dispatch margin.
