---
date: 2026-10-20
---

# Both rigs: platform hardware inventory (2026-10-20)

Inspected read-only over NetBird SSH (`root@100.75.123.203`, `ocs-intelligence-rig`, and `root@100.75.127.192`, `ocs-intelligence-rig2`) from the `Yash WSL` peer. Nothing was changed. This is a record: don't edit it. Canonical inventory: [hardware](../../docs/architecture/hardware.md).

Commands: `lscpu`, `free -h`, `dmidecode -t baseboard -t bios -t memory`, `lsblk`, `ls /dev/disk/by-id`, `dmesg | grep 'SATA link'`, `ip -br link`, `/sys/class/net/*/speed`, `ethtool`, `lspci`, `nvidia-smi --query-gpu=…`, `nvidia-smi -q`, `systemctl is-active`, and the worker env files (keys filtered out).

## Platform

| | Rig 1 | Rig 2 |
|---|---|---|
| Motherboard | ASUSTeK B250 MINING EXPERT | ASUSTeK B250 MINING EXPERT |
| BIOS | 0403 (2017-11-20) | 1001 (2017-12-13) |
| CPU | Intel Celeron G3930 @ 2.90 GHz, 2 cores, 2 threads | Same |
| RAM | 2 × 8 GB DDR4 Corsair `CMK8GX4M1A2400C16`, running at 2133 MT/s (ChannelA-DIMM1, ChannelB-DIMM1). `free`: 15 Gi | 1 × 8 GB DDR4, same part, 2133 MT/s. `free`: 7.6 Gi |
| Storage the OS sees | 1 disk: Samsung SSD 860 EVO 250 GB (SATA), 1 GB EFI + 232 GB root, 77 GB used | 1 disk: Samsung SSD 860 EVO M.2 250 GB (SATA), 1 GB EFI + 232 GB root, 63 GB used. `dmesg`: ata3 link up at 6.0 Gbps, ata4–ata6 link down |
| Network | Intel I219-V onboard Ethernet (`enp0s31f6`), up, **link at 100 Mb/s**. No Wi-Fi interface | Intel I219-V onboard Ethernet (`enp0s31f6`), up, link at 1000 Mb/s. No Wi-Fi interface |
| OS | Ubuntu 24.04.4 LTS, kernel 7.0.0-38-generic | Ubuntu 24.04.3 LTS, kernel 7.0.0-38-generic |
| Driver / CUDA | 580.178.04, CUDA 12.6 (`nvcc` 12.6) | Same |

The team reported 2026-10-20 that Rig 1 also has a 480 GB SSD and Rig 2 a second 256 GB SSD. Neither appears in `lsblk` or `/dev/disk/by-id`, so the OS doesn't see them: unplugged, or not installed.

## GPUs

| | Rig 1 | Rig 2 |
|---|---|---|
| Cards | 8 × GTX 1070 (8192 MiB) | GPU 0: GTX 1080 Ti (11264 MiB); GPUs 1–8: GTX 1070 (8192 MiB) |
| PCI subsystem | All 8: EVGA `3842:6278` | 1080 Ti: EVGA `3842:6393`; all 8 1070s: EVGA `3842:6278` |
| Power limit | 185 W each | 1080 Ti 250 W; 1070s 185 W each |
| PCIe link | gen 1, ×1, every card | gen 1, ×1, every card |
| VBIOS | 86.04.50.00.70 on all | 1080 Ti 86.02.39.00.90; 1070s 86.04.50.00.70, except GPU 5 at 86.04.50.01.70 |

EVGA's subsystem IDs match its part numbers: `6278` is the GTX 1070 FTW Hybrid Gaming (`08G-P4-6278`, hybrid water/air cooler), and `6393` is the GTX 1080 Ti SC Black Edition (`11G-P4-6393`, iCX air cooler). The match was looked up in retailer listings, not checked on the cards.

## Services and workers

| | Rig 1 | Rig 2 |
|---|---|---|
| Active | `ocs-llama-a`, `ocs-llama-b`, `ocs-orchestrator`, `docker` (container `open-webui`, `0.0.0.0:3000->8080`) | `ocs-llama`, `ocs-orchestrator` |
| Inactive | `ollama` | `ollama`, `docker` |
| Worker env | A: `qwen3.8:27b`, 4 UUIDs, `TENSOR_SPLIT=1,1,1,1`. B: `gemma4:26b` (`gemma-4-26B-A4B-it-UD-Q4_K_XL.gguf`), 4 UUIDs, `TENSOR_SPLIT=1,1,1,1`. Same UUIDs per worker as on 2026-10-19 | `qwen3.6:35b-a3b`, 9 UUIDs, `TENSOR_SPLIT=11,8,8,8,8,8,8,8,8`, `CONTEXT_SIZE=524288`, `PARALLEL=2`, `LLAMA_EXTRA_ARGS=-ub 1024` |

## Reported by the team, 2026-10-20 (not checked on the machines)

- Both rigs run on wired Ethernet now (matches the probe).
- 1800 W supplies: brand unknown on both rigs.
- Rig 2's EVGA supply is 850 W or 1300 W; which one isn't known.
- Rig 2's ninth card is on the supply that used to feed one card, believed to be the Antec 1300 W. That makes Rig 2's split 5 / 2 / 2 (1800 W / EVGA / Antec).
