---
status: proposed
date: 2026-10-15
deciders: Requested by Yash Parikh. Not yet agreed by the team or the mentor.
---

# 0009. Rig 2 serves a MoE model (Qwen3.6-35B-A3B), reached through the one Open WebUI

## Context

Rig 2 came up on 2026-10-15 serving the same dense `qwen3.8:27b` as Rig 1, at the same ~8.8 tok/s ([evidence](../../evidence/captures/2026-10-15-rig2-inference-fix.md)). Every card is on a PCIe gen 1 ×1 riser, and `--split-mode layer` runs the layers on one GPU at a time, so adding GPUs adds memory, not speed. A dense model's speed is bounded by reading all its weights for each token.

A separate public endpoint for Rig 2 (`ai2.opencodingsociety.com`) was started and dropped: the team wants **one** Open WebUI, with a router (eventually a Mac Mini) deciding which rig serves which model.

Open WebUI 0.11.3 merges the model lists of all its OpenAI connections, but if two connections offer the same model ID it keeps only the first ([`routers/openai.py`](https://github.com/open-webui/open-webui), `get_merged_models`). Two rigs serving the same model name would therefore never share load through Open WebUI.

## Options considered

1. **Same model on both rigs, load-balanced by a router** (EC2 gateway now, Mac Mini later). Needs gateway code. Open WebUI alone can't do it.
2. **Same model on both rigs, Rig 2 behind a prefixed Open WebUI connection.** Users would have to pick a rig.
3. **A different, faster model on Rig 2: a mixture-of-experts (MoE) model**, added to Open WebUI as a second connection. Users pick a model, not a rig.

## Decision

We chose **option 3**. Rig 2 serves **Qwen3.6-35B-A3B** (35B total, ~3B active per token; Unsloth `UD-Q4_K_XL` GGUF, 22.4 GB) as `qwen3.6:35b-a3b` on all 8 GPUs. With only ~3B parameters active per token, it generates about 3× faster than the dense 27B on the same cards (27.2 vs 8.8 tok/s, one request each).

Config, chosen without benchmarking at the team's request:
- `--split-mode layer`, `TENSOR_SPLIT=11,8,8,8,8,8,8,8` (GPU 0 is the 11 GB 1080 Ti)
- `PARALLEL=2`, `CONTEXT_SIZE=524288`, so each slot gets the model's full 262,144 tokens
- `-ub 1024`

Qwen3-Coder-Next (80B/3B active, 49.6 GB) was the other candidate. It was set aside to keep to one model.

## Consequences

- Good: students get a second, much faster model, and Rig 2 is useful without new routing code.
- Good: the model names differ, so Open WebUI routes each chat to the right rig with no rig shown to users.
- Bad / accepted trade-off: Rig 2 is no longer a pure dev/test rig while Open WebUI points at it.
- Bad: Open WebUI → Rig 2 skips the EC2 wait line. Only the orchestrator's queue cap (16) and llama-server's 2 slots limit it.
- Follow-up work: add the Open WebUI connection; benchmark this config against alternatives (fewer GPUs, `PARALLEL`, `-ub`) when there's time; replace the direct connection with a router that knows both rigs.

## Differs from the blueprint?

Yes, in two ways. The blueprint's compute plane has Rig 2 as dev and test, not serving students. And the blueprint's model plan is built around `qwen3.8:27b`. Switch back if the MoE's answer quality is noticeably worse for coding, or once Rig 2 is needed for testing.
