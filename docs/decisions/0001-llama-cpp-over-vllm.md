---
status: accepted
date: 2026-09-11
deciders: Recommended in Blueprint v2.2 §4 (E. Revollo); adopted by the team
---

# 0001. llama.cpp as the inference runtime, not vLLM

## Context

The rigs use GTX 1070s: Pascal, compute capability 6.1 (`sm_61`), 8 GB each ([hardware](../architecture/hardware.md)). We need an OpenAI-compatible server that runs quantized models on these cards.

## Options considered

1. **vLLM**: high throughput, but stock vLLM targets compute capability 7.0+.
2. **Ollama**: easy, and it was the first thing we ran. It wraps llama.cpp but gives less control over GPU pinning, split mode, and flags.
3. **llama.cpp `llama-server`**: supports Pascal, GGUF quantization, OpenAI-style routes, and built-in `/metrics` and `/slots`.

## Decision

Use **llama.cpp `llama-server`**, built from source with CUDA 12.6 for `sm_61`. The blueprint recommends it (§4: "stock vLLM is not the realistic path for this rack").

## Consequences

- Good: it runs on our cards, gives precise control of GPU groups and `--split-mode layer`, and has Prometheus metrics built in.
- Bad: we build from source on a 2-core rig (~35 min). **CUDA 13 dropped `sm_61`**, so we're pinned to CUDA 12.x. The build found no NCCL, which may slow down multi-GPU work ([workers](../architecture/workers.md)).
- Ollama is stopped but kept as a fallback ([status](../status.md)).

## Differs from the blueprint?

No.
