---
status: current
last_verified: 2026-09-29
---

# Roadmap

The plan, and what's planned but not built. Based on the 2026-09-28 mentor meeting, with backlog state updated 2026-09-29 ([deck](../sources/2026-09-28-week0-1-mentor-deck.md)). For what's live, see [status](../status.md).

## The six-week campaign

From [Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) §7, as adapted in the deck (slide 27). Each week closes only when its exit criteria are true **and** there is evidence.

| Week | Goal | Done when |
|---:|---|---|
| 0 | Authorize discovery | Gate 0 packet signed |
| 1 | Prove one lane end to end | Anyone can reinstall from scratch; baseline numbers recorded |
| 2 | Pick the model | Bake-off decision record; winner and fallback chosen |
| 3 | Scale up, lock down | Gateway, per-student keys, quotas, health checks live |
| 4 | Observe and attack | Full monitoring; functional, load, abuse, failure tests; no critical issue open |
| 5 | Pilot with a limited cohort | Pilot evidence complete; Night at the Museum package frozen |
| 6 | Decide, then showcase | Continuity drill, sponsor review, go/no-go signed; N@TM gallery night |

Every Friday: a one-page report in [`evidence/weekly/`](../../evidence/evidence.md) ([template](../_templates/weekly-report.md)).

**Scope lock:** during the campaign, no RAG, agents, vision, fine-tuning, or school-system integrations.

## Phases (engineering view)

From deck slide 30, as of 2026-09-28.

| Phase | What | State |
|---|---|---|
| 0 | Architecture | Done |
| 1 | Smallest end-to-end proof | Live |
| 2 | Health and registration (workers report in) | Next |
| 3 | Queue and scheduling (broker) | Planned |
| 4–6 | Sessions, scale, prod/dev split across rigs | Planned |

## Gate 0: discovery packet

Blueprint §2 says nothing gets installed until these exist. Part of it was done in the [phase-1 discovery record](../archive/phase1-discovery.md). Nothing below is signed off yet.

| Evidence | Who provides it | State |
|---|---|---|
| Hardware manifest (models, serials, VRAM, health, power) | Infra | Partial: [hardware](../architecture/hardware.md) has UUIDs and topology, but no serials, health, or power data |
| Host baseline (CPU, RAM, disk, OS, driver, CUDA) | Infra | Partial: [hardware](../architecture/hardware.md), [workers](../architecture/workers.md) |
| Network diagram | School IT | Ours: [network](../architecture/network.md). Not reviewed by school IT. |
| Ownership record (admin, operator, sponsor, contact) | John Mortensen / dean | Open |
| Data boundary (allowed prompts, logging, retention) | School privacy lead | Draft: [data policy](../security/data-policy.md) |
| Safety check (power, cooling, physical access) | Facilities / IT | Open |

## MVP checklist

From blueprint §3. Verified against the code and [status](../status.md) as of 2026-09-18.

| Item | State |
|---|---|
| OpenAI-style chat API with streaming | ✅ Live |
| Per-student keys with quotas and revocation | ❌ One shared key |
| One-click health page for replicas and GPUs | ⚠️ `/healthz` and orchestrator `/readyz` only. No GPU view. |
| Logs that don't store what students typed | ⚠️ Not verified. See [data policy](../security/data-policy.md). |
| Reproducible deploys with rollback | ⚠️ Units and templates in [`infra/`](../../infra/). No tagged releases or rollback procedure. |
| Published limitations, safe-use notice, feedback channel | ⚠️ Limitations are documented. No notice or feedback channel yet. |

## Planned, not built

| Item | Source | Notes |
|---|---|---|
| Model bake-off | Blueprint §5, deck slide 18 | Frozen task set, blind grading. Would confirm or reverse [0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md). |
| Per-student API keys, quotas, revocation | Blueprint §3, §10 | Needed so the line is fair per person |
| Broker: FastAPI + Redis (live state) + RDS (durable state) | Deck slides 07–08, 21, 32 | MVP policy: filter healthy → capable → prefer loaded → least busy → queue → log. Would revisit [0005](../decisions/0005-admission-queue-on-ec2.md). |
| Rig 2 (dev and test) | Deck slides 16–17 | Being built |
| Worker A throughput fix | [status](../status.md#open-issue-worker-a-is-slower-than-baseline) | `llama-bench`, then NCCL |
| Monitoring: GPU exporter → Prometheus → Grafana | Blueprint §4, deck slide 35 | llama-server already exposes `/metrics` |
| R&D: model warming, speculative decoding, quantization levels, YaRN | Deck slide 20 | Each needs a before/after measurement |
| Label rigs and GPUs, physical subgroups | Deck slide 33 | Also settles the [7-vs-8 card question](../architecture/hardware.md) |
| Week 0 and Week 1 playbooks | Deck slide 33 | In progress |
| Self-healing agent loop (detect → diagnose → repair → verify → log) | Deck slide 34 | "Run" stage. Research question. |

## Next-sprint backlog (as presented 2026-09-28)

From deck slide 32, with state as of 2026-09-29. Everything below refers to Rig 1. **Nothing is done on Rig 2 yet.**

| # | Item | State |
|---|---|---|
| P0 | Prove the GPU runtime: driver + llama-server + one GGUF model → one documented, benchmarked API response | ✅ Done on Rig 1: [deployment log](../../evidence/captures/2026-09-18-rig1-deployment-log.md), [e2e capture](../../evidence/captures/2026-09-17-public-api-e2e.md) |
| P1 | Prove private connectivity: NetBird across control and GPU nodes, P2P vs relay, record RTT | ⚠️ Partial: NetBird works EC2 ↔ rig. EC2 connects P2P, the rig through a relay ([discovery record](../archive/phase1-discovery.md)). **RTT not recorded.** |
| P2 | Build one EC2 worker: identity, `/health`, heartbeat, job state, forward path to llama-server | ❌ Not done. The gateway and orchestrator provide a forward path and health polling, but there's no worker identity, heartbeat, or job state. |
| P3 | Minimal broker: FastAPI + Redis registries, job queue, least-busy healthy-worker scheduling | ❌ Not done. The in-memory EC2 wait line covers queueing for now ([0005](../decisions/0005-admission-queue-on-ec2.md)). |
| P4 | First end-to-end demo with logs at every hop | ✅ Done on Rig 1 through gateway → orchestrator → worker (no broker): [e2e capture](../../evidence/captures/2026-09-17-public-api-e2e.md), [`scripts/demo.py`](../../scripts/demo.py) |
