---
date: 2026-10-19
---

# Rig 2: ninth GPU added, NVIDIA driver moved to 580, model on all 9 cards (2026-10-19)

Checked and changed live over NetBird SSH (`root@100.75.127.192`, `ocs-intelligence-rig2`) from the `Yash WSL` peer, about 10:30–11:30 PDT. Rig 1 (`root@100.75.123.203`) was inspected read-only for comparison. This is a record: don't edit it. Layout and paths: [hosts](../../docs/reference/hosts.md). Inventory: [hardware](../../docs/architecture/hardware.md).

## What was found

The team added a ninth card (a GTX 1070) to Rig 2 and rebooted it at 10:22.

| Check | Result |
|---|---|
| `lspci` | 9 NVIDIA VGA devices: 1 × GTX 1080 Ti (`01:00.0`) + 8 × GTX 1070 |
| `nvidia-smi` | `NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver` |
| Running kernel | `7.0.0-38-generic`. The previous boot (2026-10-14 to 2026-10-19 10:06) ran `6.14.0-27-generic` |
| NVIDIA modules | Only for 6.14.0-27 (`linux-modules-nvidia-550-6.14.0-27-generic`, prebuilt). `modprobe nvidia`: `Module nvidia not found in directory /lib/modules/7.0.0-38-generic` |
| How the kernel changed | `/var/log/dpkg.log`: unattended upgrade installed `linux-image-7.0.0-38-generic` and moved `linux-image-generic-hwe-24.04` to it on 2026-10-15 07:08. The 10:22 reboot was the first boot into it |
| Worker log, this boot | `ggml_cuda_init: failed to initialize CUDA: no CUDA-capable device is detected`, `no usable GPU found, --gpu-layers option will be ignored`. It loaded the model on CPU (7 GB RAM) and was listening |
| Worker log, previous boot | 2026-10-17 requests at 26.7–27.8 tok/s generation: on GPU |
| Secure Boot | Disabled |

**Rig 1** runs the same `7.0.0-38-generic` kernel without trouble: it has `nvidia-driver-580` 580.178.04 with `nvidia-dkms-580`, so DKMS rebuilds the module for each new kernel. Its 8 cards were all visible and both workers were active. Prebuilt 550 modules don't exist for kernel 7.0 (`apt-cache` lists only 580, 595 and 610 for `7.0.0-38`).

## What was changed

1. `systemctl stop ocs-llama` (it was running on CPU).
2. Swapped the 550 packages for 580 in one transaction, matching Rig 1's packages and repo (NVIDIA CUDA repo, `580.178.04-1ubuntu1`). Log: `/root/ocs-deploy/nvidia580-install-2026-10-19.log` on the rig.

   ```bash
   apt-get install -y nvidia-driver-580 nvidia-dkms-580 <every installed *nvidia*550* package with a trailing ->
   ```

   The first try without removing 550 failed with `nvidia-kernel-common-550 : Conflicts: nvidia-kernel-common` and changed nothing. The DKMS build took several minutes on the 2-core CPU. Exit 0.
3. `modprobe nvidia && modprobe nvidia_uvm`. No reboot was needed. `nvidia-smi` then showed all 9 cards:

   | Index | Card | UUID | PCI bus |
   |---:|---|---|---|
   | 0 | GTX 1080 Ti, 11264 MiB | `GPU-51bb095a-33b3-54e1-8673-58f98f275bc0` | `01:00.0` |
   | 1 | GTX 1070, 8192 MiB | `GPU-83daccf4-1ff0-6fa0-19c3-d424e6aa2a97` | `04:00.0` |
   | 2 | GTX 1070 | `GPU-5564a0bd-3c8d-fe31-5675-aaba5effb805` | `08:00.0` |
   | 3 | GTX 1070 (**new**) | `GPU-8e7ca25c-e499-1818-e488-3ba4a78b70b1` | `0B:00.0` |
   | 4 | GTX 1070 | `GPU-ee8e7563-ecfb-d5ee-0f36-74b5bd76ddaf` | `0C:00.0` |
   | 5 | GTX 1070 | `GPU-69f0a712-56fc-d954-265f-8469c2a21c9d` | `0D:00.0` |
   | 6 | GTX 1070 | `GPU-2b6607e6-a556-543b-4c88-d7ddb156b184` | `0E:00.0` |
   | 7 | GTX 1070 | `GPU-64ccc864-2ced-25a4-64bc-f23cd1f108dc` | `0F:00.0` |
   | 8 | GTX 1070 | `GPU-a512d941-05b9-654c-b47c-8cc3b03bfa1a` | `10:00.0` |

4. Backed up `/etc/ocs-intelligence/worker.env` to `/root/ocs-deploy/worker.env.bak-2026-10-19`, then set `CUDA_VISIBLE_DEVICES` to all 9 UUIDs in index order and `TENSOR_SPLIT=11,8,8,8,8,8,8,8,8`. Model, context (`524288`, 2 slots), `-ub 1024` unchanged. `systemctl restart ocs-llama`.

GRUB was not changed. The 6.14.0-27 kernel stays installed; its prebuilt 550 modules were removed with the swap, and DKMS builds 580 for it as well.

## Result

| Check | Result |
|---|---|
| Worker `/health` | `{"status":"ok"}` |
| Orchestrator `/readyz` | `{"status":"ready"}` |
| GPU memory used | GPU 0: 7187 / 11264 MiB. GPUs 1–8: 5435–6955 MiB of 8192 |
| Generation, worker direct, 400 tokens, two runs | 27.6 and 27.8 tok/s |

Speed is the same as on 8 cards (~27 tok/s on 2026-10-15). With `--split-mode layer` the cards run one after another, so the ninth adds memory, not speed ([0009](../../docs/decisions/0009-rig2-moe-behind-open-webui.md)).

## Not done

- Unattended upgrades are still on for both rigs. Rig 2 now uses DKMS like Rig 1, so a new kernel should get a module built at install time, but that hasn't been watched happen.
- The new card wasn't load-tested beyond the two requests above.
