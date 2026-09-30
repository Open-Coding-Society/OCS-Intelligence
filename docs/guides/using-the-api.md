---
status: current
last_verified: 2026-09-18
---

# How to use the API

Call OCS Intelligence from curl, Python, or GitHub Copilot Chat. The full list of endpoints and errors is in the [API reference](../reference/api.md). Real recorded responses are in [evidence](../../evidence/captures/2026-09-17-public-api-e2e.md).

## Before you start

You need the student API key. It is **not in git**. Ask an operator, then put it in a local `.env` (gitignored):

```bash
cp .env.example .env      # then set OCS_API_KEY
set -a && source .env && set +a
```

Never paste the key into issues, PRs, chat logs, or code.

| Key | Who uses it | Where it lives |
|---|---|---|
| Student key (`OCS_API_KEY`) | Students, Copilot, curl | your `.env`; `PUBLIC_API_KEYS` on EC2 and the rig |
| Worker key | Orchestrator → `llama-server` only | rig env files. Clients never see it. |

## Pick a model

- `qwen2.5:0.5b` is fast (~90 tok/s) but small. Good for quick questions.
- `qwen3.8:27b` gives better answers but is slow (~9 tok/s). It **thinks before answering**, so give it `max_tokens` of 80 or more, or the whole budget can go to hidden `reasoning_content`.

## curl

List models:

```bash
curl -sS "$OCS_BASE_URL/models" -H "Authorization: Bearer $OCS_API_KEY"
```

One completion:

```bash
curl -sS "$OCS_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OCS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:0.5b",
       "messages": [{"role": "user", "content": "Reply with exactly: ping-ok"}],
       "max_tokens": 32}'
```

Add `"stream": true` and `curl -N` to stream tokens as Server-Sent Events.

The repo has two wrappers that read `.env` for you:

```bash
./scripts/request.sh "Explain recursion in one sentence."
./scripts/request.sh -m qwen3.8:27b --stream "Name two sorting algorithms."

python3 scripts/demo.py --pause     # guided live walkthrough: health, auth, 0.5b, 7-way queue
python3 scripts/demo.py --quality   # also exercises the 27B model
```

## Python (OpenAI SDK)

The OpenAI Python SDK works with our base URL. This is the same client the [benchmark](../testing/benchmarks.md) uses.

```python
import os
from openai import OpenAI

client = OpenAI(base_url=os.environ["OCS_BASE_URL"], api_key=os.environ["OCS_API_KEY"])
reply = client.chat.completions.create(
    model="qwen2.5:0.5b",
    messages=[{"role": "user", "content": "What is a binary search?"}],
    max_tokens=120,
)
print(reply.choices[0].message.content)
```

## GitHub Copilot Chat

In Copilot Chat's "Bring your own model" settings, add an OpenAI-compatible provider:

- **Base URL:** `https://ai.opencodingsociety.com/v1`
- **API key:** your `OCS_API_KEY`
- **Model:** `qwen2.5:0.5b` or `qwen3.8:27b`

> Nobody has signed Copilot Chat in against the API end to end yet ([status](../status.md)). The API path is verified. If you get it working, update this section with the exact menu steps.

## When the class is busy

The GPUs can only run a few generations at once. Extra requests **wait in line** on EC2. The connection stays open, and streams may show `: queued` comments. If the line is full you get **429** with `Retry-After: 15`. Closing the request gives up your place. How the line works and its sizes: [gateway](../architecture/gateway.md#capacity-what-survive-concurrent-requests-actually-means).

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Missing or invalid authorization` | No `Authorization: Bearer` header | Load `.env`, check the header |
| `401 Invalid API key` | Wrong key | Get the current key from an operator |
| `404 model_not_found` | Typo in `model` | Use a name from `/v1/models` |
| `429 rate_limit_exceeded` | Line for that model is full | Wait 15 s and retry, or use the other model |
| Empty `content` from `qwen3.8:27b`, `finish_reason: length` | Budget used up by reasoning | Raise `max_tokens` |
| Long wait before the first token | You're in line, or a long 27B job is ahead of you | Wait. There's no queue timeout. |
| `502` / `503` | Rig or a worker is down | Check [status](../status.md) and tell an operator |
