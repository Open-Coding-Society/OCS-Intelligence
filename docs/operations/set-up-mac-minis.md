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

### 1. The FIX stick sets each Mac mini up by itself (one command per machine)

The stick turns on the wired port, then hands over to a setup kit that runs this same playbook **on the Mac mini itself**, as a service (`ocs-bootstrap`). Your laptop isn't needed, and the machines run in parallel.

**Not tested on a real Mac mini yet** (built 2026-11-13). The pieces are tested offline. Try it on one machine first.

**Build the stick (once, on the laptop):**

1. The repo `.env` needs `MACMINI_WIFI_SSID`, `MACMINI_WIFI_PASSWORD` and `NETBIRD_MACMINI_STICK_KEY`. The last is a setup key limited to 33 uses and 14 days: `python3 -c 'import sys; sys.path.insert(0,"infra/netbird"); import apply; print(apply.setup_key("ocs-macminis", days=14, uses=33))'`.
2. `infra/macmini/macminis.csv` holds the Post-it table (`number,serial`). It's gitignored.
3. `python3 infra/macmini/make_stick.py --out /mnt/c/Users/<you>/Downloads/ocs-macmini-stick` (the default `--out` is the gitignored `infra/macmini/build/stick`).
4. Copy everything in that folder onto a FAT32 stick labeled `FIX`. The stick now holds the Wi-Fi password and the NetBird key. Keep it with the Mac minis, and wipe it when the batch is done.

**At each Mac mini** (Ethernet plugged in; a keyboard; a monitor for the first few), log in as `ocs`, then:

```bash
sudo mount -L FIX /mnt; sudo sh /mnt/f
```

It prints the network line, then `#7 (serial C07…): setup started. You can pull the stick.` Pull it and move to the next machine.

- `#?` means the serial isn't in `macminis.csv`. The machine is still set up, but keeps its serial name. Fix the table, then rename it with `--tags hostname` from the laptop.
- No address, or `carrier=0`: check the cable and the port's light.

**What happens next, on its own** (about 20–30 minutes, with one reboot):

- **Kit:** `bootstrap.sh` copies the kit to `/root/ocs-bootstrap/` (root-only) and installs the pinned `uv`. It reads the serial from the firmware and looks up the number.
- **Service:** it starts `ocs-bootstrap.service`, which runs `run.sh`. That runs `uvx --from ansible-core==2.21.6 ansible-playbook` against `this-macmini` with a local connection.
- **Reboot:** when the upgrade brings a new kernel, the playbook marks the reboot, reboots, and the service runs it again after boot. (Ansible can't reboot its own controller and carry on.)
- **Failure:** it retries a minute later, up to 5 tries.
- **Success:** it deletes `secrets.env`, disables itself, and prints `DONE` to the console.
- **Watching:** `journalctl -fu ocs-bootstrap` on the machine shows progress, and `/var/log/ocs-bootstrap.log` holds the full log.

**Keep the Ethernet cable in until it's done.** The Wi-Fi card (BCM4360) needs the `wl` driver, which a fresh install doesn't have. The playbook builds it from the internet over the cable, then switches to Wi-Fi. After that the cable is optional.

**Afterwards, from the laptop** (on `OCS_Intel`): `infra/macmini/ansible/inventory.py --table` lists them, and `reservations.py --apply` gives each its fixed addresses.

**Without the kit** (just the `f` file on the stick), the stick only turns on the wired port, and the playbook is run from the laptop (steps 2–3). Machines flashed before 2026-11-12 need the stick either way: the install ran with no cable, so the installer disabled the wired port.

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
| `base` | Point apt at the cache when it answers, wait for unattended-upgrades, repair an interrupted install, upgrade, reboot if needed, the package list in [`group_vars/macminis.yml`](../../infra/macmini/ansible/group_vars/macminis.yml), `ocs` in the `docker` group, open-file limits, cluster sysctls, zram swap, `mbpfan` fan control, power-on after a power cut, never sleep |
| `hostname` | `ocs-intelligence-macmini-N` when `macmini_number` is set |
| `cache` | Only on the cache host (silver, `ocs_cache_server: true` in `host_vars`): `apt-cacher-ng` on `:3142`, plus the locked wheels and the pinned `uv` on `http://<host>:8090/`. The others use it when it answers, and the internet when it doesn't (apt through `Proxy-Auto-Detect`; https repos such as NetBird's always go direct). |
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
