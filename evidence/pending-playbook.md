---
status: current
last_verified: 2026-10-19
---

# Pending playbook material

Work done after a sprint's playbooks were written, waiting to go into the next sprint's playbook or a new playbook in that sprint. Past playbooks aren't edited. When an item is written up, move it out of this file and link the playbook from the [evidence log](./evidence.md).

Add each item with its date, what was done, and links to its proof.

## 2026-10-19: Rig 2 gets a ninth GPU; Rig 1 checked

Proof: [capture](./captures/2026-10-19-rig2-ninth-gpu-driver-580.md).

- **Ninth card on Rig 2.** The team added a GTX 1070, so Rig 2 has 1 × GTX 1080 Ti + 8 × GTX 1070. The new card is `GPU-8e7ca25c…` at bus `0B:00.0`.
- **Driver broke on reboot.** The reboot was the first into kernel 7.0.0-38, which an unattended upgrade had installed on 2026-10-15. Rig 2's prebuilt 550 driver had no module for it, so the worker loaded the model on CPU (`no usable GPU found`).
- **Fix: driver 580 with DKMS**, the same packages Rig 1 already runs on the same kernel. No reboot was needed after `modprobe nvidia`. GRUB wasn't changed.
- **Model on all 9 cards.** `qwen3.6:35b-a3b` with `TENSOR_SPLIT=11,8,8,8,8,8,8,8,8`: 27.6 and 27.8 tok/s, the same as on 8 cards. With layer split the extra card adds memory, not speed.
- **Rig 1's 8th GPU: resolved.** This was an open item in the [Sprint 4 inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Checked read-only: all 8 cards are in use. Worker A (`qwen3.8:27b`) has 4, and Worker B has the other 4. Worker B now serves `gemma4:26b` (config dated 2026-10-16), not `qwen2.5:0.5b` on 2. Who made that change, and its speed, aren't recorded.
