---
status: current
last_verified: 2026-10-19
---

# Pending playbook material

The week's work, logged by the people and agents who did it. Each entry is waiting to go into a playbook: the next sprint's, or a new playbook in the current sprint. Playbooks can be edited (freely while `in progress`, and if needed once `done`), but the better route for new work, including answers to an earlier playbook's open items, is to log it here.

**How to add an entry.** Find this week's section (`## Week of YYYY-MM-DD`, the Monday) or start it at the top. Put the entry under the closest category (a `###` heading): `Rigs and hardware`, `Inference and models`, `Gateway and API`, `Networking and access`, `VR`, or `Docs and process`. Give the entry a `####` heading with the date and a short title. Then add a few bullets: what was wrong or asked, what was done, and the result with numbers. Link the proof (usually a dated capture) and any earlier playbook it follows up. Don't add author names. Mark facts the team reported, but nobody captured, as reported. Full rules: [conventions](../docs/conventions.md#pending-playbook-material).

**When it's written up,** the playbook's author moves the entries it covers into the playbook and deletes them here in the same commit.

## Week of 2026-10-19

### Rigs and hardware

#### 2026-10-19: Rig 2 gets a ninth GPU; the driver breaks and is moved to 580

Sprint 4 follow-up. Proof: [capture](./captures/2026-10-19-rig2-ninth-gpu-driver-580.md).

- **Ninth card on Rig 2.** The team added a GTX 1070, so Rig 2 has 1 × GTX 1080 Ti + 8 × GTX 1070. The new card is `GPU-8e7ca25c…` at bus `0B:00.0`.
- **Driver broke on reboot.** The reboot was the first into kernel 7.0.0-38, which an unattended upgrade had installed on 2026-10-15. Rig 2's prebuilt 550 driver had no module for it, so the worker loaded the model on CPU (`no usable GPU found`).
- **Fix: driver 580 with DKMS**, the same packages Rig 1 already runs on the same kernel. No reboot was needed after `modprobe nvidia`. GRUB wasn't changed.
- **Open:** unattended upgrades are still on for both rigs. DKMS should build the driver for the next kernel, but nobody has watched that happen.

#### 2026-10-19: Rig 1's 8th GPU confirmed in use

Answers an open item in the [Sprint 4 inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Proof: [capture](./captures/2026-10-19-rig2-ninth-gpu-driver-580.md) (Rig 1 was checked read-only).

- All 8 cards are in use, 4 per worker. Inventory with UUIDs: [hardware](../docs/architecture/hardware.md#gpu-inventory-rig-1).

#### 2026-10-20: Platform inventory of both rigs

Fills the "not recorded" items in the [Sprint 3 playbook](./sprint3/2026-09-28-resolving-both-rigs.md). Proof: [capture](./captures/2026-10-20-rig-hardware-inventory.md) (read-only).

- **Same platform on both:** ASUS B250 Mining Expert, Intel Celeron G3930 (2 cores), Corsair 8 GB DDR4 sticks at 2133 MT/s. Rig 1 has 2 sticks (16 GB), Rig 2 has 1 (8 GB). BIOS 0403 on Rig 1, 1001 on Rig 2.
- **Cards:** every 1070 is an EVGA GTX 1070 FTW Hybrid (185 W limit). Rig 2's 1080 Ti is an EVGA SC Black Edition, air-cooled (250 W limit).
- **Both rigs are on wired Ethernet now** (onboard Intel I219-V). Rig 1 links at only 100 Mb/s, Rig 2 at 1 Gb/s.
- **Storage:** each OS sees one Samsung 860 EVO 250 GB. The team reports a second SSD in each (480 GB in Rig 1, 256 GB in Rig 2); neither shows up.
- **Power (reported):** both 1800 W supplies are an unknown brand. Rig 2's EVGA is 850 W or 1300 W. Rig 2's ninth card is believed to be on the Antec, making its split 5 / 2 / 2.
- **Open:** connect or check the second SSDs; find out why Rig 1 links at 100 Mb/s; read the EVGA supply's label.

### Inference and models

#### 2026-10-19: Rig 2 serves `qwen3.6:35b-a3b` on all 9 cards

Proof: [capture](./captures/2026-10-19-rig2-ninth-gpu-driver-580.md).

- `TENSOR_SPLIT=11,8,8,8,8,8,8,8,8`, all 9 UUIDs in `CUDA_VISIBLE_DEVICES`. Generation was 27.6 and 27.8 tok/s, the same as on 8 cards. With layer split the extra card adds memory, not speed.

#### Rig 1 Worker B switched to `gemma4:26b` (seen 2026-10-19)

- Worker B serves `gemma4:26b` on 4 GPUs, not `qwen2.5:0.5b` on 2. The config file is dated 2026-10-16. Who made the change, why, and the model's speed aren't recorded.
