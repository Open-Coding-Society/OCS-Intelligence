---
status: proposed
date: 2026-11-12
deciders:
---

# 0013. One Ansible playbook sets up every Mac mini, with Ray on a pinned Python, Wi-Fi as the main link

## Context

The 33 Mac minis (numbered 0–32 on their Post-its) are flashed with a bare Ubuntu Server ([0011](./0011-autoinstall-sticks-for-mac-minis.md)), and Sprint 5 puts the orchestrator and distributed compute on them ([roadmap](../project/roadmap.md#sprint-5-plan)). The team wants them ready for distributed compute and the orchestrator stack, set up once and the same everywhere, with "more installed rather than less". Each machine has a 2-core i5-4278U, 16 GB RAM, a BCM4360 Wi-Fi card that needs the out-of-tree `wl` driver, and gigabit Ethernet. The internet link is ~84 Mb/s, shared. The first flashed machines came up with the wired port disabled (fixed by the FIX stick, [set up the Mac minis](../operations/set-up-mac-minis.md)).

## Options considered

1. **Ansible playbook over SSH** from an operator laptop, rerun whenever the baseline changes.
2. **Shell script on the FIX stick** that installs everything at the console.
3. **Rebuild the ISO** with everything baked in, and reflash.
4. **Golden image + Clonezilla**, as in the team's [cluster guide](../../evidence/sprint5/macmini_golden_master_cluster_guide.md).

For Python: **(a)** the system Python 3.14 with pip, or **(b)** a uv-managed Python 3.12 venv synced to a lock file.

## Decision

We chose **option 1** with **(b)**. The stick only does what needs the console (name and wired network); everything else is in [`infra/macmini/ansible/`](../../infra/macmini/ansible/). Installs need the internet, which the stick doesn't have, and options 3 and 4 mean touching every machine again for each change. Ansible reruns are idempotent, and a change is one edit plus one run.

Ray needs the same Ray and Python minor version on every node and on any laptop that connects as a driver. A lock file ([`cluster-requirements.txt`](../../infra/macmini/ansible/files/cluster-requirements.txt), Ray 2.60.0, 89 packages) and a uv-managed Python 3.12 keep that true even as Ubuntu updates its own Python. 3.12 is Ray's most-tested version; it also has wheels for 3.14.

Wi-Fi is the main link (route metric 100) and wired the backup (200), as the team asked. Ray picks one node address, so its traffic follows the default route.

## Consequences

- Good: one source of truth for the baseline; new nodes or changes cost one run. Ray is checked on every node by the `ray_check` tag.
- Good: NetBird joins with a setup key into `ocs-macminis`, so operators reach each node from anywhere ([network](../architecture/network.md#access-policies)).
- Bad / accepted trade-off: Wi-Fi as the main link puts all 33 nodes' traffic on one 5 GHz channel, while each has gigabit Ethernet. Measure Ray throughput both ways before relying on it; flip the two metrics in `group_vars` to switch.
- Bad / accepted trade-off: the sudo password and Wi-Fi password sit in the operator's `.env`, and the NetBird setup key never expires. Sprint 6 (security) should move to SSH-only sudo rules or Ansible Vault, and rotate the weak `ocs` password.
- Follow-up work: the orchestrator's own decision record (why the Mac minis, failure handling), a Ray head node and worker units, and a package cache on one node so 31 machines don't each download the same packages.

## Differs from the blueprint?

No. The blueprint doesn't cover the Mac minis.
