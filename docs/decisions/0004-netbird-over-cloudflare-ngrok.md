---
status: accepted
date: 2026-09-16
deciders: Team (not recorded)
---

# 0004. NetBird + EC2 relay for connectivity

## Context

The GPU rig sits on the school district network, which fingerprints and blocks known tunneling products. Students need to reach the rig from anywhere, over HTTPS, without the rig being directly exposed.

## Options considered

1. **Cloudflare Tunnel**: outbound port 7844 is blocked network-wide (TCP and UDP). We can't configure around it.
2. **ngrok**: three stacked failures: DNS sinkholing of tunnel hostnames, a CRL check blocked on port 80, then Ollama's DNS-rebinding protection returned 403 on the Host header.
3. **NetBird overlay + an AWS EC2 relay running Nginx/TLS**: NetBird was already crossing this network for SSH without being flagged.

## Decision

**NetBird + EC2.** EC2 is the only public host. It reaches the rig over NetBird ([network](../architecture/network.md)).

## Consequences

- Good: works today. The rig has no public exposure. EC2 has reliable networking and can reach PyPI.
- Bad: the rig peer connects through a relay (extra latency). NetBird SSH needs browser SSO for every connection ([workaround](../guides/netbird-access.md)). We depend on NetBird continuing to go unflagged.
- Method worth keeping: isolate which layer owns the failure (port, DNS, or application) before switching tools ([deck](../sources/2026-09-28-week0-1-mentor-deck.md) slide 11).

## Differs from the blueprint?

No. The blueprint leaves the network path to Gate 0 discovery.
