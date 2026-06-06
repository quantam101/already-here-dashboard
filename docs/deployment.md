# Deployment Plan

## Current Production Assets

- Vercel team: Already Here LLC projects.
- Vercel project available: already-here-llc.
- GitHub repo used for current build: quantam101/already-here-dashboard.

## Target Domains

- field.alreadyherellc.com: primary app.
- tech.alreadyherellc.com: technician intake path.
- clients.alreadyherellc.com: client request path.
- api.alreadyherellc.com: Oracle backend API.
- status.alreadyherellc.com: health page.

## Vercel Role

Vercel hosts the Next.js PWA, dashboard, installable mobile web app, offline UI, and static assets. All private API calls must go through server-side routes or the Oracle backend.

## Oracle Role

Oracle hosts the backend API, production database, worker queue, scheduled jobs, backups, health checks, document storage, and future private model workers.

## GoDaddy Role

GoDaddy controls DNS only. Use CNAME records for Vercel-hosted subdomains and the Oracle load balancer or API endpoint for api.alreadyherellc.com.

## Required Environment Variables

Do not commit values. Configure them only in Vercel and Oracle secret storage.

- ORACLE_API_BASE_URL
- ORACLE_API_SERVICE_TOKEN
- APP_ENV
- SYNC_ENABLED
- AUDIT_LOG_ENABLED

## Acceptance Gate

Production is not complete until the app builds in CI, deploys to Vercel, opens on mobile, stores technician data locally, ranks matches offline, queues sync events, and connects to Oracle without exposing secrets.
