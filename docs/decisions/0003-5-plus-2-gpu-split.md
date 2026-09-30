---
status: accepted
date: 2026-09-17
deciders: Team (execution plan in the Cursor handoff); deployed 2026-09-17
supersedes: the 4+3 plan (archived, pre-dates this log)
---

# 0003. Split Rig 1 into 5-GPU and 2-GPU workers

## Context

Ollama spread one model across all 7 visible GPUs. Every generated token needed **6 sequential inter-GPU transfers** over PCIe Gen1 x1 risers (~250 MB/s). The result was ~12.5 tok/s, and only one request could effectively run at a time ([hardware](../architecture/hardware.md)).

## Options considered

1. **Keep all 7 GPUs in one model**: 6 hops per token, one lane.
2. **4 + 3 split** with a "flexible" worker that loads allow-listed models ([archived plan](../archive/inference-orchestrator-deployment-4plus3.md)). Why it was replaced by 5+2 wasn't recorded beyond the [handoff](../archive/cursor-handoff.md).
3. **5 + 2 split**: Worker A runs the 27B on GPUs 0–4 (40 GB total, ~23 GB left for KV cache and context, 4 hops). Worker B runs a 0.5B model on GPUs 5–6 (1 hop).

## Decision

**5 + 2**, with GPUs pinned by UUID and `--split-mode layer`. Details: [workers](../architecture/workers.md).

## Consequences

- Good: Worker B reaches ~80–97 tok/s (about 6.5× the baseline). The two workers run at the same time and never share a PCIe path.
- Bad: **Worker A is slower than the old baseline** (8.7 vs 12.5 tok/s) despite fewer hops. Not root-caused yet. Suspects are missing NCCL and too few measurements ([status](../status.md#open-issue-worker-a-is-slower-than-baseline)). Until that's fixed, the split is a regression for the quality model.
- Follow-up: run `llama-bench` for clean numbers, then try NCCL.

## Differs from the blueprint?

Follows from [0002](./0002-sharded-27b-over-per-gpu-replicas.md), which does.
