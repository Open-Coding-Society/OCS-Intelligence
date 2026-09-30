---
status: current
last_verified: 2026-09-29
---

# Configuration reference

Every environment variable, with its default taken from the code (`gateway/config.py`, `orchestrator/config.py`) and the templates in [`infra/`](../../infra/). Checked against the code on 2026-09-29. Real values live in `0600` env files on each host ([paths](./hosts.md#paths-on-disk)) and **never** in git.

## Client (`.env` on your machine)

Copy [`.env.example`](../../.env.example) to `.env`. Read by `scripts/demo.py`, `scripts/request.sh`, and `benchmark/`.

| Variable | Default | Meaning |
|---|---|---|
| `OCS_BASE_URL` | `https://ai.opencodingsociety.com/v1` | API base URL |
| `OCS_API_KEY` | — (required) | Student key. Ask an operator. |

## Admission gateway (EC2, `/etc/ocs-gateway/gateway.env`)

Template: [`infra/ec2/gateway.env.template`](../../infra/ec2/gateway.env.template).

| Variable | Default | Meaning |
|---|---|---|
| `UPSTREAM_URL` | `http://100.75.123.203:9000` | Rig orchestrator |
| `PUBLIC_API_KEYS` | empty | Comma-separated student keys. **If empty, any Bearer token is accepted.** Always set it. |
| `GROUP_A_MODEL_ALIAS` | `qwen3.8:27b` | Model name for lane A |
| `GROUP_B_MODEL_ALIAS` | `qwen2.5:0.5b` | Model name for lane B |
| `GROUP_A_INFLIGHT` | `1` | Lane A requests running at once |
| `GROUP_B_INFLIGHT` | `2` | Lane B requests running at once |
| `MAX_WAITERS_PER_WORKER` | `4` | Waiting requests per lane before a 429 |
| `KEEPALIVE_INTERVAL_SECONDS` | `15` | How often waiting streams get `: queued` |
| `CONNECT_TIMEOUT_SECONDS` | `5` | Connect timeout to the orchestrator |
| `UPSTREAM_TIMEOUT_SECONDS` | `3600` | Read timeout to the orchestrator |

What the lane numbers mean in practice: [gateway capacity](../architecture/gateway.md#capacity-what-survive-concurrent-requests-actually-means).

## Orchestrator (rig, `/etc/ocs-orchestrator/orchestrator.env`)

Template: [`infra/rig/orchestrator.env.template`](../../infra/rig/orchestrator.env.template).

| Variable | Default | Meaning |
|---|---|---|
| `GROUP_A_URL` | `http://127.0.0.1:8081` | Worker A |
| `GROUP_B_URL` | `http://127.0.0.1:8082` | Worker B |
| `GROUP_A_MODEL_ALIAS` | `qwen3.8:27b` | Model served by A |
| `GROUP_B_MODEL_ALIAS` | `qwen2.5:0.5b` | Model served by B |
| `WORKER_API_KEY` | empty | Secret the orchestrator sends to the workers (same value as in the worker env) |
| `PUBLIC_API_KEYS` | empty | Student keys accepted. **If empty, any Bearer token is accepted.** |
| `QUEUE_CAPACITY_PER_WORKER` | `16` | In-flight count above which the orchestrator returns 429 |
| `CONNECT_TIMEOUT_SECONDS` | `5` | Connect timeout to workers |
| `RESPONSE_HEADER_TIMEOUT_SECONDS` | `600` | Read timeout for blocking requests |
| `STREAM_IDLE_TIMEOUT_SECONDS` | `300` | Read timeout between stream chunks |
| `HEALTH_INTERVAL_SECONDS` | `5` | Worker health poll interval |

## Workers (rig, `/etc/ocs-intelligence/worker-*.env`)

Templates: [`infra/rig/worker-a.env.template`](../../infra/rig/worker-a.env.template), [`infra/rig/worker-b.env.template`](../../infra/rig/worker-b.env.template). Used by the `llama-server` command line in the systemd units.

| Variable | Worker A | Worker B | Meaning |
|---|---|---|---|
| `CUDA_VISIBLE_DEVICES` | GPUs 0–4 by UUID | GPUs 5–6 by UUID | Which cards the worker can use ([UUIDs](../architecture/hardware.md)) |
| `DEFAULT_MODEL_GGUF` / `SPEED_MODEL_GGUF` | `…/qwen3.8-27b-q4_k_m.gguf` | `…/qwen2.5-0.5b.gguf` | Model file |
| `DEFAULT_MODEL_ID` / `SPEED_MODEL_ID` | `qwen3.8:27b` | `qwen2.5:0.5b` | `--alias`, the public model name |
| `CONTEXT_SIZE` | `4096` | `8192` | `--ctx-size` |
| `TENSOR_SPLIT` | `1,1,1,1,1` | `1,1` | `--tensor-split` across the visible GPUs |
| `WORKER_API_KEY` | secret | same secret | `--api-key` |

Fixed flags in both units: `--n-gpu-layers 999 --split-mode layer --parallel 2 --cont-batching --flash-attn on --metrics --slots --warmup`. Why each worker is set up this way: [workers](../architecture/workers.md).
