---
type: playbook
date: 2026-09-28
title: Resolving both rigs
subtitle: Both GPU rigs rebuilt, rewired, and booting with all 8 GPUs each.
sprint: 3
state: done
---

# Resolving both rigs

Sprint 3 was hardware work. Both GPU rigs were rewired from scratch, and their power was split across several power supplies so that every GPU has a supply it can rely on. Rig 1 now runs **all 8 of its GPUs**. On 2026-09-18 only 7 appeared, and the [hardware doc](../../docs/architecture/hardware.md) had carried that as an open question ever since. Rig 2 wouldn't start: the motherboard's fan spun, but the screen never came on. We reflashed its BIOS and tested a whole replacement motherboard with a bare-minimum setup. That isolated the fault: the board wouldn't POST with two RAM sticks installed. Rig 2 went back to its original motherboard with one stick and now boots with all 8 GPUs. One of its GTX 1070s shipped with a completely broken hybrid cooler fan, so a GTX 1080 Ti takes that slot. This work is what made [Sprint 4](../sprint4/2026-10-15-inference-on-both-rigs.md) possible: inference on both rigs.

> [!NOTE]
> Sprint 3 started on 2026-09-28 or 2026-10-05 (which one wasn't recorded), and the team reported it nearly done on 2026-10-14. The facts here were reported by the team on 2026-10-16. Hardware work wasn't captured as it happened, so there are no logs or photos. The Rig 2 GPU list was checked with `nvidia-smi` on 2026-10-15 ([capture](../captures/2026-10-15-rig2-inference-fix.md)). Rig 1's 8-GPU count hasn't been captured in `evidence/` yet.

## At a glance

| | |
|---|---|
| Goal | Both rigs boot reliably, with every GPU detected, after being rebuilt |
| Outcome | Done. Rig 1: 8 GPUs. Rig 2: 8 GPUs (1 × GTX 1080 Ti + 7 × GTX 1070) |
| Where | The two physical rigs: power, cabling, RAM, BIOS, motherboard |
| Hardest part | Rig 2 not starting (no display), traced to two RAM sticks |

## The rigs after Sprint 3

| | Rig 1 (`ocs-intelligence-rig`) | Rig 2 (`ocs-intelligence-rig2`) |
|---|---|---|
| GPUs | 8 × GTX 1070 | 7 × GTX 1070 + 1 × GTX 1080 Ti (GPU 0, 11 GB), in place of a 1070 that shipped with a broken hybrid fan |
| Power supplies | 2 | 3 |
| Storage | 2 SSDs | 1 SSD |
| RAM | Not recorded | **1 stick** (two sticks stopped POST) |
| Motherboard | ASUS B250 Mining Expert | Original board, kept after a replacement was tested |
| BIOS | Not reflashed | Reflashed |

### Power layout

Each GPU draws up to about 150 W (GTX 1070) or 250 W (GTX 1080 Ti), so no single supply carries a whole rig.

| Rig | Supply | Powers |
|---|---|---|
| Rig 1 | 1800 W (lesser-known brand) | 5 GPUs + motherboard and CPU |
| Rig 1 | Antec 1300 W | 3 GPUs |
| Rig 2 | 1800 W (same brand and model as Rig 1's) | 5 GPUs + motherboard and CPU |
| Rig 2 | EVGA (wattage not recorded) | 2 GPUs |
| Rig 2 | Antec 1300 W | 1 GPU |

## Before

- **Rig 1** showed only 7 of its 8 GPUs to `nvidia-smi` on 2026-09-18. The blueprint and the mentor deck both describe 8 cards per rig.
- **Rig 2** wouldn't start. The motherboard's fan spun up, but the screen never came on, so it never reached the OS.
- **Rig 1** was mostly fine. It needed a lot of rewiring and hardware fixes, but nothing on it was broken outright.
- One of Rig 2's GTX 1070s arrived with a completely broken hybrid cooler fan.
- Both rigs had been taken apart and rebuilt. Their cabling had grown over time and was hard to trace.

## What we did

1. **Rewired both rigs, cleanly, from scratch.** Every riser, GPU power lead, and supply was re-run so each GPU's power can be traced to one supply.
2. **Split the power across several supplies** (table above). The motherboard and CPU share a supply with five GPUs on each rig, and the other GPUs get their own supplies.
3. **Brought Rig 1's 8th GPU up.** All 8 GPUs work after the rewire, which settles the 7-versus-8 question.
4. **Reflashed Rig 2's BIOS.** Rig 1's wasn't touched.
5. **Replaced the broken 1070 on Rig 2 with a GTX 1080 Ti.** It has 11 GB instead of 8, which Rig 2's worker config accounts for (`TENSOR_SPLIT=11,8,8,8,8,8,8,8`).
6. **Isolated Rig 2's POST failure with a second motherboard.** We tested an entirely different motherboard in a bare-minimum setup. That isolated the problem to the RAM: with **two sticks** installed, POST stopped working.
7. **Went back to the original motherboard** with a single RAM stick. Rig 2 POSTs and boots with all 8 GPUs.

> [!TIP]
> When a mining board won't POST, strip it to board + CPU + one RAM stick + one GPU before blaming anything else. Swapping in a known-good board, as we did, tells you whether the fault moves with the board or stays with a part.

## How to check it

| Check | Pass looks like | If it fails |
|---|---|---|
| Power on each rig | POST, then Ubuntu boots | Rig 2: check that only one RAM stick is installed |
| `nvidia-smi -L` on Rig 1 | 8 GPUs listed | Re-seat the missing card's riser and check its supply lead |
| `nvidia-smi -L` on Rig 2 | 8 GPUs, GPU 0 is the GTX 1080 Ti | Same |
| `nvidia-smi --query-gpu=index,pcie.link.gen.current,pcie.link.width.current --format=csv` | Every card at gen 1, ×1 (the riser limit) | A card missing here isn't seated or isn't powered |

## Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Rig 2: motherboard fan spins, but no display and no boot | Two RAM sticks installed | Run one stick |
| A GPU's hybrid cooler fan is dead on arrival | Shipping damage or a bad card | Don't run it. Replace the card. On Rig 2, a GTX 1080 Ti took its place |
| A GPU missing from `nvidia-smi` | Riser or supply lead not seated, or the supply is overloaded | Trace the card to its supply in the power table. Re-seat. Move it to a less loaded supply |
| Hard to tell which supply feeds which card | Cabling grown over time | Rewire cleanly, and keep the power table up to date |

## Open items

- **Use Rig 1's 8th GPU.** Workers pin GPUs by UUID, so the new card isn't in Worker A or Worker B until the [hardware inventory](../../docs/architecture/hardware.md) and worker env are updated.
- **Capture Rig 1's new GPU inventory** (`nvidia-smi -L` with UUIDs) in `evidence/`, and update [hardware](../../docs/architecture/hardware.md).
- **Label rigs, GPUs, and supplies** so the power table can be checked by eye ([roadmap](../../docs/project/roadmap.md#planned-not-built)).
- **Rig 2 runs one RAM stick.** If it needs more memory, test a matched pair, or a pair in different slots, before relying on it.
- Not recorded: the EVGA supply's wattage, the 1800 W supplies' brand, SSD and RAM sizes, the replacement motherboard's model, and the BIOS version.

## Sources

- Reported by the team: 2026-10-14 (nearly done) and 2026-10-16 (done, with the details above)
- Rig 2 GPU list and PCIe links: [Rig 2 record, 2026-10-15](../captures/2026-10-15-rig2-inference-fix.md)
- Rig 1's 7-GPU inventory before the rebuild: [hardware](../../docs/architecture/hardware.md)
