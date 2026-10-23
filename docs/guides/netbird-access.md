---
status: current
last_verified: 2026-10-20
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

**Cache the login for 10 minutes.** Since NetBird 0.60 the client can reuse one SSO token for new connections, to any host:

```bash
sudo netbird up --ssh-jwt-cache-ttl 600
```

600 seconds is the most that helps. The receiving SSH server rejects tokens older than 10 minutes, so a longer TTL just makes cached logins fail ([NetBird CLI reference](https://docs.netbird.io/get-started/cli)). The cache is cleared when the NetBird daemon restarts. Verified 2026-10-20: after one approval, a second connection to Rig 1 opened with no prompt.

**Choosing the browser profile (WSL).** `netbird ssh --no-browser` prints the login URL instead of opening a browser. To open it in a specific Brave or Chrome profile, find the profile's folder name in `User Data/Local State` (`profile.info_cache`) and pass it on the command line:

```bash
powershell.exe -NoProfile -Command "Start-Process 'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe' -ArgumentList '--profile-directory=\"Profile 1\"','<login URL>'"
```

## Check it worked

```bash
hostname      # ocs-intelligence-rig or ip-172-31-42-43
```

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| SSO prompt on every command | Opening new connections | Use the FIFO session above, and the 10-minute token cache |
| `ssh: handshake failed: ... i/o timeout` right after `Authentication successful!` | Seen on EC2 only, 2026-10-20 (its NetBird SSH server is 0.78.1; the rigs run 0.80.0 and work). Not root-caused | See [status](../status.md#other-things-worth-knowing). Try updating NetBird on EC2 through another way in (AWS console) |
| `ssh` hangs or times out | The peer is offline, or the rig's Wi-Fi dropped | `netbird status` inside the container. The rig peer usually connects through a relay. |
| Slow downloads or `apt`/`pip` failures on the rig | School Wi-Fi, PyPI DNS-blocked | Use Ubuntu packages. See [deploy the rig](../operations/deploy-rig.md). |
