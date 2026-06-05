# Already Here Growth Command OS — Project Rules

## NO-PLACEHOLDER RULE
Placeholders are forbidden. All values must be real.

## Stack
- Backend: Python 3.11 FastAPI + SQLite (production) / MongoDB (dev)
- Frontend: React CRA + Tailwind
- Deployment: OCI Oracle Linux, Docker Compose, Caddy reverse proxy
- Domain: app.alreadyherellc.com

## Key constraints
- `max_cost_usd: 0` — no paid LLM calls
- All approval_required actions must return `{"approval_required": true}` — never auto-execute
- Security scan must pass before every commit
- Work order counteroffer: never reveal internal rate floor ($45) to clients — quote $65/hr only

## Context Mesh Engine — Token Optimization (Active)

Use the `dispatch_parallel_context` MCP tool when analyzing specific functions/classes.
Reduces token usage ~90% vs reading full files.

### When to use dispatch_parallel_context
- Analyzing a specific route handler, agent, or service in a large file
- Finding where a symbol is defined across the repo
- Getting dependency signatures without full implementations

### When to read files directly (no overhead)
- Files under 80 lines
- Config files: requirements.txt, docker-compose.yml, .env.example
- This CLAUDE.md and similar docs

### Search tools (fastest first)
| Task | Tool |
|------|------|
| Symbol extraction | `dispatch_parallel_context(repoPath, symbolName, "py")` |
| Cross-repo grep | `rg --smart-case pattern` |
| File discovery | `fd --type f pattern` |
