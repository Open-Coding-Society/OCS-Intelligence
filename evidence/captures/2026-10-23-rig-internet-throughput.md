---
date: 2026-10-23
---

# Both rigs: router link and internet throughput (2026-10-23)

Run over NetBird SSH (`root@100.75.123.203`, `ocs-intelligence-rig`, and `root@100.75.127.192`, `ocs-intelligence-rig2`) from the `Yash WSL` peer, 10:03–10:10 PDT. Read-only apart from the downloaded test data, which went to `/dev/null`. This is a record: don't edit it. Follows the [rig-to-rig iperf3 test](./2026-10-22-rig-to-rig-iperf3.md), which only covered the LAN between the rigs.

## Rig to router

Both rigs get a DHCP address on `enp0s31f6` with the default route via `192.168.8.1`.

| | Rig 1 | Rig 2 |
|---|---|---|
| Address | 192.168.8.112/24 | 192.168.8.213/24 |
| Link (`ethtool`) | 1000 Mb/s, full | 1000 Mb/s, full |
| `ping -c 10 192.168.8.1` | 0% loss, avg 0.507 ms (0.457–0.552) | 0% loss, avg 0.537 ms (0.487–0.618) |

No iperf3 test was run against the router itself (whether it can run an iperf3 server wasn't checked), so the router hop wasn't measured by throughput. The [2026-10-22 iperf3 run](./2026-10-22-rig-to-rig-iperf3.md) carried 934 Mb/s each way across both rigs' links to the LAN.

## To the internet

`curl` against `speed.cloudflare.com` (`__down?bytes=N` and `__up`). Requests for 100 MB or more got HTTP 403, so downloads use 25 MB pieces. `releases.ubuntu.com` returned 403 and `ash-speed.hetzner.com` didn't connect, so Cloudflare is the only source.

**One rig at a time:**

| Test | Rig 1 | Rig 2 |
|---|---:|---:|
| Download, 25 MB | 71 Mb/s | 87 Mb/s |
| Upload, 50 MB | 61 Mb/s | 88 Mb/s |

**Both rigs at once** (6 × 25 MB down, then 3 × 25 MB up, each rig):

| Test | Rig 1 | Rig 2 |
|---|---:|---:|
| Download, 150 MB | 62 Mb/s (19.2 s) | 42 Mb/s (28.3 s) |
| Upload, 75 MB | 74 Mb/s (8.0 s) | 53 Mb/s (11.3 s) |

Rig 2's download ran alone for its last ~9 s, so during the overlap it got about 22 Mb/s, and the two rigs shared about 84 Mb/s.

## Reading

- Each rig's link to the router runs at 1 Gb/s, and the LAN carries line rate.
- Internet throughput is about 60–90 Mb/s each way and is **shared** by the rigs. The limit is upstream of the router: its WAN port, the line it's plugged into, or the plan. A 100 Mb/s Ethernet hop would cap TCP at about 94 Mb/s, which fits these numbers, but the router's WAN link speed wasn't read.
- Single short runs from one test server. Treat the numbers as a rough range, not a benchmark.
