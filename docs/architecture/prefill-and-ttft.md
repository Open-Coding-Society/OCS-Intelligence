---
status: draft
last_verified: 2026-10-15
---

# Reducing prompt prefill time and TTFT

This note suggests ways to make the first response token arrive sooner. It is a tuning plan, not a report of changes or measured improvements. It is based on the checked-in Worker A service, worker environment template, and benchmark docs; the live host has not been checked for this note.

## What contributes to TTFT

Time to first token (TTFT) includes request travel and any queue wait, prompt tokenization, prompt prefill, and the first decode step. Prompt prefill is the model processing the input tokens into its KV cache. Reducing prefill helps most when prompts are long; if the gateway queued the request, the queue may dominate the observed TTFT instead.

## Current setup in the repository

Worker A's service enables Flash Attention, uses layer splitting across its selected GPUs, and runs one slot. The Worker A environment template sets a `163840` context ceiling. The workers architecture page separately lists a 4096-token per-slot context, so confirm the actual running command and effective context before changing context-related settings. The existing public benchmark currently exercises 1k-token input prompts for the 27B model; it also records TTFT and flags queued samples.

See [Worker A's service](../../infra/rig/ocs-llama-a.service), the [Worker A environment template](../../infra/rig/worker-a.env.template), [worker architecture](./workers.md), [benchmark methodology](../testing/benchmarks.md), and [configuration reference](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env).

## Recommendations, in order

### 1. Reduce input tokens where the workload allows

This is the most predictable way to reduce prefill work. Trim stale chat history, avoid repeatedly sending long instructions or retrieved passages, and keep only the context needed for the current turn. Compare requests at fixed input-token lengths; character count is not a reliable substitute for token count.

If the client repeatedly sends an identical system prompt and shared prefix, preserve that prefix exactly and keep request formatting stable. Then check whether this deployed `llama-server` revision reuses cached prompt state for the single slot. Treat cache reuse as unverified until cold and repeated-prefix requests show lower prompt-evaluation time. A changed prefix or slot eviction may require prefill again.

### 2. Tune prompt-processing batch sizes on the exact runtime

Test `--batch-size` and `--ubatch-size` with the installed binary's `--help` output first. llama.cpp uses these for prompt processing; larger values can improve prompt throughput on some setups, but need more temporary memory and can fail or regress on a memory-constrained multi-GPU host. The repo pins Rig 1 to llama.cpp commit `972d231`, so do not assume current upstream flag behavior or defaults apply to that build.

Sweep a small set of supported values (for example, batch sizes 512, 1024, and 2048, with microbatches 128, 256, and 512 where accepted), one setting at a time. Keep the model, prompt tokens, context, output limit, and GPU assignment fixed. Reject settings that cause startup errors, offload, allocation failures, or worse p95 TTFT. Record peak VRAM as well as prompt tokens per second.

### 3. Right-size the context ceiling after confirming the real workload

A smaller configured context does not make a fixed prompt shorter, so it is not by itself a reliable prefill speedup. It can reduce KV-cache memory pressure and may leave room for a more effective prompt batch size. Choose a ceiling that safely holds the longest real prompt plus expected output and margin; validate that it does not truncate or reject normal requests. The checked-in template and architecture page disagree on the context value, so resolve that mismatch against the running process before editing either configuration.

### 4. Measure the multi-GPU path before changing it

The checked-in Worker A command already has Flash Attention enabled and uses layer splitting. Avoid assuming that adding GPUs or switching split mode will improve TTFT: this host has constrained PCIe links, and multi-GPU communication can outweigh added compute. First compare prompt-processing throughput on the current GPU group and build, then evaluate topology or a newer llama.cpp build as a separate, controlled change. The worker docs identify missing NCCL and limited measurements as open performance suspects; NCCL is not a proven prefill fix.

### 5. Use a smaller model when latency matters more than answer quality

Worker B now serves `gemma4:26b`, a mixture-of-experts model, instead of the earlier 0.5B model ([status](../status.md)). Whether it answers short, simple tasks with lower prefill and first-token latency than the 27B hasn't been measured. This is a workload-routing choice, not a tuning change to the 27B worker; measure latency and compare quality on representative requests before directing users to it.

## A small, useful measurement plan

1. Capture the live `llama-server --version`, effective command line, model/GGUF, context, GPU assignment, and current queue policy. Confirm supported batch flags from that binary's help.
2. Establish a baseline with one request at a time and fixed prompt lengths, such as 128, 512, 1k, and 2k tokens, plus a representative repeated-prefix case. Keep output length and sampling settings fixed.
3. Record end-to-end TTFT, whether the request queued, worker prompt-evaluation time or prompt tokens/second when exposed, first-answer-token time for reasoning responses, and GPU memory. Compare medians and p95 across repeated warm requests; report cold-start separately.
4. Change one variable at a time. Start with batch-size tuning, then evaluate context headroom or caching. Keep a candidate only if prompt-evaluation speed improves and end-to-end p95 TTFT improves without memory or correctness regressions.
5. Save measured results as a new dated file under `evidence/benchmarks/` and link it from the evidence index. Do not describe an unmeasured suggestion as a deployed improvement.

The repo's benchmark reports TTFT and excludes queued samples from the aggregate, while `llama-bench` isolates prompt processing from networking and request queuing. Neither alone replaces the other for diagnosing public API TTFT.

## References

- [llama.cpp server options](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [llama.cpp `llama-bench` guide](https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md)
