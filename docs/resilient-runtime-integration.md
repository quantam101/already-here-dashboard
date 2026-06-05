# Shared Resilient Runtime Integration

## Architecture

The resilient runtime is integrated directly into `already-here-dashboard` as the authoritative backend package.

```text
One shared resilient runtime package
        ↓
Dashboard integrates it directly
        ↓
Other repos use thin adapters/API calls only where it adds operational value
```

## Dashboard endpoints

Base path:

```text
/api/resilient-runtime
```

Endpoints:

```text
GET  /api/resilient-runtime/health
POST /api/resilient-runtime/execute
GET  /api/resilient-runtime/events
POST /api/resilient-runtime/match-technicians
```

## Runtime guarantees

- Local deterministic execution path.
- No cloud API dependency for core validation.
- No arbitrary generated-code execution.
- SQLite-backed event and result logging.
- Idempotency cache for repeated execution requests.
- Declarative operation allow-list instead of code-string execution.

## Runtime boundaries

This runtime does not embed live secrets in source code. Production secrets must be injected through environment variables, GitHub Actions secrets, host-level secrets, or a proper secrets manager.

## Adapter strategy for other repositories

Do not copy the runtime engine into other repositories. Use one of these integration options:

1. HTTP API adapter that calls dashboard endpoints.
2. Lightweight client module that posts validation or matching requests to `/api/resilient-runtime`.
3. Export/import job for offline reports when a repo does not need live runtime access.

## Recommended repo usage

| Repo | Integration type |
| --- | --- |
| `already-here-dashboard` | Core runtime owner |
| `lifelong-catch-correct` | Thin adapter for labs, evidence validation, replay checks |
| `soc-operator-training-platform` | Thin adapter for scoring and local validation |
| `unified-publisher-operator` | Thin adapter for content QA and workflow validation |
| `alreadyhere-site` | API-only status display, no embedded runtime |
| `already-here-llc` | API-only status display, no embedded runtime |
| `ai-profit-suite` / `ai-profit-suite-pro` | API-only validator or preflight adapter |
| `profitengine-v4` / `profitenginev5` / `tradegate2` | Strict adapter only with additional financial risk controls |

## Example execute request

```json
{
  "query": "validate revenue not null and revenue range 0 to 100000 then describe",
  "records": [
    {"customer": "A", "revenue": 1200, "state": "AZ"},
    {"customer": "B", "revenue": 3000, "state": "AZ"}
  ],
  "schema_context": {"revenue": "number", "state": "str"},
  "session_id": "dashboard"
}
```

## Example technician matching request

```json
{
  "work_order": {
    "city": "Phoenix",
    "state": "AZ",
    "pay_rate": 85,
    "minimum_hours": 2,
    "required_skills": ["smart hands", "data center", "network support"]
  },
  "technicians": [
    {
      "id": "sf",
      "name": "Stephen Franklin / Already Here LLC",
      "city": "Phoenix",
      "state": "AZ",
      "accepts_1099": true,
      "minimum_effective_rate": 65,
      "minimum_hours": 2,
      "availability": "priority",
      "skills": ["smart hands", "data center", "network support", "printer", "pos"]
    }
  ],
  "min_skill_ratio": 0.55
}
```
