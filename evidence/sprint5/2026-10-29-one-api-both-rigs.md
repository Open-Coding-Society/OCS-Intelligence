---
type: playbook
date: 2026-10-29
title: One API, both rigs
subtitle: The public API now serves Rig 2's qwen3.6:35b-a3b with the same student key, and the repo's infra/ matches what the three hosts actually run.
sprint: 5
state: done
---

# One API, both rigs

Until today, `https://ai.opencodingsociety.com/v1` only reached Rig 1. Rig 2's faster MoE model, `qwen3.6:35b-a3b`, was only in Open WebUI, which connects to Rig 2 directly and skips the EC2 wait line. Rig 2 also rejected the student key. We added a third lane to the EC2 admission gateway. It sends requests for `qwen3.6:35b-a3b` to Rig 2's orchestrator, and swaps the caller's student key for a Rig 2 key stored on EC2. That key is the one Open WebUI already uses, so no new key was made and nothing on Rig 2 changed. Since 2026-10-29 17:53 UTC, one base URL and one key reach all three models, and the model name picks the rig. In the same session, every service file, config file and env file on the three hosts was copied into `infra/`, with keys replaced by `CHANGE_ME`. Doing that turned up config drift, and showed that the shared student key has been in this public repo's git history since 2026-09-17.

## At a glance

| | |
|---|---|
| Goal | Reach Rig 2's model through EC2 with the one student key; make `infra/` a true copy of what's deployed |
| Outcome | Done. `/v1/models` lists `qwen3.8:27b`, `gemma4:26b`, `qwen3.6:35b-a3b`; Rig 2 answers through the gateway; `infra/` matches all three hosts except key values |
| Where | EC2 (`/opt/ocs-gateway/gateway/`, `/etc/ocs-gateway/gateway.env`, `ocs-gateway.service`). Rig 1 and Rig 2 read-only. Repo: `gateway/`, `tests/`, `infra/`, docs |
| Why | [Decision 0012](../../docs/decisions/0012-gateway-routes-rig2-with-stored-key.md) (proposed), following up [0009](../../docs/decisions/0009-rig2-moe-behind-open-webui.md) |

| Piece | Status |
|---|---|
| Gateway Rig 2 lane (`RIG2_*` settings) | Live on EC2 since 2026-10-29 17:53:56 UTC |
| Rig 2 orchestrator | Unchanged. Its existing Open WebUI key is now also used by the gateway |
| `infra/` env templates | Exact copies of the six live env files, keys as `CHANGE_ME` |
| `infra/` units, Nginx sites, scripts | 12 files byte-identical to the hosts; 5 added that were missing |
| Real key values | Only in the operator's local `.env` (gitignored, mode `0600`) |
| Student key in git history | Found; redacted from the current file. **Still public until rotated** |
| Open WebUI's direct Rig 2 connection | Still there (not changed) |

## The system, before and after

Before, the gateway had one upstream. It passed the caller's key through, and Rig 1's orchestrator checked that key a second time.

```text
BEFORE
 student ──key S──▶ Nginx ─▶ gateway (EC2) ──key S──▶ Rig 1 orchestrator ─▶ qwen3.8:27b / gemma4:26b
                              checks S                 checks S again
 Open WebUI ──key W──────────────────────────────────▶ Rig 2 orchestrator ─▶ qwen3.6:35b-a3b
                                                       checks W  (S → 401)
```

After, the gateway picks the upstream by model name. On the Rig 2 path it **translates the key**: the student's key `S` is checked at EC2 and goes no further, and the gateway sends the stored key `W` to Rig 2.

```text
AFTER
                                ┌─ lane qwen3.8:27b     (1 running + 4 waiting) ──key S──▶ Rig 1 :9000
 student ──key S──▶ Nginx ─▶ gateway checks S ─┼─ lane gemma4:26b      (2 running + 4 waiting) ──key S──▶ Rig 1 :9000
                                └─ lane qwen3.6:35b-a3b (2 running + 4 waiting) ──key W──▶ Rig 2 :9000
 Open WebUI ──key W───────────────────────────────────────────────────────────────────────────▶ Rig 2 :9000
```

