---
status: current
last_verified: 2026-10-19
---

# Pending playbook material

The week's work, logged by the people and agents who did it. Each entry is waiting to go into a playbook: the next sprint's, or a new playbook in the current sprint. Playbooks can be edited (freely while `in progress`, and if needed once `done`), but the better route for new work, including answers to an earlier playbook's open items, is to log it here.

**How to add an entry.** Find this week's section (`## Week of YYYY-MM-DD`, the Monday) or start it at the top. Put the entry under the closest category (a `###` heading): `Rigs and hardware`, `Inference and models`, `Gateway and API`, `Networking and access`, `VR`, or `Docs and process`. Give the entry a `####` heading with the date and a short title. Then add a few bullets: what was wrong or asked, what was done, and the result with numbers. Link the proof (usually a dated capture) and any earlier playbook it follows up. Don't add author names. Mark facts the team reported, but nobody captured, as reported. Full rules: [conventions](../docs/conventions.md#pending-playbook-material).

**When it's written up,** the playbook's author moves the entries it covers into the playbook and deletes them here in the same commit.

**Sprint 4 was written up on 2026-10-23.** Its hardware and inference entries moved into [the hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md) and [the inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Everything below feeds Sprint 5 ([plan](../docs/project/roadmap.md#sprint-5-plan)).

## Week of 2026-10-19

### Networking and access

#### 2026-10-22: Rig 1's Ethernet now links at 1 Gb/s

Feeds Sprint 5 (networking): this and the throughput numbers are its measured baseline. Answers the 100 Mb/s open item from the [Sprint 4 hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md). Proof: [capture](./captures/2026-10-22-rig1-gigabit-link.md) (read-only).

- **Was:** Rig 1 linked at 100 Mb/s on the onboard I219-V while Rig 2 got 1 Gb/s.
- **Now:** `ethtool` shows 1000 Mb/s full duplex, and the switch side advertises 1000baseT/Full. The cable or switch port was changed (which one wasn't recorded).
- **Watch:** the link dropped 6 times that morning, consistent with recabling. It had been up at 1 Gb/s for about 14 minutes when checked.
- **Throughput:** `iperf3` (now installed on both rigs) measured 934 Mb/s each way between the rigs, and about 931 Mb/s in both directions at once, with 0 retransmits and a 0.23 ms ping. That's line rate. No new drops during the test. Proof: [capture](./captures/2026-10-22-rig-to-rig-iperf3.md).
- **Internet (2026-10-23):** both rigs reach the router (`192.168.8.1`) in 0.5 ms at 1 Gb/s, but get only about 60–90 Mb/s to the internet each way, and they share it: about 84 Mb/s combined when both download at once. The cap is upstream of the router (WAN port, line or plan); the router's WAN link speed wasn't read. Proof: [capture](./captures/2026-10-23-rig-internet-throughput.md).
- **Where the cap is:** the team's [routing playbook](./sprint4/2026-10-16-rig-routing.md) has the Flint 2's WAN on Ethernet to a Mac mini, which reaches the internet over its built-in Wi-Fi on the school network. That single Wi-Fi link is the most likely cap. It wasn't measured hop by hop.
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

