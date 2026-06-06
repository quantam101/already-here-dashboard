# Already Here Field Network OS

Owned by Already Here LLC.

This repository contains the production PWA foundation for the Already Here LLC technician network, dispatch command center, retainer tracker, deterministic matching engine, offline queue, and audit workflow.

## Current Capabilities

- Mobile-first Next.js PWA shell.
- Technician opt-in intake workflow.
- Local IndexedDB persistence.
- Offline failover state indicator.
- Deterministic technician matching engine.
- Work order creation and match ranking.
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
