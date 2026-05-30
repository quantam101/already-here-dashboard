---
title: D-ASI Kernel v4.0.0-ENTERPRISE
emoji: 🛰️
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: true
---

# Declarative Autonomous Swarm Intelligence (D-ASI) — v4.0.0-ENTERPRISE

Production release of the Declarative Autonomous Swarm Intelligence framework.
Event-Driven Actor Matrix orchestrating a 4-agent VHLL Directed Acyclic Graph
(orchestrator_router → context_distiller → execution_unit → adversarial_critic)
with hard zero-placeholder policy enforcement.

## Deploy to Hugging Face Spaces

1. Create a new Space → **Docker** SDK.
2. Push these 4 files to the repository root: `Dockerfile`, `requirements.txt`,
   `agent_manifest.yaml`, `main.py` (this `README.md` is optional).
3. In Space → Settings → Repository secrets, add **`HF_TOKEN`** with a token
   that has Inference API access.
4. The Space builds and exposes the kernel on port 7860.

## Endpoints

| Method | Path                  | Purpose                                       |
|--------|-----------------------|-----------------------------------------------|
| GET    | `/health`             | Kernel vitality + current matrix step         |
| GET    | `/matrix/telemetry`   | Full live in-memory state + telemetry stream  |
| POST   | `/matrix/execute`     | Queue a directive for the 4-stage pipeline    |

### Smoke test (after deploy)

```bash
SPACE="https://YOUR_USER-YOUR_SPACE.hf.space"

curl -X POST "$SPACE/matrix/execute" \
     -H "Content-Type: application/json" \
     -d '{"directive": "Generate production configuration schema for zero-trust API routing infrastructure."}'

curl -X GET "$SPACE/matrix/telemetry"
```

## Local verification

```bash
HF_TOKEN=hf_xxx uvicorn main:app --host 0.0.0.0 --port 7860
curl http://127.0.0.1:7860/health
```

## Security policy

`SEC_ZERO_PLACEHOLDER_POLICY` blocks any node output matching
`(?i)(\.\.\.|//\s*todo|/\*\s*insert|todo:|<placeholder>|missing_logic)` and
forces up to 3 re-renders before halting the pipeline with
`engine_status=HALTED_ON_SECURITY_VIOLATION`.

## Operational profile (manifest)

- Primary LLM: `deepseek-ai/DeepSeek-V4-Flash`
- Fallback LLM: `Qwen/Qwen2.5-Coder-72B-Instruct`
- Temperature: `0.1`
- Max token budget: `3072`
- Circuit breaker threshold: `3`

Models can be substituted by editing `agent_manifest.yaml`.

## Transaction log

Append-only NDJSON written to `/tmp/dasi_transaction.log` — one entry per
stage completion or pipeline abort.
