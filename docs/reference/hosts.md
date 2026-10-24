---
status: current
last_verified: 2026-10-19
---

# Hosts, ports, and paths

The single place for machine names, addresses, ports, on-disk paths, and service names. Other docs link here instead of repeating them. EC2 verified live over NetBird SSH on 2026-09-18, Rig 1 and Rig 2 on 2026-10-19, their hardware on 2026-10-20 (see [status](../status.md)).

## Machines

| Host | NetBird IP | LAN IP | Hostname | Role | OS / hardware |
|---|---|---|---|---|---|
| EC2 gateway | `100.75.172.167` | — | `ip-172-31-42-43` | Public TLS entry point, admission gateway | Ubuntu 24.04, AWS m5.large |
| GPU rig (Rig 1) | `100.75.123.203` | `192.168.8.112` | `ocs-intelligence-rig` | llama.cpp workers, orchestrator, Open WebUI | Ubuntu 24.04.4, ASUS B250 Mining Expert, 8 × GTX 1070 ([hardware](../architecture/hardware.md)) |
| GPU rig (Rig 2) | `100.75.127.192` | `192.168.8.213` | `ocs-intelligence-rig2` | One llama.cpp worker (`qwen3.6:35b-a3b`), orchestrator | Ubuntu 24.04.3, Python 3.12.3, ASUS B250 Mining Expert, 1 × GTX 1080 Ti + 8 × GTX 1070 ([hardware](../architecture/hardware.md)) |

Public name: `ai.opencodingsociety.com`, which resolves to EC2. (`ai2.opencodingsociety.com` also resolves to EC2 and has a cert there, but isn't used: [status](../status.md).) SSH to either host goes through NetBird ([how](../guides/netbird-access.md)). LAN IPs are DHCP leases from the Flint 2 on the OCS LAN, seen on both rigs' `enp0s31f6` on 2026-10-22 and 2026-10-23 ([network](../architecture/network.md#the-ocs-lan)); the routing playbook says they're reserved on the router.

## Ports

| Host | Bind | Port | Service | Reachable from |
|---|---|---:|---|---|
| EC2 | `0.0.0.0` | 80, 443 | Nginx (`llm-relay` site) | Internet |
| EC2 | `127.0.0.1` | 9100 | `ocs-gateway` (admission gateway) | EC2 only (Nginx) |
| Rig | `0.0.0.0` | 9000 | `ocs-orchestrator` | EC2 and `outbound-only` peers over NetBird ([policies](../architecture/network.md#access-policies)), **and anything on the OCS LAN**, other class groups included: `ufw` was inactive on both rigs on 2026-10-22 |
| Rig | `127.0.0.1` | 8081 | `ocs-llama-a` (Worker A, `qwen3.8:27b`, 4 GPUs) | Rig only |
| Rig | `127.0.0.1` | 8082 | `ocs-llama-b` (Worker B, `gemma4:26b`, 4 GPUs, since 2026-10-16) | Rig only |
| Rig | — | 3000 | Open WebUI (Docker). Its OpenAI connections: `https://ai.opencodingsociety.com/v1` (Rig 1 via the gateway) and `http://100.75.127.192:9000/v1` (Rig 2) | EC2 and `outbound-only` peers over NetBird (Nginx `/` proxies to it) |
| Rig 2 | `0.0.0.0` | 9000 | `ocs-orchestrator` (one model) | EC2, Rig 1, and `outbound-only` peers over NetBird ([policies](../architecture/network.md#access-policies)), **and anything on the OCS LAN** (same as Rig 1) |
| Rig 2 | `127.0.0.1` | 8081 | `ocs-llama` (`qwen3.6:35b-a3b`, all 9 GPUs) | Rig 2 only |

## systemd services

| Host | Unit | Repo copy |
|---|---|---|
| EC2 | `ocs-gateway.service` | [`infra/ec2/ocs-gateway.service`](../../infra/ec2/ocs-gateway.service) |
| Rig | `ocs-llama-a.service` | [`infra/rig/ocs-llama-a.service`](../../infra/rig/ocs-llama-a.service) |
| Rig | `ocs-llama-b.service` | [`infra/rig/ocs-llama-b.service`](../../infra/rig/ocs-llama-b.service) |
| Rig | `ocs-orchestrator.service` | [`infra/rig/ocs-orchestrator.service`](../../infra/rig/ocs-orchestrator.service) |
| Rig | `ollama.service` | not in repo; **stopped**, kept as the fallback path |
| Rig 2 | `ocs-llama.service` | [`infra/rig2/ocs-llama.service`](../../infra/rig2/ocs-llama.service) |
| Rig 2 | `ocs-orchestrator.service` | [`infra/rig2/ocs-orchestrator.service`](../../infra/rig2/ocs-orchestrator.service) |
| Rig 2 | `ollama.service` | not in repo; disabled by `setup.sh` (it was only used to pull the model) |

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
| `/var/lib/docker/volumes/open-webui/_data/webui.db` | Open WebUI's database, including its connection settings (`config` table). Backup from before the Rig 2 connection: `webui.db.bak-20261015` next to it |
| `/var/lib/ocs-orchestrator/` | Orchestrator state dir |

### Rig 2

Same layout as Rig 1 for CUDA (`/usr/local/cuda-12.6/`), llama.cpp (`/opt/llama.cpp/`, commit `b76b13379`), models (`/srv/ocs-intelligence/models/`, same `qwen3.8-27b-q4_k_m.gguf` blob), and the orchestrator (`/opt/ocs-orchestrator/`, `/etc/ocs-orchestrator/orchestrator.env`, `/var/lib/ocs-orchestrator/`). Differences:

| Path | What |
|---|---|
| `/etc/ocs-intelligence/worker.env` | The one worker's env, mode `0600`, written by [`setup.sh`](../../infra/rig2/setup.sh) (template: [`infra/rig2/worker.env.template`](../../infra/rig2/worker.env.template)) |
| `/opt/ocs-orchestrator/.venv` | Installed from **PyPI**: Rig 2 can reach it, Rig 1 can't |
| `/home/ocs/OCS-Intelligence/` | A clone of this repo, owned by user `ocs` |
| `/srv/ocs-intelligence/models/qwen3.6-35b-a3b-ud-q4_k_xl.gguf` | The served model: a plain file from Hugging Face (`unsloth/Qwen3.6-35B-A3B-GGUF`, 22,360,456,160 B, SHA-256 `707a55a8…4f450`), not an Ollama blob |
| `/root/ocs-deploy/` | The orchestrator bundle copied in on 2026-10-15, the temporary `PUBLIC_API_KEYS` value, and `worker.env.bak-qwen3.8` (the env from before the model switch) |

### Model files

| Symlink in `/srv/ocs-intelligence/models/` | Ollama blob | Size |
|---|---|---|
| `qwen3.8-27b-q4_k_m.gguf` | `sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d` | 16,810,714,464 B |
| `qwen2.5-0.5b.gguf` | `sha256-c5396e06af294bd101b30dce59131a76d2b773e76950acc870eda801d3ab0515` | ~380 MB |
