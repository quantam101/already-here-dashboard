# Already Here Field Network OS

Owned by Already Here LLC.

This repository contains the production PWA foundation for the Already Here LLC technician network, dispatch command center, retainer tracker, compliant opportunity mesh, deterministic matching engine, offline queue, and audit workflow.

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
- Audit event capture.
- Sync queue capture for future Oracle backend sync.
- Strict TypeScript configuration.
- CI verification workflow.
- Hardened HTTP response headers.

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

See `docs/deployment.md` and `docs/oracle-schema.md`.

## Security Rule

No private API keys, credentials, payment secrets, cloud credentials, or tokens belong in client-side code or committed files. Use Vercel environment variables and Oracle secret storage.

## Lead Mesh Compliance Rule

This system does not bypass logins, CAPTCHAs, robots policies, account terms, or platform access controls. Opportunity intake must come from authorized email, official portals, public procurement notices, partner channels, or manual review of public listings. High-risk actions such as bid submission, counter submission, email outreach, credential changes, payments, and contract acceptance require manual approval.
