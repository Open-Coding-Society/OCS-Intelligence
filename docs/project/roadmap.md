---
status: current
last_verified: 2026-10-23
---

# Roadmap

The plan, and what's planned but not built. Based on the 2026-09-28 mentor meeting ([deck](../sources/2026-09-28-week0-1-mentor-deck.md)), the [2026-10-14 mentor audit](../sources/2026-10-14-mentor-audit.md), and the [2026-10-20 mentor meeting](../sources/2026-10-20-mentor-meeting-notes.md). Sprint 5 and 6 plans added 2026-10-23. For what's live, see [status](../status.md).

## Sprints

We plan in sprints, not fixed weeks, because some pieces of work take longer than others. A sprint closes when its goal is met **and** there is evidence, however long that takes. Sprints can overlap, so more than one can be running in the same week. Sprint material goes in `evidence/sprintN/`. Proposed in [0007](../decisions/0007-sprints-over-fixed-weeks.md).

| Sprint | Weeks | Goal | State |
|---:|---|---|---|
| 1 | 0–1 | Authorize discovery and prove one lane end to end (blueprint Weeks 0 and 1) | Playbooks in [`evidence/sprint1/`](../../evidence/evidence.md). Backlog [below](#sprint-1-backlog-as-presented-2026-09-28). |
| 2 | 2–3 | VR-related work (owner: yashpatil321) | In progress. Playbook in [`evidence/sprint2/`](../../evidence/evidence.md): [the VR experience](../../evidence/sprint2/2026-09-16-vr-experience.md) (in progress: full arc passes in simulation; not yet run on a headset) |
| 3 | 2–4 | Resolve both rigs after they were rebuilt and rewired | Done (reported 2026-10-16): both rigs boot with 8 GPUs. [Playbook](../../evidence/sprint3/2026-09-28-resolving-both-rigs.md) |
| 4 | 3–5 | Get inference working on both rigs | In progress (week 5 is the current week as of 2026-10-14). **Proposed (2026-10-23):** close Sprint 4 on what it has shown, both rigs serving through one chat, and move its "one provider" open item into Sprint 5. The team hasn't decided this yet. Playbooks in [`evidence/sprint4/`](../../evidence/evidence.md): [NetBird lockdown](../../evidence/sprint4/2026-10-15-netbird-one-way-access.md) (done), [inference on both rigs](../../evidence/sprint4/2026-10-15-inference-on-both-rigs.md) (in progress: both rigs serve through one Open WebUI; one router still to come) |
| 5 | 6– | Establish a stronger scheduling/orchestrator mechanism and improve networking systems | Started (week 6, from 2026-10-19). [Plan below](#sprint-5-plan). First material: networking measurements in the [pending playbook](../../evidence/pending-playbook.md) and a [Mac mini cluster guide](../../evidence/sprint5/macmini_golden_master_cluster_guide.md) |
| 6 | Projected | Prove it under classroom load, finish the security work, and make it ready to hand off | Projected. [Plan below](#sprint-6-plan) |

## Sprint 5 plan

**Goal:** establish a stronger scheduling/orchestrator mechanism and improve networking systems.

It answers the [2026-10-20 meeting](../sources/2026-10-20-mentor-meeting-notes.md) ("focus on developing a good orchestrator", failure procedures, closed-loop network) and takes the [audit](../sources/2026-10-14-mentor-audit.md) items that live in the orchestrator, the gateway, and the network. The audit's "Now" items go first even where they're off-theme, because each one is small and the rest of the sprint depends on them. No owners or end date are set yet.

### First: the audit's "Now" items

| Item | Done when | Source |
|---|---|---|
| CI | A GitHub Actions workflow runs `uv run pytest -q` and `python3 scripts/check_docs.py` on every push and PR | Audit D1 |
| Changes through pull requests | Code changes land through a reviewed PR. The first one is the auth fix below | Audit D2 |
| Open WebUI under management | A unit (or compose file) with a restart policy in `infra/`, deployed, plus an uptime check that alerts | Audit M1 |
| Fail-closed auth | An empty key list rejects every request on both tiers; keys compared with `hmac.compare_digest`; tests for both | Audit S1, S4 |

### Orchestrator and scheduling

| Item | Done when | Source |
|---|---|---|
| One provider for both rigs | One API in front of both rigs. Open WebUI uses one connection, Rig 2 goes through the wait line, and the `rigs-to-rigs` NetBird rule is removed | [Sprint 4 open item](../../evidence/sprint4/2026-10-15-inference-on-both-rigs.md#open-items), [0009](../decisions/0009-rig2-moe-behind-open-webui.md) |
| Where the orchestrator runs | A decision record comparing a Mac mini, a rig, and EC2 on availability, latency, and failure | Meeting §4.3 |
| Health checks and failover | The router drops an unhealthy model or rig and sends eligible requests elsewhere. A model-down drill and a rig-down drill each pass once and are written up | Meeting §5, deck slides 07–08 |
| Streaming counted correctly | A streamed request holds its slot until the stream ends, with a test | Audit C1 |
| Bad input returns 400 | Malformed JSON returns 400, not 500, in both services; the lane semaphore can't over-release | Audit C3, C4 |
| Tests for auth, routing, health | Offline tests cover them | Audit coverage gap |
| Timeouts sized to the work | One stuck request can't hold the quality slot for an hour | Audit (long timeouts) |
| Worker speed decision | `llama-bench` on Rig 1's current 4 + 4 layout and Rig 2. Fix NCCL or accept the number, with a date | Audit, [status](../status.md#open-issue-worker-a-is-slower-than-baseline) |
| Pinned services | Service dependencies locked like local dev ([0010](../decisions/0010-uv-for-local-dev.md)), the rig's version-floor gap closed or recorded, llama.cpp commit recorded per rig | Audit M2, M4, M5 |

### Networking

| Item | Done when | Source |
|---|---|---|
| Measured baseline | Done 2026-10-22/23: both rigs link at 1 Gb/s, 934 Mb/s rig to rig, ~84 Mb/s shared to the internet ([pending playbook](../../evidence/pending-playbook.md)) | Meeting §3 |
| Uplink throughput | The internet path goes Flint 2 → Mac mini → school Wi-Fi ([routing playbook](../../evidence/sprint4/OCS_Rig_Routing_Playbook.pdf)). Measure each hop and decide whether a wired uplink or a second path is needed | Routing playbook §12 |
| WireGuard relay to EC2 | Routing playbook Steps 6–10 done and checked, or replaced by a decision | Routing playbook |
| Orchestrator firewalled | Each rig's `:9000` accepts only the gateway (and the new router), enforced on the host | Audit S2 |
| Closed-loop network, defined | A decision record that says what stays on the GPU LAN, what may leave, and why | Meeting §6 |
| Latency side by side | The same request timed from a machine on the GPU LAN and from one over the internet | Mortensen, 2026-10-21 |
| Source into the GPU LAN | A local mirror or cache so rigs don't pull models and source over the shared uplink | Mortensen, 2026-10-21 |
| Operator access works | NetBird SSH to EC2 works again (likely the client MTU problem logged on 2026-10-23) | [pending playbook](../../evidence/pending-playbook.md) |

### Record

- Friday reports resume in `evidence/weekly/` ([template](../_templates/weekly-report.md)). Audit D4.
- `status.md` re-verified at least weekly.

## Sprint 6 plan

**Proposed goal:** prove the system under classroom load, finish the security work, and make it ready to hand off. Not started; it depends on Sprint 5's orchestrator.

| Area | Items | Source |
|---|---|---|
| Load and failure proofs | 8-user sustained load, the 4-hour soak, the quality test set, the remaining failure drills (orchestrator host, network link, GPU OOM), against targets set first (users, response time, error rate) | Blueprint §11–13, audit fix order, meeting §9 |
| Hardware experiment | Compare the current layout with 4 GPUs per host under the same load | Meeting §3.2 |
| Security | Per-student keys with quotas and revocation; services as non-root users and per-person SSH; rate limits and request-size limits; security headers on Nginx; decide what stays out of the public repo | Audit S3, S5–S8, S10, M3 |
| Raven | Evaluate in isolation once Revollo sends it | Meeting §2.2 |
| Safety and upkeep | Safety guide (ESD, grounding, power-down), antistatic mat, dated diagrams on the wall, weekly inspection and cleaning checklist | Meeting §10–11 |
| Handoff | Change log, handoff README, and the continuity drill: someone who didn't build it restores the service from the runbook | Meeting §12, audit D3 |

## Parked: outside the scope lock

The blueprint's [scope lock](#the-blueprints-six-week-campaign) rules out agents, vision, and school-system integrations during the campaign. These came up on 2026-10-20 and stay parked until a decision record (`status: proposed`, marking the blueprint difference) says otherwise.

| Idea | Why it's parked | Source |
|---|---|---|
| AI assignment grading (Gists, code runners, rubrics, review) | A school-system integration. It was named the primary classroom use case, so it's the first candidate for a decision record | Meeting §7 |
| Tool-call harness | An agent feature | Meeting §4.4 |
| Jarvis images to a vision model | Vision, and it also needs school privacy authorization | Meeting §8.1 |

## The blueprint's six-week campaign

From [Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) §7, as adapted in the deck (slide 27). This is the plan we're measured against. We now track work as [sprints](#sprints), and Sprint 1 corresponds to Weeks 0 and 1. Each week closes only when its exit criteria are true **and** there is evidence.

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
| Router that knows both rigs (Mac Mini; EC2 gateway in the meantime) | Team, 2026-10-15 | Would replace Open WebUI's direct connection to Rig 2 and the temporary rigs-to-rigs NetBird rule ([0009](../decisions/0009-rig2-moe-behind-open-webui.md)) |
| Broker: FastAPI + Redis (live state) + RDS (durable state) | Deck slides 07–08, 21, 32 | MVP policy: filter healthy → capable → prefer loaded → least busy → queue → log. Would revisit [0005](../decisions/0005-admission-queue-on-ec2.md). |
| Rig 2 (dev and test) | Deck slides 16–17 | Built and serving `qwen3.6:35b-a3b` through Open WebUI since 2026-10-15 ([status](../status.md), [0009](../decisions/0009-rig2-moe-behind-open-webui.md)) |
| Worker A throughput fix | [status](../status.md#open-issue-worker-a-is-slower-than-baseline) | `llama-bench`, then NCCL |
| Monitoring: GPU exporter → Prometheus → Grafana | Blueprint §4, deck slide 35 | llama-server already exposes `/metrics` |
| R&D: model warming, speculative decoding, quantization levels, YaRN | Deck slide 20 | Each needs a before/after measurement |
| Label rigs and GPUs, physical subgroups | Deck slide 33 | The 7-vs-8 card question was settled in [Sprint 3](../../evidence/sprint3/2026-09-28-resolving-both-rigs.md): Rig 1 runs 8 |
| Week 0 and Week 1 (Sprint 1) playbooks | Deck slide 33 | In progress: two in [`evidence/sprint1/`](../../evidence/evidence.md) |
| Self-healing agent loop (detect → diagnose → repair → verify → log) | Deck slide 34 | "Run" stage. Research question. |

## Sprint 1 backlog (as presented 2026-09-28)

From deck slide 32, with state as of 2026-09-29. Everything below refers to Rig 1. Rig 2's state is in [status](../status.md).

| # | Item | State |
|---|---|---|
| P0 | Prove the GPU runtime: driver + llama-server + one GGUF model → one documented, benchmarked API response | ✅ Done on Rig 1: [deployment log](../../evidence/captures/2026-09-18-rig1-deployment-log.md), [e2e capture](../../evidence/captures/2026-09-17-public-api-e2e.md) |
| P1 | Prove private connectivity: NetBird across control and GPU nodes, P2P vs relay, record RTT | ⚠️ Partial: NetBird works EC2 ↔ rig. EC2 connects P2P, the rig through a relay ([discovery record](../archive/phase1-discovery.md)). **RTT not recorded.** |
| P2 | Build one EC2 worker: identity, `/health`, heartbeat, job state, forward path to llama-server | ❌ Not done. The gateway and orchestrator provide a forward path and health polling, but there's no worker identity, heartbeat, or job state. |
| P3 | Minimal broker: FastAPI + Redis registries, job queue, least-busy healthy-worker scheduling | ❌ Not done. The in-memory EC2 wait line covers queueing for now ([0005](../decisions/0005-admission-queue-on-ec2.md)). |
| P4 | First end-to-end demo with logs at every hop | ✅ Done on Rig 1 through gateway → orchestrator → worker (no broker): [e2e capture](../../evidence/captures/2026-09-17-public-api-e2e.md), [`scripts/demo.py`](../../scripts/demo.py) |
