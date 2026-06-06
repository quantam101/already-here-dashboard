# Oracle Backend Schema

Use this schema plan for the Oracle production database behind Already Here Field Network OS.

## Core Tables

- technicians: identity, contact, country, metro, travel radius, rate, availability, compliance, performance score, consent timestamp, referral code.
- technician_skills: many-to-one skill map for technician capability matching.
- clients: company, contact, segment, retainer status, monthly target.
- work_orders: client, title, location, metro, status, schedule, budget, estimated hours, urgency.
- work_order_skills: required skills per work order.
- assignments: work order to technician assignment state.
- referrals: technician/client referral tracking.
- closeouts: completion notes, evidence references, QA status.
- audit_logs: actor, action, entity type, entity id, timestamp.
- sync_queue: offline operations waiting for backend sync.
- system_health: API, database, worker, and sync health state.

## Index Requirements

- technicians by metro.
- technicians by compliance status.
- technician_skills by skill.
- work_orders by status.
- work_orders by metro.
- work_orders by scheduled date.
- sync_queue by unsynced created date.

## Security Requirements

- No public database access.
- Backend-only database credentials.
- Least-privilege service account.
- Daily backup policy.
- Separate read/write roles.
- Audit log writes are append-only from application code.
- File/document storage must be private by default.

## Sync Contract

Every offline action is recorded locally with operation, entity type, entity id, payload, and timestamp. The backend sync worker applies queued actions idempotently and marks them synced only after successful persistence.
