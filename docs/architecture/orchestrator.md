---
status: current
last_verified: 2026-09-18
---

# Orchestrator

A small FastAPI service on the rig that turns "a request for model X" into "a request to worker Y". Code: [`orchestrator/`](../../orchestrator/). Unit: [`infra/rig/ocs-orchestrator.service`](../../infra/rig/ocs-orchestrator.service). Code behavior checked on 2026-09-29; deployment facts are as of 2026-09-18.

## What it does

1. **Authenticates** the student Bearer key against `PUBLIC_API_KEYS` ([`auth.py`](../../orchestrator/auth.py)). This is a second check: the gateway already checked the key, but anyone who reaches `:9000` directly over NetBird is still checked here.
2. **Routes** by the `model` field ([`routing.py`](../../orchestrator/routing.py)): `qwen3.8:27b` → Worker A (`:8081`), `qwen2.5:0.5b` → Worker B (`:8082`). An unknown model gets a 404.
3. **Swaps keys.** It sends the worker-only `WORKER_API_KEY` to `llama-server` ([`proxy.py`](../../orchestrator/proxy.py)). Students never see the worker secret.
4. **Polls worker health** every `HEALTH_INTERVAL_SECONDS` via llama.cpp's `/health` ([`health.py`](../../orchestrator/health.py)). `ok`, `loading model`, and `no slot available` all count as healthy. Anything else, or no answer, is unhealthy, and requests get 503.
5. **Passes SSE through** without buffering, and stops streaming if the client disconnects.

## What it doesn't do

- **Queueing.** That's the [gateway's](./gateway.md) job. The orchestrator's `QUEUE_CAPACITY_PER_WORKER` (16) is a reject threshold, not a line. The public path never reaches it, because the gateway admits at most 1 or 2 per model.
- **Load balancing across replicas.** Each model has exactly one worker today. The broker planned in the [roadmap](../project/roadmap.md) would add health-aware scheduling across rigs.

## Endpoints

`/healthz` (process up), `/readyz` (at least one worker healthy), `/v1/models` (built from its own config, not asked of the workers), `/v1/chat/completions`. Details: [API reference](../reference/api.md#rig-internal-endpoints-not-public).

## Deployment notes

- It runs **on the rig**, not EC2, so the rig-side hop to the workers stays on localhost. NetBird carries only gateway → orchestrator traffic.
- PyPI is blocked on the school network, so its venv uses Ubuntu's `python3-fastapi`, `python3-uvicorn`, and `python3-httpx` through `--system-site-packages`. The unit runs `python -m uvicorn`. See [deploy the rig](../operations/deploy-rig.md).
- It binds `0.0.0.0:9000` so EC2 can reach it over NetBird. No firewall limits it to the EC2 peer yet ([threat model](../security/threat-model.md)).
