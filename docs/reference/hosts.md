---
status: current
last_verified: 2026-09-18
---

# Hosts, ports, and paths

The single place for machine names, addresses, ports, on-disk paths, and service names. Other docs link here instead of repeating them. Verified live over NetBird SSH on 2026-09-18 (see [status](../status.md)). Rig 2 isn't listed yet because it's still being built.

## Machines

| Host | NetBird IP | Hostname | Role | OS / hardware |
|---|---|---|---|---|
| EC2 gateway | `100.75.172.167` | `ip-172-31-42-43` | Public TLS entry point, admission gateway | Ubuntu 24.04, AWS m5.large |
| GPU rig (Rig 1) | `100.75.123.203` | `ocs-intelligence-rig` | llama.cpp workers, orchestrator, Open WebUI | Ubuntu 24.04.4, ASUS B250 Mining Expert, GTX 1070s ([hardware](../architecture/hardware.md)) |

Public name: `ai.opencodingsociety.com`, which resolves to EC2. SSH to either host goes through NetBird ([how](../guides/netbird-access.md)).

## Ports

| Host | Bind | Port | Service | Reachable from |
|---|---|---:|---|---|
| EC2 | `0.0.0.0` | 80, 443 | Nginx (`llm-relay` site) | Internet |
| EC2 | `127.0.0.1` | 9100 | `ocs-gateway` (admission gateway) | EC2 only (Nginx) |
| Rig | `0.0.0.0` | 9000 | `ocs-orchestrator` | NetBird peers (no firewall rule yet, see [threat model](../security/threat-model.md)) |
| Rig | `127.0.0.1` | 8081 | `ocs-llama-a` (Worker A, `qwen3.8:27b`) | Rig only |
| Rig | `127.0.0.1` | 8082 | `ocs-llama-b` (Worker B, `qwen2.5:0.5b`) | Rig only |
| Rig | — | 3000 | Open WebUI (Docker) | NetBird (Nginx `/` proxies to it) |

## systemd services

| Host | Unit | Repo copy |
|---|---|---|
| EC2 | `ocs-gateway.service` | [`infra/ec2/ocs-gateway.service`](../../infra/ec2/ocs-gateway.service) |
| Rig | `ocs-llama-a.service` | [`infra/rig/ocs-llama-a.service`](../../infra/rig/ocs-llama-a.service) |
| Rig | `ocs-llama-b.service` | [`infra/rig/ocs-llama-b.service`](../../infra/rig/ocs-llama-b.service) |
| Rig | `ocs-orchestrator.service` | [`infra/rig/ocs-orchestrator.service`](../../infra/rig/ocs-orchestrator.service) |
| Rig | `ollama.service` | not in repo; **stopped**, kept as the fallback path |

## Paths on disk

### EC2

| Path | What |
|---|---|
| `/opt/ocs-gateway/` | Gateway code + `.venv` (installed from PyPI) |
| `/etc/ocs-gateway/gateway.env` | Gateway env, mode `0600` (template: [`infra/ec2/gateway.env.template`](../../infra/ec2/gateway.env.template)) |
| `/var/lib/ocs-gateway/` | Gateway state dir |
| `/etc/nginx/sites-available/llm-relay` | Live Nginx site (repo copy: [`infra/ec2/llm-relay-nginx.conf`](../../infra/ec2/llm-relay-nginx.conf)) |
| `/etc/nginx/sites-available/llm-relay.bak.20260918T044602Z` | Nginx backup from before the gateway went live |
| `/etc/letsencrypt/live/ai.opencodingsociety.com/` | TLS certificate (Certbot) |

### Rig

| Path | What |
|---|---|
| `/usr/local/cuda-12.6/` | CUDA 12.6 toolkit (supports the GTX 1070's `sm_61`) |
| `/opt/llama.cpp/src/build/` | llama.cpp build. **Don't delete:** the installed binary's RUNPATH points here. |
| `/opt/llama.cpp/bin/` | `llama-server`, `llama-bench` |
| `/srv/ocs-intelligence/models/` | GGUF symlinks into Ollama's blob store |
| `/usr/share/ollama/.ollama/models/blobs/` | The actual model files |
| `/etc/ocs-intelligence/worker-{a,b}.env` | Worker env, mode `0600` (templates: [`infra/rig/`](../../infra/rig/)) |
| `/var/lib/ocs-intelligence/` | Worker state dir |
| `/opt/ocs-orchestrator/` | Orchestrator code + `.venv` (`--system-site-packages`, Ubuntu packages) |
| `/etc/ocs-orchestrator/orchestrator.env` | Orchestrator env, mode `0600` |
| `/var/lib/ocs-orchestrator/` | Orchestrator state dir |

### Model files

| Symlink in `/srv/ocs-intelligence/models/` | Ollama blob | Size |
|---|---|---|
| `qwen3.8-27b-q4_k_m.gguf` | `sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` | 16,810,714,464 B |
| `qwen2.5-0.5b.gguf` | `sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515` | ~380 MB |
