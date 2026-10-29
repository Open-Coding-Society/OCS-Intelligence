---
status: current
last_verified: 2026-10-29
---

# Pending playbook material

The week's work, logged by the people and agents who did it. Each entry is waiting to go into a playbook: the next sprint's, or a new playbook in the current sprint. Playbooks can be edited (freely while `in progress`, and if needed once `done`), but the better route for new work, including answers to an earlier playbook's open items, is to log it here.

**How to add an entry.** Find this week's section (`## Week of YYYY-MM-DD`, the Monday) or start it at the top. Put the entry under the closest category (a `###` heading): `Rigs and hardware`, `Inference and models`, `Gateway and API`, `Networking and access`, `VR`, or `Docs and process`. Give the entry a `####` heading with the date and a short title. Then add a few bullets: what was wrong or asked, what was done, and the result with numbers. Link the proof (usually a dated capture) and any earlier playbook it follows up. Don't add author names. Mark facts the team reported, but nobody captured, as reported. Full rules: [conventions](../docs/conventions.md#pending-playbook-material).

**When it's written up,** the playbook's author moves the entries it covers into the playbook and deletes them here in the same commit.

**Sprint 4 was written up on 2026-10-23.** Its hardware and inference entries moved into [the hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md) and [the inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Everything below feeds Sprint 5 ([plan](../docs/project/roadmap.md#sprint-5-plan)).

## Week of 2026-10-26

### Rigs and hardware

#### 2026-10-27: Autoinstall USB sticks for the Mac minis, tested in a VM

Feeds Sprint 5 (orchestrator on the Mac minis). Follows [issue #30](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/30) (PXE boot).

- **Asked:** flash the remaining Mac minis (32 left after losses: `mac1` done, 31 to go; `Macmini7,1`, A1347 EMC 2840, 1 TB drive reported) with Ubuntu Server 26.04, user `ocs`, SSH, as quickly as possible. No network during the install; hostnames and packages later.
- **Chosen:** autoinstall sticks, not PXE or Clonezilla ([decision 0011](../docs/decisions/0011-autoinstall-sticks-for-mac-minis.md)). Intel Macs netboot with Apple's BSDP, not standard PXE, and no report of it working on this model was found. Clonezilla clones share machine-id, SSH host keys and hostname, and fail on smaller disks.
- **Built:** [`infra/macmini/`](../infra/macmini/): `build_iso.py` adds `/autoinstall.yaml` and the `autoinstall` kernel argument to the stock ISO. The install is offline, names the machine `ocs-intelligence-<serial>`, sets key-only SSH, and powers off. Guide: [flash the Mac minis](../docs/operations/flash-mac-minis.md).
- **Tested (QEMU/KVM, OVMF, no network, the real `ubuntu-26.04.1-live-server-amd64.iso`, SHA-256 `cc8a95cd…`):** no prompts; install took 4.5 minutes and powered off. After boot: hostname `ocs-intelligence-c07test1g1j1` from the fake serial `C07TEST1G1J1`, in `/etc/hostname` and `/etc/hosts`; Ubuntu 26.04.1 LTS; apt sources on `archive.ubuntu.com` (`resolute`); key login worked; password login refused (`Permission denied (publickey)`); `en_US.UTF-8`, `America/Los_Angeles`; disk wiped into `/boot/efi` + `/`.
- **Open:** not yet tried on a real Mac mini (boot picker "EFI Boot", Mac firmware, the real serial). Whether holding C boots the stick with no monitor. Whether any Mac mini has a Fusion Drive (two disks).

### Gateway and API

#### 2026-10-29: The public API serves Rig 2's `qwen3.6:35b-a3b` with the one student key

Follows [0009](../docs/decisions/0009-rig2-moe-behind-open-webui.md)'s follow-up (a router that knows both rigs). Proof: [capture](./captures/2026-10-29-ec2-gateway-rig2-lane.md). Decision: [0012](../docs/decisions/0012-gateway-routes-rig2-with-stored-key.md).

- **Asked:** reach Rig 2's model through EC2, with students needing only one key and no new keys.
- **Was:** the gateway had one upstream (Rig 1) and forwarded the caller's key; Rig 2 returned 401 to the student key.
- **Done:** a Rig 2 lane in the gateway with its own upstream and a stored key: Rig 2's existing Open WebUI key. Rig 2 unchanged.
- **Result:** `/v1/models` lists all three models; `qwen3.6:35b-a3b` answered in 6.3 s and streamed; Rig 1 unaffected; wrong key 401.
- **Open:** remove Open WebUI's direct Rig 2 connection so its chats get the wait line too.

### Docs and process

#### 2026-10-29: Repo `infra/` copies re-synced with the three hosts

- **Asked:** copy every deployed OCS config file into the repo.
- **Compared (read-only, over NetBird SSH):** the systemd units, env files (secrets masked), Nginx sites, and the Open WebUI container on Rig 1, Rig 2 and EC2, against `infra/`.
- **Already matched:** both orchestrator units, Rig 2's `ocs-llama.service`, `ocs-gateway.service`, the `llm-relay` Nginx site, Rig 2's orchestrator env.
- **Had drifted (repo updated to match):** Rig 1 Worker B (`gemma4:26b` on 4 GPUs, `--flash-attn auto`, **no `--metrics`**, so its `/metrics` is off), Worker A's description, the `GROUP_B_MODEL_ALIAS` in Rig 1's orchestrator and EC2's gateway templates, Rig 2's worker env (`qwen3.6:35b-a3b`, 9 GPUs, `524288` context, `PARALLEL=2`, `-ub 1024`).
- **Newly in the repo:** Rig 1's `ollama.service` and its override (`OLLAMA_HOST=0.0.0.0`), EC2's `ai2` site and `websocket-upgrade.conf`, and a `docker run` for Open WebUI rebuilt from `docker inspect`.
- **Open:** whether Worker B dropping `--metrics` was on purpose.

### Networking and access

#### 2026-10-22: Rig 1's Ethernet now links at 1 Gb/s

Feeds Sprint 5 (networking): this and the throughput numbers are its measured baseline. Answers the 100 Mb/s open item from the [Sprint 4 hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md). Proof: [capture](./captures/2026-10-22-rig1-gigabit-link.md) (read-only).

- **Was:** Rig 1 linked at 100 Mb/s on the onboard I219-V while Rig 2 got 1 Gb/s.
- **Now:** `ethtool` shows 1000 Mb/s full duplex, and the switch side advertises 1000baseT/Full. The cable or switch port was changed (which one wasn't recorded).
- **Watch:** the link dropped 6 times that morning, consistent with recabling. It had been up at 1 Gb/s for about 14 minutes when checked.
- **Throughput:** `iperf3` (now installed on both rigs) measured 934 Mb/s each way between the rigs, and about 931 Mb/s in both directions at once, with 0 retransmits and a 0.23 ms ping. That's line rate. No new drops during the test. Proof: [capture](./captures/2026-10-22-rig-to-rig-iperf3.md).
- **Internet (2026-10-23):** both rigs reach the router (`192.168.8.1`) in 0.5 ms at 1 Gb/s, but get only about 60–90 Mb/s to the internet each way, and they share it: about 84 Mb/s combined when both download at once. The cap is upstream of the router (WAN port, line or plan); the router's WAN link speed wasn't read. Proof: [capture](./captures/2026-10-23-rig-internet-throughput.md).
- **Where the cap is:** the team's [routing playbook](./sprint4/2026-10-22-rig-routing.md) has the Flint 2's WAN on Ethernet to a Mac mini, which reaches the internet over its built-in Wi-Fi on the school network. That single Wi-Fi link is the most likely cap. It wasn't measured hop by hop.
- **Open:** measure each hop (rig → Flint → Mac mini → school Wi-Fi) to confirm where the cap is.

#### 2026-10-20: Fewer NetBird SSO prompts; EC2 SSH stops working

Feeds Sprint 5.

- **Asked:** stop the browser login on every SSH connection.
- **Done:** turned on the client's token cache (`netbird up --ssh-jwt-cache-ttl`) on one operator machine. NetBird's CLI reference says servers reject tokens older than 10 minutes, so 600 s is the useful maximum. The login link now opens in a chosen Brave profile ([guide](../docs/guides/netbird-access.md#avoid-re-approving-every-command)).
- **Result:** after one approval, a new connection to Rig 1 needed no prompt.
- **Found:** NetBird SSH to EC2 fails right after a successful login (`ssh handshake failed: ... i/o timeout`, three tries). EC2's SSH server is NetBird 0.78.1; the rigs are on 0.80.0 and work. The public API was unaffected (`/healthz` 200). Open: fix via the AWS console, then re-check the instance type.

#### 2026-10-22/23: NetBird SSH from a WSL laptop fails on the OCS LAN (MTU)

Feeds Sprint 5.

- **Wrong:** from one operator's WSL machine, `netbird ssh` to the rigs stopped with `ssh handshake failed: ... i/o timeout`, while `ping` and a TCP connect to port 22 still worked.
- **Found:** WSL's `eth0` had MTU 1280, apparently copied from an idle Tailscale adapter on Windows. NetBird's tunnel is also 1280 and adds its own overhead, so full-size packets were dropped. The largest tunnel packet that got through was 1216 bytes (`ping -M do`). It only broke when the laptop was on `OCS_Intel`, where NetBird connects peer to peer over the LAN. On the phone hotspot it worked, most likely through a TCP relay (not confirmed).
- **Fix:** `sudo ip link set eth0 mtu 1500` on the WSL side, plus a `[boot]` command in `/etc/wsl.conf` to keep it. Not applied yet on that machine.
- **Likely related:** the EC2 SSH failure above has the same symptom. Not confirmed.

#### Planned: WireGuard tunnel from the Flint 2 to EC2

Feeds Sprint 5 (networking). Not built. Split out of the [Sprint 4 rig routing playbook](./sprint4/2026-10-22-rig-routing.md) on 2026-10-23, as the team planned it on 2026-10-16. Goal: all OCS traffic leaves from EC2's public IP, so the school network sees one encrypted connection, and EC2 can reach the rigs directly.

- **Why EC2 is the server.** Encryption only protects traffic up to where the tunnel ends, so a server on the router would decrypt inside the room. The school network blocks inbound connections, but outbound ones get through. EC2 has a public address, so EC2 is the server and the Flint is the client.
- **Addresses:** tunnel `10.8.0.0/24`, EC2 = `10.8.0.1`, Flint = `10.8.0.2`. It must not overlap the school subnet, `10.42.0.0/24`, or `192.168.8.0/24`.
- **Needs:** SSH with sudo on the EC2 relay, AWS console access to its security group, and its Elastic IP (`dig +short ai.opencodingsociety.com`). About 1 hour for Steps 6–9.
- **Risk once it's up:** EC2 becomes the trust boundary for both rigs. Keep its security group tight and its keys private. With the kill switch on, the whole LAN, other groups included, loses internet when the tunnel drops.

##### Step 6: Test which port the tunnel can use

WireGuard's default port, UDP 51820, is very likely blocked by the district. UDP 443 often gets through. nginx on the relay uses TCP 443, so UDP 443 doesn't conflict.

1. AWS console → the relay instance → Security → its security group → Edit inbound rules. Add Custom UDP, port 443, source `0.0.0.0/0`.
2. On the relay: `sudo nc -ul 443`
3. On the Mac mini (it must be the machine on the school Wi-Fi):

   ```bash
   EC2_IP=$(dig +short ai.opencodingsociety.com)
   echo hello | nc -u -w2 $EC2_IP 443
   ```

If `hello` appears on the relay, UDP 443 gets out: continue with Step 7. If nothing appears, UDP is blocked: stop, and use the TCP 443 fallback in the table below. Ctrl+C stops the listener.

##### Step 7: WireGuard server on the EC2 relay

Run each block on the relay and check for errors before the next. This adds WireGuard beside the existing nginx without changing it.

```bash
# 7a. Install WireGuard and turn on forwarding
sudo apt update && sudo apt install -y wireguard
echo "net.ipv4.ip_forward=1" | sudo tee /etc/sysctl.d/99-wg.conf
sudo sysctl --system

# 7b. Server keys
sudo sh -c 'umask 077; wg genkey | tee /etc/wireguard/server_private.key \
    | wg pubkey > /etc/wireguard/server_public.key'

# 7c. Server config
IFACE=$(ip route show default | awk '{print $5}')
SERVER_PRIV=$(sudo cat /etc/wireguard/server_private.key)
sudo tee /etc/wireguard/wg0.conf >/dev/null <<EOF
[Interface]
Address = 10.8.0.1/24
ListenPort = 443
PrivateKey = $SERVER_PRIV
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT
PostUp = iptables -A FORWARD -o wg0 -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o $IFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT
PostDown = iptables -D FORWARD -o wg0 -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -o $IFACE -j MASQUERADE
EOF
sudo chmod 600 /etc/wireguard/wg0.conf

# 7d. The Flint's keys, registered as a peer
sudo sh -c 'umask 077; wg genkey | tee /etc/wireguard/flint_private.key \
    | wg pubkey > /etc/wireguard/flint_public.key'
sudo tee -a /etc/wireguard/wg0.conf >/dev/null <<EOF
[Peer]
PublicKey = $(sudo cat /etc/wireguard/flint_public.key)
AllowedIPs = 10.8.0.2/32
EOF

# 7e. Start it, and keep it across reboots
sudo systemctl enable --now wg-quick@wg0
sudo wg show                  # interface wg0, listening port 443
sudo ufw allow 443/udp        # only if ufw is enabled

# 7f. Print the Flint's config
EC2_IP=$(curl -s https://checkip.amazonaws.com)
cat <<EOF
[Interface]
PrivateKey = $(sudo cat /etc/wireguard/flint_private.key)
Address = 10.8.0.2/32
DNS = 1.1.1.1
MTU = 1380

[Peer]
PublicKey = $(sudo cat /etc/wireguard/server_public.key)
Endpoint = $EC2_IP:443
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
EOF
```

Save 7f's output on your laptop as `flint.conf`.

> [!CAUTION]
> `flint.conf` contains a private key. Never paste it into GitHub, Slack, a shared doc, or a chat. If it leaks, delete the peer on EC2 and redo 7d and 7f.

| Setting | What it does |
|---|---|
| `ListenPort = 443` | The relay listens for WireGuard on UDP 443, the port that passed Step 6 |
| `PostUp ... MASQUERADE` | Tunnel traffic leaves to the internet from EC2's public IP |
| `AllowedIPs = 0.0.0.0/0` (Flint) | All of the Flint's internet traffic goes into the tunnel (full tunnel) |
| `PersistentKeepalive = 25` | A small packet every 25 s keeps the school's NAT entry open |
| `MTU = 1380` | Leaves room for tunnel overhead so large packets aren't dropped |

##### Step 8: WireGuard client on the Flint 2

Menu names vary a little between firmware versions.

1. Open `http://192.168.8.1` from a device on the OCS LAN.
2. VPN → WireGuard Client → Add a New WireGuard Configuration → upload (or paste) `flint.conf`. Name it `ocs-ec2` and save.
3. Turn the toggle on to connect.
4. In the VPN options, choose **Global Proxy** so every device on the OCS LAN uses the tunnel.
5. Turn on **Block Non-VPN Traffic** (the kill switch), so nothing leaks out through the school filter if the tunnel drops.

> [!NOTE]
> With the kill switch on, the whole OCS LAN loses internet when the tunnel is down; traffic between local devices keeps working. That's intended. Check Step 9 first whenever the internet stops. Other groups share the LAN (ports 5 and 6), so agree on this with them before turning it on.

##### Step 9: Test the tunnel end to end

| # | Where | Command or action | Pass looks like |
|---:|---|---|---|
| 1 | EC2 relay | `sudo wg show` | Peer `10.8.0.2` has a recent handshake, and the transfer counters climb |
| 2 | Rig 2 | `curl -s https://ifconfig.me` | The EC2 Elastic IP, not the school's address |
| 3 | Rig 1 | `curl -s https://checkip.amazonaws.com` | The same EC2 IP |
| 4 | Any device | Open a site the district normally filters | It loads |
| 5 | Flint admin | Turn the VPN off for a moment | Clients lose internet (the kill switch works). Turn it back on |
| 6 | Mac mini | `sudo reboot`, wait, then repeat 1–3 | Everything comes back with no manual steps |

##### Step 10: Reach the rigs from EC2 through the tunnel

After Step 9 passes:

1. On EC2, change the Flint peer's line in `/etc/wireguard/wg0.conf` to `AllowedIPs = 10.8.0.2/32, 192.168.8.0/24`, then `sudo systemctl restart wg-quick@wg0`.
2. On the Flint, in the WireGuard client settings, turn on remote access to the LAN.
3. From EC2, ping or curl each rig at its reserved address, for example `curl http://192.168.8.112:<port>/`. Both rigs should answer.

| Symptom | Likely cause | Fix |
|---|---|---|
| No handshake in `wg show` | UDP 443 blocked, security group rule missing, or wrong Endpoint | Re-check Step 6 and the inbound rule; the Endpoint must be the Elastic IP |
| Handshake works but some sites hang | MTU too high | Set `MTU = 1280` in `flint.conf` and re-upload it |
| UDP blocked entirely | The district filters all outbound UDP | Fall back to OpenVPN over TCP 443 (the Flint supports it). nginx already owns TCP 443 on the relay, so it needs port sharing or a second address |
| The whole LAN lost internet | Tunnel down, with the kill switch on | `sudo wg show` on EC2, and the VPN page on the Flint |

### Docs and process

#### 2026-10-22: Stray root `STATUS.md` and `CONTEXT.md` archived

Feeds Sprint 5 (answers [audit](../docs/sources/2026-10-14-mentor-audit.md) C6).

- **Wrong:** `check_docs.py` reported 9 broken links, all in a root `STATUS.md` and `CONTEXT.md` from 2026-09-23. Commit `0bc27d4` (2026-09-30) had added them back at the root after the docs moved into `docs/`, so their links pointed at the old layout.
- **Done:** moved them to [`docs/archive/`](../docs/archive/archive.md) as superseded, fixed their links, and listed them in the archive index. `check_docs.py`: 0 problems.

#### 2026-10-23: Local setup moves to uv and a root `pyproject.toml`

Feeds Sprint 5 (part of [audit](../docs/sources/2026-10-14-mentor-audit.md) M4). Proposed in [decision 0010](../docs/decisions/0010-uv-for-local-dev.md).

- **Wrong:** the documented `python3 -m pip install …` fails on Ubuntu 24.04 and WSL (`externally-managed-environment`), and nothing was locked.
- **Checked:** uv is on both rigs, but only for the `ocs` user's side experiments. The deployed venvs are plain `python3 -m venv`, and the repo had never used uv.
- **Done:** added `pyproject.toml` (a `dev` group, a `playbook` group, pytest config) and `uv.lock`, and switched AGENTS.md, getting started, the test plan, benchmarks, and conventions to `uv sync` and `uv run`. Result: 32 tests pass under `uv run pytest -q`. Deployment is unchanged.

