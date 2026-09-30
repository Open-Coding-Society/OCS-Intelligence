# OCS-Intelligence

Free, student-built AI coding help for the Open Coding Society, served from donated GTX 1070 GPUs at `https://ai.opencodingsociety.com`.

Students point GitHub Copilot (or any OpenAI client) at `/v1`. An admission gateway on EC2 holds extra requests in a fair wait line, so the GPUs only run what they can actually serve. Open WebUI stays at `/`.

```text
Copilot / curl ─HTTPS─▶ EC2 Nginx ─▶ admission gateway ─NetBird─▶ rig orchestrator ─▶ llama.cpp workers (GTX 1070s)
```

## Documentation

**Start at [`docs/docs.md`](./docs/docs.md).** Common entry points:

- [Getting started](./docs/guides/getting-started.md): for new team members
- [Using the API](./docs/guides/using-the-api.md): curl, Python, Copilot
- [Architecture overview](./docs/architecture/overview.md): how it all fits together
- [Status](./docs/status.md): what's running right now
- [Decisions](./docs/decisions/decisions.md): why it's built this way
- [Conventions](./docs/conventions.md): how to write and add docs

Coding agents: read [`AGENTS.md`](./AGENTS.md).

## Quick start

```bash
cp .env.example .env                 # set OCS_API_KEY (ask an operator; .env is gitignored)
python3 scripts/demo.py --pause      # live walkthrough: health, auth, a completion, the wait line
./scripts/request.sh "Explain recursion in one sentence."
```

Models: `qwen2.5:0.5b` (fast) and `qwen3.8:27b` (quality, reasoning, slower).

## Repo layout

| Path | What |
|---|---|
| [`gateway/`](./gateway/) | EC2 admission gateway (FastAPI) |
| [`orchestrator/`](./orchestrator/) | Rig-side model router (FastAPI) |
| [`infra/`](./infra/) | systemd units, env templates, and the Nginx site for [`ec2/`](./infra/ec2/) and [`rig/`](./infra/rig/) |
| [`benchmark/`](./benchmark/) | Speed benchmark and Pareto chart ([guide](./docs/testing/benchmarks.md)) |
| [`scripts/`](./scripts/) | `demo.py`, `request.sh`, `check_docs.py` |
| [`tests/`](./tests/) | Offline tests: `python3 -m pytest -q` |
| [`docs/`](./docs/docs.md) | Documentation |
| [`evidence/`](./evidence/evidence.md) | Dated, append-only proof: captures, benchmark runs, weekly reports |
