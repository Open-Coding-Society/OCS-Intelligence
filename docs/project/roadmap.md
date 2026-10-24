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
| 4 | 3–5 | Get inference working on both rigs | **Done** (closed 2026-10-23). Both rigs serve through one chat; "one provider" moved to Sprint 5. Playbooks in [`evidence/sprint4/`](../../evidence/evidence.md): [NetBird lockdown](../../evidence/sprint4/2026-10-15-netbird-one-way-access.md) (done), [inference on both rigs](../../evidence/sprint4/2026-10-15-inference-on-both-rigs.md) (done), [a ninth GPU and driver 580](../../evidence/sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md) (done), and the team's [rig routing playbook](../../evidence/sprint4/2026-10-16-rig-routing.md) (PDF; its VPN steps continue in Sprint 5) |
| 5 | 6– | Establish a stronger scheduling/orchestrator mechanism and improve networking systems: orchestrator (Mac minis), networking (router and VPN), benchmarking | Started (week 6, from 2026-10-19). [Plan below](#sprint-5-plan). First material: networking measurements in the [pending playbook](../../evidence/pending-playbook.md) and a [Mac mini cluster guide](../../evidence/sprint5/macmini_golden_master_cluster_guide.md) |
| 6 | Projected | Security, cleaning up the solution, and the start of per-user access | Projected. [Plan below](#sprint-6-plan) |
| — | Trimester 2 | Assignment grading on the system | [Below](#later-trimester-2) |

## Sprint 5 plan

**Goal:** establish a stronger scheduling/orchestrator mechanism and improve networking systems.

Three big tasks: **the orchestrator** (hosted on the Mac minis), **networking** (router and VPN config), and **benchmarking**. Sprint 5 answers the [2026-10-20 meeting](../sources/2026-10-20-mentor-meeting-notes.md) ("focus on developing a good orchestrator", failure procedures, classroom load, a closed-loop network). It also takes the [audit](../sources/2026-10-14-mentor-audit.md) items that live in the orchestrator, gateway, and network. No owners or end date are set yet.

### First: the audit's "Now" items

Small, and the three tasks build on them.

| Item | Done when | Source |
|---|---|---|
| CI | A GitHub Actions workflow runs `uv run pytest -q` and `python3 scripts/check_docs.py` on every push | Audit D1 |
| Open WebUI under management | A unit (or compose file) with a restart policy in `infra/`, deployed, plus an uptime check that alerts | Audit M1 |
| Fail-closed auth | An empty key list rejects every request on both tiers; keys compared with `hmac.compare_digest`; tests for both | Audit S1, S4 |

### Task 1: orchestrator (from the Mac minis)

| Item | Done when | Source |
|---|---|---|
| Mac mini host | The orchestrator runs on the Mac minis, with a decision record on why (vs. a rig or EC2) and what happens when that host fails. Starting point: the team's [Mac mini cluster guide](../../evidence/sprint5/macmini_golden_master_cluster_guide.md) | Meeting §4.3 |
| One provider for both rigs | One API in front of both rigs. Open WebUI uses one connection, Rig 2 goes through the wait line, and the `rigs-to-rigs` NetBird rule is removed | [Sprint 4 carry-over](../../evidence/sprint4/2026-10-15-inference-on-both-rigs.md#open-items), [0009](../decisions/0009-rig2-moe-behind-open-webui.md) |
| Scheduling | Requests go to the healthy, capable, least-busy worker, with separate priorities for interactive chat and long jobs (grading, later) | Meeting §4.1, deck slides 07–08 |
| Health checks and failover | The orchestrator drops an unhealthy model or rig and sends eligible requests elsewhere. A model-down drill and a rig-down drill each pass once and are written up | Meeting §5 |
| Streaming counted correctly | A streamed request holds its slot until the stream ends, with a test | Audit C1 |
| Bad input returns 400 | Malformed JSON returns 400, not 500; the lane semaphore can't over-release | Audit C3, C4 |
| Tests for auth, routing, health | Offline tests cover them | Audit coverage gap |
| Timeouts sized to the work | One stuck request can't hold a slot for an hour | Audit (long timeouts) |
| Pinned services | Service dependencies locked like local dev ([0010](../decisions/0010-uv-for-local-dev.md)); the rig's version-floor gap closed or recorded; llama.cpp commit recorded per rig | Audit M2, M4, M5 |

### Task 2: networking (router and VPN)

| Item | Done when | Source |
|---|---|---|
| Measured baseline | Done 2026-10-22/23: both rigs at 1 Gb/s, 934 Mb/s rig to rig, ~84 Mb/s shared to the internet ([pending playbook](../../evidence/pending-playbook.md)) | Meeting §3 |
| WireGuard relay to EC2 | [Routing playbook](../../evidence/sprint4/2026-10-16-rig-routing.md) Steps 6–10 done and checked: the Flint 2 tunnels to EC2, and EC2 reaches the rigs through it | Routing playbook |
| Router config | The Flint 2's settings (LAN, DHCP reservations, Wi-Fi, VPN) written down and backed up; how the LAN is shared with other groups decided | [Network](../architecture/network.md#the-ocs-lan) |
| Uplink | Measure each hop (Flint → Mac mini → school Wi-Fi) and decide whether a wired uplink or a second path is needed | Routing playbook §12 |
| Orchestrator firewalled | Each rig's `:9000` accepts only the orchestrator host and EC2, enforced on the host. Other groups on the LAN can't reach it | Audit S2, [status](../status.md) |
| Closed-loop network, defined | A decision record: what stays on the GPU LAN, what may leave, and why | Meeting §6 |
| Source into the GPU LAN | A local mirror or cache so rigs don't pull models and source over the shared uplink | Mortensen, 2026-10-21 |
| Operator access | NetBird SSH to EC2 works again (likely the client MTU problem in the [pending playbook](../../evidence/pending-playbook.md)) | — |

### Task 3: benchmarking

| Item | Done when | Source |
|---|---|---|
| Targets first | Written targets for classroom users, response time, tokens per second, and error rate, so every benchmark has a mark to hit | Meeting §9.2 |
| Per-worker baseline | `llama-bench` and the [benchmark](../testing/benchmarks.md) on every worker: Rig 1's new 4 + 4 split (`qwen3.8:27b`, `gemma4:26b`) and Rig 2 (vs. fewer GPUs, `PARALLEL`, `-ub`). Decide on Worker A's speed (fix NCCL or accept the number) | Audit, [status](../status.md#open-issue-worker-a-is-slower-than-baseline), Sprint 4 carry-over |
| Classroom load | Simulated concurrent students through the public API, starting at the charter's 8 sustained, with time to first token, queue wait, and errors recorded | Meeting §3.1, §9; blueprint §11–13 |
| Latency side by side | The same request timed from a machine on the GPU LAN and from one over the internet | Mortensen, 2026-10-21 |
| 4 GPUs per host | Current layout vs. 4 GPUs per host under the same load, before any hardware change | Meeting §3.2 |

### Record

- Friday reports resume in `evidence/weekly/` ([template](../_templates/weekly-report.md)). Audit D4.
- `status.md` re-verified at least weekly.

## Sprint 6 plan

**Goal:** security, cleaning up the solution, and the start of per-user access. Projected; it builds on Sprint 5's orchestrator.

| Area | Items | Source |
|---|---|---|
| Security | Services run as non-root users; per-person SSH instead of root; rate limits and request-size limits on every path; security headers on Nginx (HSTS, no version); decide what stays out of the public repo (internal IPs, GPU IDs); evaluate Raven in isolation once Revollo sends it | Audit S5–S8, S10, M3; meeting §2.2 |
| Per-user access | Start the design and the first version: per-student keys with quotas and revocation, so one leaked key doesn't expose everyone and usage can be attributed | Audit S3, blueprint §3, §10 |
| Clean up the solution | Remove what's temporary: `rigs-to-rigs` (if Sprint 5 didn't), the `ai2` leftovers, Open WebUI's second connection, stale docs (`workers.md` and decision 0003 still describe the 5 + 2 split). Settle the `proposed` decisions | Sprint 4 carry-over, audit |
| Prove it holds | The 4-hour soak, the remaining failure drills (orchestrator host, network link, GPU OOM), and the continuity drill: someone who didn't build it restores the service from the runbook | Blueprint §11–13, audit D3, meeting §5.3 |
| Safety and upkeep | Safety guide (ESD, grounding, power-down), antistatic mat, dated diagrams on the wall above the rigs, weekly inspection and cleaning checklist | Meeting §10–11 |
| Handoff | Change log and a handoff README for the next group | Meeting §12 |

## Later: trimester 2

**Assignment grading is the main reason for the system.** It isn't plugged in yet; the plan is to start it at the beginning of trimester 2, on top of Sprint 5's orchestrator and Sprint 6's per-user access. It will connect to Gists, code runners, and submissions, use classroom rubrics, and have students and teachers review the grades (meeting §7).

The blueprint's [scope lock](#the-blueprints-six-week-campaign) rules out school-system integrations, agents, and vision during the campaign. So grading needs a decision record (`status: proposed`, marking the blueprint difference) before work starts. The same goes for the other ideas from 2026-10-20:

| Idea | What it needs first | Source |
|---|---|---|
| AI assignment grading | A decision record; the orchestrator's job priorities; per-user access | Meeting §7 |
| Tool-call harness | A decision record (it's an agent feature) | Meeting §4.4 |
| Jarvis images to a vision model | A decision record and school privacy authorization | Meeting §8.1 |

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