What that means for the system as a whole:

- **The gateway is now the single front door for both rigs.** All three models get the same auth, the same per-model wait line, and the same `: queued` keepalives while a request waits. Students need one URL, one key and a model name. They never need to know which rig answers.
- **Two kinds of keys, kept apart.** The student key `S` is the user credential. It's valid at EC2, and still at Rig 1, which checks it again. Rig 2's key `W` is a service credential: only the gateway and Open WebUI hold it, and students never see it. Rig 2 still returns 401 to `S`, so a student on the OCS LAN can't reach Rig 2 around the wait line. Rig 1 still accepts `S` directly ([status](../../docs/status.md#other-things-worth-knowing)), so the Rig 1 side of that bypass stays open.
- **Capacity matches the hardware.** Rig 2's `llama-server` runs `--parallel 2`, so the lane allows 2 requests at once (`RIG2_INFLIGHT=2`) and 4 waiting. The seventh concurrent request for `qwen3.6:35b-a3b` gets a `429`. Each model's line is separate, so a busy Rig 2 never slows Rig 1's models, and the reverse.
- **Rig 2's two slots now have two front doors.** Open WebUI still connects to Rig 2 directly, and the gateway doesn't see that traffic. If Open WebUI is using both slots, gateway requests that were let through still wait inside `llama-server`, where nobody sees a queue. That ends when Open WebUI goes through the gateway too (open item).
- **Failures stay contained.** If Rig 2 is down, `/v1/models` still answers with Rig 1's models, and only `qwen3.6:35b-a3b` requests fail. If Rig 1 is down, `/v1/models` fails as before (Rig 1 is the primary upstream), but Rig 2 chats still work.
- **One process holds every line.** The gateway still runs as one uvicorn worker (`--workers 1`), because the lines live in its memory. Restarting it now drops waiting and running requests for all three models, not two. The restart was done after checking that no requests were in progress.
- **The blast radius of EC2 grew.** EC2 already held the student key. It now also holds `W`, which is Open WebUI's key too. Anyone who takes over EC2 can now reach both rigs' orchestrators. Changing `W` means updating EC2 and Open WebUI together.
- **`infra/` is now a record you can trust.** Before this, the repo described a Worker B (`qwen2.5:0.5b`, 2 GPUs) that hadn't run since 2026-10-16, and was missing 5 files that are live. Now every repo copy was checked against its host on 2026-10-29. The env templates match the live files line for line, so a template is the real file minus its keys. One drift item affects monitoring: Rig 1's Worker B runs **without** `--metrics`, so its Prometheus endpoint is off.
- **The front door was already open to anyone who reads the repo.** The student key is the only thing guarding the public API. It sat in plain text in this repo from 2026-09-17, first in `CURSOR_HANDOFF.md` and later in `docs/archive/cursor-handoff.md`. Redacting the current file doesn't fix that; only a new key does. Until then, rate limits and the wait line are the only defence against outside use.

## Before

- **Rig 2 unreachable from the API.** From EC2, Rig 2's orchestrator answered `/healthz` with `200` and listed `qwen3.6:35b-a3b`, but returned **401** to the student key. Its `PUBLIC_API_KEYS` held two keys: a temporary operator key and Open WebUI's key.
- **The gateway could only reach one upstream.** `UPSTREAM_URL` was used for every request, and the caller's `Authorization` header was forwarded as-is (`gateway/proxy.py`).
- **The deployed gateway differed from the repo:** the live `config.py` defaulted `GROUP_B_MODEL_ALIAS` to `gemma4:26b`, and the live `lanes.py` lacked the repo's optional-lane-B change.
- **`infra/` had drifted from the hosts:**

  | Repo said | Host runs |
  |---|---|
  | Worker B: `qwen2.5:0.5b`, 2 GPUs, `8192` context, `--flash-attn on --metrics` | `gemma4:26b`, 4 GPUs, `256000` context, `--flash-attn auto`, no `--metrics` |
  | Worker A: "5 GPUs"; template comment "GPUs 0,1,2,3" | 4 GPUs: indexes 1, 3, 5, 7 ([hardware](../../docs/architecture/hardware.md)) |
  | `GROUP_B_MODEL_ALIAS=qwen2.5:0.5b` (Rig 1 orchestrator, EC2 gateway templates) | `gemma4:26b` |
  | Rig 2 worker: `qwen3.8:27b`, 8 GPUs, `PARALLEL=1` | `qwen3.6:35b-a3b`, 9 GPUs, `524288` context, `TENSOR_SPLIT=11,8,…`, `PARALLEL=2`, `-ub 1024` |
  | — | Rig 1 `ollama.service` + override (`OLLAMA_HOST=0.0.0.0`), EC2 `ai2` site, EC2 `websocket-upgrade.conf`, the Open WebUI container, Rig 2 `pull-moe.sh` |

