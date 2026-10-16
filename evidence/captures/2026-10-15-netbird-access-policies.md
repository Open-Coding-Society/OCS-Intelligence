---
date: 2026-10-15
---

# NetBird access policies: before and after (2026-10-15)

Replacing NetBird's built-in `Default` policy (every peer can reach every peer, both ways) with one-way, group-based policies. Made from the `Yash WSL` peer (`100.75.108.36`, NetBird 0.77.1) with the management API (`https://api.netbird.io`). This is a record: don't edit it. Desired state: [`infra/netbird/acl.json`](../../infra/netbird/acl.json). Why: [decision 0008](../../docs/decisions/0008-one-way-netbird-policies.md).

## Before

Groups: only `All`, containing every peer: `ocs-intelligence-rig`, `ocs-intelligence-rig2`, `ip-172-31-42-43`, `Yash WSL`, `adi-dell`, `chrome-152-browser-client`, `chrome-155-browser-client`.

| Policy | Source → Destination | Direction | Protocol / ports |
|---|---|---|---|
| `Default` | `All` → `All` | both ways | all |
| `SSH Access` (×3) | `All` → rig, rig2, EC2 (one per peer) | one-way | netbird-ssh 22 |
| Temporary access (×2) | a `chrome-*-browser-client` peer → rig | one-way | netbird-ssh 22022 |

`Default` was the only policy with `Yash WSL` or `adi-dell` as a destination.

Checks before the change:

```text
https://ai.opencodingsociety.com/healthz 200
https://ai.opencodingsociety.com/ 200          # EC2 Nginx -> rig :3000 over NetBird
WSL -> 100.75.123.203:9000 open
WSL -> 100.75.127.192:9000 closed/timeout      # rig2: nothing listening on 9000 yet
WSL -> 100.75.123.203:22 open
WSL -> 100.75.172.167:22 open
```

## Changes

1. Created groups `outbound-only` (`Yash WSL`, `adi-dell`), `ocs-gateway` (`ip-172-31-42-43`), `ocs-rigs` (`ocs-intelligence-rig`, `ocs-intelligence-rig2`).
2. Created policies `gateway-to-rigs` (`ocs-gateway` → `ocs-rigs`, one-way, TCP 9000, 3000) and `outbound-only-to-infra` (`outbound-only` → `ocs-gateway`, `ocs-rigs`, one-way, all protocols).
3. Disabled (didn't delete) `Default`.

The first attempt at step 1 failed with `403 permission denied`: the API token belonged to a service user with the `user` role, which can read but not write. A token from an admin service user worked.

## After

Checks about 20 s after disabling `Default`:

```text
https://ai.opencodingsociety.com/healthz 200
https://ai.opencodingsociety.com/ 200
https://ai.opencodingsociety.com/healthz 200
https://ai.opencodingsociety.com/ 200
WSL -> 100.75.123.203:9000 open
WSL -> 100.75.123.203:3000 open
WSL -> 100.75.123.203:22 open
WSL -> 100.75.172.167:22 open
```

`netbird status -d` on `Yash WSL` now lists only three peers: `ocs-intelligence-rig`, `ocs-intelligence-rig2`, `ip-172-31-42-43`. `adi-dell` and the browser-client peers dropped out of its network map.

`python3 infra/netbird/apply.py check` → `live NetBird config matches acl.json`.

## Not checked

- A connection started from the rig or EC2 toward `100.75.108.36`. It needs a shell on a server, which needs browser SSO. Expected result: timeout.
- `/v1/*` through the gateway to the rig's `:9000` (needs a student key). `/` covers the same EC2 → rig path under the same policy rule.
- Dashboard browser SSH after the change.
