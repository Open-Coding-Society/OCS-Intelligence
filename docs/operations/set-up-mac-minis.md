---
status: draft
last_verified: 2026-11-12
---

# How to set up the Mac minis after flashing (FIX stick, then Ansible)

By the end, every Mac mini is named `ocs-intelligence-macmini-N`, is on the OCS LAN over Wi-Fi with wired as backup, has joined NetBird, and runs the same baseline: build tools, Docker, uv, Python 3.12, and Ray 2.60.0. The same playbook sets them all up, so a change is made once, in [`infra/macmini/ansible/`](../../infra/macmini/ansible/), and rerun.

**Draft:** tested on one Mac mini, `ocs-intelligence-macmini-25` ("silver"), on 2026-11-12/13. The playbook ran to the end. A rerun changed nothing, Wi-Fi alone worked with the cable unplugged, and NetBird and Ray were checked on the machine. Reboot and power-cut recovery over Wi-Fi alone both worked (2026-11-13). The FIX stick's current version, which has no prompt, and naming from the serial table aren't tested on a new machine yet. See the [pending playbook](../../evidence/pending-playbook.md).

## Before you start

- The Mac minis are flashed ([flash the Mac minis](./flash-mac-minis.md)) and wired to the OCS LAN.
- Your laptop is on the OCS LAN (`OCS_Intel`) and holds the SSH key that went into the ISO.
- The repo-root `.env` has the Mac mini values (template: [`.env.example`](../../.env.example)): `MACMINI_SUDO_PASSWORD`, `MACMINI_WIFI_SSID`, `MACMINI_WIFI_PASSWORD`, `NETBIRD_MACMINI_SETUP_KEY`. The setup key comes from `python3 infra/netbird/apply.py setup-key ocs-macminis` (it never expires, has unlimited uses, and adds each peer to `ocs-macminis`; revoke it in the NetBird dashboard if it leaks).
- `uv sync --group ansible` once.

## Steps

### 1. FIX stick: wired network, at each Mac mini (about 20 s each)

Machines flashed before 2026-11-12 came up with no network: the install ran with no cable, so the installer disabled the wired port. ISOs built from the current template don't have this problem. The stick asks nothing and leaves the name alone: Ansible names each machine from its serial (step 2).

**Keep the Ethernet cable in for the first playbook run.** Wi-Fi can't work yet: the BCM4360 needs the `wl` driver, which a fresh install doesn't have. The playbook builds the driver on each machine (it needs the internet for its packages and kernel headers), then switches to Wi-Fi. After that the cable is optional.

1. Format a USB stick FAT32 with the label `FIX`. Copy [`infra/macmini/fix-network.sh`](../../infra/macmini/fix-network.sh) onto it as `f`.
2. At the Mac mini, with a keyboard (a monitor helps for the first few), log in as `ocs`, then:

   ```bash
   sudo mount -L FIX /mnt; sudo sh /mnt/f
   ```

3. It prints one line, for example `ocs-intelligence-c07rx0xxxg1j1  enp3s0f0  carrier=1  ip=192.168.8.x/24`. Write the IP down. `carrier=0` means no link: check the cable and the port's light.

### 2. Check Ansible finds them

There's no list of IPs to keep. [`inventory.py`](../../infra/macmini/ansible/inventory.py) runs at the start of every playbook run: it tries SSH on every address of `192.168.8.0/24` (set `OCS_LAN` for another range), logs in as `ocs` with your key, and keeps the machines that report `Macmini7,1`. Each one is named by its hostname, and Ansible uses its wired address when it has one, its Wi-Fi address otherwise. So addresses can change (they do, after a reboot or when Wi-Fi comes up) and the next run still finds them.

```bash
cd infra/macmini/ansible
./inventory.py --table     # about 5 s: one line per Mac mini, with its wired and Wi-Fi addresses
```

A machine named `ocs-intelligence-macmini-N` gets `macmini_number` from its name. One still named by its serial gets it from `infra/macmini/macminis.csv` (`number,serial`, one row per Post-it; template [`macminis.example.csv`](../../infra/macmini/macminis.example.csv)), and the playbook renames it. That file is gitignored: serials identify the school's hardware, and the repo is public. To name one the FIX stick missed, create `host_vars/<its current hostname>.yml` with `macmini_number: 7`. Run `--tags hostname`, then delete that file (the new name carries the number). If it has already joined NetBird, rename its peer in the NetBird dashboard too: NetBird keeps the name a machine joined with.

