---
date: 2026-10-22
---

# Rig 1 ↔ Rig 2: iperf3 over the LAN (2026-10-22)

Run over NetBird SSH (`root@100.75.123.203`, `ocs-intelligence-rig`, and `root@100.75.127.192`, `ocs-intelligence-rig2`) from the `Yash WSL` peer, about 10:27 PDT. This is a record: don't edit it. Follows up the [Rig 1 gigabit link check](./2026-10-22-rig1-gigabit-link.md) from the same morning.

## What changed on the rigs

- Installed the `iperf3` package (3.16) on both rigs with `apt-get install -y iperf3`. The packaged `iperf3` service is `disabled` and `inactive` on both.
- Ran a temporary server on Rig 2 (`iperf3 -s -D -B 192.168.8.213`) and stopped it after the tests. No `iperf3` process was left running on either rig.
- `ufw` is inactive on both rigs, so no firewall rule was needed.

## Path

Direct over the local LAN, not NetBird: Rig 1 `enp0s31f6` 192.168.8.112/24 → Rig 2 `enp0s31f6` 192.168.8.213/24. Both links at 1000 Mb/s full duplex.

## Results

Client on Rig 1, 10 s per test, one TCP stream, default settings.

| Test | Command | Sender | Receiver | Retransmits |
|---|---|---:|---:|---:|
| Rig 1 → Rig 2 | `iperf3 -c 192.168.8.213 -t 10` | 936 Mb/s | 934 Mb/s | 0 |
| Rig 2 → Rig 1 | `iperf3 -c 192.168.8.213 -t 10 -R` | 936 Mb/s | 934 Mb/s | 0 |
| Both at once, Rig 1 → Rig 2 | `iperf3 -c 192.168.8.213 -t 10 --bidir` | 932 Mb/s | 930 Mb/s | 0 |
| Both at once, Rig 2 → Rig 1 | (same run) | 933 Mb/s | 931 Mb/s | 0 |

`ping -c 10 192.168.8.213`: 0% loss, RTT min/avg/max 0.172 / 0.232 / 0.268 ms.

About 934 Mb/s is the most a gigabit link can carry as TCP payload with a 1500-byte MTU, so each direction runs at full line rate, and the link is full duplex.

At 10:29 both rigs still linked at 1000 Mb/s. Rig 1's count of link drops for the day was still 6, so none happened during the tests. Rig 2 had 0.

Not tested: throughput to the internet or to EC2. Those paths go through the school network and NetBird, not just this LAN.
