---
status: current
last_verified: 2026-10-19
---

# Hardware

The physical rigs and the single source for the GPU inventory. Both rigs' inventories verified with `nvidia-smi` over NetBird SSH on 2026-10-19.

## Rigs

| Rig | Role | State | Cards |
|---|---|---|---|
| Rig 1 (`ocs-intelligence-rig`) | Production inference | Serving on all 8 cards (4 per worker) | 8 × GTX 1070 (8 GB). Driver 580.178.04 (DKMS) on kernel 7.0.0-38 (2026-10-19) |
| Rig 2 (`ocs-intelligence-rig2`) | Development and test; proposed to serve students through Open WebUI ([0009](../decisions/0009-rig2-moe-behind-open-webui.md)) | Serving `qwen3.6:35b-a3b` on all 9 cards (2026-10-19). Every card is on PCIe gen 1 ×1 | 9: GPU 0 is a **GTX 1080 Ti** (11 GB, in place of a 1070 that shipped with a broken hybrid fan), GPUs 1–8 are GTX 1070 (8 GB). The ninth card (a 1070) was added 2026-10-19. Driver 580.178.04 (DKMS) on kernel 7.0.0-38 ([evidence](../../evidence/captures/2026-10-19-rig2-ninth-gpu-driver-580.md)) |

> **Card count, resolved.** The 2026-09-18 inventory of Rig 1 showed 7 cards. After the Sprint 3 rewire ([playbook](../../evidence/sprint3/2026-09-28-resolving-both-rigs.md)) all 8 work; the table below is the 2026-10-19 inventory and includes the 8th card (`GPU-4de8c392…`). Indices and bus numbers changed in the rewire, which is why workers pin by UUID.

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

| Index | UUID | PCI bus | Worker |
|---:|---|---|---|
| 0 | `GPU-a25606af-913d-22d1-5ebe-ecea656819cb` | `03:00.0` | B |
| 1 | `GPU-728d79b7-b5ed-e1ec-cf29-0572f97956ba` | `07:00.0` | A |
| 2 | `GPU-4de8c392-e998-738f-0078-d4d4e54fc2b0` | `0A:00.0` | B |
| 3 | `GPU-71f15481-4db3-9d2a-8d30-6e68dba08617` | `0B:00.0` | A |
| 4 | `GPU-2a70bbf9-ed03-162f-ddd5-c7ed42149d84` | `0C:00.0` | B |
| 5 | `GPU-fb4eb983-84aa-664f-b97d-94b12caffb37` | `0D:00.0` | A |
| 6 | `GPU-bc07dc85-473b-9927-538e-986f80b80486` | `0E:00.0` | B |
| 7 | `GPU-24899ea8-3258-0dd0-5aa4-6ef9104cdc68` | `0F:00.0` | A |

Worker assignment is from each worker's `CUDA_VISIBLE_DEVICES` on 2026-10-19. The 2026-09-18 inventory also recorded topology (`nvidia-smi topo -m`); it hasn't been re-run since the rewire.

Workers pin their GPUs by UUID, not index, so re-cabling can't silently reassign cards ([worker env](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env)).

## GPU inventory (Rig 2)

From `nvidia-smi` on 2026-10-19 ([evidence](../../evidence/captures/2026-10-19-rig2-ninth-gpu-driver-580.md)). The worker uses all nine, in this order.

| Index | Card | UUID | PCI bus |
|---:|---|---|---|
| 0 | GTX 1080 Ti (11 GB) | `GPU-51bb095a-33b3-54e1-8673-58f98f275bc0` | `01:00.0` |
| 1 | GTX 1070 | `GPU-83daccf4-1ff0-6fa0-19c3-d424e6aa2a97` | `04:00.0` |
| 2 | GTX 1070 | `GPU-5564a0bd-3c8d-fe31-5675-aaba5effb805` | `08:00.0` |
| 3 | GTX 1070 (added 2026-10-19) | `GPU-8e7ca25c-e499-1818-e488-3ba4a78b70b1` | `0B:00.0` |
| 4 | GTX 1070 | `GPU-ee8e7563-ecfb-d5ee-0f36-74b5bd76ddaf` | `0C:00.0` |
| 5 | GTX 1070 | `GPU-69f0a712-56fc-d954-265f-8469c2a21c9d` | `0D:00.0` |
| 6 | GTX 1070 | `GPU-2b6607e6-a556-543b-4c88-d7ddb156b184` | `0E:00.0` |
| 7 | GTX 1070 | `GPU-64ccc864-2ced-25a4-64bc-f23cd1f108dc` | `0F:00.0` |
| 8 | GTX 1070 | `GPU-a512d941-05b9-654c-b47c-8cc3b03bfa1a` | `10:00.0` |

Which power supply feeds the ninth card isn't recorded; the power table above predates it.

## Why the hardware matters

- **8 GB per card** limits model size. A 27B Q4 model (~16.8 GB) needs several cards.
- **x1 risers and no NVLink** make every cross-card transfer slow. Splitting a model across more cards adds a hop per token ([decision 0003](../decisions/0003-5-plus-2-gpu-split.md)).
- **Pascal** rules out CUDA 13 and stock vLLM ([decision 0001](../decisions/0001-llama-cpp-over-vllm.md)).
- **Used parts** have no known history. Each card must be proven under sustained load (thermal paste, power rails, risers).
