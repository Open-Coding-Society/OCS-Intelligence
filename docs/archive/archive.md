---
status: current
last_verified: 2026-09-29
---

# Archive

Superseded plans and records, kept for history. **Don't follow them as instructions.** Each file says what replaced it in its `superseded_by:` header. Commands and paths in these files may refer to the old repo layout (for example `systemd/` instead of `infra/`).

| Doc | What it was | Replaced by |
|---|---|---|
| [Phase-1 discovery record](./phase1-discovery.md) | 2026-09-16 audit of NetBird access, the hosts, and the hardware before deployment | [status](../status.md), [hardware](../architecture/hardware.md), [deployment log](../../evidence/captures/2026-09-18-rig1-deployment-log.md) |
| [4+3 orchestrator deployment guide](./inference-orchestrator-deployment-4plus3.md) | First plan: 4-GPU pinned + 3-GPU flexible workers, orchestrator on EC2 | [decision 0003](../decisions/0003-5-plus-2-gpu-split.md) |
| [Cursor handoff](./cursor-handoff.md) | The 5+2 execution plan handed to a coding agent | [deploy the rig](../operations/deploy-rig.md), [workers](../architecture/workers.md) |
| [EC2 gateway plan](./plan-ec2-gateway.md) | Implementation plan for the admission gateway | [gateway](../architecture/gateway.md), [deploy EC2](../operations/deploy-ec2.md) |

To archive a doc: `git mv` it here, set `status: superseded` and `superseded_by:`, update links that pointed to it, and add a row above.
