---
status: current
last_verified: 2026-09-29
---

# Charter

What the project is for, what it will and won't do, how we'll know it worked, and who is responsible. Based on [Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) §1–3, 8–9, 16 and the [Week 0+1 deck](../sources/2026-09-28-week0-1-mentor-deck.md). Where we differ from the blueprint, the decision record says why.

## Mission

> We're giving every student free access to a capable coding assistant. We're proving we can run it safely, measure it honestly, and hand it off cleanly. (Blueprint)

Paid AI coding assistants cost money per seat, and students who can't pay fall behind. A donor gave the program GTX 1070 GPUs. We turn them into a free, OpenAI-compatible coding assistant that students reach from their editor, built and run by students on infrastructure we own.

**The one rule:** don't approve a cool demo. Approve a service you can measure, attack, recover, explain, and hand to someone else. Every checkpoint closes with evidence ([`evidence/`](../../evidence/evidence.md)).

## Scope

**In scope**

- A text-only coding assistant behind an OpenAI-compatible, streaming API.
- Running it on our own hardware: rigs, drivers, runtime, networking, gateway, monitoring.
- Measuring it: speed, capacity, quality, safety, recovery.
- A runbook good enough that a new operator can run it alone.

**Non-goals (for the six-week campaign)**

- The model **suggests** code. It never runs code, browses the web, reads private repos, writes files, or touches school systems. It's a text box, not an agent.
- No sensitive student data: no grades, records, health or accommodation info, passwords, or private repos.
- No RAG, vision, fine-tuning, or school-system integrations.
- No mentor as help desk, root admin, or on-call operator.

**Where we differ from the blueprint:** a sharded 27B model instead of one small model per GPU ([0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md)), and a public endpoint instead of network-only ([0006](../decisions/0006-public-endpoint.md)). Both are in production and accepted, with a review against the blueprint still pending.

## Success targets

Proposed by the blueprint (§3). They get tightened or relaxed with the sponsor after baseline measurements, and any change is recorded as a decision.

| Measure | Target | Proven by |
|---|---|---|
| Access | Your key works from the school network | API test |
| Availability | Up ≥ 99% of scheduled pilot hours | Gateway numbers |
| Concurrency | 8 students sustained. 24 degrades gracefully (slower, not dead). | Load test report |
| Reliability | No crashes, leaks, or out-of-memory in a 4-hour soak | Soak log |
| Speed | P95 time to first token ≤ 15 s at 8 users | Latency chart |
| Quality | ≥ 70% on the frozen school coding test set | Blind grading |
| Safety | 100% of secret-leak probes blocked. The model can't run anything. | Red-team results |
| Recovery | One dead card absorbed; fully back within 10 min | Failure drill |
| Handoff | A new operator restores everything from the runbook, alone | Continuity drill |

Progress against these and the MVP checklist: [roadmap](./roadmap.md#mvp-checklist).

## People

| Role | Who | Responsible for |
|---|---|---|
| Mentor | Eddie Revollo (Prometheus) | Architecture calls, adversarial review, checkpoint meetings, final recommendation. About 6 hours total ([escalation rules](../sources/2026-09-11-blueprint-v2.2.md)). |
| Teacher / capstone coordinator | John Mortensen | Calendar, deliverables, learning outcomes |
| Primary team lead | Yash Parikh | Whole team. First person anyone calls. |
| Secondary team lead | Nikhil Maturi | Nikhil's pod (Yash Patil, Adi Katre) |
| Team | Mihir Bapat, Anvay Vahia (report to Yash P.); Yash Patil, Adi Katre (report to Nikhil) | Workstreams below |

Sign-off path named in the deck: the principal and CTE specialist. The blueprint also expects school IT (network, host admin), a privacy authority, and a dean/sponsor (launch approval and kill switch). Who fills those roles is still open ([roadmap: Gate 0](./roadmap.md#gate-0-discovery-packet)).

### Workstreams

From deck slide 26. We use workstreams where the blueprint uses three pairs.

| Workstream | Covers |
|---|---|
| Cloud / API | EC2, Nginx, FastAPI gateway, auth, public endpoint |
| Networking | NetBird, peer connectivity, P2P vs relay |
| GPU runtime | Drivers, CUDA, llama.cpp, model benchmarks, rig builds |
| Broker / scheduler | Worker registry, queues, GPU assignment, failover |
| Observability | Health checks, logs, queue depth, latency, GPU utilization |
| Docs / testing | Issues, guides, diagrams, experiment results |

## When to stop

From blueprint §16. **Stop immediately** if: no accountable school owner for infrastructure, privacy, or operations; an unresolved electrical, cooling, or physical-safety concern; one user's data is visible to another, a credential leaks, or we lose admin control; or the school requires sensitive student data.

**Pivot** (after checkpoint 2 or 4) if the model fails the quality bar badly, the rack can't sustain 8 users, cards keep failing, operating it takes more than ~2 h/week, or mentor time goes over the cap. Stopping on evidence isn't failure. The learning and test assets survive.
