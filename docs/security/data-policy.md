---
status: draft
last_verified: 2026-09-29
---

# Data policy

What data may go through the service and what the service keeps. The blueprint (§10) says the school's privacy/security authority, not the students or the mentor, signs off on this. **Until then, this is a proposal.**

## Allowed and not allowed

From blueprint §10.

| Allowed | Never |
|---|---|
| Public code examples | Grades |
| Synthetic practice assignments | Names tied to school records |
| Your own non-sensitive snippets | Accommodation or health information |
| General coding questions | Passwords or API keys |
| | Private repositories |
| | Disciplinary records |

## What each component logs today

From reading the code and default configs on 2026-09-29. Not yet checked on the live hosts.

| Component | Logs | Prompt text? |
|---|---|---|
| Nginx (EC2) | Default access log: client IP, time, method, path, status, user agent | No (bodies aren't logged by default) |
| Admission gateway | Startup config, disconnects, upstream errors (journald). Uvicorn access lines: method, path, status, client address. | No |
| Orchestrator | Same pattern as the gateway | No |
| llama-server workers | Startup and slot events (journald) | **Not verified.** Check whether request contents appear at the configured verbosity. |
| Open WebUI | Stores chat history for its users, by design | **Yes**, inside Open WebUI |

## Open decisions (need an owner)

- Retention period for Nginx and journald logs, and a deletion procedure.
- Whether Open WebUI chat history is acceptable, and for how long.
- The notice shown to students (what's logged, what not to paste).
- Who the privacy authority is ([Gate 0](../project/roadmap.md#gate-0-discovery-packet)).