## What we did

All from one operator laptop (macOS, NetBird 0.82.0) over NetBird SSH as `root`.

1. **Opened one SSH connection per host and reused it.** NetBird SSH asks for a browser SSO login on every new connection. A shared background connection (`ControlMaster`) for each host meant one login per host for the whole session:

   ```bash
   ssh -o ControlMaster=yes -o ControlPath=~/.ssh/ocs-r1 -o ControlPersist=4h -fN root@ocs-intelligence-rig.netbird.cloud
   ssh -o ControlPath=~/.ssh/ocs-r1 root@ocs-intelligence-rig.netbird.cloud 'systemctl list-unit-files "ocs-*"'
   ```

   Same for `ocs-r2` (`ocs-intelligence-rig2`) and `ocs-ec2` (`ip-172-31-42-43`). Three terminal tabs, one per host, also stayed open for the operator.

2. **Took an inventory and diffed it against `infra/`** (read-only): units in `/etc/systemd/system/`, `/etc/ocs-*`, Nginx `sites-available` and `conf.d`, crontabs, Docker containers, sysctl, and `/root/ocs-deploy` on Rig 2. Not copied: Kasm, `/root/*.ovpn` and the docker-login cron job on EC2 (not OCS), NetBird's own config (holds private keys), and stock files (`nginx.conf`, sysctl, NVIDIA units).

3. **Brought `infra/` in line** (commit `426739a`): copied the live units over the repo copies, fixed the templates, and added the missing files. The Open WebUI container was started by hand, so its `docker run` was rebuilt from `docker inspect`. Comparing against the image's own env showed that only `OLLAMA_BASE_URL` was passed at start.

4. **Saved the real keys to the operator's `.env`, without printing them.** Each value was written straight from the host to the file, and only key names were shown:

   ```bash
   v(){ ssh -o ControlPath=~/.ssh/ocs-$1 root@<host> "grep -m1 '^$3=' $2 | cut -d= -f2-"; }
   echo "RIG2_WORKER_API_KEY=$(v r2 /etc/ocs-intelligence/worker.env WORKER_API_KEY)" >> .env
   ```

   A check that compared values without showing them found the keys consistent: each worker's key matches its orchestrator's, and EC2's student key matches Rig 1's.

5. **Added the Rig 2 lane to the gateway** (commit `a7915fb`):
   - `config.py`: `RIG2_MODEL_ALIAS` (empty = no lane), `RIG2_UPSTREAM_URL`, `RIG2_UPSTREAM_API_KEY`, `RIG2_INFLIGHT`.
   - `lanes.py`: each `Lane` now carries its upstream URL and an optional stored key.
   - `proxy.py`: every call takes the upstream URL to use.
   - `main.py`: sends the lane's stored key if it has one, else the caller's. Merges Rig 2's models into `/v1/models`, and skips them if Rig 2 doesn't answer. Logs `key=set`/`MISSING`, never the key.
   - `tests/test_rig2_lane.py`, 6 tests: the lane is off by default; Rig 2 traffic uses `W` and Rig 2's URL; Rig 1 traffic keeps the caller's key; `W` alone is rejected at the gateway (401); the model list is merged, and still answers when Rig 2 is down.

   `uv` wasn't installed, so the tests ran in a throwaway venv: 21 passed (the gateway and NetBird tests).

