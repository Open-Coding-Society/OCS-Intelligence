---
status: current
last_verified: 2026-09-18
---

# Status

What is running **right now** and what's broken. This is the only page for time-sensitive state. Everything else lives in the linked docs. Rig 1 and EC2 were last verified live over NetBird SSH on **2026-09-18**. Rig 2 state is as reported by the team on 2026-09-29.

**How it works:** [architecture overview](./architecture/overview.md) · **Where things are:** [hosts](./reference/hosts.md), [configuration](./reference/configuration.md), [hardware](./architecture/hardware.md) · **How we got here:** [deployment log](../evidence/captures/2026-09-18-rig1-deployment-log.md) · **What's next:** [roadmap](./project/roadmap.md)

## Components

| Component | Status |
|---|---|
| CUDA 12.6 toolkit on rig (`sm_61`/Pascal support) | ✅ Installed, verified |
| `llama.cpp` built with CUDA backend | ✅ Built, all 7 GPUs detected |
| Model symlinks (`/srv/ocs-intelligence/models/`) | ✅ Done |
| Worker A (`qwen3.8:27b`, 5 GPUs, port 8081) | ✅ Running, healthy |
| Worker B (`qwen2.5:0.5b`, 2 GPUs, port 8082) | ✅ Running, healthy |
| Ollama (old single-worker path) | 🛑 Stopped (freed for the two new workers) |
| FastAPI orchestrator (on the rig, `:9000`) | ✅ Running, healthy; routes both models |
| EC2 admission gateway (`127.0.0.1:9100`) | ✅ Running; auth + wait line, then proxy to the rig |
| EC2 Nginx `/v1/` route | ✅ Live → localhost gateway; `/` still Open WebUI |
| Open WebUI | ✅ Still running (port 3000, untouched); reports version 0.11.3 |
| Rig 2 | 🚧 Being built; nothing deployed (team, 2026-09-29) |
| **Open issue:** Worker A throughput | ⚠️ 8.7 tok/s, *slower* than the 12.5 tok/s baseline. NCCL deferred. See below. |

## Open issue: Worker A is slower than baseline

This is the one thing standing between "technically works" and "actually done." Measured numbers are in the [deployment log](../evidence/captures/2026-09-18-rig1-deployment-log.md#measured-performance-live-worker-direct). Two candidate explanations, not yet root-caused:

1. **Missing NCCL.** The build warned that without NCCL, multi-GPU reductions fall back to a slower path. Installing NCCL would need ~474 MB of downloads, and only CUDA 13.3/13.4-linked packages are available, not CUDA 12.6 (a version-mismatch risk). **NCCL is deferred** until after the public `/v1/` path is live.
2. **One short, cold request isn't representative.** Only one very short prompt went through Worker A. `llama-bench` (already built and installed) would give a cleaner, repeatable number that separates decode speed from prompt processing and warm-up.

**Neither has been tried yet.** Until this is resolved, the 5+2 split is a regression on the model most students will actually use ([decision 0003](./decisions/0003-5-plus-2-gpu-split.md)).

## Other things worth knowing

- **Rig disk usage grew by ~4.3 GB.** That's `apt`'s package cache from the CUDA install (`/var/cache/apt/archives/`). It's safe to clear with `apt-get clean`. The rig has 151 GB free, so this isn't urgent.
- **EC2 disk is about 61% used** (~19 GB free of 48 GB) after removing the unused Kasm 1.16.0.
- **Ollama is stopped, not removed.** See [runbook: roll back](./operations/runbook.md#6-roll-back).
- **Open WebUI was never touched.** Direct Ollama-backed chat in WebUI will fail while Ollama is stopped. WebUI traffic still bypasses the EC2 wait line.
- **No firewall rule limits rig port 9000 to the EC2 NetBird IP**, so a NetBird peer can still skip the wait line ([threat model](./security/threat-model.md)).
- **Installed package versions:** the rig orchestrator runs on Ubuntu's `python3-fastapi` 0.101.0, `python3-uvicorn` 0.27.1, and `python3-httpx` 0.26.0 (PyPI is unreachable from the rig). The EC2 gateway venv came from PyPI (FastAPI 0.141.1).
- **Copilot Chat** hasn't been signed in from a student machine yet. The API path is verified.

## Next steps

In rough priority order. The full list is in the [roadmap](./project/roadmap.md#planned-not-built).

1. **NCCL / Worker A throughput:** deferred.
2. **Per-student API keys:** still one shared Bearer key. Needed so one laptop can't fill the wait line.
3. **Housekeeping:** `apt-get clean` on the rig. Optionally restrict rig port 9000 to the EC2 NetBird IP.
4. **Copilot Chat** from a student machine ([using the API](./guides/using-the-api.md)).

## Updating this page

When you check the live system, update the tables above and `last_verified`. Record what you measured or changed as a new dated file in [`evidence/`](../evidence/evidence.md) and link it here. Don't paste configs or inventories here. Link to their canonical docs ([conventions](./conventions.md#the-rules)).
