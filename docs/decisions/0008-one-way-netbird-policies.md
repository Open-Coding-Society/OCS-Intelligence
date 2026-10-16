---
status: proposed
date: 2026-10-15
deciders: Requested by Yash Parikh. Not yet agreed by the team or the mentor.
---

# 0008. One-way, group-based NetBird policies instead of All ↔ All

## Context

NetBird ([0004](./0004-netbird-over-cloudflare-ngrok.md)) ships with a `Default` policy that lets every peer reach every other peer in both directions. Our network holds the servers (EC2, Rig 1, Rig 2) and also operators' personal machines (laptops, WSL). Under `Default`, any peer, including a compromised server, could open connections to an operator's machine. The [threat model](../security/threat-model.md) also notes that the rig's orchestrator port `9000` had no firewall rule, so every peer could reach it.

NetBird policies go from a source group to a destination group, and the client firewall is stateful: a one-way policy lets the source start connections and lets the replies back, but the destination can't start a connection to the source.

## Options considered

1. **Keep `Default`**: nothing to manage, but every peer can reach every operator machine.
2. **Per-peer policies**: precise, but every new operator needs new policies.
3. **Groups with one-way policies, `Default` disabled**: operators go in an `outbound-only` group that can reach the servers and that no policy points at; the gateway → rig path gets its own narrow rule.

## Decision

We chose **option 3**. Adding an operator means adding their peer to one group in the dashboard. Policies and groups are recorded in [`infra/netbird/acl.json`](../../infra/netbird/acl.json) and checked with [`infra/netbird/apply.py`](../../infra/netbird/apply.py). Applied on 2026-10-15 ([evidence](../../evidence/captures/2026-10-15-netbird-access-policies.md)).

## Consequences

- Good: nothing in the NetBird network can start a connection to an `outbound-only` machine. Peers in it don't even appear in each other's network maps.
- Good: the rig's `:9000` and `:3000` are reachable only from EC2 and from `outbound-only` peers, instead of from every peer.
- Bad / accepted trade-off: a new peer that isn't in any group can only use NetBird SSH to the servers (through the existing `SSH Access` policies, whose source is `All`) until someone adds it to a group.
- Amended 2026-10-15: the rigs may reach each other both ways (`rigs-to-rigs`), so Open WebUI on Rig 1 can call a model on Rig 2. Restricting server-to-server traffic adds little here: EC2, the most exposed host, already reaches both rigs. What this decision protects is the `outbound-only` machines, and that rule is unchanged. **Temporary:** remove `rigs-to-rigs` once a router (the planned Mac Mini, or EC2) sits between the rigs.
- Bad / accepted trade-off: any new service that has to cross NetBird needs a new rule in `acl.json` and in the dashboard.
- Follow-up work: verify from a server that a connection to an `outbound-only` peer times out; confirm dashboard browser SSH still works; add Rig 2's orchestrator port to `gateway-to-rigs` if it isn't `9000`.

## Differs from the blueprint?

Not in design: the [blueprint](../sources/2026-09-11-blueprint-v2.2.md) doesn't specify access rules inside the overlay. **In process, yes:** §6 asks for two-person review on firewall changes, and this one was applied live by one person before review. A second operator should review `acl.json` and the live policies (`python3 infra/netbird/apply.py check`) before this is accepted.
