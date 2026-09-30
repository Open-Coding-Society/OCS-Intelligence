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
- `/` (Open WebUI) goes straight to the rig with a 300 s read timeout and WebSocket upgrade. It **skips the gateway**.

## NetBird

A WireGuard-based overlay network. Both hosts are peers, and so are operator laptops (through the `netbird-dev` Docker container). On 2026-09-16 the EC2 peer connected peer-to-peer and the rig peer connected **through a relay** ([discovery record](../archive/phase1-discovery.md)).

NetBird SSH needs a browser SSO approval for **every new connection**. For how operators work around that, see [NetBird access](../guides/netbird-access.md).

## The district network

The school network doesn't block "servers" in general. It fingerprints known tunneling products. What we tried ([deck](../sources/2026-09-28-week0-1-mentor-deck.md) slides 10–11):

| Tool | Result | Root cause |
|---|---|---|
| Cloudflare Tunnel | Abandoned | Outbound port 7844 blocked network-wide (TCP and UDP) |
| ngrok | Abandoned | Three stacked failures: DNS sinkhole of tunnel hostnames, a CRL check blocked on port 80, then Ollama's DNS-rebinding protection returned 403 on the Host header |
| NetBird + AWS relay | **Works** | Already crossing this network for SSH, and not flagged as a tunnel |

Decision: [0004](../decisions/0004-netbird-over-cloudflare-ngrok.md). The lesson from the method: find the layer that owns the failure (port, DNS, or application) before changing tools.

Other side effects of the network: the rig can't reach PyPI (DNS timeouts), and large downloads are slow (CUDA's 4.5 GB took ~80 minutes).
