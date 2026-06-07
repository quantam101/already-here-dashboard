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
- Right-fit dispatch: do not waste senior technicians on mediocre/simple work unless no better fit exists.
- Senior technician preservation for complex, high-margin, sensitive, large-project, or leadership work.
- Project-lead matching for larger jobs, multi-state projects, rollouts, and team coordination.
- Team builder logic for combining helper, field tech, specialist, and project-lead roles.
- Compliant opportunity mesh for break/fix, retainer, teaming, dispatch, hauling, and procurement targets.
- A/B/C/Avoid opportunity grading against Already Here LLC rate floors and dispatch minimums.
- Proceed / Counter / Discard decision states for lead suppression and follow-through.
- Owner/company monthly income floor targeting $25,000 before technician-network upside.
- Job-rate-first revenue model: Already Here LLC sets the client/job rate by job type, market, urgency, complexity, and risk before technician payout is negotiated.
- Negotiable technician payout model with verified certifications, degrees, licenses, tools, and additional skills able to justify roughly $20–$30/hr above baseline when margin supports it.
- Technician contribution model estimating Already Here LLC income lift based on location, demand, negotiated payout, client price, skill level, reliability, and routed work volume.
- Automated and semi-passive productized income queue.
- Prime contractor readiness panel for vendor packet, compliance, coverage, and national capacity milestones.
- Audit event capture.
- Sync queue capture for future Oracle backend sync.
- Strict TypeScript configuration.
- Node test coverage for the revenue model and dispatch matcher.
- CI verification workflow.
- Vercel production configuration.
- Hardened HTTP response headers.

## Revenue Model

The $25,000 target is the Already Here LLC owner/company income floor. It is not the ceiling and it is not dependent on adding technicians.

The pricing order is:

1. Set the Already Here LLC client/job rate based on job type, location, urgency, complexity, risk, SLA, travel, and whether the work is hourly, flat-rate, retainer, project, or dispatch coverage.
2. Negotiate technician payout per tech, per market, per job, and per scope.
3. Apply a verified-skill premium only when justified by actual certifications, degrees, licenses, specialized tools, or additional skills needed for the work.
4. Approve dispatch only when company margin, client quality, and repeat-work potential remain viable.

Company income is calculated as:

```text
client charge - technician payout - travel/admin/platform/QA/non-labor costs = Already Here LLC margin
Already Here LLC margin x profitable work volume = monthly company income lift
```

Technician expansion is tracked as estimated company-income upside, not a fixed pay rate or fixed promise.

| Contribution profile | Estimated Already Here LLC income lift per tech/month | When it applies |
|---|---:|---|
| Low-volume / developing market | $500–$1,500 | Secondary markets, rural routes, limited demand, or early-market testing |
| Standard metro / reliable coverage | $1,500–$4,000 | Normal planning range when enough profitable work can be routed consistently |
| High-demand / specialized market | $4,000–$8,000 | Dense metros, urgent coverage lanes, specialized skills, and strong client pricing |

Actual income lift depends on client bill rate, negotiated tech payout, route density, location, urgency premium, repeat volume, QA quality, closeout reliability, and how much work Already Here LLC can push through the technician.

## Dispatch Logic

The matcher does not automatically assign the highest-skilled available technician. It uses right-fit dispatch.

| Work type | Preferred assignment |
|---|---|
| Simple or mediocre work | Basic/intermediate right-fit tech, preserving senior capacity |
| Standard field work | Intermediate field tech or specialist when margin supports it |
| Complex/sensitive work | Advanced specialist or lead-qualified technician |
| Larger project | Project lead plus right-fit field/support techs |
| Multi-state rollout | Multi-state lead plus local right-fit technicians in each market |

Senior technicians should become team leads, project leads, trainers, or state/region coordinators when the project size and margin justify it. Networking and combining technicians expands the database, creates team depth, and reduces dependence on one operator.

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

This means deployment must pass typecheck, lint, revenue-model tests, dispatch matching tests, and the production Next.js build.

See `docs/deployment.md` and `docs/oracle-schema.md`.

## Security Rule

No private API keys, credentials, payment secrets, cloud credentials, or tokens belong in client-side code or committed files. Use Vercel environment variables and Oracle secret storage.

## Lead Mesh Compliance Rule

This system does not bypass logins, CAPTCHAs, robots policies, account terms, or platform access controls. Opportunity intake must come from authorized email, official portals, public procurement notices, partner channels, or manual review of public listings. High-risk actions such as bid submission, counter submission, email outreach, credential changes, payments, and contract acceptance require manual approval.

## Operating Model

Morning work funds the system. The system removes Stephen as the bottleneck by capturing technician capacity, QA evidence, repeat clients, and dispatch margin.
