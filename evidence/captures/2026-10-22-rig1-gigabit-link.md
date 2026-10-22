---
date: 2026-10-22
---

# Rig 1: Ethernet now links at 1 Gb/s (2026-10-22)

Checked read-only over NetBird SSH (`root@100.75.123.203`, `ocs-intelligence-rig`) from the `Yash WSL` peer at 10:24 PDT. Nothing was changed. This is a record: don't edit it. Follows up the 100 Mb/s link in the [2026-10-20 inventory](./2026-10-20-rig-hardware-inventory.md). Canonical hardware page: [hardware](../../docs/architecture/hardware.md).

Commands: `ethtool enp0s31f6`, `ip -s link show enp0s31f6`, `journalctl -k | grep 'enp0s31f6.*Link'`.

## Link

| | Value |
|---|---|
| Interface | `enp0s31f6`, Intel I219-V (`e1000e`) |
| Speed / duplex | **1000 Mb/s, full**. Auto-negotiation on |
| Advertised (rig) | 10/100 half and full, 1000baseT/Full |
| Advertised (link partner) | 10/100 half and full, 1000baseT/Full |
| Link detected | yes |
| Counters since boot | RX 650 MB, 0 errors, 0 dropped. TX 509 MB, 0 errors, 152 dropped, 0 carrier errors, 0 collisions |

The link partner now advertises 1000baseT/Full, so the switch port or cable that held it at 100 Mb/s was changed. Nobody recorded which one.

## Kernel link events on 2026-10-22

6 `NIC Link is Down` events today. The last five events:

```
09:55:55  NIC Link is Up 100 Mbps Full Duplex
09:55:55  NIC Link is Down
10:01:47  NIC Link is Up 1000 Mbps Full Duplex
10:09:36  NIC Link is Down
10:10:51  NIC Link is Up 1000 Mbps Full Duplex
```

The link had been up at 1000 Mb/s for about 14 minutes when checked. The drops this morning fit someone recabling. Whether the gigabit link stays stable hasn't been watched.

Only the negotiated link speed was checked. Throughput (for example `iperf3` between the rigs) wasn't measured.
