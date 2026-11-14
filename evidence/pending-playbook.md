---
status: current
last_verified: 2026-10-29
---

# Pending playbook material

The week's work, logged by the people and agents who did it. Each entry is waiting to go into a playbook: the next sprint's, or a new playbook in the current sprint. Playbooks can be edited (freely while `in progress`, and if needed once `done`), but the better route for new work, including answers to an earlier playbook's open items, is to log it here.

**How to add an entry.** Find this week's section (`## Week of YYYY-MM-DD`, the Monday) or start it at the top. Put the entry under the closest category (a `###` heading): `Rigs and hardware`, `Inference and models`, `Gateway and API`, `Networking and access`, `VR`, or `Docs and process`. Give the entry a `####` heading with the date and a short title. Then add a few bullets: what was wrong or asked, what was done, and the result with numbers. Link the proof (usually a dated capture) and any earlier playbook it follows up. Don't add author names. Mark facts the team reported, but nobody captured, as reported. Full rules: [conventions](../docs/conventions.md#pending-playbook-material).

**When it's written up,** the playbook's author moves the entries it covers into the playbook and deletes them here in the same commit.

**Sprint 4 was written up on 2026-10-23.** Its hardware and inference entries moved into [the hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md) and [the inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Everything below feeds Sprint 5 ([plan](../docs/project/roadmap.md#sprint-5-plan)).

## Week of 2026-11-09

### Rigs and hardware

#### 2026-11-13: First Mac mini fully set up by Ansible (`ocs-intelligence-macmini-25`), and the playbook hardened

Follows the 2026-11-12 entry below.

- **Done:** the playbook ran to the end on the silver Mac mini, now `ocs-intelligence-macmini-25` (Post-it 25; a monitor was plugged in for the test): `ok=52 changed=26 failed=0`. Checked on the machine, not only in the log:
  - default route over Wi-Fi (`wlp2s0`, metric 100), wired as the backup (metric 200)
  - NetBird Management and Signal connected, `100.75.4.11`, in `ocs-macminis`
  - uv 0.13.5, Python 3.12.15, Ray 2.60.0; the local Ray test returned 285
  - mbpfan, the power-on service, chrony, avahi, node-exporter, docker, zram and netbird all active
  - power-on register `0xa4` reads `08` (bit 0 clear: power on after an outage)
  - sleep targets masked; 7.5 GB zram ahead of the swap file; open files 65536; the netplan with the Wi-Fi password readable by root only
- **Wi-Fi alone works:** with the Ethernet cable unplugged, it stayed reachable on Wi-Fi, reached PyPI (HTTP 200, about 5 MB/s) and NetBird, and a full playbook rerun over Wi-Fi changed nothing (`changed=0 failed=0`). So the playbook is safe to rerun.
- **Addresses change:** it came back from its kernel reboot at a new address (.156 → .155), Wi-Fi added another (.186), and switching the DHCP client ID to the MAC moved it again (.187). Fixes:
  - The hand-written inventory is gone. [`inventory.py`](../infra/macmini/ansible/inventory.py) scans `192.168.8.0/24` for SSH at the start of each run and keeps machines that report `Macmini7,1` (about 5 s).
  - Host keys are remembered by machine name, not IP, in `~/.ssh/known_hosts_ocs_macminis`. A moved address doesn't break SSH, and a machine claiming a known name with a different key is left out and reported. Tested with a forged entry and a rename. Turning host key checking off was blocked by Claude Code's auto mode and wasn't needed.
  - Both netplans (the playbook's and the FIX stick's) set `dhcp-identifier: mac`, so the router should hand back the same address after a reboot. Not yet seen across a reboot.
- **Bugs fixed:**
  - Found by running: `/etc/systemd/system.conf.d` didn't exist.
  - Found by an independent read-only review, each checked against the code:
    - settings that take effect on a restart (ARP, zram, fan) were applied only at the end of the play, after the Wi-Fi switch, and never if a run failed
    - headers for the pre-upgrade kernel were requested
    - a netplan was put in place before validation, and the validation error could print the Wi-Fi password
    - the Wi-Fi check was hard-coded to `192.168.`
    - the NetBird apt cache was skipped after an interrupted run
    - a race between loading `wl` and reading the interfaces
    - the setup key was on the command line (now `--setup-key-file`, a root-only file that's deleted afterwards)
    - `%` in a `.env` value would break the lookup
- **Rename:** `macmini_number: 25` in `host_vars`, then `--tags hostname` (briefly `macmini-0` by mistake; the mastermac is a different machine, Post-it 0). cloud-init is disabled on the installed system (`/etc/cloud/cloud-init.disabled`), so it can't reset the name. NetBird keeps the name a peer joined with, so the peer was renamed through the API (`ocs-intelligence-macmini-25.netbird.cloud`). Machines named by the FIX stick before joining won't need that.
- **Reboot over Wi-Fi only:** rebooted with the cable out. It came back on its own in 83 s on Wi-Fi at the **same** address (.187), so the MAC-based client ID kept it. Name, NetBird (`100.75.4.11`), the power-on service, mbpfan, zram and Ray were all fine after.
- **Power cut over Wi-Fi only:** the team pulled the power plug and plugged it back in without pressing the button. It powered on by itself and was back in about a minute: on Wi-Fi at the same address (.187), NetBird connected, the power-on service, mbpfan, zram and netbird active. So power-on after an outage works.
- **Other groups' Mac minis:** other class groups also use Mac minis on this LAN (reported). `inventory.py`, and so `reservations.py`, only takes machines that accept our ISO's SSH key, report `Macmini7,1`, and carry one of our names. The three others seen (.108, .117, .152) refuse the key, and each scan lists them as "not ours".
- **Router (read-only):** logged into the Flint over SSH. Its DHCP pool is `.100`–`.249`, and the rigs already have reservations at `.112` and `.213` ([network](../docs/architecture/network.md#dhcp-on-the-flint)). Plan, agreed in principle but not applied: reserve Mac mini N at `.10+N` wired and `.50+N` Wi-Fi, outside the pool, generated from a serial-to-number table the team is writing. Three other Mac minis are on the LAN running Ubuntu 24.04 (`ubuntu-macmini` ×2, `intelligence-Macmini7-1`). They refuse the stick's key, so they aren't stick-installed.
- **Serial-to-number table:** the team sent #0 (the mastermac) through #32, except #25, which is silver. That's **33 Mac minis**, all ours (reported). It corrects the earlier count of 32. It's in `infra/macmini/macminis.csv`, which is local and gitignored; a placeholder `macminis.example.csv` is committed. Four entries were read off the Post-its with some doubt: #22 `406` and #27 `6ER` (every other serial's third character is `G`), plus #28 and #32. A wrong entry is harmless: the machine shows as `#?` in `inventory.py --table`, with its real serial in the hostname.
- **Reservations applied (first one):** `reservations.py --apply` reserved #25 at `.35` wired (`38:C9:86:56:ED:F3`) and `.75` Wi-Fi (`2C:F0:A2:F0:72:64`). It took a backup first (`/root/dhcp.backup-2026-11-13-110421`, plus `/root/dhcp.backup-2026-11-13` from earlier), found no clashes, and checked each entry afterwards. The rigs, the router, dnsmasq and the leases were unaffected.
- **Moving to the reserved address:** `networkctl renew` wasn't enough. The router answered `DHCPNAK ... static lease available`, but networkd kept `.187` and didn't ask again. `networkctl reconfigure wlp2s0` moved it to `.75` within 30 s (it drops the address, so run it in the background). A reboot would do it too.
- **Scan reliability:** the scan missed the machine once while it was up, which would have dropped it from that run. `inventory.py` now retries probes that got no answer, twice. A scan takes about 8 s.
- **FIX stick asks nothing now:** with the serial table in place, the stick only turns on the wired port. The playbook renames each machine from its serial, before NetBird joins, so the peer gets the final name too. Wi-Fi still needs the first playbook run over the cable, because the `wl` driver is built on each machine from the internet.
- **One command per machine (built, not yet run on a Mac mini):** the team wants to plug in the stick, run one command, and have the machine fully set up, so it's ready to run on Monday 2026-11-16. Pushing from the laptop, with a watcher, was considered and dropped: the stick is plugged in anyway, and running on the machine needs no laptop. Built:
  - [`make_stick.py`](../infra/macmini/make_stick.py) builds the stick: `f`, plus a kit holding the playbook, the pinned `uv`, the serial table and `secrets.env`.
  - `secrets.env` has only the Wi-Fi SSID and password and a NetBird setup key limited to 33 uses and 14 days, created 2026-11-13 (`NETBIRD_MACMINI_STICK_KEY`). The permanent key stays on the laptop.
  - [`bootstrap.sh`](../infra/macmini/stick/bootstrap.sh) copies the kit off the stick (root-only), finds the Post-it number from the firmware serial, and starts `ocs-bootstrap.service`.
  - [`run.sh`](../infra/macmini/stick/run.sh) runs the playbook locally with ansible-core 2.21.6 through `uvx`. It resumes after the new-kernel reboot, retries up to 5 times, and deletes the secrets when done.
  - The playbook's reboot step now has a local path: mark the reboot, reboot 15 s later, end the run.
  - Tested offline: the bootstrap with test hooks; the local inventory and secrets lookup with ansible-core 2.21.6 on Python 3.14 (Ubuntu 26.04's version).
- **Download cache (started):** silver (`ocs_cache_server: true`) runs `apt-cacher-ng`, and serves the 89 locked wheels and the pinned `uv` on `:8090`. Clients use it when it answers, the internet otherwise.
  - The first run on silver installed `apt-cacher-ng`, then stopped while it was downloading wheels, because the operator laptop left the LAN. The wheel download now resumes based on which wheels are missing, not on whether the requirements file changed.
  - Python and NetBird now run before the Wi-Fi step, so a new machine's big downloads go over its cable.
  - That the cache is faster is not measured yet (planned: `iperf3` silver → a wired Mac mini).
  - Fixed after a second review, before any client used the cache:
    - Silver's wired link becomes its main link (`ocs_wired_metric: 100` in its `host_vars`). Otherwise the cache's replies would leave over Wi-Fi.
    - Silver writes `wheels/READY` with the sha256 of the lock it built from, once every wheel is there. Clients use the cache only when that matches their own lock, and go to PyPI otherwise, so a half-built or stale wheelhouse can't fail every machine.
    - The stick's reboot-and-resume stops after 3 reboots.
    - Checked locally with ansible-core 2.21.6: `meta: end_host` inside a `when` block exits 0, skips the rest, and still runs pending handlers. `run.sh` relies on that.
  - Silver is wired again: reserved `.35`, 1 Gb/s full duplex.
- **Cabling:** the Mac minis have no Ethernet yet. The team will connect them 7 at a time to a gigabit switch uplinked to the Flint (reported).
- **Naming:** silver's Post-it is 25. The mastermac is a different machine, Post-it 0.
- **Open:**
  - Monday:
    1. Rerun silver with `--limit ocs-intelligence-macmini-25` **before sticking anything**. That finishes the wheelhouse and the metric swap. `apt-cacher-ng` is already listening, so new machines' apt would go through it, and silver's own `apt update` through it is the check.
    2. Measure the cache.
    3. Rebuild the stick if anything changed. A build is in Downloads (`ocs-macmini-stick`, 2026-11-13); the old `ocs-macmini-netfix` is network-only.
    4. Try one Mac mini with a monitor, watching `journalctl -fu ocs-bootstrap` through the reboot to `DONE`, then batches of 7.
    5. `reservations.py --apply`, then reboot the machines or `networkctl reconfigure` them.
  - check the uncertain serials (#22 `406`, #27 `6ER`, #28, #32) against each machine's real hostname when it comes online
  - a Ray cluster (head node on the mastermac, `macmini-0`, plus worker services)
  - wired vs Wi-Fi for Ray traffic
  - an apt and Python package cache before the other 30 run
  - a full-fleet run currently needs `--limit` per machine, because Claude Code's auto mode blocked an unlimited run

#### 2026-11-12: Flashed Mac minis had no network; fixed with a stick, and an Ansible baseline started

Feeds Sprint 5 (orchestrator on the Mac minis). Follows the 2026-10-29 entry below.

- **Wrong:** all Mac minis were reported on power. One of them, the silver one (named by its serial at the time, now `ocs-intelligence-macmini-25`), was wired to the Flint but `ping 192.168.8.1` said "Network is unreachable" (reported). A ping sweep of `192.168.8.0/24` from an operator laptop on `OCS_Intel` found 7 hosts: both rigs, two Ubuntu 24.04 machines with Apple MAC prefixes that refuse the stick's SSH key (`OpenSSH_9.6p1 Ubuntu-3ubuntu13.20`, so not stick-installed), and two others. No stick-installed Mac mini answered.
- **Cause:** the autoinstall had no `network:` section. Ubuntu's autoinstall reference says the default "disables any interface that does not receive an address", applied "during installation as well as in the installed system". The installs ran with no cable, so the wired port was left disabled. The 2026-10-27 QEMU test didn't catch it, apparently because its VM still had a virtual network card that got an address.
- **Fix (installed machines):** a FIX stick script ([`infra/macmini/fix-network.sh`](../infra/macmini/fix-network.sh)) moves the installer's netplan to `/etc/netplan.installer/` and writes DHCP for the wired port. On the silver one it got `192.168.8.156/24` from the Flint, a default route via `192.168.8.1`, and `archive.ubuntu.com` answered HTTP 200 in 0.3 s. Checked over SSH with the stick's key. The script now also asks for the Post-it number and names the machine `ocs-intelligence-macmini-N`. That part is tested offline only.
- **Fix (future ISOs):** the template now writes DHCP on `en*` explicitly ([`autoinstall.yaml.template`](../infra/macmini/autoinstall.yaml.template)). Not test-installed yet.
- **Wi-Fi:** the card is present (`14e4:43a0`, BCM4360), but there's no Wi-Fi interface: only `b43` loaded, which doesn't drive this card, and `wpasupplicant` isn't installed. Unplugging the cable takes the machine offline until the `wl` driver is installed.
- **Ansible baseline ([decision 0013](../docs/decisions/0013-ansible-baseline-with-ray-for-mac-minis.md), proposed):** [`infra/macmini/ansible/`](../infra/macmini/ansible/) covers packages, Mac fan and power-on settings, zram, Wi-Fi as the main link (wired as backup), uv 0.13.5 from Astral's installer, Python 3.12 managed by uv, Ray 2.60.0 and 88 other locked packages in `/opt/ocs/venv`, and NetBird. Guide: [set up the Mac minis](../docs/operations/set-up-mac-minis.md). Every apt package was checked as available in 26.04 first (`dnsutils` is `bind9-dnsutils` there). SSH and sudo worked on the silver Mac mini. Both runs stopped in the first upgrade step: the first because unattended-upgrades held the dpkg lock, the second because the operator laptop's Wi-Fi switched off `OCS_Intel` mid-upgrade. The playbook now waits for the lock and repairs an interrupted install first. Nothing past the upgrade has run yet.
- **NetBird:** new group `ocs-macminis` and policy `operators-to-macminis` (operators → Mac minis, all ports, one way), created with `apply.py apply`. A reusable setup key that never expires and adds peers to `ocs-macminis` is in the operator's `.env`. A separate admin service user for the Mac minis wasn't created (it needs the dashboard).
- **Open:** finish the playbook run on the silver Mac mini, then the rest. FIX-stick every other Mac mini. Measure Wi-Fi vs. wired for Ray traffic. Weak `ocs` password and secrets in `.env` (Sprint 6).

## Week of 2026-11-02

### Inference and models

#### 2026-11-03: Rig 1 speed tuning, and the cause of its OOM kills

Feeds the next playbook on inference. Followed [the tuning guide](../docs/operations/tune-rig1-speed.md), and cut short at the operator's request. Proof: [capture](./captures/2026-11-03-rig1-speed-tuning.md).

- **Asked:** run the tuning guide on Rig 1, with no new downloads or rebuilds.
- **Found:** Worker A generates 8.7 tok/s and Worker B 27.4 tok/s, the first recorded speed for `gemma4:26b`. The kernel's OOM killer stopped `llama-server` 8 times from 2026-10-20 to 2026-11-02. A restart of Worker A freed about 7.5 GB of host RAM.
- **Changed:** added a `$LLAMA_EXTRA_ARGS` hook to both units. Both workers: `--cache-ram 4096` (down from the 8 GB default). Worker A: `ngram-mod` speculative decoding.
- **Result:** Worker A copies text at 37.2 tok/s, up from 8.6, and free generation is unchanged (8.83 vs 8.75 tok/s). The 4 GB cap restored an evicted 20k-token prompt in 19.3 s, the same as the 8 GB default and against about 66 s cold. A 2 GB cap holds only one state that size, so it fell back to a full 66 s.
- **Rejected:** `-ub 1024` on Worker A: prefill fell from 194 to 138 tok/s (1.8k tokens) and from 335 to 286 tok/s (7.8k tokens). `--cache-reuse`: this build disables it on this context.
- **Open:** not tested: `-ub` changes on Worker A below 512, Worker B batch size and speculative decoding, CPU threads, `--flash-attn on` on Worker B. Whether the cap ends the OOM kills needs a busy class to show. Worker A's speculative gain on real agent traffic isn't measured.

## Week of 2026-10-26

### Rigs and hardware

#### 2026-10-27: Autoinstall USB sticks for the Mac minis, tested in a VM

Feeds Sprint 5 (orchestrator on the Mac minis). Follows [issue #30](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/30) (PXE boot).

- **Asked:** flash the remaining Mac minis (32 left after losses: `mac1` done, 31 to go; `Macmini7,1`, A1347 EMC 2840, 1 TB drive reported) with Ubuntu Server 26.04, user `ocs`, SSH, as quickly as possible. No network during the install; hostnames and packages later.
- **Chosen:** autoinstall sticks, not PXE or Clonezilla ([decision 0011](../docs/decisions/0011-autoinstall-sticks-for-mac-minis.md)). Intel Macs netboot with Apple's BSDP, not standard PXE, and no report of it working on this model was found. Clonezilla clones share machine-id, SSH host keys and hostname, and fail on smaller disks.
- **Built:** [`infra/macmini/`](../infra/macmini/): `build_iso.py` adds `/autoinstall.yaml` and the `autoinstall` kernel argument to the stock ISO. The install is offline, names the machine `ocs-intelligence-<serial>`, sets key-only SSH, and powers off. Guide: [flash the Mac minis](../docs/operations/flash-mac-minis.md).
- **Tested (QEMU/KVM, OVMF, no network, the real `ubuntu-26.04.1-live-server-amd64.iso`, SHA-256 `cc8a95cd…`):** no prompts; install took 4.5 minutes and powered off. After boot: hostname `ocs-intelligence-c07test1g1j1` from the fake serial `C07TEST1G1J1`, in `/etc/hostname` and `/etc/hosts`; Ubuntu 26.04.1 LTS; apt sources on `archive.ubuntu.com` (`resolute`); key login worked; password login refused (`Permission denied (publickey)`); `en_US.UTF-8`, `America/Los_Angeles`; disk wiped into `/boot/efi` + `/`.
- **Open:** not yet tried on a real Mac mini (boot picker "EFI Boot", Mac firmware, the real serial). Whether holding C boots the stick with no monitor. Whether any Mac mini has a Fusion Drive (two disks). The flashing is logged in the next entry.

#### 2026-10-29: All Mac minis flashed; on 2026-10-30 most went on power in their own corner

Feeds Sprint 5 (orchestrator on the Mac minis). Follows the entry above. All of this is reported by the team. Nobody captured it from the machines.

- **Flashed:** the team started on Wednesday 2026-10-28 and finished all of the Mac minis on Thursday 2026-10-29 (31 to go by the 2026-10-27 count).
- **Power:** on Friday 2026-10-30 the team connected them to power, all but 6.
- **Space:** the same day, the team cleared a corner of the room. It now holds only the Mac minis, plus a monitor and keyboard for the `mastermac`, the only Mac mini with a UI.
- **Open:** connect the last 6. Not recorded: whether holding C booted the sticks without a monitor, whether every hostname came out as `ocs-intelligence-<serial>` from the real serial, and whether any machine had a Fusion Drive. Network cabling isn't reported, so SSH key login on a real Mac mini is still unchecked. The serial → `macN` list and the renames are still to do ([guide](../docs/operations/flash-mac-minis.md#5-rename-them-later)).

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

