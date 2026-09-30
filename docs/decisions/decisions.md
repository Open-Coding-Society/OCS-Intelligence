---
status: current
last_verified: 2026-09-29
---

# Decision log

Architecture decision records (ADRs): why we chose X over Y, so nobody has to argue it again from memory. Format based on [MADR](https://adr.github.io/madr/). Template: [`_templates/decision.md`](../_templates/decision.md).

| # | Decision | Status | Date | Differs from blueprint? |
|---|---|---|---|---|
| [0001](./0001-llama-cpp-over-vllm.md) | llama.cpp as the inference runtime, not vLLM | accepted | 2026-09-11 | no |
| [0002](./0002-sharded-27b-over-per-gpu-replicas.md) | One 27B model split across several GPUs, not one 7–8B copy per GPU | accepted ⚠️ blueprint review pending | 2026-09-28 | **yes** (§4, §5) |
| [0003](./0003-5-plus-2-gpu-split.md) | Split Rig 1 into 5-GPU and 2-GPU workers | accepted | 2026-09-17 | follows from 0002 |
| [0004](./0004-netbird-over-cloudflare-ngrok.md) | NetBird + EC2 relay for connectivity | accepted | 2026-09-16 | no |
| [0005](./0005-admission-queue-on-ec2.md) | The wait line lives on EC2, in process, with no Redis | accepted | 2026-09-18 | partly (§4 queue: yes; routing to replicas: n/a) |
| [0006](./0006-public-endpoint.md) | Serve the API on the public internet | accepted ⚠️ blueprint review pending | 2026-09-17 | **yes** (§7 scope lock) |

## Statuses

- **proposed:** written down but not agreed or built yet.
- **accepted:** agreed by the team and, where required, by the mentor.
- **rejected:** considered and turned down. Kept so it isn't proposed again without new evidence.
- **superseded:** replaced by a later decision (`superseded_by:`).

**Against the blueprint:** an accepted decision that differs from the blueprint and hasn't been reviewed against it yet carries `blueprint_review: pending` in its header and a ⚠️ in the table. Find them with `grep -l 'blueprint_review: pending' docs/decisions/`. Once reviewed, record the outcome in the decision and remove the flag, or supersede the decision.

## Adding a decision

1. Copy the template to `NNNN-short-title.md`, using the next number.
2. Start at `status: proposed`. Record who decided in `deciders:` when that's known. Leave it blank rather than guessing.
3. Add a row above.
4. Never delete or renumber a record. To change a decision, write a new one and mark the old one superseded.
