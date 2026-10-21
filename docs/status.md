---
status: current
last_verified: 2026-10-19
---

# Status

What is running **right now** and what's broken. This is the only page for time-sensitive state. Everything else lives in the linked docs. EC2 was last verified live over NetBird SSH on **2026-09-18**. Rig 1 was inspected read-only and Rig 2 was checked and changed over NetBird SSH on **2026-10-19** ([evidence](../evidence/captures/2026-10-19-rig2-ninth-gpu-driver-580.md)).

**How it works:** [architecture overview](./architecture/overview.md) · **Where things are:** [hosts](./reference/hosts.md), [configuration](./reference/configuration.md), [hardware](./architecture/hardware.md) · **How we got here:** [deployment log](../evidence/captures/2026-09-18-rig1-deployment-log.md) · **What's next:** [roadmap](./project/roadmap.md)

## Components

| Component | Status |
|---|---|
| CUDA 12.6 toolkit on rig (`sm_61`/Pascal support) | ✅ Installed, verified |
| `llama.cpp` built with CUDA backend | ✅ Built. Rig 1 now has 8 GPUs, driver 580.178.04 (2026-10-19) |
| Model symlinks (`/srv/ocs-intelligence/models/`) | ✅ Done |
| Worker A (`qwen3.8:27b`, 4 GPUs, port 8081) | ✅ Running (2026-10-19) |
| Worker B (`gemma4:26b`, 4 GPUs, port 8082) | ✅ Running (2026-10-19). Changed from `qwen2.5:0.5b` on 2 GPUs on 2026-10-16 (config file date); who changed it and its speed aren't recorded. Docs describing the 5 + 2 split ([workers](./architecture/workers.md), [0003](./decisions/0003-5-plus-2-gpu-split.md)) predate this |
| Ollama (old single-worker path) | 🛑 Stopped (freed for the two new workers) |
| FastAPI orchestrator (on the rig, `:9000`) | ✅ Running, healthy; routes both models |
| EC2 admission gateway (`127.0.0.1:9100`) | ✅ Running; auth + wait line, then proxy to the rig |
| EC2 Nginx `/v1/` route | ✅ Live → localhost gateway; `/` still Open WebUI |
| Open WebUI | ✅ Running (port 3000), version 0.11.3. Two model connections: Rig 1 via the gateway, Rig 2 direct (2026-10-15). Admin password reset 2026-10-15 ([evidence](../evidence/captures/2026-10-15-open-webui-admin-password-reset.md)) |
| Rig 2 worker (`qwen3.6:35b-a3b` MoE, all 9 GPUs, port 8081) | ✅ Running, healthy (2026-10-19). ~27.7 tok/s generation, 2 slots × 262k context ([0009](./decisions/0009-rig2-moe-behind-open-webui.md)). Ninth GPU added and driver moved to 580 that day ([evidence](../evidence/captures/2026-10-19-rig2-ninth-gpu-driver-580.md)) |
| Rig 2 orchestrator (`:9000`, one model) | ✅ Running, ready (2026-10-19). Accepts the Open WebUI key and a temporary operator key, not the student key |
| Open WebUI → Rig 2 | ✅ Connected (2026-10-15): second OpenAI connection `http://100.75.127.192:9000/v1` with its own key ([evidence](../evidence/captures/2026-10-15-open-webui-rig2-connection.md)). The team saw all three models in the dropdown as a regular user on 2026-10-16 ([screenshot](../evidence/sprint4/2026-10-16-open-webui-model-picker.png)) |
| `ai2.opencodingsociety.com` | 🛑 Not pursued. A teammate's TLS cert and Nginx site exist on EC2 (answers `301` to itself). Left untouched |
| **Open issue:** Worker A throughput | ⚠️ 8.7 tok/s, *slower* than the 12.5 tok/s baseline. NCCL deferred. See below. |

## Open issue: Worker A is slower than baseline

