---
status: current
last_verified: 2026-09-29
---

# Glossary

Terms used in this repo. Plain-language definitions of the general terms come from the [blueprint](../sources/2026-09-11-blueprint-v2.2.md) (p.2–3).

| Term | Meaning here |
|---|---|
| **ADR / decision record** | A short doc recording why we chose X over Y ([decisions](../decisions/decisions.md)). |
| **Admission gateway** | Our FastAPI service on EC2 that checks keys and holds extra requests in a per-model wait line ([gateway](../architecture/gateway.md)). |
| **Bake-off** | A fair contest: every candidate model takes the same test under the same conditions. |
| **CUDA / `sm_61`** | NVIDIA's GPU toolkit. `sm_61` is the GTX 1070's compute capability (6.1). CUDA 13 dropped it, so we use 12.6. |
| **Evidence** | A dated, never-edited record proving a claim ([evidence](../../evidence/evidence.md)). |
| **Gate 0** | The blueprint's discovery checkpoint: nothing is installed until owners and constraints are known. |
| **GGUF** | llama.cpp's model file format. |
| **In flight** | A request that currently holds a GPU slot, as opposed to waiting. |
| **KV cache** | GPU memory holding the conversation so far. It grows with context length. |
| **Lane** | The gateway's per-model line: an in-flight cap plus a waiting cap. |
| **Latency / TTFT** | Time to first token: how long until the first word appears. "P95 ≤ 15 s" means 95 of 100 requests start within 15 s. |
| **llama.cpp / `llama-server`** | The inference engine we run. `llama-server` is its OpenAI-compatible HTTP server. |
| **NetBird** | WireGuard-based private overlay network connecting EC2, the rig, and operators. |
| **NCCL** | NVIDIA's library for fast multi-GPU communication. Missing from our llama.cpp build. |
| **OpenAI-compatible API** | Speaks the same HTTP format as OpenAI's Chat Completions, so Copilot and the OpenAI SDKs work unchanged. |
| **Orchestrator** | Our FastAPI router on the rig: model name → worker ([orchestrator](../architecture/orchestrator.md)). |
| **PIX / PHB** | `nvidia-smi` topology: two GPUs behind the same PCIe switch (PIX), or talking through the host bridge (PHB). |
| **Prompt injection** | Hidden instructions in input trying to make the model break its rules. |
| **Quantization / Q4_K_M** | Storing model weights in fewer bits. Q4_K_M is about 4 bits per weight: smaller and faster, slightly less precise. |
| **Reasoning model / `reasoning_content`** | A model that "thinks" before answering. The thinking arrives in `reasoning_content`, the answer in `content`. |
| **Red team** | People who attack the system on purpose to find holes first. |
| **Replica** | One running copy of a model. The blueprint planned one per GPU. We run one per GPU group. |
| **Rollback** | Undoing a bad update by switching back to the last version that worked. |
| **Runbook** | Step-by-step operating and emergency procedures ([runbook](../operations/runbook.md)). |
| **Soak test** | Running for hours to catch slow leaks: memory creep, overheating. |
| **SSE** | Server-Sent Events: how tokens stream back (`data: …` lines, ending with `data: [DONE]`). |
| **Tensor split / split mode `layer`** | How one model is divided across GPUs. `layer` gives each GPU a block of layers. |
| **Tokens/sec (tok/s)** | How fast the model writes once it starts. |
| **VRAM** | GPU memory. 8 GB per GTX 1070. |
| **Worker** | A `llama-server` process pinned to a GPU group (Worker A: 27B on 5 GPUs; Worker B: 0.5B on 2) ([workers](../architecture/workers.md)). |
