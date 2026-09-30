---
status: current
last_verified: 2026-09-29
---

# OCS Intelligence documentation

Start here. Every doc in the repo is linked from this page, either directly or through a folder index. To add a doc, read [conventions](./conventions.md) first.

**New to the project?** Read [getting started](./guides/getting-started.md), then [architecture overview](./architecture/overview.md).
**What's running right now?** See [status](./status.md).

## Project

| Doc | What it answers |
|---|---|
| [Charter](./project/charter.md) | Why the project exists, scope, non-goals, success targets, who's on the team |
| [Roadmap](./project/roadmap.md) | The six-week campaign, phases, and what's planned but not built |
| [Glossary](./project/glossary.md) | Terms and abbreviations |

## Guides (how to do things)

| Doc | For |
|---|---|
| [Getting started](./guides/getting-started.md) | New team members: the project, the repo, and your first request |
| [Using the API](./guides/using-the-api.md) | Anyone calling the API: curl, Python, GitHub Copilot |
| [NetBird access](./guides/netbird-access.md) | Operators: SSH to the rig and EC2 |

## Architecture (how it works and why)

| Doc | Covers |
|---|---|
| [Overview](./architecture/overview.md) | The whole system on one page: request path, components, what's planned |
| [Admission gateway](./architecture/gateway.md) | The EC2 wait line: why it exists and how it works |
| [Orchestrator](./architecture/orchestrator.md) | The rig-side model router |
| [Workers](./architecture/workers.md) | llama.cpp, the 5+2 GPU split, models |
| [Network](./architecture/network.md) | EC2, Nginx, NetBird, and the tunnels that didn't work |
| [Hardware](./architecture/hardware.md) | The rigs, GPU inventory, PCIe topology |
| [Decisions](./decisions/decisions.md) | Why we chose X over Y (decision records) |

## Reference (facts to look up)

| Doc | Contents |
|---|---|
| [API](./reference/api.md) | Endpoints, models, error codes |
| [Configuration](./reference/configuration.md) | Every environment variable for each service |
| [Hosts](./reference/hosts.md) | Machines, IPs, ports, paths on disk, service names |

## Operations (running the service)

| Doc | Covers |
|---|---|
| [Runbook](./operations/runbook.md) | Day-to-day and emergency procedures |
| [Deploy the rig](./operations/deploy-rig.md) | CUDA, llama.cpp, workers, orchestrator |
| [Deploy EC2](./operations/deploy-ec2.md) | Admission gateway and Nginx |

## Security and testing

| Doc | Covers |
|---|---|
| [Threat model](./security/threat-model.md) | Risks, current controls, known gaps |
| [Data policy](./security/data-policy.md) | What data is allowed, what's logged |
| [Test plan](./testing/test-plan.md) | Smoke → soak tests and the five failure drills |
| [Benchmarks](./testing/benchmarks.md) | How to run the speed benchmark and read the Pareto chart |

## Records

| Folder | Contents |
|---|---|
| [Status](./status.md) | The only "what's running right now" page |
| [Evidence](../evidence/evidence.md) | Dated captures, benchmark results, weekly reports |
| [Sources](./sources/sources.md) | Original documents we build from: mentor blueprint, presentation decks |
| [Archive](./archive/archive.md) | Superseded plans, kept for history |

## For agents

Instructions for coding agents are in [`AGENTS.md`](../AGENTS.md). Run `python3 scripts/check_docs.py` after editing any doc.