Host keys are remembered by machine name in `~/.ssh/known_hosts_ocs_macminis`, so a moved address doesn't break SSH. A Mac mini whose key doesn't match the one remembered for its name is left out, and `--table` says so. After reflashing one, delete its line from that file.

Both netplans use `dhcp-identifier: mac`, so the router sees the same client after a reboot and usually hands back the same address. It's still DHCP.

### 3. Run the playbook

```bash
cd infra/macmini/ansible
uv run --group ansible ansible-playbook site.yml --limit ocs-intelligence-macmini-7   # one, to start
uv run --group ansible ansible-playbook site.yml                                      # all it finds
```

It's safe to rerun. The first run on a machine takes a while (a full upgrade, a reboot into the new kernel, the Wi-Fi driver build, and the Python packages). The internet link is shared and slow (about 84 Mb/s, [network](../architecture/network.md#the-ocs-lan)), so run big batches with `--forks 5` or less.

| Part (tag) | What it does |
|---|---|
| `base` | Wait for unattended-upgrades, repair an interrupted install, upgrade, reboot if needed, the package list in [`group_vars/macminis.yml`](../../infra/macmini/ansible/group_vars/macminis.yml), `ocs` in the `docker` group, open-file limits, cluster sysctls, zram swap, `mbpfan` fan control, power-on after a power cut, never sleep |
| `hostname` | `ocs-intelligence-macmini-N` when `macmini_number` is set |
| `network` | The `wl` Wi-Fi driver, then one netplan: Wi-Fi on `MACMINI_WIFI_SSID` (route metric 100, the main link) and wired DHCP (metric 200, the backup) |
| `python` | uv from Astral's installer (pinned version, `/usr/local/bin`), Python 3.12 managed by uv, and `/opt/ocs/venv` synced to [`cluster-requirements.txt`](../../infra/macmini/ansible/files/cluster-requirements.txt) |
| `netbird` | NetBird from its apt repo, as a service, joined with the setup key |
| `ray_check` | Starts a throwaway local Ray, runs 10 tasks, prints the versions |

### 4. Use it

```bash
ssh ocs@<ip>          # or the NetBird IP from anywhere, from a peer in outbound-only
ray --version         # /opt/ocs/venv/bin is on the PATH for login shells
uv pip install --python /opt/ocs/venv/bin/python <pkg>   # one-off; add it to cluster-requirements.in to keep it
```

To add a Python package for every node: edit `cluster-requirements.in`, re-lock with the command at its top, and rerun with `--tags python`.

## Check it worked

- The playbook ends with `failed=0`. `ray_check` prints `ray 2.60.0 python 3.12.… result 285`.
- On the Mac mini: `ip -4 route` shows the default route on the Wi-Fi interface (`wlp2s0`) with metric 100, and a second one on `enp3s0f0` with metric 200.
- `netbird status` shows `Management: Connected`, and the peer shows up in the `ocs-macminis` group.

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| "No wl* interface" | The `wl` module didn't build for the running kernel | `dkms status`; `sudo apt install linux-headers-$(uname -r)`; reboot; rerun |
| Wi-Fi task times out | Wrong SSID or password in `.env`, or the 5 GHz signal is weak in the corner | `sudo journalctl -u netplan-wpa-wlp2s0 -b`; fix `.env`; rerun `--tags network` |
| Ansible loses the host after `network` or a reboot | Its address changed mid-run | Rerun: `inventory.py` finds it at the new address |
| Host unreachable mid-run | Your laptop left `OCS_Intel` (Windows may switch Wi-Fi networks) | Rejoin `OCS_Intel` and rerun; the first task repairs an interrupted upgrade |
| A Mac mini is missing from `inventory.py --table` | It's off, has no network yet (FIX stick), or rejects your SSH key | `ssh ocs@<ip> hostname` to see which |
| `sudo: a password is required` | `MACMINI_SUDO_PASSWORD` missing from `.env` | Add it |
| NetBird join skipped | `NETBIRD_MACMINI_SETUP_KEY` empty | Create one (see above) and rerun `--tags netbird` |
