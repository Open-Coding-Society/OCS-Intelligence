---
status: accepted
blueprint_review: pending
date: 2026-09-17
deciders: Built by the team (the /v1 path went public 2026-09-17). No sign-off recorded.
---

# 0006. Serve the API on the public internet

> **Accepted (against the blueprint):** in production, but it differs from [Blueprint v2.2](../sources/2026-09-11-blueprint-v2.2.md) and hasn't been reviewed against it yet. When the review happens, record the outcome here and remove `blueprint_review: pending`.

## Context

The blueprint's scope lock (§7) says "nothing on the public internet" during the six-week campaign. Its assumptions (§17) say the project "stays a supervised school pilot — never a public internet service". The pilot envelope (§15) is "only over the approved network".

The team's goal ([deck](../sources/2026-09-28-week0-1-mentor-deck.md) slide 05) is "a public, authenticated platform … students can reach from anywhere". Practically, the rig couldn't be reached from inside the district network either ([0004](./0004-netbird-over-cloudflare-ngrok.md)), so the working path goes through a public EC2 host.

## Options considered

1. **School network only** (blueprint): the smallest attack surface, but students can't use it from home, and the district network blocked every path we tried.
2. **Public HTTPS endpoint with auth** (`ai.opencodingsociety.com`): reachable anywhere, with TLS and a Bearer key checked before any GPU work.

## Decision

A **public HTTPS endpoint** on EC2, with the rig kept private behind NetBird.

## Consequences

- Good: students can use it from anywhere. It works with Copilot without VPN setup.
- Bad: exposed to the whole internet with **one shared key**, no per-user revocation, no quotas, and no `max_tokens` cap. The blueprint's safety controls (§10) matter more here, and several aren't built yet ([threat model](../security/threat-model.md)).
- Required before a real pilot: per-student keys, token caps, and a firewall limiting rig `:9000` to the EC2 peer.

## Differs from the blueprint?

**Yes**: §7 scope lock, §15 pilot envelope, §17 assumptions. What would make us switch back: the mentor or school requiring a network-only pilot, or a red-team finding we can't fix at the gateway.
