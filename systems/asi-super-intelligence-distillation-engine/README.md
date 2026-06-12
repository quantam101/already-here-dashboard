# ASI Super-Intelligence Distillation Engine

This is the standalone, local-first revenue-intelligence core for Already Here LLC. ASI is a product name for an orchestration and operational-intelligence engine. It is not a claim of AGI or autonomous superintelligence.

## Production Role

The engine normalizes revenue signals from email, dispatch platforms, public leads, procurement paths, vendor conversations, project opportunities, and field history into an owned intelligence layer.

It supports:

- $500 minimum daily field-revenue scoring.
- Contract, retainer, project/SOW, dispatch, procurement, and vendor-routing evaluation.
- Company, contact, opportunity, action, sync, and audit storage.
- Local SQLite WAL operation when cloud/API access is down.
- Approval-gated action drafts. It does not send, accept, submit, or modify external systems automatically.

## Run

```bash
cd systems/asi-super-intelligence-distillation-engine
python asi_master_engine.py --demo --db ./state_mesh_wal.db
```

## Test

```bash
cd systems/asi-super-intelligence-distillation-engine
python -m pytest -q
```

## Integration Pattern

The optimized architecture is standalone core plus adapters:

- `already-here-dashboard`: command panel, review queue, API endpoint, local field-network scoring.
- `already-here-llc`: public product/marketing surface and RFQ/intake path.
- `profitenginev5`: revenue automation connector and monetization workflows.
- Other repos: thin adapters only, not duplicate intelligence engines.

## Security Rule

Do not hard-code production API keys in source code or public client bundles. Use environment variables, platform secret stores, tenant-specific provisioning, least-privilege access, rotation, and audit logging.
