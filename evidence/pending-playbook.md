---
status: current
last_verified: 2026-10-29
---

# Pending playbook material

The week's work, logged by the people and agents who did it. Each entry is waiting to go into a playbook: the next sprint's, or a new playbook in the current sprint. Playbooks can be edited (freely while `in progress`, and if needed once `done`), but the better route for new work, including answers to an earlier playbook's open items, is to log it here.

**How to add an entry.** Find this week's section (`## Week of YYYY-MM-DD`, the Monday) or start it at the top. Put the entry under the closest category (a `###` heading): `Rigs and hardware`, `Inference and models`, `Gateway and API`, `Networking and access`, `VR`, or `Docs and process`. Give the entry a `####` heading with the date and a short title. Then add a few bullets: what was wrong or asked, what was done, and the result with numbers. Link the proof (usually a dated capture) and any earlier playbook it follows up. Don't add author names. Mark facts the team reported, but nobody captured, as reported. Full rules: [conventions](../docs/conventions.md#pending-playbook-material).

**When it's written up,** the playbook's author moves the entries it covers into the playbook and deletes them here in the same commit.

**Sprint 4 was written up on 2026-10-23.** Its hardware and inference entries moved into [the hardware playbook](./sprint4/2026-10-19-rig-hardware-ninth-gpu-driver-580.md) and [the inference playbook](./sprint4/2026-10-15-inference-on-both-rigs.md). Everything below feeds Sprint 5 ([plan](../docs/project/roadmap.md#sprint-5-plan)).

## Week of 2026-11-16

### Rigs and hardware

#### 2026-11-17: Download cache on silver finished and measured

Follows the 2026-11-13 entry below.

- **Silver rerun** (`--limit ocs-intelligence-macmini-25`): `ok=65 changed=6 failed=0`. Wired is now silver's main link (`default via ... enp3s0f0 ... metric 100`, Wi-Fi metric 200). Ray test still `result 285`.
- **Cache contents, checked on silver:**
  - all 89 locked wheels in `/srv/ocs-cache/wheels` (242 MB)
  - `wheels/READY` equals the sha256 of `cluster-requirements.txt` (`ab44ae99…`)
  - `apt-cacher-ng` and `ocs-cache-http` active
  - `ocs-apt-proxy` returns `http://192.168.8.35:3142`, and silver's own upgrade went through it (8.7 MB cached so far, from `security.ubuntu.com`)
- **Speed:** the Ray wheel (79 MB) downloaded to the operator laptop, which is on Wi-Fi:
  - from silver: 1.65 s (48 MB/s)
  - from PyPI: 8.09 s (9.8 MB/s)
  - About 5×, and silver's downloads stay off the shared internet link. A wired Mac mini should be faster still (not measured; needs a second wired machine).
- **First stick run (mac26, serial-named `…c07rx09wg1j1`, found as #26 from the table):** two bugs, both fixed:
  - `run.sh` called `uvx`, but the stick carries only the `uv` binary (`uvx` is a separate file in uv's release). It now calls `uv tool run`, which does the same.
  - The `uv` copied from the stick was corrupted: same size (37,597,160 bytes), different sha256 (`805df19e…` instead of `8a70db72…`), and it crashed with `Inconsistency detected by ld.so`. The other 18 kit files matched. The Downloads copy and silver's copy were fine, so the damage happened on the USB stick, most likely when it was pulled before Windows finished writing. Now `make_stick.py` writes `SHA256SUMS`, and `bootstrap.sh` checks it, and that `uv` runs, before changing anything. On a mismatch it stops and says to re-copy and eject properly.
  - mac26 itself was fixed remotely: the fixed `run.sh` copied in, `uv` replaced from silver's cache (`/uv/uv`, hash matches), the service restarted. Its setup then ran on its own, with apt going through silver's cache.
- **mac26 finished the stick flow on its own:** it upgraded through silver's cache (179 packages; the cache grew to 360 MB), renamed itself `ocs-intelligence-macmini-26`, rebooted into kernel 7.0.0-30, and resumed (`reboot 1; setup carries on after boot`). It went on through Python and NetBird to the Wi-Fi step.
- **mac26 DONE** at 11:33, about 20 minutes after its setup started at 11:13 (including the reboot): `ocs-intelligence-macmini-26`, NetBird `100.75.176.246`, Ray `result 285`. `secrets.env` deleted, `ocs-bootstrap` inactive. That's the first machine fully set up by the stick.
- **Reservations:** `reservations.py --apply` added #26 (`.36` wired, `.76` Wi-Fi) and #27 wired (`.37`; its Wi-Fi MAC only exists once the `wl` driver loads). Backup `/root/dhcp.backup-2026-11-17-105852`, all entries verified. `networkctl reconfigure enp3s0f0 wlp2s0` moved mac26 to `.36`/`.76`.
- **mac27 DONE** at 11:50, about 17 minutes after it started (faster than mac26, with more of the upgrade in silver's cache): `ocs-intelligence-macmini-27`, NetBird `100.75.182.79`, Ray `result 285`, secrets deleted. On 2026-11-18 its Wi-Fi reservation was added (`.77`; backup `/root/dhcp.backup-2026-11-18-104143`) and it was moved there. #25–#27 are now all on their reserved addresses: `.35`/`.75`, `.36`/`.76`, `.37`/`.77`.
- **Cabling:** an 8-port gigabit switch is now uplinked to the Flint for the batches. Silver stays on the router (reported).
- **Serial readings:** every serial ends in `G1J1`, the model code for this Mac mini, so the third character of a three-character reading is always `G`. Corrections:
  - #27 read `6ER`, really `…06EG1J1`. It showed as `#?`; it was given its number on the machine before its reboot, and the table was fixed.
  - #28 `5CG` confirmed.
  - #24 is `NNG`.
  - Alternate rows were added where a reading is still unsure: #0 `DZ6`/`DZG`, #22 `406`/`40G`, #32 `CYG`/`LYG`. A serial that doesn't exist matches nothing.
  - Re-read later that day: #0 is `DZG`. #22 is `90G` or `40G`, and #32 is `CYG` or `LYG`; both keep two rows until the machines show their real serials.
- **Plan for the rest:** batches of 6 on the switch (1 port is the uplink, 1 spare). Per batch:
  1. Re-copy the stick if it was rebuilt, and eject it properly.
  2. Cable each machine to the switch, run the stick, and pull it.
  3. Wait about 20–30 minutes.
  4. `inventory.py --table` until every machine shows a number and Wi-Fi.
  5. `reservations.py --apply`.
  6. Move the batch to its reservations (reboot, or `networkctl reconfigure`).
  7. Free the switch ports for the next batch.
