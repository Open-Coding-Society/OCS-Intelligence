---
date: 2026-10-29
---

# EC2 gateway: Rig 2 lane for `qwen3.6:35b-a3b` (2026-10-29)

Run over NetBird SSH (`root@ip-172-31-42-43.netbird.cloud`, `root@ocs-intelligence-rig2.netbird.cloud`, `root@ocs-intelligence-rig.netbird.cloud`) from an operator's macOS peer (NetBird 0.82.0), about 10:30–11:00 PDT. This is a record: don't edit it. Decision: [0012](../../docs/decisions/0012-gateway-routes-rig2-with-stored-key.md). Keys are never shown.

## Before

- From EC2, Rig 2's orchestrator answered `GET /healthz` with `200 {"status":"ok"}` and listed `qwen3.6:35b-a3b`, but returned **401** to the student key. Rig 2's `PUBLIC_API_KEYS` holds two keys: the temporary operator key (same as `/root/ocs-deploy/temp-public-key`) and the key in Open WebUI's `config` table on Rig 1 (compared in place, read-only).
- The deployed gateway's `config.py` (default `GROUP_B_MODEL_ALIAS` = `gemma4:26b`) and `lanes.py` (no optional lane B) differed from the repo; the other files matched by MD5.
- No upstream connections and no `POST /v1/chat` in the 10 minutes before the restart.

## Change (EC2 only; Rig 2 untouched)

1. Backups: `/opt/ocs-gateway/gateway.bak-20261029T175308Z`, `/etc/ocs-gateway/gateway.env.bak-20261029T175308Z`.
2. Copied the repo's `gateway/*.py` into `/opt/ocs-gateway/gateway/` (MD5s match the repo). `scp` failed (`Received message too long`), so the copy went through `tar` over `ssh`.
3. Appended to `/etc/ocs-gateway/gateway.env` (mode `0600`): `RIG2_MODEL_ALIAS=qwen3.6:35b-a3b`, `RIG2_UPSTREAM_URL=http://100.75.127.192:9000`, `RIG2_UPSTREAM_API_KEY=<Rig 2's Open WebUI key>`, `RIG2_INFLIGHT=2`.
4. `systemctl restart ocs-gateway` at 17:53:56 UTC. Log: `Rig 2 lane: upstream=http://100.75.127.192:9000 model=qwen3.6:35b-a3b inflight=2 key=set`. `/healthz` 200.

## Result (public URL, student key only)

| Check | Result |
|---|---|
| `GET /v1/models` | `['qwen3.8:27b', 'gemma4:26b', 'qwen3.6:35b-a3b']` |
| `qwen3.6:35b-a3b`, blocking, "Reply with exactly: rig2 ok", `max_tokens` 400 | 200 in 6.27 s, content `rig2 ok`, 17 prompt + 130 completion tokens |
| `qwen3.6:35b-a3b`, streaming, count 1 to 5 | 189 `data:` chunks |
| `gemma4:26b` (Rig 1), "Say hi." | 200 in 2.23 s |
| Wrong key | 401 |

## Roll back

```bash
cp -a /opt/ocs-gateway/gateway.bak-20261029T175308Z/. /opt/ocs-gateway/gateway/
cp -p /etc/ocs-gateway/gateway.env.bak-20261029T175308Z /etc/ocs-gateway/gateway.env
systemctl restart ocs-gateway
```
