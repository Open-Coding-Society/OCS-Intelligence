---
status: current
last_verified: 2026-09-18
---

# How to get a shell on the rig or EC2

Operators reach both machines over NetBird SSH, either from the NetBird client installed on their machine (Linux, WSL, macOS, Windows) or from the Docker container in [`infra/netbird/`](../../infra/netbird/). Host IPs: [hosts](../reference/hosts.md#machines).

## Before you start

- A NetBird peer on the OCS network: the client installed natively, or the container below.
- Your peer added to the **`outbound-only`** group by a NetBird admin (dashboard → Peers → your peer → Groups). Without it you can only use NetBird SSH; with it you can reach every server port, and nothing on the network can connect to your machine. Why: [decision 0008](../decisions/0008-one-way-netbird-policies.md).
- A browser, for NetBird's SSO approval.

## The container (optional)

Use this if you don't want the NetBird client installed on your machine. It uses the host's network, and keeps its identity in `infra/netbird/netbird_data/` (gitignored: it holds the peer's private key).

```bash
docker compose -f infra/netbird/docker-compose.yml up -d   # start it
docker exec -it netbird-client netbird up                   # first time only: join, approve SSO in the browser
docker exec -it netbird-client bash                         # open a shell inside it
docker compose -f infra/netbird/docker-compose.yml down     # when you're done
```

## SSH in

From your machine, or from inside the container:

```bash
ssh root@100.75.123.203   # GPU rig  (ocs-intelligence-rig)
ssh root@100.75.172.167   # EC2      (ip-172-31-42-43)
```

NetBird prints an SSO link:

```text
SSH authentication required.
Please do the SSO login in your browser.
URL: https://login.netbird.io/activate?user_code=XXXX-XXXX
```

Open it and approve. You're logged in for as long as **that** connection stays open.

## Avoid re-approving every command

NetBird asks for SSO on **every new SSH connection**, so one-off `ssh host cmd` calls each trigger a prompt. Keep one long-lived session per host instead:

```bash
mkfifo /tmp/rig.fifo
tail -f /tmp/rig.fifo | ssh -tt root@100.75.123.203     # approve SSO once
# from another shell in the container:
echo 'systemctl status ocs-llama-a --no-pager' > /tmp/rig.fifo
```

This also works for coding agents: an agent can write commands into the FIFO after a person approves the login once.

## Check it worked

```bash
hostname      # ocs-intelligence-rig or ip-172-31-42-43
```

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| SSO prompt on every command | Opening new connections | Use the FIFO session above |
| `ssh` hangs or times out | The peer is offline, or the rig's Wi-Fi dropped | `netbird status` inside the container. The rig peer usually connects through a relay. |
| Slow downloads or `apt`/`pip` failures on the rig | School Wi-Fi, PyPI DNS-blocked | Use Ubuntu packages. See [deploy the rig](../operations/deploy-rig.md). |
