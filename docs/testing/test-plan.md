---
status: draft
last_verified: 2026-09-29
---

# Test plan

How we prove the service works and fails gracefully. Based on blueprint §11–13. "The service passes only if it fails gracefully." Each run records its setup, model and llama.cpp commit, temperatures, VRAM, queue depth, speed, and errors, and goes into [`evidence/`](../../evidence/evidence.md).

## Offline tests (in the repo)

```bash
python3 -m pytest -q
```

| File | Covers |
|---|---|
| [`tests/test_lanes.py`](../../tests/test_lanes.py) | Gateway lanes: waiter cap, FIFO, disconnect handling |
| [`tests/test_benchmark.py`](../../tests/test_benchmark.py) | Benchmark metrics, workloads, Pareto chart |

As the suites below get built, add them under `tests/` in the blueprint's layout (`tests/functional/`, `tests/quality/`, `tests/load/`, `tests/chaos/`).

## Load ladder

| Test | Shape | Passes when | State |
|---|---|---|---|
| Smoke | 1 user, 20 prompts | Everything valid; streaming works | Partial: the 9-check [e2e run](../../evidence/captures/2026-09-17-public-api-e2e.md) |
| Baseline | 1 lane, fixed 30-task set | No out-of-memory; numbers recorded | Speed only ([benchmarks](./benchmarks.md)). No task set yet. |
| Sustained | 8 users, 30 min | < 1% errors; P95 TTFT ≤ 15 s | Not run |
| Burst | 24 users, 5 min | Queue forms politely (429); nothing crashes | Partial: the [7-way check](../../evidence/captures/2026-09-18-gateway-concurrency.md) |
| Soak | 8 users, 4 h | No memory creep, no heat shutdown | Not run |
| Long context | Max context | Memory bounded; oversized input rejected cleanly | Not run |
| Abuse | Rapid-fire, oversized, forged keys | Limits hold; every attempt logged | Partial: forged keys → 401 ([evidence](../../evidence/captures/2026-09-18-gateway-concurrency.md)) |

With the current capacity (1 quality + 2 fast in flight), the 8-user targets are expected to fail. That's the point of measuring. See [0002](../decisions/0002-sharded-27b-over-per-gpu-replicas.md).

## Failure drills

| Drill | What we do | What should happen | State |
|---|---|---|---|
| SPECTER (capacity) | Whole class at once | Fair queue, bounded wait, no crash | Not run |
| FORGE (component loss) | Kill a worker or GPU mid-test | Router drops it; everyone else keeps working | Not run. With one worker per model, the affected model goes down. |
| RED TEAM (abuse) | Injection, giant contexts, a stolen key | No tools to abuse; quotas hold; key revoked; logged | Not run ([threat model](../security/threat-model.md)) |
| SOVEREIGN (governance) | "Who owns the data, and who can shut this off?" | Named owners, evidence on file, a working kill switch | Not run ([runbook §8](../operations/runbook.md#8-emergency-shutdown)) |
| ORACLE (continuity) | The lead disappears | A new operator restores service from the runbook alone | Not run |

## Quality

A frozen 56-task set, blind-graded 0–2 by two reviewers. Pass: ≥ 70%, with zero catastrophic security or secret-leak failures. **Not built yet.**

| Category | Tasks |
|---|---:|
| Explain code | 8 |
| Debug | 10 |
| Write tests | 8 |
| Refactor | 6 |
| Security | 6 |
| Honesty (admits uncertainty, no invented APIs) | 6 |
| Abuse / refusal | 6 |

## Stop a test immediately if

Sustained heat past the hardware limit, electrical problems, smoke or a burning smell, cooling failure, repeated out-of-memory, the system freezing or resetting, one user's data visible to another, a leaked secret, or lost admin control. Save the logs, isolate the machine, file an incident, and restart only after an owner signs off.
