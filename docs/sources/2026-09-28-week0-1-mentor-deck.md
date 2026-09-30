---
status: current
last_verified: 2026-09-29
---

# Week 0+1 intro deck (summary)

| | |
|---|---|
| **Original** | [`2026-09-28-week0-1-mentor-deck.pptx`](./2026-09-28-week0-1-mentor-deck.pptx) (36 slides) |
| **Author** | OCS Intelligence team |
| **Date** | Presented 2026-09-28 to Eddie Revollo (mentor, Prometheus) |
| **What it is** | Our Week 0+1 status and plan presentation: architecture, connectivity findings, hardware, model decision, roadmap, team. |

## Summary

- **Headline:** "a distributed AI infrastructure, built and owned by students," with 2 rigs × 8 GTX 1070s, NetBird, llama.cpp, and Qwen3.8-27B.
- **Target architecture:** Student → AWS relay (Nginx/TLS) → FastAPI broker → NetBird → GPU rig (llama-server). A **control plane** (auth, API, broker, RDS for durable state, Redis for live worker/queue state) is split from a **compute plane** (Rig 1 production, Rig 2 dev and test).
- **Connectivity:** NetBird + AWS relay works on the district network. Cloudflare Tunnel (port 7844 blocked) and ngrok (DNS sinkhole, then CRL check, then Ollama Host-header 403) were abandoned. Method: isolate which layer owns the failure.
- **Model decision, where we pushed back on the blueprint:** fewer, larger, sharded replicas (Qwen3.8-27B across several GPUs) in place of one 7–8B model per card, because 7–8B is too weak for real coding-agent work. A bake-off is still promised before committing.
- **Performance:** ~12 tok/s now, 60+ targeted; cold TTFT 2 m 27 s vs warm 2 s. R&D queue: model warming, speculative decoding, quantization levels, YaRN context scaling.
- **Broker (planned):** filter healthy → capable → prefer already-loaded → least busy → queue → log the decision.
- **Roadmap:** the blueprint's 6 weeks, ending with a Night at the Museum showcase. Status: Phase 0 architecture done, Phase 1 E2E proof live, Phase 2 health and registration next, Phases 3–6 planned.
- **Next steps:** label the rigs and every GPU, split rigs into physical subgroups, Week 0/1 playbooks. Crawl → walk → run toward a self-healing agent loop.

## Slide outline

Numbers are the ones printed on each slide (the file stores some slides out of order).

| # | Slide | # | Slide |
|---|---|---|---|
| 01 | Title | 19 | Performance metrics |
| 02 | One request, six hops | 20 | Four R&D techniques |
| 03 | Evidence: live demo | 21–25 | Broker / scheduling |
| 04 | Team and reporting lines | 26 | Seven workstreams |
| 05 | Mission | 27 | Six-week roadmap |
| 06 | The problem | 28 | Testing and drills |
| 07 | Control vs compute plane | 29 | Safety |
| 08 | Three kinds of state | 30 | Status by phase |
| 09 | Full stack end to end | 31 | Ground Zero milestone |
| 10 | Connectivity: three tools | 32 | Next-sprint backlog P0–P4 |
| 11 | Debugging method | 33 | Next steps: label the rigs |
| 12 | Current live state | 34 | Crawl, walk, run |
| 13–15 | Demo and evidence | 35 | Vision beyond the pilot |
| 16 | Hardware: two rigs | 36 | Thank you |
| 17 | Rebuilding Rig 2 | | |
| 18 | Model decision | | |

## Where each part is handled in our docs

| Deck slides | Our doc | Notes |
|---|---|---|
| 02, 07, 08, 09 (architecture, planes, state) | [overview](../architecture/overview.md), [roadmap](../project/roadmap.md) | The broker, Redis, and RDS are **planned**, not built. The live system uses an in-memory gateway queue ([decision 0005](../decisions/0005-admission-queue-on-ec2.md)). |
| 10–11 (connectivity) | [network](../architecture/network.md), [decision 0004](../decisions/0004-netbird-over-cloudflare-ngrok.md) | — |
| 12 (current state: WebUI → Ollama) | [status](../status.md) | Ollama was stopped when the llama.cpp workers went live (see status). |
| 16–17 (hardware, Rig 2) | [hardware](../architecture/hardware.md) | The deck says 8 cards per rig. The 2026-09-18 live inventory of Rig 1 lists 7. Rig 2 is still being built. |
| 18 (model decision) | [decision 0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md) | — |
| 19–20 (performance, R&D) | [benchmarks](../testing/benchmarks.md), [workers](../architecture/workers.md) | — |
| 21–25 (broker) | [roadmap](../project/roadmap.md) | Planned |
| 04, 26 (team, workstreams) | [charter](../project/charter.md) | — |
| 27, 30–34 (roadmap, status, backlog, next steps) | [roadmap](../project/roadmap.md) | — |
| 28–29 (testing, safety) | [test plan](../testing/test-plan.md), [threat model](../security/threat-model.md) | Some slide-29 controls aren't built yet (see threat model). |
