---
status: proposed
date: 2026-10-23
deciders:
supersedes:
superseded_by:
---

# 0010. uv and a root `pyproject.toml` for local development

## Context

The documented setup was `python3 -m pip install pytest fastapi httpx -r benchmark/requirements.txt` ([AGENTS.md](../../AGENTS.md), [getting started](../guides/getting-started.md)). On Ubuntu 24.04, Debian 12, and WSL, the system Python refuses it with `externally-managed-environment` (PEP 668). Anyone on those systems who followed the docs got a failed install and no test run. On 2026-10-22 this happened on a contributor's WSL machine.

There was also no lock file, so two people could test against different FastAPI versions.

uv was already in use around the project, but not by the repo. On 2026-10-23 both rigs had uv installed for the `ocs` user (Rig 1 0.12.7 since 2026-08-27, Rig 2 0.13.1 since 2026-10-13), used for side experiments: a uv-made `/home/ocs/.venv` and a `/root/LLM_GPU` project with its own `uv.lock` on Rig 1. Every deployed service venv was made with `python3 -m venv` ([hosts](../reference/hosts.md)).

## Options considered

1. **Keep pip, add a venv step to the docs**: works everywhere, but it's still unlocked and the dependency list stays spread across commands.
2. **uv with a root `pyproject.toml` and `uv.lock`**: one declared, locked list. `uv sync` builds `.venv`, and `uv run` uses it without activation. uv also installs a matching Python if the system one is too old.
3. **pip-tools or Poetry**: also locked, but more setup and less familiar to the team than uv.

## Decision

We chose **option 2** for local development, tests, the benchmark, and playbook rendering.

- `pyproject.toml` is a virtual project (`[tool.uv] package = false`). The `dev` group (installed by default) has pytest plus everything the tests and benchmark import. The `playbook` group has weasyprint.
- `uv.lock` is committed.
- pytest config (`pythonpath = ["."]`) lives in the same file, so `uv run pytest` finds `gateway`, `orchestrator`, and `benchmark` from the repo root.
- `scripts/check_docs.py` and `scripts/demo.py` use only the standard library and still run with plain `python3`.

## Consequences

- Good: one command (`uv sync`) gives every contributor the same locked environment, on any system with uv. Verified 2026-10-23: 32 tests pass under `uv run pytest -q`.
- Bad / accepted trade-off: contributors need uv installed. The [getting-started guide](../guides/getting-started.md) keeps a plain-venv fallback.
- Bad / accepted trade-off: the gateway and orchestrator version ranges now appear twice, in their `requirements.txt` and in `pyproject.toml`. The pyproject comment and [AGENTS.md](../../AGENTS.md) say to keep them in step.
- Out of scope: **deployment doesn't change.** EC2 and the rigs still install from `gateway/requirements.txt` and `orchestrator/requirements.txt` into `python3 -m venv` venvs ([deploy EC2](../operations/deploy-ec2.md), [deploy the rig](../operations/deploy-rig.md)). Moving the services to uv would need an operator on each host. The PyPI access it would rely on needs re-checking first: Rig 1's DNS block is documented from the old network.

## Differs from the blueprint?

No. The blueprint doesn't specify Python tooling.
