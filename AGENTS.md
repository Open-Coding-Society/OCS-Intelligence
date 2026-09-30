# AGENTS.md

Instructions for coding agents (Claude Code, Codex, Cursor, Copilot, etc.) working in this repo. People are welcome to read it too.

## What this is

OCS Intelligence is a student-built, OpenAI-compatible coding API at `https://ai.opencodingsociety.com/v1`, served from donated GTX 1070 GPUs. A request goes EC2 Nginx → EC2 admission gateway (`gateway/`) → NetBird → rig orchestrator (`orchestrator/`) → a llama.cpp worker. Full picture: [`docs/architecture/overview.md`](./docs/architecture/overview.md).

## Where to look

| Need | Go to |
|---|---|
| Any doc | [`docs/docs.md`](./docs/docs.md), the index |
| What is deployed right now | [`docs/status.md`](./docs/status.md). Check its `last_verified` date. |
| Hosts, ports, paths | [`docs/reference/hosts.md`](./docs/reference/hosts.md) |
| Env vars | [`docs/reference/configuration.md`](./docs/reference/configuration.md) |
| Why something is the way it is | [`docs/decisions/`](./docs/decisions/decisions.md) |
| The mentor's plan we measure against | [`docs/sources/`](./docs/sources/sources.md) |

## Repo map

| Path | What | Runs on |
|---|---|---|
| `gateway/` | FastAPI admission gateway: auth, per-model wait line, proxy | EC2, `127.0.0.1:9100` |
| `orchestrator/` | FastAPI router: model → worker, injects worker key | GPU rig, `:9000` |
| `infra/ec2/`, `infra/rig/` | systemd units, env templates, Nginx site | copied to each host by hand |
| `benchmark/` | Speed benchmark + Pareto chart against the public API | your machine |
| `scripts/` | `demo.py` (live walkthrough), `request.sh`, `check_docs.py` | your machine |
| `tests/` | Offline tests (no network, no GPU) | your machine |
| `docs/` | Documentation | — |
| `evidence/` | Dated, append-only proof: captures, results, weekly reports | — |

## Commands

```bash
python3 -m pip install pytest fastapi httpx -r benchmark/requirements.txt
python3 -m pytest -q                 # all offline tests
python3 scripts/check_docs.py        # doc headers, links, index reachability
python3 scripts/demo.py              # live API walkthrough (needs .env)
```

Run both `pytest` and `check_docs.py` before you commit.

## Rules

- **Never commit secrets.** `.env` is gitignored. Env templates use `CHANGE_ME`. This repo is public.
- **You can't reach the live machines from here.** The rig and EC2 are reachable only over NetBird with browser SSO ([`docs/guides/netbird-access.md`](./docs/guides/netbird-access.md)). Don't claim a deployed state you haven't seen. Point to `docs/status.md` and its date.
- **Files in `infra/` mirror what's deployed.** If you change one, the change isn't live until an operator copies it to the host. Say so.
- **The gateway must run with `--workers 1`.** The wait line lives in process memory, so two workers would mean two separate lines.
- **Workers bind `127.0.0.1` only.** Only the orchestrator talks to them.

## Documentation rules

Full rules: [`docs/conventions.md`](./docs/conventions.md). The short version:

1. **One fact, one place.** Link to it, don't copy it. The table of canonical homes is in the conventions doc.
2. **Every doc under `docs/` has a header** with `status` (`draft | current | superseded`) and `last_verified: YYYY-MM-DD`. Only set `last_verified` to a date when you actually checked the content against the code or the live system. Reading the code counts for code-derived docs. It doesn't count for claims about live machines.
3. **Put new docs in the right folder:** how-to → `docs/guides/` or `docs/operations/`; a fact to look up → `docs/reference/`; how/why → `docs/architecture/`; X over Y → `docs/decisions/NNNN-*.md`; proof → `evidence/`. Copy a template from `docs/_templates/`.
4. **Link every new doc** from `docs/docs.md` or its folder index.
5. **Update docs in the same commit as the code change.**
6. **If you change something the blueprint specifies, write a decision record** with `status: proposed`. Don't mark decisions `accepted` yourself. An accepted decision that differs from the blueprint carries `blueprint_review: pending` until someone reviews it.
7. **Evidence files are never edited after they're committed.** Add a new dated file instead.
