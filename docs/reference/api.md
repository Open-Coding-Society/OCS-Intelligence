---
status: current
last_verified: 2026-09-29
---

# API reference

The public API is an OpenAI-compatible subset. Checked against the code in `gateway/` and `orchestrator/` on 2026-09-29. For examples, see [using the API](../guides/using-the-api.md). For real recorded responses, see [evidence](../../evidence/evidence.md).

**Base URL:** `https://ai.opencodingsociety.com/v1`
**Auth:** `Authorization: Bearer <OCS_API_KEY>`, one shared student key for now (see [threat model](../security/threat-model.md)).

## Endpoints

| Method | Path | Auth | Uses a GPU slot | Notes |
|---|---|---|---|---|
| `GET` | `/healthz` | no | no | Gateway liveness: `{"status":"ok"}`. Doesn't check the rig. |
| `GET` | `/v1/models` | yes | no | Lists the models below. Skips the wait line. |
| `POST` | `/v1/chat/completions` | yes | yes | Blocking or `"stream": true` (SSE). Goes through the [wait line](../architecture/gateway.md). |
| `GET` | `/` and everything else | Open WebUI login | — | Open WebUI (browser chat). `/api/version` returns its version. Skips the wait line. |

Anything else OpenAI offers (embeddings, completions, images, tools, …) isn't implemented.

## Models

| `model` | Worker | Context | Notes |
|---|---|---:|---|
| `qwen2.5:0.5b` | B | 8192 | Fast, small. |
| `qwen3.8:27b` | A | 4096 | Quality. A **reasoning model**: it streams hidden `reasoning_content` before `content`, so set `max_tokens` to 80 or more or the answer may be empty. |

Context is per slot, set in the [worker env](./configuration.md#workers-rig-etcocs-intelligenceworker-env).

## Responses and errors

| HTTP | When | Body / headers | Raised by |
|---|---|---|---|
| 200 | Success | OpenAI `chat.completion` / `chat.completion.chunk`, plus llama.cpp `timings` | worker |
| 401 | Missing or malformed `Authorization` | `{"detail":"Missing or invalid authorization"}` | gateway (before queueing) |
| 401 | Wrong key | `{"detail":"Invalid API key"}` | gateway |
| 404 | Unknown `model` | `error.code = "model_not_found"` | gateway (no queue entry) |
| 429 | Wait line for that model is full | `error.code = "rate_limit_exceeded"`, `Retry-After: 15` | gateway |
| 429 | Orchestrator's own cap (`QUEUE_CAPACITY_PER_WORKER`) hit | same body, `Retry-After: 5` | orchestrator (only reachable if someone bypasses the gateway) |
| 499 | Blocking client disconnected while waiting | empty | gateway |
| 502 | Gateway couldn't reach the orchestrator | `{"detail":"Upstream communication failed"}` | gateway |
| 503 | Worker for that model is unhealthy | `error.code = "worker_unavailable"` | orchestrator |

If an upstream error happens **mid-stream**, the error arrives as an SSE event (`data: {"error": {...}}`) followed by `data: [DONE]`, because the HTTP status has already been sent.

## Streaming details

- Content type `text/event-stream`. Chunks follow OpenAI's format and end with `data: [DONE]`.
- While a request is **waiting in line**, the gateway sends the SSE comment `: queued` about every 15 s. OpenAI clients ignore comments.
- For `qwen3.8:27b`, `delta.reasoning_content` chunks come before `delta.content` chunks.
- Closing the connection leaves the line, or frees the GPU slot if you already had it.

## Rig-internal endpoints (not public)

The orchestrator on `:9000` also serves `/healthz`, `/readyz` (200 if at least one worker is healthy, otherwise 503), `/v1/models`, and `/v1/chat/completions`. Workers serve llama.cpp's `/health`, `/metrics`, and `/slots` on localhost. Ports are in [hosts](./hosts.md).
