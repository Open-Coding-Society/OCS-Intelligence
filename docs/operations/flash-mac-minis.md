---
status: draft
last_verified: 2026-10-27
---

# How to flash the Mac minis with Ubuntu Server (autoinstall sticks)

By the end, every Mac mini runs Ubuntu Server 26.04.1 with user `ocs`, key-only SSH, and nothing else installed. Each one is named after its serial number for now, and gets renamed to `ocs-intelligence-macN` later. Packages come later too, with Ansible. Why sticks and not netboot or Clonezilla: [decision 0011](../decisions/0011-autoinstall-sticks-for-mac-minis.md). The kit is in [`infra/macmini/`](../../infra/macmini/).

**Draft:** tested end to end in a QEMU VM, but not yet on a real Mac mini. Do [step 3](#3-test-one-mac-mini-with-a-monitor) before the rest.

## How it works

- `build_iso.py` makes one ISO from the stock Ubuntu ISO. It has `/autoinstall.yaml` at its root and `autoinstall` on the kernel line, so the installer runs without asking anything. Every stick gets the same image.
- No network is needed. The install uses only the packages on the stick (apt's mirror is set to `offline.invalid`, so Subiquity falls back to an offline install even if a cable is plugged in). At the end, apt is pointed back at `archive.ubuntu.com` for later.
- The hostname is `ocs-intelligence-` plus the serial number from the bottom of the box, lowercased (e.g. `ocs-intelligence-c07p1234g1j1`). It's unique with no network, and it matches the label.
- When the install finishes, the Mac mini powers off.

**Warning:** a stick wipes the largest disk of any computer it boots, without asking. Label the sticks and keep them away from other machines.

| Setting | Value |
|---|---|
| User | `ocs`, with the password typed into `build_iso.py` (works at the console and for `sudo`, not over SSH) |
| SSH | `openssh-server`, key only, keys from `--ssh-key` (default `~/.ssh/id_ed25519.pub`) |
| Disk | The largest disk (the 1 TB drive), wiped, one ext4 root partition |
| Locale, keyboard, timezone | `en_US.UTF-8`, `us`, `America/Los_Angeles` |
| Hostname | `ocs-intelligence-<serial>` until [renamed](#5-rename-them-later) |

## Before you start

- The stock ISO, [`ubuntu-26.04.1-live-server-amd64.iso`](https://releases.ubuntu.com/26.04/). Check it against `SHA256SUMS` from the same page.
- WSL or Linux with `xorriso`, `openssl` and Python 3, only to build the ISO (`sudo apt install xorriso`).
- USB sticks of 4 GB or more, and [balenaEtcher](https://etcher.balena.io/) or Rufus on Windows.
- One USB keyboard. For the first machine, a monitor too.

## Steps

### 1. Build the ISO (once)

In WSL, reading the ISO from Windows and writing the result back there:

```bash
python3 infra/macmini/build_iso.py \
    --iso /mnt/c/Users/<you>/Downloads/ubuntu-26.04.1-live-server-amd64.iso \
    --out-dir /mnt/c/Users/<you>/Downloads/ocs-macmini
```

It asks for the `ocs` password twice and writes `ubuntu-26.04.1-ocs-macmini-amd64.iso` (plus the filled-in `autoinstall.yaml` and patched `grub.cfg`, for inspection) to `--out-dir`. The default `--out-dir` is `infra/macmini/build/`, which is gitignored because the output holds the password hash. To let other operators in, repeat `--ssh-key path/to/key.pub`.

### 2. Write the sticks (on Windows)

Every stick gets the same image, written as a raw image.

- **balenaEtcher** writes one image to several sticks at once: Flash from file → pick the ISO → Select target → tick every stick.
- **Rufus** does one stick at a time. When it asks, choose **Write in DD Image mode**, not ISO mode.
- **Linux:** `sudo dd if=ubuntu-26.04.1-ocs-macmini-amd64.iso of=/dev/sdX bs=4M status=progress conv=fsync` (check `/dev/sdX` with `lsblk` first; it wipes it).

Rewrite from the image; don't copy stick to stick.

### 3. Test one Mac mini with a monitor

1. Plug in the keyboard, monitor, stick, then power. No network cable needed.
2. Hold **Option (⌥)** right after the chime until the boot picker appears. Pick the orange drive labeled **EFI Boot**.
3. GRUB waits 5 seconds, then the installer runs by itself. Nothing should ask a question. The machine powers off when it's done.
4. Unplug the stick and power on. Log in at the console as `ocs` and run `hostname`. It should be `ocs-intelligence-` plus the serial on the bottom of the box.

Also try holding **C** instead of Option on this machine. Apple documents C as "start up from a bootable CD, DVD, or USB thumb drive", so it may skip the picker. If it does, the other machines need only a keyboard, no monitor. Update this guide either way.

### 4. Do the rest

For each Mac mini: stick in, power on while holding Option (or C), pick **EFI Boot**, let go, and move the keyboard on. Run as many at once as you have sticks and power outlets. A machine that has powered off is finished; pull its stick.

The Option or C key is needed because these Mac minis still have macOS on the internal disk, so the firmware boots that unless told otherwise.

### 5. Rename them later

Once a machine is on the network, from the Mac mini (or over SSH, with its IP from the router's client list):

```bash
sudo hostnamectl set-hostname ocs-intelligence-macN
sudo sed -i "s/ocs-intelligence-[a-z0-9]*/ocs-intelligence-macN/g" /etc/hosts
sudo reboot
```

Keep a list of serial → `macN` so the stickers and names match.

## Check it worked

- At the console: `hostname` prints `ocs-intelligence-<serial>`.
- Once on the network: `ssh ocs@<IP> hostname` works with the key, and `ssh -o PubkeyAuthentication=no ocs@<IP>` is refused (`Permission denied (publickey)`).

The QEMU run is logged in the [pending playbook](../../evidence/pending-playbook.md).

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| No **EFI Boot** in the Option picker | Stick written in ISO/file mode, or a bad stick | Rewrite it as a raw image (Etcher, or Rufus in DD mode) |
| The installer asks questions | `autoinstall.yaml` missing or invalid | Check `autoinstall.yaml` in the out-dir; rebuild; check the kernel line in `grub.cfg` has `autoinstall` |
| Installer stops with an error | Usually a late-command | Switch to a shell (Alt+F2) and read `/var/log/installer/subiquity-server-debug.log` |
| Hostname is `ocs-intelligence-unknown` or a MAC address | Firmware gave no serial | Rename it (step 5) |
| Installed on the wrong disk | A model with two internal disks (Fusion Drive) | `lsblk` on mac1; set `storage.layout.match` in the template to a `serial` or `ssd` match |
| `apt update` fails after install | No internet yet | Expected until it's on a network with internet |
