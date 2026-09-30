# Context windows

Live as of 2026-09-23. Worker A (`qwen3.8:27b`) serves one request at a time with a **262,144-token** context window. Worker B is unchanged.

The server setting is context size (`CONTEXT_SIZE` / `llama-server --ctx-size`). With one slot, that number is the context window: prompt tokens and generated tokens share it. `max_tokens` on a request only caps the reply. It does not raise the window.

| Model | Where | Context size | Slots | Window per request |
|---|---|---:|---:|---:|
| `qwen3.8:27b` | Worker A, GPUs 0–4 | 262,144 | 1 | **262,144** |
| `qwen2.5:0.5b` | Worker B, GPUs 5–6 | 8,192 | 2 | **4,096** |

`llama-server` divides `--ctx-size` by `--parallel`. The old Worker A setting was `CONTEXT_SIZE=4096` and `--parallel 2`, so each coding-agent request only had 2,048 tokens. The admission gateway already allows one 27B job in flight, so the second slot was unused. Worker A is now `--parallel 1`.

The model file itself can do 262,144 tokens. That is also the largest power of two that stays on the five GTX 1070s with an f16 KV cache. Measured on the rig:

| Context | Result | Busiest GPU |
|---:|---|---:|
| 32,768 | fit | 4,325 MiB |
| 131,072 | fit | 5,861 MiB |
| 262,144 | fit | 7,391 MiB of 8,192 |

Startup logged one compute-buffer allocation failure on GPU 2, then llama.cpp retried without pipeline parallelism and came up. No KV-cache quantization. After a few-thousand-token prompt, GPU 2 sits around 7.4 GB of 8 GB, so a prompt near the full window has little scratch memory left and will be slow to prefill across the PCIe x1 risers. Deployed env and unit: [`STATUS.md`](./STATUS.md) §4.2 and §4.4. Templates: [`systemd/worker-a.env.template`](./systemd/worker-a.env.template), [`systemd/ocs-llama-a.service`](./systemd/ocs-llama-a.service).

Checked on the rig after the change:

- `GET /props` on Worker A reports `n_ctx` 262144 and `total_slots` 1.
- A short prompt returned an answer.
- A prompt of about 3,000 tokens, which the old 2,048-token slot would have rejected, was accepted.
- A 400,052-token prompt was rejected with `exceed_context_size_error` and `n_ctx` 262144.
- GPUs 5–6 stayed on Worker B.

The orchestrator and the EC2 gateway do not cap context. A request that is too long fails at `llama-server`.

---

## GitHub Copilot

Copilot’s `maxInputTokens` and `maxOutputTokens` are client caps. They are not the server window. Their sum has to stay under the per-request window, with room for the chat template.

```json
[
  {
    "name": "OCS Intelligence",
    "vendor": "customendpoint",
    "apiKey": "${input:chat.lm.secret.-6b4ba861}",
    "apiType": "chat-completions",
    "models": [
      {
        "id": "qwen2.5:0.5b",
        "name": "qwen2.5:0.5b",
        "url": "https://ai.opencodingsociety.com/v1",
        "toolCalling": true,
        "vision": false,
        "maxInputTokens": 3072,
        "maxOutputTokens": 512
      },
      {
        "id": "qwen3.8:27b",
        "name": "qwen3.8:27b",
        "url": "https://ai.opencodingsociety.com/v1",
        "toolCalling": true,
        "vision": false,
        "maxInputTokens": 200000,
        "maxOutputTokens": 16384
      }
    ]
  }
]
```

The 0.5B caps add up to 3,584, under the 4,096-token slot. The 27B caps add up to 216,384, under 262,144, and leave most of the window for the prompt. A 128,000-token reply would hold the only 27B slot for hours at about 8 tokens per second.

Replace the `apiKey` input id with the secret already stored in your Copilot settings. Do not paste the student key into this file if you commit it.

---

## Try the 27B API

From this repo, with `OCS_API_KEY` in `.env`:

```bash
set -a && source .env && set +a

curl -sS "${OCS_BASE_URL:-https://ai.opencodingsociety.com/v1}/chat/completions" \
  -H "Authorization: Bearer $OCS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3.8:27b","messages":[{"role":"user","content":"In one sentence, what is a binary search?"}],"max_tokens":80}'
```

`qwen3.8:27b` thinks before it answers, so `max_tokens` of 80 is enough for one sentence. Expect several seconds. If the single 27B slot is busy, the gateway returns HTTP 429 with `Retry-After: 15`.
