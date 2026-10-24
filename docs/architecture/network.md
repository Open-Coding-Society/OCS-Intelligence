---
status: current
last_verified: 2026-09-18
---

# Network

How traffic gets from the internet to a GPU in a school building whose network blocks the usual ways of doing that. Addresses and ports: [hosts](../reference/hosts.md).

## The path

```text
Internet ──HTTPS──▶ EC2 Nginx (TLS, ai.opencodingsociety.com)
                     ├─ /v1/*, /healthz ──▶ 127.0.0.1:9100 admission gateway ──NetBird──▶ rig :9000 orchestrator
                     └─ /               ──NetBird──▶ rig :3000 Open WebUI
```

- **EC2 is the only public host.** It has the public IP, the DNS name, and the Let's Encrypt certificate (Certbot). Port 80 redirects to 443.
- **The rig has no inbound exposure to the internet.** EC2 reaches it over the NetBird overlay using its `100.75.x.x` address.
- **Nginx settings for `/v1/`** ([`infra/ec2/llm-relay-nginx.conf`](../../infra/ec2/llm-relay-nginx.conf)): `proxy_buffering off` and `proxy_request_buffering off` so tokens stream immediately; `proxy_read_timeout` and `proxy_send_timeout` of 3600 s so long waits in line aren't cut off; `client_max_body_size 2m`. The path isn't rewritten, so `/v1/models` stays `/v1/models`.
- `/` (Open WebUI) goes straight to the rig with a 300 s read timeout and WebSocket upgrade. The page **skips the gateway**. Open WebUI's own model calls go to the public `/v1` (Rig 1's models) and over NetBird to Rig 2's `:9000` (Rig 2's model).

## The OCS LAN

As of 2026-10-23. Sources: the team's [rig routing playbook](../../evidence/sprint4/OCS_Rig_Routing_Playbook.pdf) (2026-10-16), the team's report of the router setup on 2026-10-23, and measurements on 2026-10-22/23 ([link speed](../../evidence/captures/2026-10-22-rig1-gigabit-link.md), [rig to rig](../../evidence/captures/2026-10-22-rig-to-rig-iperf3.md), [internet](../../evidence/captures/2026-10-23-rig-internet-throughput.md)).

The room's wall jacks don't work, so the rigs sit on a private LAN behind the school Wi-Fi:

```text
School Wi-Fi (PUSD-Onboard, district filter)
   │  Wi-Fi: Mac mini's built-in BCM4360, open side of the SSID
Mac mini (Ubuntu): NAT + DHCP, 10.42.0.1/24 on its Ethernet
   │  Ethernet into the router's WAN port
GL.iNet Flint 2 (GL-MT6000): OCS LAN 192.168.8.0/24, admin 192.168.8.1
   ├─ LAN port 2, 3: Rig 1 and Rig 2 (wired)
   ├─ LAN port 4:    orchestrator testing
   ├─ LAN port 5, 6: other groups in the class
   └─ Wi-Fi OCS_Intel: 5 GHz only (2.4 GHz off)
```

- **Ports and Wi-Fi** are as the team reported on 2026-10-23. Which rig is on port 2 and which on 3 wasn't recorded. The routing playbook calls the SSID `OCS-IoT` and has Rig 2 on a USB Wi-Fi dongle; both are out of date. Rig 2 has been wired since at least 2026-10-20.
- **Speeds:** each rig links at 1 Gb/s, rig to rig carries 934 Mb/s each way, and the router answers in ~0.5 ms. The internet is the bottleneck: ~60–90 Mb/s each way, **shared** by everything on the LAN (~84 Mb/s with both rigs at once). Every byte to the internet crosses the Mac mini's single Wi-Fi link. The hops behind the Flint weren't measured separately.
- **The LAN is shared with other groups.** Their devices are on the same `192.168.8.0/24` as the rigs. The orchestrators bind `0.0.0.0:9000` with no host firewall, so those devices can reach them directly, skipping the EC2 wait line ([hosts](../reference/hosts.md#ports), audit S2 in the [Sprint 5 plan](../project/roadmap.md#sprint-5-plan)).
- **Planned, not built:** a WireGuard tunnel from the Flint to the EC2 relay (routing playbook Steps 6–10).
- **Single points of failure** (routing playbook §12): the Mac mini, the pinned school access point, its out-of-tree `wl` Wi-Fi driver, and EC2.

## NetBird

A WireGuard-based overlay network. Both hosts are peers, and so are operator machines (the NetBird client, natively or in the [`infra/netbird/`](../../infra/netbird/) container). On 2026-09-16 the EC2 peer connected peer-to-peer and the rig peer connected **through a relay** ([discovery record](../archive/phase1-discovery.md)).

NetBird SSH needs a browser SSO approval for **every new connection**. For how operators work around that, see [NetBird access](../guides/netbird-access.md).

### Access policies

NetBird's built-in `Default` policy (every peer reaches every peer, both ways) is disabled. Access is one-way, group to group ([decision 0008](../decisions/0008-one-way-netbird-policies.md)):

| Group | Members | Can reach | Can be reached by |
|---|---|---|---|
| `ocs-gateway` | EC2 | `ocs-rigs` on TCP 9000, 3000 | `outbound-only`; anyone via NetBird SSH |
| `ocs-rigs` | Rig 1, Rig 2 | each other, all ports | each other; `ocs-gateway` (9000, 3000); `outbound-only`; anyone via NetBird SSH |
| `outbound-only` | operator machines | `ocs-gateway`, `ocs-rigs`, all ports | **nobody** |

"Anyone via NetBird SSH" is the `SSH Access` policies that NetBird's SSH feature created (source `All`, one per server). Policies are stateful: replies to a connection come back even though the rule is one-way. The rigs talk to each other both ways (`rigs-to-rigs`) so that Open WebUI on one rig can call a model served by the other. **This is temporary:** once a router (the planned Mac Mini, or EC2) sits between the rigs, traffic goes through it and `rigs-to-rigs` is removed.

The groups and policies are recorded in [`infra/netbird/acl.json`](../../infra/netbird/acl.json). `python3 infra/netbird/apply.py check` compares that file with the live account; `apply` creates anything missing. Group membership is managed in the dashboard, not by the script. Last applied and checked: [2026-10-15](../../evidence/captures/2026-10-15-netbird-access-policies.md).

## The district network

The school network doesn't block "servers" in general. It fingerprints known tunneling products. What we tried ([deck](../sources/2026-09-28-week0-1-mentor-deck.md) slides 10–11):

| Tool | Result | Root cause |
|---|---|---|
| Cloudflare Tunnel | Abandoned | Outbound port 7844 blocked network-wide (TCP and UDP) |
| ngrok | Abandoned | Three stacked failures: DNS sinkhole of tunnel hostnames, a CRL check blocked on port 80, then Ollama's DNS-rebinding protection returned 403 on the Host header |
| NetBird + AWS relay | **Works** | Already crossing this network for SSH, and not flagged as a tunnel |

Decision: [0004](../decisions/0004-netbird-over-cloudflare-ngrok.md). The lesson from the method: find the layer that owns the failure (port, DNS, or application) before changing tools.

Other side effects of the network, from 2026-09, before the rigs moved to the OCS LAN: the rig couldn't reach PyPI (DNS timeouts), and large downloads were slow (CUDA's 4.5 GB took ~80 minutes). Not re-checked since the move.
