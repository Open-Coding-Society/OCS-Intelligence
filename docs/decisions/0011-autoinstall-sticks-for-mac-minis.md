---
status: proposed
blueprint_review:
date: 2026-10-27
deciders:
supersedes:
superseded_by:
---

# 0011. Flash the Mac minis with autoinstall USB sticks, not netboot or Clonezilla

## Context

Sprint 5's orchestrator runs on the Mac minis ([roadmap](../project/roadmap.md#sprint-5-plan)). There are 32 (`Macmini7,1`, Late 2014, A1347 EMC 2840): `ocs-intelligence-mac1` was installed by hand, 31 remain. Each needs Ubuntu Server 26.04, user `ocs`, SSH, and its own hostname, `ocs-intelligence-macN`.

Two approaches were on the table. [Issue #30](https://github.com/Open-Coding-Society/OCS-Intelligence/issues/30) proposed network booting (PXE) from Tiny PXE Server. The team's [cluster guide](../../evidence/sprint5/macmini_golden_master_cluster_guide.md) used Clonezilla to clone a golden master.

Constraints:

- Intel Macs don't do standard PXE. Holding N starts Apple NetBoot (BSDP), a DHCP exchange with Apple vendor options. The dnsmasq and ISC configs for it ([FOG wiki](https://wiki.fogproject.org/wiki/index.php/FOG_on_a_MAC)) were reported on 2011–2012 Macs. None for `Macmini7,1` was found.
- The building's internet is about 60–90 Mb/s, shared ([pending playbook](../../evidence/pending-playbook.md)).
- The OCS switch has 7 free ports. USB sticks are plentiful.
- The Late 2014 Mac mini shipped with 500 GB or 1 TB drives, a Fusion Drive, or an SSD.

## Options considered

1. **Netboot (BSDP) + autoinstall:** no sticks, unlimited parallel installs, easiest to reflash. Unproven on this model, and needs a DHCP server set up specially for Apple clients.
2. **USB sticks + autoinstall:** the stock installer runs from a config file with no questions. Each machine gets its own identity at install time. Parallelism is the number of sticks. Known to boot (mac1 was installed from a stick).
3. **Clonezilla from a golden master:** fastest per machine (a 3–6 minute restore vs. a 10–15 minute install, estimated). But every clone shares a machine-id, SSH host keys and hostname until a first-boot script fixes them, restores fail on a smaller disk than the master, and the image goes stale with every change.
4. **Manual installs:** 3–5 minutes of clicking per machine, and typos in 31 hostnames.

## Decision

We chose **option 2**: one ISO with `/autoinstall.yaml` at its root, written to many sticks. The install is offline (packages from the stick only, no network cable needed). Each machine is named `ocs-intelligence-<serial>` at install, unique without a network, and renamed to `ocs-intelligence-macN` later. Packages beyond `openssh-server` are installed later with Ansible. Guide: [flash the Mac minis](../operations/flash-mac-minis.md).

For 31 machines, the time saved by cloning roughly equals the time to build the golden master. And the per-machine time is mostly the install itself, which is the same however the machine boots.

## Consequences

- Good: each machine gets its own machine-id, SSH host keys and hostname. Mixed disk sizes don't matter. Changing the setup means editing a text file and rebuilding one ISO, not recapturing an image.
- Good: the autoinstall file also works for netboot, if we try it later.
- Bad / accepted trade-off: someone touches every machine at boot (hold Option, pick the stick).
- Bad / accepted trade-off: every machine is renamed by hand (or by Ansible) once it's on the network.
- Follow-up work: an Ansible playbook for packages (uv, aws-cli, the rest of the list). Revisit Clonezilla if the per-machine setup grows large (built software, model files).

## Differs from the blueprint?

No. The blueprint doesn't cover how the Mac minis are installed.
