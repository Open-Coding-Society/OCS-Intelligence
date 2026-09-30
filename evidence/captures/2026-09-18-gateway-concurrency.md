---
date: 2026-09-18
---

# Admission gateway concurrency check (2026-09-18)

Live checks made against `https://ai.opencodingsociety.com` when the EC2 admission gateway went live. Collected from the original `USAGE.md` §2.4, `GATEWAY.md`, and `STATUS.md` §3 step 11. This is a record: don't edit it. How the wait line works: [gateway](../../docs/architecture/gateway.md).

## Setup

- Gateway `ocs-gateway` on EC2 `127.0.0.1:9100`, lanes A: 1 in flight + 4 waiting; B: 2 in flight + 4 waiting.
- Nginx `/v1/` and `/healthz` pointed at the gateway, with `proxy_read_timeout` / `proxy_send_timeout` 3600 s.
- Synchronous checks: 7/7 passed. The individual checks weren't recorded separately.

## Results

| Test | Result |
|---|---|
| Worker B (`qwen2.5:0.5b`), 7 parallel streams | **6 × HTTP 200, 1 × HTTP 429** |
| Worker A (`qwen3.8:27b`), 6 parallel streams | **5 × HTTP 200, 1 × HTTP 429**. `: queued` keepalives seen on A. |
| 5 requests with forged keys while Worker B was busy | All HTTP 401, and they didn't take places in the line |
| `/v1/models` with the real key during the same load | HTTP 200 |

Body of the rejected request (7th concurrent `qwen2.5:0.5b` stream), with `Retry-After: 15`:

```json
{"detail":{"error":{"message":"Too many requests. Please retry later.","type":"rate_limit_error","code":"rate_limit_exceeded"}}}
```