This is the one thing standing between "technically works" and "actually done." Measured numbers are in the [deployment log](../evidence/captures/2026-09-18-rig1-deployment-log.md#measured-performance-live-worker-direct). Two candidate explanations, not yet root-caused:

1. **Missing NCCL.** The build warned that without NCCL, multi-GPU reductions fall back to a slower path. Installing NCCL would need ~474 MB of downloads, and only CUDA 13.3/13.4-linked packages are available, not CUDA 12.6 (a version-mismatch risk). **NCCL is deferred** until after the public `/v1/` path is live.
2. **One short, cold request isn't representative.** Only one very short prompt went through Worker A. `llama-bench` (already built and installed) would give a cleaner, repeatable number that separates decode speed from prompt processing and warm-up.

**Neither has been tried yet.** Until this is resolved, the 5+2 split is a regression on the model most students will actually use ([decision 0003](./decisions/0003-5-plus-2-gpu-split.md)).

## Other things worth knowing

- **NetBird SSH to EC2 fails** (2026-10-20, three tries): SSO succeeds, then `ssh handshake failed: ... i/o timeout`. The peer is connected peer-to-peer, port 22 answers with `NetBird-SSH-Server-0.78.1`, and the public API is up (`/healthz` 200). The same client (0.77.1) reaches both rigs, which run NetBird 0.80.0. Until it's fixed, EC2 can only be changed through AWS. Its instance type (`m5.large`, from the 2026-09-16 audit) couldn't be re-checked.
- **Rig 1's Ethernet links at 100 Mb/s**; Rig 2 gets 1 Gb/s on the same onboard port (2026-10-20, [evidence](../evidence/captures/2026-10-20-rig-hardware-inventory.md)). Likely a cable or switch port. The second SSD the team reports in each rig isn't visible to the OS.
- **Both rigs take kernel updates automatically** (unattended upgrades). On 2026-10-19 Rig 2 rebooted into a new kernel that its prebuilt 550 driver didn't cover and served on CPU until the driver was moved to 580 with DKMS, the setup Rig 1 already had ([evidence](../evidence/captures/2026-10-19-rig2-ninth-gpu-driver-580.md)). After any rig reboot, check `nvidia-smi` and the worker log for `no usable GPU found`.
- **Rig disk usage grew by ~4.3 GB.** That's `apt`'s package cache from the CUDA install (`/var/cache/apt/archives/`). It's safe to clear with `apt-get clean`. The rig had 139 GB free on 2026-10-20, so this isn't urgent.
- **EC2 disk is about 61% used** (~19 GB free of 48 GB) after removing the unused Kasm 1.16.0.
- **Ollama is stopped, not removed.** See [runbook: roll back](./operations/runbook.md#6-roll-back).
- **Open WebUI** (2026-10-15) has two enabled OpenAI connections. `https://ai.opencodingsociety.com/v1` serves Rig 1's models through the EC2 gateway and wait line. `http://100.75.127.192:9000/v1` serves Rig 2's model straight from its orchestrator, **skipping the wait line**. Its Ollama connections are disabled. Open WebUI 0.11.3 keeps only the **first** connection that offers a given model ID, so two rigs serving the same model name would never load-balance there.
- Rig port 9000 is reachable over NetBird from EC2 and `outbound-only` operator peers only (NetBird policies applied 2026-10-15, [evidence](../evidence/captures/2026-10-15-netbird-access-policies.md)). Operators can still skip the wait line.
- **Installed package versions:** the rig orchestrator runs on Ubuntu's `python3-fastapi` 0.101.0, `python3-uvicorn` 0.27.1, and `python3-httpx` 0.26.0 (PyPI is unreachable from the rig). The EC2 gateway venv came from PyPI (FastAPI 0.141.1).
- **Copilot Chat** hasn't been signed in from a student machine yet. The API path is verified.

## Next steps

In rough priority order. The full list is in the [roadmap](./project/roadmap.md#planned-not-built).

1. **Rotate the student key:** the current shared key is a guessable string.
1. **NCCL / Worker A throughput:** deferred.
2. **Per-student API keys:** still one shared Bearer key. Needed so one laptop can't fill the wait line.
3. **Housekeeping:** `apt-get clean` on the rig.
4. **Copilot Chat** from a student machine ([using the API](./guides/using-the-api.md)).

## Updating this page

When you check the live system, update the tables above and `last_verified`. Record what you measured or changed as a new dated file in [`evidence/`](../evidence/evidence.md) and link it here. Don't paste configs or inventories here. Link to their canonical docs ([conventions](./conventions.md#the-rules)).
