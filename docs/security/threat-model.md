---
status: draft
last_verified: 2026-09-29
---

# Threat model

What we protect, from whom, what's in place, and what's missing. Built from the code, the [Nginx config](../../infra/ec2/llm-relay-nginx.conf), and blueprint §10. The blueprint's stance: design as if every input is hostile and the model itself can't be trusted.

> **Draft:** no red-team exercise has been run. The gaps below come from reading the code and config, not from testing.

## What we protect

| Asset | Why it matters |
|---|---|
| GPU capacity | One abuser can starve a class |
| Student key, worker key | Access to the service. The worker key opens the raw workers. |
| Rig and EC2 hosts | Root on either host means the whole service |
| Prompts and responses | May contain student work. Must not leak or pile up in logs. |
| The school network's trust | Getting flagged or abused could end the project |

## Entry points

| Entry | Exposure | Auth |
|---|---|---|
| `https://ai.opencodingsociety.com/v1/*` | **Public internet** ([0006](../decisions/0006-public-endpoint.md)) | Shared Bearer key, checked by the gateway |
| `https://ai.opencodingsociety.com/` (Open WebUI) | Public internet | Open WebUI accounts |
| Rig `:9000` (orchestrator) | Any NetBird peer | Same shared key |
| Rig `:3000` (Open WebUI) | Any NetBird peer | Open WebUI accounts |
| SSH on both hosts | NetBird peers only | NetBird SSO |

## Controls vs blueprint §10

| Risk | Blueprint control | In place today | Gap |
|---|---|---|---|
| Strangers getting in | Per-user keys, TLS, firewall allow-list | TLS (Certbot). One shared key. Bad keys get 401 before queueing. | **No per-user keys or revocation.** Leaking the one key exposes everyone. |
| One user hogging everything | Limits on tokens, context, request rate, queue size | Per-model wait line: 1+4 (A), 2+4 (B), then 429 | **No `max_tokens` cap**: one long 27B job holds the only quality slot. **No per-user or per-IP rate limit.** The deck (slide 29) lists "per-IP rate limiting at NGINX", but the repo copy of the config has no `limit_req`. One retry loop can fill both lanes. |
| Skipping the wait line | — | Gateway on `127.0.0.1` only | **Rig `:9000` has no firewall rule** limiting it to the EC2 peer, so any NetBird peer can bypass the line. **Open WebUI skips the line** entirely. |
| Misconfiguration opening access | — | Env templates use `CHANGE_ME` | **An empty `PUBLIC_API_KEYS` accepts any Bearer token**, in both the gateway and the orchestrator ([configuration](../reference/configuration.md)). |
| Secrets leaking | No secrets in prompts; scan outputs; don't log prompts | Keys only in `0600` env files and gitignored `.env`. The orchestrator swaps in the worker key, so clients never see it. | No output scanning. Prompt logging not verified ([data policy](./data-policy.md)). |
| Sneaky instructions (prompt injection) | Model has no tools or actions; fixed system rules | The model has no tools. Text in, text out. | No fixed system prompt. No jailbreak test suite. |
| Poisoned software | File hashes, pinned versions, approved model sources | Models symlinked to known Ollama blob hashes ([hosts](../reference/hosts.md#model-files)). llama.cpp commit recorded. | Python deps use ranges, not pins. No release checklist. |
| Data piling up | Metadata-only logs, short retention, deletion procedure | — | **No retention policy** |
| Dangerous code suggestions | Warning labels; nowhere to run code | Nothing executes model output | No safe-use notice published |

## Priority fixes

Suggested order. Each needs an issue and evidence when it's done.

1. Firewall rig `:9000` (and `:3000`) to the EC2 NetBird IP only.
2. Refuse to start the gateway and orchestrator when `PUBLIC_API_KEYS` is empty.
3. Add a `max_tokens` cap at the gateway.
4. Per-student keys with revocation. This also makes the line fair per person.
5. Per-IP `limit_req` in Nginx, or confirm where the deck's rate limiting lives.
6. Run the RED TEAM drill ([test plan](../testing/test-plan.md)).
