---
status: current
last_verified: 2026-10-23
---

# Mentor meeting, 2026-10-20 (summary)

| | |
|---|---|
| **Original** | [GitHub issue #28, "Meeting Notes 10/20"](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/28): the team's notes, a formal meeting report posted as a comment the same day, and a follow-up comment from John Mortensen on 2026-10-21 |
| **Author** | OCS Intelligence team (notes and report). Mortensen's comment is his own |
| **Date** | Meeting 2026-10-20, with Eddie Revollo (mentor). John Mortensen joined for parts of it |
| **What it is** | The walkthrough after the [2026-10-14 audit](./2026-10-14-mentor-audit.md): a demo, what to focus on next, the classroom use cases, and safety and handoff |

## Summary

- **Demo:** Open WebUI. Revollo described Raven, his own security product, and said he'd send it and some security test scripts. Nothing has been received or installed.
- **Central priority: a good orchestrator** (report §4). It should do routing, load balancing and scheduling, queues with priorities (interactive vs. grading), health checks, failover, controlled tool calls, job state and logs, and access control. Where to host it is open: a Mac mini, a rig, or EC2 (§4.3).
- **Failure procedures** (§5): what happens when one model goes down, when a whole rig goes down, and when the orchestrator host goes down. Prove each with a deliberate, documented drill.
- **Performance and capacity** (§3, Mortensen): can the system handle a classroom? Find the bottlenecks. Test whether a second motherboard with GPUs split into groups of 4 helps (a hypothesis). The report lists metrics to capture (§3.3).
- **Network** (§6, Mortensen): a "closed-loop" network. The report asks for that to be defined before anything is built.
- **Stress testing** (§9): a simulated classroom load, then repeated test → find the bottleneck → change one thing → retest cycles against a target that isn't defined yet.
- **Primary use case: assignment grading** (§7). Gemini runs out of tokens. Grading should cover Gists, code runners, and submissions, with classroom rubrics and student/teacher review. Also raised: a tool-call harness (§4.4) and sending images from the Jarvis presence system to a vision model (§8.1, an idea only).
- **Physical safety and upkeep** (§10–11): diagrams on the wall above the rigs, a safety guide (ESD, grounding, gloves), an antistatic mat, and a weekly inspection and cleaning procedure.
- **Handoff** (§12): change logs and a handoff path so an incoming group can pick up tasks.
- **No owners or dates were recorded** (report §13). Its priorities are recommendations.
- **Mortensen's follow-up (2026-10-21):**
  - Measure latency to the orchestrator side by side: one machine on the LAN, one over the internet.
  - Align with OCS-in-a-kit and the OCS project structure (projects, AGENTS.md scope, MJS scripts and tests).
  - Find a faster way to get source (mirrored pages, Flask, Spring) into the GPU LAN.

## Where each part is handled in our docs

| Source section | Our doc | Notes / where we differ |
|---|---|---|
| §4 orchestrator, §5 failure | [roadmap: Sprint 5 orchestrator](../project/roadmap.md#task-1-orchestrator-from-the-mac-minis) | Hosted on the Mac minis; the choice still gets a decision record |
| §3 capacity, §9 stress tests | [roadmap: Sprint 5 benchmarking](../project/roadmap.md#task-3-benchmarking), [test plan](../testing/test-plan.md) | Targets, baselines, classroom load, and the 4-GPU comparison in Sprint 5; the soak and remaining drills in Sprint 6 |
| §6 closed-loop network, Mortensen's latency and source-mirror items | [roadmap: Sprint 5](../project/roadmap.md#sprint-5-plan), [network](../architecture/network.md) | Builds on the team's [rig routing playbook](../../evidence/sprint4/2026-10-22-rig-routing.md) |
| §7 grading, §4.4 tool harness, §8.1 Jarvis | [roadmap: trimester 2](../project/roadmap.md#later-trimester-2) | Grading is the system's main purpose, planned for the start of trimester 2. It and the other two fall under the blueprint's scope lock, so each needs a decision record first. Jarvis also needs privacy authorization |
| §10–12 safety, maintenance, change logs | [roadmap: Sprint 6](../project/roadmap.md#sprint-6-plan) | |
| §2.2 Raven | [roadmap: Sprint 6](../project/roadmap.md#sprint-6-plan) | Evaluate in isolation once it arrives |
