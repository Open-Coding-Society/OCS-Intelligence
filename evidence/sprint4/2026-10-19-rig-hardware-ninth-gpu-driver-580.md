---
type: playbook
date: 2026-10-19
title: A ninth GPU, a driver that broke, and what's in the rigs
subtitle: Rig 2 gets a ninth card and moves to driver 580 with DKMS after a kernel update; both rigs' platforms are inventoried.
sprint: 4
state: done
---

# A ninth GPU, a driver that broke, and what's in the rigs

On 2026-10-19 the team added a ninth GPU, a GTX 1070, to Rig 2 and rebooted it. The model came back on CPU. An unattended upgrade had moved Rig 2 to kernel 7.0 four days earlier, and its prebuilt NVIDIA 550 driver had no module for that kernel. We moved Rig 2 to driver 580 with DKMS, the setup Rig 1 already ran on the same kernel. All nine cards came up without a reboot, and the model now runs on all nine at the same ~27.7 tok/s as on eight. The same day we confirmed Rig 1 uses all eight of its cards. On 2026-10-20 we recorded both rigs' platforms (board, CPU, RAM, disks, network, and the exact card models), which Sprint 3 had left as "not recorded".

## At a glance

| | |
|---|---|
| Goal | Keep both rigs serving on every card they have, and record what hardware they are |
| Outcome | Rig 2 serves `qwen3.6:35b-a3b` on 9 cards (1 × 1080 Ti + 8 × 1070), driver 580.178.04 with DKMS. Rig 1 serves on all 8 cards, 4 per worker. Both platforms recorded in [hardware](../../docs/architecture/hardware.md) |
| Where | Rig 2 (`ocs-intelligence-rig2`): NVIDIA packages, `/etc/ocs-intelligence/worker.env`. Rig 1: read-only |
| Why | No decision record. The driver choice matches Rig 1 |

## Before

| Check on Rig 2, after the 10:22 reboot | What we saw |
|---|---|
| `lspci` | 9 NVIDIA cards: the new 1070 was seen by the board |
| `nvidia-smi` | `couldn't communicate with the NVIDIA driver` |
| Running kernel | `7.0.0-38-generic`. The boot before ran `6.14.0-27-generic` |
| Installed NVIDIA modules | Only prebuilt 550 modules for 6.14 |
| How the kernel changed | `/var/log/dpkg.log`: unattended upgrade installed 7.0.0-38 on 2026-10-15 07:08. This reboot was the first into it |
| Worker log | `no CUDA-capable device is detected`, `no usable GPU found`: the model loaded into 7 GB of system RAM, and the service still showed `active` |

Rig 1 runs the same kernel without trouble because it uses `nvidia-driver-580` with `nvidia-dkms-580`, which rebuilds the module for each new kernel. Prebuilt 550 modules don't exist for kernel 7.0.

## What we did

All over NetBird SSH. Full record: [capture](../captures/2026-10-19-rig2-ninth-gpu-driver-580.md).

1. **Stop the worker,** which was running on CPU: `systemctl stop ocs-llama`.

2. **Swap driver 550 for 580 in one transaction,** the same packages and repo as Rig 1:

   ```bash
   apt-get install -y nvidia-driver-580 nvidia-dkms-580 <every installed *nvidia*550* package, with a trailing ->
   ```

   Installing 580 without removing 550 in the same command fails (`nvidia-kernel-common-550 : Conflicts: nvidia-kernel-common`) and changes nothing. The DKMS build takes several minutes on the 2-core Celeron.

3. **Load the driver without a reboot:** `modprobe nvidia && modprobe nvidia_uvm`. `nvidia-smi` then listed all nine cards. The new one is index 3, `GPU-8e7ca25c…`, at bus `0B:00.0`. GRUB wasn't changed.

4. **Put the worker on all nine cards.** After backing up `worker.env`, we listed all nine UUIDs in `CUDA_VISIBLE_DEVICES` and set:

   ```bash
   TENSOR_SPLIT=11,8,8,8,8,8,8,8,8   # GPU 0 is the 11 GB 1080 Ti
   ```

   Then `systemctl restart ocs-llama`. Two 400-token runs: **27.6 and 27.8 tok/s**, the same as on eight cards. With `--split-mode layer` the cards run one after another, so the ninth adds memory, not speed.

