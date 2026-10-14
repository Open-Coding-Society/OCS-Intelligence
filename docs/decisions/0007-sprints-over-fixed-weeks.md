---
status: proposed
date: 2026-10-14
deciders: Requested by Yash Parikh. Not yet agreed by the team or the mentor.
---

# 0007. Track work in sprints, not fixed weeks

## Context

[Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) §7 lays out a six-week campaign in which each week has fixed exit criteria. In practice some work takes longer than a week, and some work the team is doing isn't in the blueprint's week list. Since Week 1, both rigs have been rebuilt and rewired, and VR-related work has been added. Naming everything by week (for example `evidence/week1/`) makes it look as if work is on or off schedule when the week number doesn't reflect what's being done.

## Options considered

1. **Keep fixed weeks** (blueprint): the plan is easy to compare against the blueprint, but labels drift from reality whenever a week's work runs long.
2. **Sprints of variable length**: each sprint has one goal and closes on evidence, not on a date.

## Decision

We'd track work as **sprints**, listed in the [roadmap](../project/roadmap.md#sprints):

| Sprint | Goal |
|---:|---|
| 1 | Prove one lane end to end (the blueprint's Week 1) |
| 2 | VR-related work (owner: yashpatil321) |
| 3 | Resolve both rigs after they were rebuilt and rewired |
| 4 | Get inference working on both rigs |

## Consequences

- Good: labels match what the team is actually doing, and a long piece of work doesn't throw off the numbering.
- Bad / accepted trade-off: it's harder to see at a glance how far we are from the blueprint's six-week schedule. The roadmap keeps the blueprint's week table so the two can be compared.
- The Friday one-page report continues unchanged (`evidence/weekly/YYYY-Www.md`). Its checkpoint line names the current sprint.
- Sprint material goes in `evidence/sprintN/`. `evidence/week1/` was renamed `evidence/sprint1/`. The files themselves weren't changed.
- Follow-up work: give Sprints 2–4 exit criteria once their scope is written down.

## Differs from the blueprint?

Yes, §7, which uses six fixed weeks with fixed exit criteria. The blueprint's exit criteria still apply. Only the time-boxing changes. To switch back: the mentor asks for weekly checkpoints, or sprints keep slipping with no evidence that would have shown up under weekly gates.
