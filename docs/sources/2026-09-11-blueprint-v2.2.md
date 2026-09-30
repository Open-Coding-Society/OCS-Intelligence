---
status: current
last_verified: 2026-09-29
---

# Build Blueprint v2.2 + PROMX-OCS-001 (summary)

| | |
|---|---|
| **Original** | [`2026-09-11-blueprint-v2.2.pdf`](./2026-09-11-blueprint-v2.2.pdf) (21 pages) |
| **Author** | Eduardo "Eddie" Revollo, Founder/CEO, Prometheus (our mentor) |
| **Date** | 2026-09-11 |
| **What it is** | The mentor's plan for the project: a 19-page plain-language blueprint (Student Edition v2.2), then the 2-page technical spec PROMX-OCS-001 Rev 0.1 DRAFT. Its own words: "a planning document, not an authorization to build yet." |

## Summary

- **The one rule:** "don't approve a cool demo. Approve a service you can measure, attack, recover, explain, and hand to someone else." Every checkpoint closes with evidence: a file, a number, a screenshot, a log, or a signed decision.
- **Mission:** free coding-assistant access for students, so a paid subscription becomes optional.
- **The deal:** a bounded 6-week campaign, 6 student builders in 3 pairs, about 6 hours of mentor time in total. The mentor advises; he is not the help desk or on call.
- **Gate 0 (§2):** before installing anything, collect a discovery packet: hardware manifest, host baseline, network diagram, ownership record, data boundary, safety check. If nobody owns root, the network, the physical rack, and long-term operation, stop.
- **Success targets (§3), to be tuned after the week-1 baseline:** ≥99% availability in pilot hours; 8 concurrent users sustained, 24 degrading gracefully; P95 time to first token ≤15 s at 8 users; ≥70% on a coding test set; 100% of secret-leak probes blocked; one dead card recovered in ≤10 min; a new operator can restore everything from the runbook alone.
- **MVP checklist (§3):** streaming OpenAI-style API; per-student keys with quotas and revocation; a health page; logs that don't store prompts; reproducible deploys with rollback; published limitations.
- **Architecture (§4, spec p.1–2):** **one 7–8B Q4 model copy per GPU (8 replicas)**, "copy the model across cards; don't split one model across cards." Gateway (TLS, per-user keys, rate limits, health-aware routing, bounded queue) → llama.cpp `llama-server`. Monitoring with Prometheus + DCGM. llama.cpp over vLLM because stock vLLM needs compute capability 7.0+ and the GTX 1070 is 6.1.
- **Model bake-off (§5):** Qwen 7–8B, Llama 8B, Phi, DeepSeek 7B, run on a frozen task set and graded blind. Weights: quality 35%, speed 25%, reliability 15%, safety 15%, license 10%. Publish a decision record.
- **Repo (§6):** one repo, protected main, pinned versions, evidence committed next to the code. Suggested layout: `docs/ infra/ gateway/ clients/ tests/{functional,quality,load,chaos} evidence/ scripts/`. Three environments: DEV, STAGE (one lane), PILOT (all lanes). Two-person review on gateway, auth, firewall, and logging changes.
- **Six-week plan (§7):** W0 discovery → W1 prove one lane → W2 pick the model → W3 scale up and lock down → W4 observe and attack → W5 pilot → W6 approve or stop. One-page Friday report. **Scope lock:** no RAG, agents, vision, fine-tuning, school-system integrations, or **public-internet exposure** during the campaign.
- **Roles (§8–9):** Pair A model + runtime, Pair B gateway + client, Pair C reliability + safety. Mentor meetings are capped. An escalation to the mentor needs 6 things (want, got, minimal repro, logs, two attempts, the decision needed). If unscheduled mentor time goes over 2 h/week, feature work pauses.
- **Safety (§10), stress tests (§11), simulations (§12):** a controls table; test ladder smoke → baseline → sustained → burst → soak → long-context → abuse; five drills: SPECTER (capacity), FORGE (component loss), RED TEAM (abuse), SOVEREIGN (governance), ORACLE (continuity).
- **Quality (§13):** a frozen 56-task set in 7 categories, blind-graded 0–2 by two reviewers. Zero catastrophic security failures allowed.
- **Approval (§14), operations (§15), kill/pivot (§16):** a decision packet for the dean/sponsor; outcomes GO / LIMITED GO / NO-GO; a runbook of at least 8 procedures; a 5-minute daily operator check; explicit stop and pivot triggers.

## Where each part is handled in our docs

| Blueprint section | Our doc | Where we differ |
|---|---|---|
| Why / decision / scope (§1–3) | [charter](../project/charter.md) | — |
| Gate 0 discovery packet (§2) | [roadmap](../project/roadmap.md), [phase-1 discovery record](../archive/phase1-discovery.md) | — |
| Success targets, MVP checklist (§3) | [charter](../project/charter.md) | — |
| Architecture: one replica per GPU (§4) | [overview](../architecture/overview.md), [workers](../architecture/workers.md) | **Yes:** we split one 27B model across 5 GPUs → [decision 0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md) |
| llama.cpp over vLLM (§4) | [decision 0001](../decisions/0001-llama-cpp-over-vllm.md) | — |
| Bake-off (§5) | [roadmap](../project/roadmap.md), [benchmarks](../testing/benchmarks.md) | Not run yet. The 27B was picked before a bake-off (see 0002). |
| Repo layout, environments, release rules (§6) | [conventions](../conventions.md), this repo's layout | `infra/` and `evidence/` adopted. `clients/` and the tests subfolders will be added when needed. |
| Six-week plan (§7) | [roadmap](../project/roadmap.md) | — |
| Roles (§8–9) | [charter](../project/charter.md) | We run 7 workstreams (deck slide 26), not 3 pairs |
| Safety controls, data rules (§10) | [threat model](../security/threat-model.md), [data policy](../security/data-policy.md) | **Yes:** public endpoint → [decision 0006](../decisions/0006-public-endpoint.md) |
| Stress tests, simulations, quality (§11–13) | [test plan](../testing/test-plan.md) | — |
| Approval packet (§14) | [roadmap](../project/roadmap.md) | — |
| Runbook, daily check (§15) | [runbook](../operations/runbook.md) | — |
| Kill / pivot (§16) | [charter](../project/charter.md) | — |
| Glossary (p.2–3) | [glossary](../project/glossary.md) | — |