5. **Check Rig 1, read-only.** All 8 cards are in use: Worker A (`qwen3.8:27b`) on 4, Worker B (`gemma4:26b`) on 4. Worker B had been changed from `qwen2.5:0.5b` on 2 cards; its config file is dated 2026-10-16. Who changed it, and its speed, weren't recorded.

6. **Inventory both platforms** (2026-10-20, read-only): `lscpu`, `free`, `dmidecode`, `lsblk`, `ethtool`, `lspci`, `nvidia-smi -q`. Full record: [capture](../captures/2026-10-20-rig-hardware-inventory.md).

   | | Rig 1 | Rig 2 |
   |---|---|---|
   | Board, BIOS | ASUS B250 Mining Expert, 0403 | Same board, 1001 |
   | CPU | Intel Celeron G3930, 2 cores | Same |
   | RAM | 2 × 8 GB Corsair DDR4 at 2133 MT/s | 1 × 8 GB, same part |
   | Disk the OS sees | Samsung 860 EVO 250 GB | Samsung 860 EVO M.2 250 GB |
   | Cards | 8 × EVGA GTX 1070 FTW Hybrid (185 W) | EVGA GTX 1080 Ti SC Black (250 W, air) + 8 × EVGA GTX 1070 FTW Hybrid |
   | PCIe | gen 1 ×1, every card | Same |

   Card models come from the PCI subsystem IDs (`3842:6278`, `3842:6393`) matched against EVGA part numbers in retailer listings. They weren't read off the cards.

> [!WARNING]
> A worker that can't find a GPU doesn't fail: llama.cpp falls back to CPU, and systemd reports the service as `active`. After any reboot, check `nvidia-smi` and grep the worker log for `no usable GPU found`.

## How to check it

| Check | Pass looks like | If it fails |
|---|---|---|
| `nvidia-smi -L` on Rig 2 | 9 lines: one 1080 Ti, eight 1070s | `dkms status` shows whether the module built for `uname -r` |
| `dkms status` | `nvidia/580.178.04, <running kernel>, x86_64: installed` | Rebuild: `dkms autoinstall`, then `modprobe nvidia` |
| `journalctl -u ocs-llama -b \| grep -i 'no usable GPU'` | No output | The worker is on CPU: fix the driver, then restart `ocs-llama` |
| `curl -s http://127.0.0.1:9000/readyz` on Rig 2 | `{"status":"ready"}` | Worker still loading, or crashed |
| `nvidia-smi -L` on Rig 1 | 8 × GTX 1070 | — |

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `nvidia-smi` fails after a reboot, but the GPUs show in `lspci` | An unattended upgrade moved to a kernel the prebuilt driver doesn't cover | Use the DKMS driver (`nvidia-dkms-580`), as both rigs now do |
| Model is slow and system RAM is full, but the service is `active` | Worker fell back to CPU | See the warning above |
| `apt-get install nvidia-driver-580` refuses to install | 550 and 580 packages conflict | Remove the 550 packages in the same command (trailing `-`) |
| A new card adds no speed | Layer split runs one card at a time | Expected. It adds memory (context, or a bigger model) |

## Open items

- **Unattended upgrades are still on for both rigs.** DKMS should build the driver for the next kernel at install time, but nobody has watched it happen. Decide whether to keep them on, hold the kernel, or watch the next one.
- **Second SSDs.** The team reports a 480 GB SSD in Rig 1 and a second 256 GB in Rig 2. Neither OS sees them: unplugged, or not installed.
- **Power supplies (reported, not checked):** both 1800 W supplies are an unknown brand. Rig 2's EVGA supply is 850 W or 1300 W. Rig 2's ninth card is believed to be on the Antec, making its split 5 / 2 / 2. Read the labels.
- **Worker B's change to `gemma4:26b`** needs its owner, its reason, and a speed measurement.
- Rig 1's Ethernet linked at 100 Mb/s on 2026-10-20. It was fixed on 2026-10-22 and is written up with the Sprint 5 networking work ([pending playbook](../pending-playbook.md)).

## Sources

- [Rig 2: ninth GPU added, driver moved to 580](../captures/2026-10-19-rig2-ninth-gpu-driver-580.md) (also Rig 1, read-only)
- [Both rigs: platform hardware inventory](../captures/2026-10-20-rig-hardware-inventory.md)
- [Hardware](../../docs/architecture/hardware.md), the canonical inventory
- Power supply and second-SSD details: reported by the team on 2026-10-20
