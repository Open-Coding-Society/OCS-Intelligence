---
status: current
last_verified: 2026-09-18
---

# Hardware

The physical rigs and the single source for the GPU inventory. Rig 1 inventory verified with `nvidia-smi` on 2026-09-18.

## Rigs

| Rig | Role | State | Cards |
|---|---|---|---|
| Rig 1 (`ocs-intelligence-rig`) | Production inference | Serving | 8 × GTX 1070, as reported by the team on 2026-10-16 after the Sprint 3 rebuild. The 2026-09-18 inventory (table below) shows 7. The 8th card's UUID hasn't been recorded |
| Rig 2 (`ocs-intelligence-rig2`) | Development and test; proposed to serve students through Open WebUI ([0009](../decisions/0009-rig2-moe-behind-open-webui.md)) | Serving `qwen3.6:35b-a3b` on all cards (2026-10-15). Every card is on PCIe gen 1 ×1 | 8 visible to `nvidia-smi`: GPU 0 is a **GTX 1080 Ti** (11 GB, in place of a 1070 that shipped with a broken hybrid fan), GPUs 1–7 are GTX 1070 (8 GB). Driver 550.163.01 |

> **Card count, resolved.** The 2026-09-18 inventory of Rig 1 showed 7 cards. After the Sprint 3 rewire, the team reports all 8 working ([playbook](../../evidence/sprint3/2026-09-28-resolving-both-rigs.md)). The table below still needs a fresh `nvidia-smi` inventory with the 8th UUID.

## Power, storage, and memory

As reported by the team on 2026-10-16 ([Sprint 3](../../evidence/sprint3/2026-09-28-resolving-both-rigs.md)). Not checked on the machines.

| | Rig 1 | Rig 2 |
|---|---|---|
| Power supplies | 1800 W (5 GPUs + board and CPU), Antec 1300 W (3 GPUs) | 1800 W (5 GPUs + board and CPU), EVGA (2 GPUs), Antec 1300 W (1 GPU) |
| SSDs | 2 | 1 |
| RAM | Not recorded | 1 stick: with two, the board doesn't start |
| BIOS | Not reflashed | Reflashed in Sprint 3 |

## Rig 1 platform

| | |
|---|---|
| Motherboard | ASUS B250 Mining Expert |
| CPU | 2 cores (llama.cpp builds take ~35 min) |
| OS | Ubuntu 24.04.4 |
| GPU links | PCIe Gen1 x1 risers, ~250 MB/s each. **No NVLink.** |
| Network | School Wi-Fi over a USB 2.0 dongle. PyPI is DNS-blocked. |
| Disk | ~151 GB free (2026-09-18) |

## GPU inventory (Rig 1)

GTX 1070: Pascal, compute capability 6.1 (`sm_61`), 8 GB GDDR5, 150 W board power.

| Index | UUID | PCI bus | Topology | Group |
|---:|---|---|---|---|
| 0 | `GPU-24899ea8-3258-0dd0-5aa4-6ef9104cdc68` | `03:00.0` | PIX with GPU 1 | A |
| 1 | `GPU-728d79b7-b5ed-e1ec-cf29-0572f97956ba` | `08:00.0` | PIX with GPU 0 | A |
| 2 | `GPU-fb4eb983-84aa-664f-b97d-94b12caffb37` | `0A:00.0` | PHB | A |
| 3 | `GPU-71f15481-4db3-9d2a-8d30-6e68dba08617` | `0B:00.0` | PHB | A |
| 4 | `GPU-bc07dc85-473b-9927-538e-986f80b80486` | `0C:00.0` | PHB | A |
| 5 | `GPU-2a70bbf9-ed03-162f-ddd5-c7ed42149d84` | `0E:00.0` | PHB | B |
| 6 | `GPU-a25606af-913d-22d1-5ebe-ecea656819cb` | `0F:00.0` | PHB | B |

`PIX` means the two cards share a PCIe switch. `PHB` means traffic goes through the host bridge. Workers pin their GPUs by UUID, not index, so re-cabling can't silently reassign cards ([worker env](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env)).

## Why the hardware matters

- **8 GB per card** limits model size. A 27B Q4 model (~16.8 GB) needs several cards.
- **x1 risers and no NVLink** make every cross-card transfer slow. Splitting a model across more cards adds a hop per token ([decision 0003](../decisions/0003-5-plus-2-gpu-split.md)).
- **Pascal** rules out CUDA 13 and stock vLLM ([decision 0001](../decisions/0001-llama-cpp-over-vllm.md)).
- **Used parts** have no known history. Each card must be proven under sustained load (thermal paste, power rails, risers).
