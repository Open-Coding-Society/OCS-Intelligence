# OCS-Intelligence

Inference infrastructure for the Open Coding Society at `https://ai.opencodingsociety.com`.

Seven GTX 1070s cannot run a classroom of Copilot tabs at once. An admission gateway on EC2 holds extra students in a fair wait line and only forwards as many inferences as the rig can actually serve. GitHub Copilot still uses a normal OpenAI `/v1/` API. Open WebUI stays at `/`.

**How the wait line works, and why it is there:** [`GATEWAY.md`](./GATEWAY.md)

## Docs

- **[`GATEWAY.md`](./GATEWAY.md)** — inner workings of the EC2 admission queue.
- **[`USAGE.md`](./USAGE.md)** — how to call the API, Copilot setup, and **real captured responses**.
- **[`STATUS.md`](./STATUS.md)** — live architecture, deployed configs, open issues.
- **[`CURSOR_HANDOFF.md`](./CURSOR_HANDOFF.md)** — original execution plan.

## Quick start

```bash
cp .env.example .env   # set OCS_API_KEY (file is gitignored)
python3 scripts/demo.py --pause          # live walkthrough
python3 scripts/demo.py                  # health, auth, 0.5b, 7-way queue
python3 scripts/demo.py --quality        # also hit the 27B model
```

Or a single curl:

```bash
set -a && source .env && set +a

curl -sS "$OCS_BASE_URL/models" \
  -H "Authorization: Bearer $OCS_API_KEY"
```

Models: `qwen2.5:0.5b` (fast) and `qwen3.8:27b` (quality).

## Repo layout

- [`scripts/demo.py`](./scripts/demo.py) — live demo / test walkthrough against the public API.
- [`orchestrator/`](./orchestrator/) — FastAPI router (deployed on the GPU rig).
- [`systemd/`](./systemd/) — worker, orchestrator, and gateway units.
- [`llm-relay-nginx.conf`](./llm-relay-nginx.conf) — live EC2 Nginx site (`/v1/` → localhost:9100).
- [`archive/`](./archive/) — superseded planning docs.