6. **Picked Rig 2's key from what already exists.** The two keys were compared in place, without printing either. Key 1 equals `/root/ocs-deploy/temp-public-key` (temporary). Key 2 appears in Open WebUI's `config` table on Rig 1, read through a read-only SQLite connection. Key 2 was used.

7. **Deployed on EC2**, after backing up the code and env:

   ```bash
   cp -a /opt/ocs-gateway/gateway /opt/ocs-gateway/gateway.bak-20261029T175308Z
   cp -p /etc/ocs-gateway/gateway.env /etc/ocs-gateway/gateway.env.bak-20261029T175308Z
   ```

   `scp` failed against NetBird's SSH server, so the code went over through `tar`:

   ```bash
   tar -cf - -C gateway __init__.py auth.py config.py lanes.py main.py proxy.py \
     | ssh root@ip-172-31-42-43.netbird.cloud 'tar -xf - --no-same-owner -C /opt/ocs-gateway/gateway'
   ```

   Then four lines were appended to `/etc/ocs-gateway/gateway.env` (left at mode `0600`):

   ```bash
   RIG2_MODEL_ALIAS=qwen3.6:35b-a3b
   RIG2_UPSTREAM_URL=http://100.75.127.192:9000
   RIG2_UPSTREAM_API_KEY=<redacted: Rig 2's Open WebUI key>
   RIG2_INFLIGHT=2
   ```

   Before restarting, MD5s on EC2 were checked against the repo (all match), and the lanes were built offline with the live env. The output showed three lanes, Rig 2's with a key. The gateway had no upstream connections and no chat requests in the previous 10 minutes, so it was restarted at 17:53:56 UTC:

   ```bash
   systemctl restart ocs-gateway
   journalctl -u ocs-gateway -n 8 --no-pager -o cat
   ```

