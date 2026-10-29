---
status: proposed
date: 2026-10-29
deciders:
---

# 0012. The EC2 gateway routes `qwen3.6:35b-a3b` to Rig 2 with a key it stores

## Context

Rig 2 serves `qwen3.6:35b-a3b` ([0009](./0009-rig2-moe-behind-open-webui.md)), but only Open WebUI reaches it, directly and without the EC2 wait line. API users of `https://ai.opencodingsociety.com/v1` can't use it. The gateway had one upstream (Rig 1) and forwarded the caller's key unchanged. Rig 2's orchestrator doesn't accept the student key (401 from EC2, checked 2026-10-29), and the team wants students to need **one** key.

## Options considered

1. **Add the student key to Rig 2's orchestrator** and give the gateway a second upstream. Same key on both rigs, so anyone with it on the OCS LAN could also skip the wait line on Rig 2 ([status](../status.md#other-things-worth-knowing)).
2. **A second gateway on `ai2.opencodingsociety.com`.** A second base URL, and the `ai2` site was already dropped.
3. **A Rig 2 lane in the one gateway, with its own upstream URL and a stored Rig 2 key** sent in place of the caller's.

## Decision

We chose **option 3**. One base URL and one student key; the model name picks the rig. The gateway checks the student key, then sends `RIG2_UPSTREAM_API_KEY` to Rig 2. That is Rig 2's existing Open WebUI key, so Rig 2 needs no change and no new key exists. It sits in EC2's `0600` env file, and Rig 2 keeps rejecting the student key. `/v1/models` lists both rigs, and lists Rig 1 only if Rig 2 doesn't answer.

## Consequences

- Good: `qwen3.6:35b-a3b` gets the EC2 wait line (`RIG2_INFLIGHT=2`, Rig 2's two slots).
- Good: no change on Rig 2; empty `RIG2_MODEL_ALIAS` turns the lane off.
- Bad: the gateway and Open WebUI share one Rig 2 key, so rotating it means updating both.
- Bad / accepted trade-off: the gateway now holds a rig secret, so EC2 compromise exposes Rig 2's orchestrator too (it already exposed the student key).
- Bad: Open WebUI's gateway connection will also offer `qwen3.6:35b-a3b`. Open WebUI keeps the first connection with a given ID, so which path its chats take depends on connection order.
- Follow-up work: drop Open WebUI's direct Rig 2 connection (live since 2026-10-29, [evidence](../../evidence/captures/2026-10-29-ec2-gateway-rig2-lane.md)); the Mac mini router replaces this lane later.

## Differs from the blueprint?

Yes. The blueprint's gateway forwards to one rig orchestrator, and Rig 2 is dev/test (see 0009). Switch back if Rig 2 is needed for testing: set `RIG2_MODEL_ALIAS=` and restart the gateway.
