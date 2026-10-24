---
status: current
last_verified: 2026-10-23
---

# Mentor deep audit and open-issues report, 2026-10-14 (summary)

| | |
|---|---|
| **Originals** | [`2026-10-14-mentor-audit-deck.pdf`](./2026-10-14-mentor-audit-deck.pdf) (10 slides, "Deep Audit & Project Review") and [`2026-10-14-mentor-audit-open-issues.pdf`](./2026-10-14-mentor-audit-open-issues.pdf) (7 pages, "Open Issues Report", with the fix order) |
| **Author** | Eddie Revollo (Prometheus), mentor. Sent to the team and John Mortensen with a covering email on 2026-10-14 |
| **Date** | Audit run 2026-10-14 against the public repo at the 2026-09-30 HEAD, plus live probes of the public service |
| **What it is** | A full review of security, configuration, code, and process: 32 findings (4 high, 14 medium, 14 low), a recommended fix order, and five questions for the walkthrough |

## Summary

- **Verdict:** "strong bones, weak operations." The API path worked end to end. Open WebUI returned 502 on 2026-10-14, while `status.md` still said it was running.
- **Credit:** no real secret in any of the 30 commits, the offline tests passed (16/16 then), the measurements were honest, the systemd hardening was real, the threat model named most of the gaps, and no log line holds keys or prompts.
- **Security (open-issues p. 4):**
  - S1 (high): auth fails open on both tiers when the key list is empty.
  - S2 (high): the orchestrator binds `0.0.0.0:9000` with no firewall.
  - S3: one shared student key, with no per-student keys, quotas, or revocation.
  - S4: key comparison isn't constant-time.
  - S5/S6: every service runs as root, and operators SSH in as root.
  - S7/S8/S10: no rate limit beyond the lanes, internal IPs and GPU IDs are public, and the orchestrator's direct path accepts unbounded request bodies.
- **Configuration (p. 3, 5):**
  - M1 (high): Open WebUI is a hand-started container with no unit, no restart policy, and no monitoring. This was the most likely cause of the outage.
  - M2: the rig runs FastAPI, uvicorn, and httpx below the repo's own floors.
  - M4/M5: nothing is pinned, and llama.cpp was built from an unpinned master.
  - M3: no HSTS or security headers, and the server version is disclosed.
  - Hour-long timeouts can tie up the single quality slot.
- **Code (p. 5):**
  - C1: streamed replies release their in-flight slot before generation starts, so capacity limits don't apply to streaming.
  - C6: `check_docs.py` failed with 10 broken links.
  - C3/C4: malformed JSON returns 500 instead of 400, and the lane code can over-release its semaphore.
  - The tests covered no auth, routing, or health code.
- **Process (p. 6):**
  - D1 (high): no CI.
  - D2: no pull requests.
  - D3: only two people have committed.
  - D4: the record stopped on 2026-09-30 (no evidence, no Friday reports, no `evidence/weekly/`) while Rig 2 work continued off the record.
- **Capacity (p. 3):** 11 seats (3 running and 8 waiting) against the charter's 8 sustained. Worker A was at 8.7 tok/s against a 12.5 baseline, with NCCL deferred. These are 2026-09-30 numbers. Rig 1's layout has changed since then ([status](../status.md)).
- **Fix order (p. 7):**
  - **Now:** put Open WebUI under management with an uptime check, fail closed (S1), and the first PR and CI (D1/D2).
  - **Next:** restore the record (D4), firewall the orchestrator (S2), per-student keys (S3), fix C1 with auth/routing tests, pin everything, and decide on Worker A.
  - **Before the showcase:** the 8-user load test, the soak, the quality set, failure drills, the continuity drill, and a status page kept honest weekly.

The per-person commit counts on p. 6 of the open-issues report aren't repeated here.

## State of each finding, 2026-10-23

Checked against the code on `main`. Where each one is scheduled: [roadmap](../project/roadmap.md#sprint-5-plan).

| Finding | State on 2026-10-23 | Sprint |
|---|---|---|
| S1 auth fails open | Open: `gateway/auth.py` and `orchestrator/auth.py` return the token when `PUBLIC_API_KEYS` is empty | 5 |
| S2 orchestrator on all interfaces | Open in the units (`--host 0.0.0.0` in `infra/rig/` and `infra/rig2/`). The [one-way NetBird policies](../decisions/0008-one-way-netbird-policies.md) (2026-10-15) narrow who can reach it, but there's no host firewall | 5 |
| S3 one shared key | Open | 6 |
| S4 non-constant-time compare | Open: no `compare_digest` in either `auth.py` | 5 |
| S5/S6 root services, root SSH | Open: no `User=` in any unit | 6 |
| S7/S8/S10 | Open | 6 |
| M1 Open WebUI unmanaged | Open: no unit for it in `infra/`. [Status](../status.md) has it running as of 2026-10-15 | 5 (first) |
| M2 rig below version floors | Not re-checked | 5, with pinning |
| M3 security headers | Open: `infra/ec2/llm-relay-nginx.conf` has `client_max_body_size` but no HSTS or headers | 6 |
| M4/M5 unpinned | Partly done: local dev is locked by `uv.lock` ([0010](../decisions/0010-uv-for-local-dev.md)). Services and llama.cpp are still unpinned | 5 |
| Long timeouts | Open: gateway `UPSTREAM_TIMEOUT_SECONDS` defaults to 3600 | 5 |
| C1 streaming slot | Open: `orchestrator/main.py` decrements `active_requests` in `finally` as soon as the `StreamingResponse` is returned | 5 |
| C3/C4 | Open: `await request.json()` isn't guarded in either service | 5 |
| C6 broken doc links | **Fixed** 2026-10-22: 0 problems | — |
| No auth/routing/health tests | Open: 32 tests now, none on auth or routing | 5 |
| D1 no CI | Open: no `.github/` | 5 (first) |
| D2 no PRs | Open | 5 (first) |
| D3 bus factor | Open | 6 (continuity drill) |
| D4 record gap | Partly done: evidence and playbooks resumed 2026-10-15. Friday reports and `evidence/weekly/` still missing | 5 |
| Worker A speed decision | Open, and the layout it was measured on has changed | 5 |
| Load, soak, quality set, failure drills | Not run | 6 |

## Where each part is handled in our docs

| Source section | Our doc | Notes / where we differ |
|---|---|---|
| Security findings | [threat model](../security/threat-model.md) | The threat model already listed S2 as open |
| Outage (deck slide 6) | [status](../status.md) | Open WebUI was back by 2026-10-15. The audit's root cause is marked "most likely"; it wasn't confirmed on the host |
| Capacity and Worker A | [gateway](../architecture/gateway.md), [workers](../architecture/workers.md) | `workers.md` still describes the 2026-09-18 layout |
| Fix order | [roadmap: Sprint 5 and 6](../project/roadmap.md#sprint-5-plan) | Split by sprint theme; the "Now" items lead Sprint 5 |
| Process | [conventions](../conventions.md), [pending playbook](../../evidence/pending-playbook.md) | Weekly reports: [template](../_templates/weekly-report.md) exists, folder doesn't |