8. **Tested through the public URL with only the student key** (results under [How to check it](#how-to-check-it)).

9. **Made the env templates exact copies of the live env files** (commit `454589d`). A script copied each live file line by line. It replaced the value of every `*KEY*`, `*TOKEN*`, `*SECRET*` or `*PASS*` line with that template's existing `CHANGE_ME` placeholder. A diff of each template against its live file then showed only those lines. Rig 2's `pull-moe.sh` (no token in it) was added.

10. **Scanned the repo for every live key value.** One hit: the shared student key, 5 times in `docs/archive/cursor-handoff.md`. It has been in the repo since the commit that added `CURSOR_HANDOFF.md` (`634bd1e`, 2026-09-17), and `53bfd1e` (2026-09-29) carried it into `docs/archive/`. All 5 were replaced with `<redacted>`, and rotating the key went to the top of [status: next steps](../../docs/status.md#next-steps).

## How to check it

From the repo root, with `.env` loaded (`. ./.env`):

| Check | Pass looks like | If it fails |
|---|---|---|
| `curl -s https://ai.opencodingsociety.com/v1/models -H "Authorization: Bearer $OCS_API_KEY"` | `qwen3.8:27b`, `gemma4:26b`, `qwen3.6:35b-a3b` | Only two models: Rig 2 didn't answer the gateway. Check `curl http://100.75.127.192:9000/healthz` from EC2 |
| `POST /v1/chat/completions` with `"model":"qwen3.6:35b-a3b"` and the student key | `200`. On 2026-10-29: "Reply with exactly: rig2 ok" gave `rig2 ok` in 6.27 s (17 prompt + 130 completion tokens) | `502`/upstream error: Rig 2's orchestrator refused `W`. Compare `RIG2_UPSTREAM_API_KEY` with Rig 2's `PUBLIC_API_KEYS` |
| Same, with `"stream":true` | `data:` chunks, then `[DONE]`. 189 chunks for "count 1 to 5" | Only `: queued`: the lane is full, or Rig 2's slots are busy |
| `"model":"gemma4:26b"` | `200` (2.23 s for "Say hi.") | Rig 1 side; unrelated to this change |
| Any model with a wrong key | `401` | If `200`, `PUBLIC_API_KEYS` is empty on EC2 (any key accepted) |
| On EC2: `journalctl -u ocs-gateway \| grep "Rig 2 lane"` | `upstream=http://100.75.127.192:9000 model=qwen3.6:35b-a3b inflight=2 key=set` | `key=MISSING` or no line: `RIG2_*` settings not in `gateway.env` |

To undo, on EC2:

```bash
cp -a /opt/ocs-gateway/gateway.bak-20261029T175308Z/. /opt/ocs-gateway/gateway/
cp -p /etc/ocs-gateway/gateway.env.bak-20261029T175308Z /etc/ocs-gateway/gateway.env
systemctl restart ocs-gateway
```

To turn off only the Rig 2 lane, set `RIG2_MODEL_ALIAS=` and restart.

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| A browser login for every `ssh` | NetBird SSH asks for SSO on each new connection | One `ControlMaster` connection per host, reused with `-o ControlPath=…` |
| `unix_listener: path … too long for Unix domain socket` | `ControlPath` in a long scratch directory (macOS limit 104 bytes) | Use a short path such as `~/.ssh/ocs-r1` |
| `scp: Received message too long 1397966880` | `scp`/SFTP doesn't work against NetBird's SSH server | `tar -cf - … \| ssh host 'tar -xf - -C …'` |
| `tar: Ignoring unknown extended header keyword 'LIBARCHIVE.xattr…'` | macOS `tar` adds extended attributes | Harmless. `COPYFILE_DISABLE=1` reduces it |
| Rig 2 says 401 to the student key | By design: Rig 2 only takes Open WebUI's and an operator key | The gateway sends `W` to Rig 2; don't add the student key to Rig 2 |
| Picking the wrong Rig 2 key | Rig 2 has two keys, one of them temporary | Key 1 = `/root/ocs-deploy/temp-public-key`; use the one in Open WebUI's config |
| `uv: command not found`; no pytest | `uv` not installed on that laptop | Install `uv` ([decision 0010](../../docs/decisions/0010-uv-for-local-dev.md)), or use a throwaway venv. Never `pip install` into the system Python |

## Open items

- **Rotate the student key.** It's in public git history. Change `PUBLIC_API_KEYS` on EC2 and Rig 1's orchestrator together, then give students the new key. Rewriting history would hide the old key but not make it safe.
- **Send Open WebUI through the gateway for Rig 2.** Delete its direct Rig 2 connection, so all Rig 2 traffic shares one wait line. Which of its two connections it uses for `qwen3.6:35b-a3b` now wasn't checked.
- **Worker B has no `--metrics`.** Decide whether that was on purpose before building monitoring ([roadmap](../../docs/project/roadmap.md#planned-not-built)).
- **Rig 1 still accepts the student key directly,** so anyone with it on the OCS LAN can skip the wait line on Rig 1. Giving Rig 1 a gateway-only key, the way Rig 2 now works, would close it (audit S2, Sprint 5).
- **Load not tested.** No concurrent test of the Rig 2 lane (the `429` on the seventh request comes from the lane code and its tests, not a live run).
- **[Decision 0012](../../docs/decisions/0012-gateway-routes-rig2-with-stored-key.md) is `proposed`.** It needs the team's and mentor's review: it differs from the blueprint, which has one rig behind the gateway and Rig 2 as dev/test.
- **No PDF yet.** `pandoc` wasn't installed; render with `uv run --group playbook scripts/build_playbook.py evidence/sprint5/2026-10-29-one-api-both-rigs.md`.

## Sources

- [Capture: EC2 gateway Rig 2 lane](../captures/2026-10-29-ec2-gateway-rig2-lane.md)
- [Decision 0012](../../docs/decisions/0012-gateway-routes-rig2-with-stored-key.md), [decision 0009](../../docs/decisions/0009-rig2-moe-behind-open-webui.md)
- Commits `426739a` (infra re-sync), `a7915fb` (gateway Rig 2 lane), `454589d` (env files mirrored, student key redacted)
- [Hosts](../../docs/reference/hosts.md), [configuration](../../docs/reference/configuration.md), [status](../../docs/status.md)
