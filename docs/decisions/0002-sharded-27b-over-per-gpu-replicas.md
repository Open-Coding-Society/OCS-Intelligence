---
status: accepted
blueprint_review: pending
date: 2026-09-28
deciders: Team; in production; presented to the mentor 2026-09-28 (deck slide 18). No mentor sign-off recorded yet.
---

# 0002. One 27B model split across several GPUs, not one 7–8B copy per GPU

> **Accepted (against the blueprint):** in production, but it differs from [Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) and hasn't been reviewed against it yet. When the review happens, record the outcome here and remove `blueprint_review: pending`.

## Context

The blueprint (§4, spec p.1) says: "copy the model across cards; don't split one model across cards." That means one 7–8B Q4 replica per GPU, 8 lanes, with the model chosen by a bake-off (§5).

The team's view ([deck](../sources/2026-09-28-week0-1-mentor-deck.md) slide 18): 7–8B models are **too weak for real coding-agent work and heavier assignments**. Qwen3.8-27B was already running on the rig under Ollama across all cards at ~12.5 tok/s.

## Options considered

1. **One 7–8B Q4 copy per GPU** (blueprint): up to 8 independent lanes, no inter-GPU traffic, and a dead card only loses one lane. Weaker answers.
2. **A 27B model split across a group of GPUs** (Qwen3.8-27B Q4_K_M, ~16.8 GB): stronger answers, but every token crosses PCIe x1 risers with no NVLink, and there are fewer lanes.
3. **A mid-size model on a single card** (the deck mentions "gemma4 12b or a4b on a single card"): not evaluated yet.

## Decision

Serve **Qwen3.8-27B split across a GPU group**, alongside a small fast model. It's live as Worker A ([0003](./0003-5-plus-2-gpu-split.md)). The deck promises that candidates still get a head-to-head bake-off before a winner and fallback are committed.

## Consequences

- Good: stronger model for coding tasks. It's a reasoning model (`reasoning_content`).
- Bad: **Worker A measures ~8.7 tok/s, slower than the 12.5 tok/s all-GPU baseline** ([status](../status.md#open-issue-worker-a-is-slower-than-baseline)). Only 1 quality request runs at a time ([gateway](../architecture/gateway.md)), far from the blueprint's 8 concurrent users. Losing any one of the 5 cards takes the quality model down. The blueprint's FORGE drill expects a lost card to be absorbed.
- Open: the bake-off hasn't been run. Neither has the blueprint's quality bar (≥70% on the frozen 56-task set).

## Differs from the blueprint?

**Yes**: §4 (topology) and §5 (model chosen before the bake-off). What would make us switch back: a bake-off where a single-card model clears the quality bar, or Worker A failing to reach usable speed and concurrency after the NCCL and benchmark work.
