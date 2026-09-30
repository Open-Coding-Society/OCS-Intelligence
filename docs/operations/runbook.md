---
status: draft
last_verified: 2026-09-29
---

# Runbook

Procedures for operating the service. The blueprint (§15) requires at least eight procedures, and the handoff test is whether a new operator can restore service from this page alone. Commands are derived from the code and units. **None of these procedures has been drilled yet.** Mark each one `tested YYYY-MM-DD` once it has, with evidence.

Hosts and ports: [hosts](../reference/hosts.md). Shell access: [NetBird access](../guides/netbird-access.md).

## Daily check (5 minutes)

From your machine:

```bash
curl -sS https://ai.opencodingsociety.com/healthz        # gateway alive
./scripts/request.sh "Reply with exactly: ok"            # one real completion through the whole path
```

On the rig:

```bash
systemctl is-active ocs-llama-a ocs-llama-b ocs-orchestrator
curl -s http://127.0.0.1:9000/readyz
nvidia-smi --query-gpu=index,temperature.gpu,memory.used,power.draw --format=csv
```

Also look for: errors in the logs (below), key abuse (many 401s or 429s from one IP in the Nginx access log), and open incidents.

## 1. Verify host, disk, network, and GPUs

```bash
# rig
nvidia-smi -L            # every card listed; compare with the hardware inventory
df -h / /srv /opt
netbird status           # EC2 peer connected
```

Compare the card list with [hardware](../architecture/hardware.md).

## 2. Start everything

The order matters: workers, then orchestrator, then gateway.

```bash
# rig
systemctl start ocs-llama-a ocs-llama-b      # A can take minutes to load
systemctl start ocs-orchestrator
# EC2
systemctl start ocs-gateway
```

TODO: start from a *pinned release*. There are no tagged releases yet ([roadmap](../project/roadmap.md#mvp-checklist)).

## 3. Confirm health

```bash
curl -s http://127.0.0.1:9000/readyz                                   # rig
curl -sS https://ai.opencodingsociety.com/healthz                      # public
python3 scripts/demo.py --skip-queue                                   # your machine
```

## 4. Rotate the student key

There's one shared key today. Per-student issue and revoke aren't built.

1. Generate a new key, for example `echo "sk-ocs-$(openssl rand -hex 24)"`. Any string works. The gateway and orchestrator compare it exactly.
2. On **EC2**, set `PUBLIC_API_KEYS` in `/etc/ocs-gateway/gateway.env`, then `systemctl restart ocs-gateway`. This drops anyone waiting in line.
3. On the **rig**, set the same value in `/etc/ocs-orchestrator/orchestrator.env`, then `systemctl restart ocs-orchestrator`.
4. Check: the old key gets 401 and the new key gets 200 on `/v1/models`.
5. Share the new key with students out of band. Never in git or issues.

`PUBLIC_API_KEYS` accepts a comma-separated list, so you can add the new key alongside the old one first and remove the old one later.

## 5. Drain and restart one worker

TODO: impossible without an outage today. Each model has exactly one worker, so restarting `ocs-llama-a` makes `qwen3.8:27b` return 503 until it reloads. Tell users first, or do it outside class hours:

```bash
systemctl restart ocs-llama-a && journalctl -u ocs-llama-a -f     # wait for the model to load
```

## 6. Roll back

TODO: there are no tagged releases. What exists:

- **Nginx:** restore the latest `/etc/nginx/sites-available/llm-relay.bak.*`, then `nginx -t && systemctl reload nginx`.
- **Back to Ollama (last resort):** `systemctl stop ocs-orchestrator ocs-llama-a ocs-llama-b`, check VRAM is free, then `systemctl start ollama`. Open WebUI works again. **`/v1/` won't work**, because the gateway expects the orchestrator.

## 7. Capture an incident bundle

```bash
T=$(date -u +%Y%m%dT%H%M%SZ)
journalctl -u ocs-llama-a -u ocs-llama-b -u ocs-orchestrator --since "1 hour ago" > /tmp/incident-$T-rig.log   # rig
journalctl -u ocs-gateway --since "1 hour ago" > /tmp/incident-$T-ec2.log                                     # EC2
nvidia-smi -q > /tmp/incident-$T-gpu.txt
```

Remove keys from the logs, then write up what happened, when, the impact, and the fix in `evidence/`. TODO: named owner and contact list ([Gate 0](../project/roadmap.md#gate-0-discovery-packet)).

## 8. Emergency shutdown

- **Gateway level** (stops all API traffic, leaves the rig up): `systemctl stop ocs-gateway` on EC2. `/v1/` then returns 502. Open WebUI keeps working.
- **Everything public:** `systemctl stop nginx` on EC2.
- **Host level** (stops the GPUs): `systemctl stop ocs-orchestrator ocs-llama-a ocs-llama-b` on the rig, and `docker stop` the Open WebUI container if needed.

The blueprint's stop-immediately triggers (heat, smoke, electrical problems, data exposure, a leaked secret, losing admin control): shut down at host level, save logs, isolate the machine, file an incident, and restart only after an owner signs off.

## Logs

| Where | Command |
|---|---|
| Workers | `journalctl -u ocs-llama-a -f` (rig) |
| Orchestrator | `journalctl -u ocs-orchestrator -f` (rig) |
| Gateway | `journalctl -u ocs-gateway -f` (EC2) |
| Nginx | `/var/log/nginx/access.log`, `error.log` (EC2) |
