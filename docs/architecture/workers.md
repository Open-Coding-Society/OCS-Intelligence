---
status: current
last_verified: 2026-09-18
---

# Inference workers

Two `llama-server` processes on Rig 1, each pinned to its own GPU group. Configuration details: [configuration](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env). Units: [`infra/rig/`](../../infra/rig/).

## The split

| | Worker A | Worker B |
|---|---|---|
| Model | `qwen3.8:27b` (Q4_K_M, ~16.8 GB) | `gemma4:26b` (`gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`) |
| GPUs | 4 cards | 4 cards |
| Context (`CONTEXT_SIZE`) | 163840 | 256000 |
| Port | `127.0.0.1:8081` | `127.0.0.1:8082` |
| Role | Reasoning model | Second model |

The split started as 5 + 2 GPUs with a 0.5B model on Worker B. On 2026-10-16 the rig was changed to 4 + 4 with `gemma4:26b` on Worker B ([status](../status.md)). The GPU counts, context sizes and model above come from the [env templates](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env); the rest of this page was written for the 5 + 2 split. Before any split, Ollama spread one model across all 7 cards: 6 hops per token, ~12.5 tok/s. Why split at all: [decision 0003](../decisions/0003-5-plus-2-gpu-split.md). Why a sharded 27B instead of one small model per card: [decision 0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md).

## Runtime: llama.cpp

- **Why llama.cpp:** it still supports Pascal GPUs and serves an OpenAI-style API ([decision 0001](../decisions/0001-llama-cpp-over-vllm.md)).
- **CUDA 12.6 is required.** CUDA 13 dropped `sm_61`: `nvcc fatal : Unsupported gpu architecture 'compute_61'`.
- **Build:** from source with `-DCMAKE_CUDA_ARCHITECTURES=61`, commit `972d231` (`0.4.1-dev`), installed to `/opt/llama.cpp/bin/`. Steps: [deploy the rig](../operations/deploy-rig.md).
- **Gotcha:** the installed binary has an absolute RUNPATH into `/opt/llama.cpp/src/build/bin`. Don't delete the build directory.
- **No NCCL.** The build warned multi-GPU performance will be worse. This is the leading suspect for Worker A's slow speed (below).

## Flags that matter

| Flag | Why |
|---|---|
| `--split-mode layer --tensor-split …` | Layers are spread evenly across the group's GPUs |
| `--n-gpu-layers 999` | Everything on the GPU |
| `--parallel 2 --cont-batching` | 2 slots per worker. The gateway still admits only 1 (A) or 2 (B) at a time. |
| `--flash-attn on` | **Must have a value** in this llama.cpp version. A bare `--flash-attn` swallowed `--metrics` as its value and crash-looped the service. |
| `--api-key ${WORKER_API_KEY}` | Only the orchestrator knows this secret |
| `--metrics --slots` | Prometheus metrics and slot inspection, for future monitoring |
| `UnsetEnvironment=GGML_CUDA_P2P` | Makes sure forced CUDA peer-to-peer isn't turned on. Some motherboard/IOMMU combinations fail or corrupt output with it. Only enable it after P2P tests pass for every GPU pair and a correctness soak passes ([original plan](../archive/inference-orchestrator-deployment-4plus3.md)). |

## Performance

Measured numbers: [deployment log](../../evidence/captures/2026-09-18-rig1-deployment-log.md#measured-performance-live-worker-direct) (worker-direct) and [e2e capture](../../evidence/captures/2026-09-17-public-api-e2e.md) (through the public API). The short version:

- **Worker B (`gemma4:26b`) has no recorded speed yet.** The 80–97 tok/s in the logs below were measured on the old 0.5B model, so they don't describe it ([status](../status.md)).
- **Worker A is slower than the baseline.** About 8.6–8.7 tok/s vs 12.5, even though it has fewer hops. This is an **open issue**. The suspects are the missing NCCL and too few measurements ([status](../status.md#open-issue-worker-a-is-slower-than-baseline)). Research ideas from the deck (slide 20): speculative decoding, quantization levels, YaRN.

`qwen3.8:27b` is a reasoning model. It emits `reasoning_content` before `content`, which uses up `max_tokens` ([API](../reference/api.md#models)).
