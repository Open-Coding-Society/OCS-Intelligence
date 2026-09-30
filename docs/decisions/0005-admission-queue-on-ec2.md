---
status: accepted
date: 2026-09-18
deciders: Team (not recorded); deployed 2026-09-18
---

# 0005. The wait line lives on EC2, in process, with no Redis

## Context

The rig can run 1 quality and 2 fast generations at once. A class of Copilot tabs sends far more. Before this decision the orchestrator forwarded every authenticated request immediately. Its limit of 16 was a *reject* threshold, not a line, so bursts produced "no slot" errors, hangs, and a service that looked random. Full reasoning: [gateway](../architecture/gateway.md).

## Options considered

1. **A queue on the rig**, in the orchestrator: waiting sockets compete with inference on a 2-core machine on USB Wi-Fi. If the rig's network flakes, the queue goes down with it. A second rig would need a second queue.
2. **A job queue** (Redis, SQS, or the broker planned in the deck): Copilot holds a live HTTP stream and has no callback, so a job queue adds infrastructure without helping.
3. **An in-process FIFO on EC2**, in front of the rig: one asyncio semaphore per model plus a cap on waiters. EC2 already terminates TLS and has reliable networking.

## Decision

**An in-process admission gateway on EC2** (`127.0.0.1:9100`, `--workers 1`): authenticate first, 404 for unknown models, per-model FIFO lanes, 429 with `Retry-After: 15` when full, SSE `: queued` keepalives, no wait timeout.

## Consequences

- Good: the rig only receives work it can start. The line is fair (FIFO) and bounded. Failures come back as HTTP codes Copilot understands. A future second rig becomes another upstream behind the same URL.
- Bad: **one uvicorn worker only**, because two workers would be two separate lines. The line is lost on restart. With one shared key it's first-come, not per person. Open WebUI and anyone who reaches rig `:9000` directly skip the line ([threat model](../security/threat-model.md)).
- Relation to the planned broker (deck slides 07–08, 21): if Redis-backed scheduling across rigs is built, revisit this and supersede it if needed.

## Differs from the blueprint?

Partly. The blueprint wants a "bounded queue · honest wait / fail" in the gateway, which this is. It doesn't yet do health-aware routing across replicas, because there's one worker per model.
