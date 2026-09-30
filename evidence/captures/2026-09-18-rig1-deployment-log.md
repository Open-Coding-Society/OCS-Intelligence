---
date: 2026-09-18
---

# Rig 1 deployment log (2026-09-17 – 2026-09-18)

What was done to bring up the llama.cpp workers, orchestrator, public `/v1/` path, and EC2 gateway, with the build details and the first measured speeds. Moved unchanged from `docs/status.md` §3, §4.5, and §5 when status was trimmed on 2026-09-29. This is a record: don't edit it.

## What we did (chronological)

1. **Connected to both machines** over NetBird SSH, routed through the local `netbird-dev` Docker container. Because NetBird SSH triggers a browser SSO prompt for every *new* SSH connection, we set up two long-lived interactive sessions instead of one-off commands — a named FIFO (`mkfifo`) feeds `tail -f fifo | ssh -tt ...`, so we authenticate once per host and then just write commands into the FIFO for the rest of the session.
2. **Found and cleaned up a stale, half-finished deployment attempt** from a previous session: a background process was stuck for 25+ minutes re-trying `apt-get install cuda-toolkit-12-6` because of a transient DNS resolution failure (the rig is on a school WiFi network via a slow USB 2.0 dongle, with occasional site-blocking/DNS flakiness). Killed it, cleared the `dpkg` lock, and restarted cleanly.
3. **Step 1 — Installed CUDA 12.6 toolkit** (`/usr/local/cuda-12.6`). This is required because CUDA 13 (what was previously on the system via a Python venv) dropped support for Pascal (`sm_61`, i.e. the GTX 1070's compute capability). Download was ~4.5GB over the slow rig WiFi, took about 80 minutes.
4. **Step 2 — Built `llama.cpp` from source** with `-DGGML_CUDA_ARCHITECTURES=61`, targeting the correct `nvcc` this time. Build took ~35 minutes on the rig's 2 CPU cores. Verified `llama-server --list-devices` sees all 7 GPUs.
5. **Step 3 — Set up model directories**: symlinked the existing Ollama GGUF blobs into `/srv/ocs-intelligence/models/` under friendly names, without duplicating the ~17GB of model data.
6. **Step 4 — Deployed the two systemd workers**:
   - Generated a shared worker secret (`openssl rand -hex 24`).
   - Wrote `/etc/ocs-intelligence/worker-a.env` and `worker-b.env` (mode `0600`).
   - Installed `ocs-llama-a.service` / `ocs-llama-b.service` to `/etc/systemd/system/`.
   - **Hit and fixed a bug**: the version of `llama.cpp` we built changed `--flash-attn` from a bare boolean flag to one that requires an explicit value (`on`/`off`/`auto`). The original service files (copied verbatim from the plan) passed a bare `--flash-attn`, which caused `llama-server` to swallow the next argument (`--metrics`) as its value and crash-loop. Fixed by changing to `--flash-attn on` in both service files (and updated the checked-in templates to match).
   - Stopped `ollama.service` to free all VRAM, then started both workers. Confirmed via `nvidia-smi` that GPUs are fully freed before the workers claim them.
7. **Verified both workers end-to-end** with real `/v1/chat/completions` requests (see timings below).
8. **Step 5 — Deployed the FastAPI orchestrator on the rig** (not EC2). PyPI is DNS-blocked from school WiFi, so deps came from Ubuntu packages into a `--system-site-packages` venv. Service `ocs-orchestrator` is enabled and listening on `0.0.0.0:9000`. Verified `/healthz`, `/readyz`, `/v1/models`, 401 without a key, and a Worker B completion through the orchestrator (~91 tok/s). NCCL left for later.
9. **Step 6 — EC2 Nginx `/v1/`**. Backed up `llm-relay`, added `/v1/` (no URI rewrite, so `/v1/models` stays `/v1/models` on the orchestrator) and exact `/healthz`. `nginx -t` passed, then reload. Kasm and default vhosts were not edited.
10. **Step 7 — Public e2e tests (2026-09-17):** 9/9 passed — `/healthz`, WebUI `/api/version` 0.11.3, 401 without a key, both models listed, unknown model 404, 0.5b blocking (~87 tok/s) and SSE, 27b blocking (~8.6 tok/s, real answer) and SSE. Open WebUI login page loads in the browser. Copilot Chat itself was not signed into.
11. **EC2 admission gateway (2026-09-18):** FastAPI process `ocs-gateway` on `127.0.0.1:9100` with in-process per-model lanes (A: 1 in-flight + 4 waiters; B: 2 + 4). Nginx `/v1/` and `/healthz` now point at localhost; `proxy_read_timeout` / `proxy_send_timeout` on `/v1/` raised to 3600s. Live concurrency: B 6×200+1×429, A 5×200+1×429; invalid keys 401 without occupying the line. Rig workers and orchestrator were not changed.

## `llama-server` binary details

- Built at `/opt/llama.cpp/src/build` (commit `972d231`, version `0.4.1-dev`), installed to `/opt/llama.cpp/bin/llama-server` and `llama-bench`.
- The installed binary has an **absolute `RUNPATH`** (`/opt/llama.cpp/src/build/bin`), so it depends on the build directory staying in place — it is *not* a fully self-contained static binary. This is fine as long as nobody deletes `/opt/llama.cpp/src/build`.
- Confirmed dynamically linked against `libggml-cuda.so.0`, `libcudart.so.12`, `libcublas.so.12`, `libcuda.so.1` — CUDA backend is real and working.
- **No NCCL.** Build output: `-- Could NOT find NCCL ... Warning: NCCL not found, performance for multiple CUDA GPUs will be suboptimal`. This is the leading suspect for Worker A's slowness.

## Measured performance (live, worker-direct)

| Worker | Model | GPUs | Prompt processing | Generation | Notes |
|---|---|---:|---:|---:|---|
| B | `qwen2.5:0.5b` | 2 (1 PCIe hop) | 216 tok/s | **80.8 tok/s** | Full response, no truncation |
| A | `qwen3.8:27b` | 5 (4 PCIe hops) | 23.2 tok/s | **8.7 tok/s** | Truncated at `max_tokens` — this is a *reasoning* model that spends tokens on hidden `reasoning_content` before answering; not a bug, just needed a bigger token budget for a full test |

**Baseline for comparison** (from `CURSOR_HANDOFF.md`, all 7 GPUs via Ollama, 6 PCIe hops): ~12.5 tok/s generation, ~10.85 tok/s prompt eval.

Worker B is a clear win — nearly **6.5x** the baseline throughput on the small model, as expected from cutting hops from 6 to 1.

Worker A is a problem — **slower** than baseline (8.7 vs 12.5 tok/s) despite fewer PCIe hops (4 vs 6). See the open issue in [status](../../docs/status.md#open-issue-worker-a-is-slower-than-baseline).
