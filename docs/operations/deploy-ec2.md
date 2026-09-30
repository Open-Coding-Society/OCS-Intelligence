---
status: draft
last_verified: 2026-09-18
---

# How to deploy EC2 (gateway + Nginx)

Brings up the admission gateway and points Nginx `/v1/` at it. These are the steps as deployed on 2026-09-18, reconstructed from the [archived gateway plan](../archive/plan-ec2-gateway.md) and [status](../status.md). Why the gateway exists: [gateway](../architecture/gateway.md).

> **Draft:** reconstructed, not re-run. Correct it the next time someone deploys.

Paths and ports: [hosts](../reference/hosts.md#ec2). Env vars: [configuration](../reference/configuration.md#admission-gateway-ec2-etcocs-gatewaygatewayenv).

## Before you start

- A root shell on EC2 ([NetBird access](../guides/netbird-access.md)).
- The rig orchestrator reachable at `http://100.75.123.203:9000` over NetBird (`curl …/healthz`).
- Nginx and the Certbot certificate for `ai.opencodingsociety.com` already set up.

## 1. Gateway

EC2 can reach PyPI, so use a normal venv.

```bash
mkdir -p /opt/ocs-gateway /var/lib/ocs-gateway /etc/ocs-gateway
cp -r gateway /opt/ocs-gateway/
python3 -m venv /opt/ocs-gateway/.venv
/opt/ocs-gateway/.venv/bin/pip install -r /opt/ocs-gateway/gateway/requirements.txt
cp infra/ec2/gateway.env.template /etc/ocs-gateway/gateway.env
# edit: PUBLIC_API_KEYS = the student key (same value as on the rig). Never leave it empty: empty accepts any key.
chmod 0600 /etc/ocs-gateway/gateway.env
cp infra/ec2/ocs-gateway.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now ocs-gateway
curl http://127.0.0.1:9100/healthz
```

Keep `--workers 1` in the unit. The wait line lives in process memory.

## 2. Nginx

Always back up first.

```bash
cp /etc/nginx/sites-available/llm-relay /etc/nginx/sites-available/llm-relay.bak.$(date -u +%Y%m%dT%H%M%SZ)
```

Make the live site match [`infra/ec2/llm-relay-nginx.conf`](../../infra/ec2/llm-relay-nginx.conf):

- `location /v1/` → `proxy_pass http://127.0.0.1:9100;`, buffering off, `proxy_read_timeout` and `proxy_send_timeout` `3600s`
- `location = /healthz` → `http://127.0.0.1:9100/healthz`
- `location /` unchanged (Open WebUI on the rig)

```bash
nginx -t && systemctl reload nginx
```

Don't edit other vhosts on the box.

## Check it worked

```bash
curl -sS https://ai.opencodingsociety.com/healthz                # {"status":"ok"}
curl -sS -o /dev/null -w "%{http_code}\n" https://ai.opencodingsociety.com/v1/models   # 401
python3 scripts/demo.py        # from your machine: auth, completion, 7-way queue → one 429
```

Save the results as a new file in [`evidence/`](../../evidence/evidence.md).

## Roll back

Restore the Nginx backup, `nginx -t && systemctl reload nginx`, then `systemctl stop ocs-gateway`. Nginx `/v1/` then goes straight to the rig again, with no wait line.
