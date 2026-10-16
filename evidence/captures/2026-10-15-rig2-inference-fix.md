---
date: 2026-10-15
---

# Rig 2: worker crash loop fixed, orchestrator deployed, switched to a MoE model (2026-10-15)

Checked and changed live over NetBird SSH (`root@100.75.127.192`, `ocs-intelligence-rig2`) from the `Yash WSL` peer, 18:18–19:06 PDT. This is a record: don't edit it. Layout and paths: [hosts](../../docs/reference/hosts.md). How to redo it: [deploy the rig](../../docs/operations/deploy-rig.md#rig-2-one-script).

## What was found

[`infra/rig2/setup.sh`](../../infra/rig2/setup.sh) had already been run earlier in the day (`/etc/ocs-intelligence/worker.env` and `/opt/llama.cpp/bin/` dated 11:23). CUDA 12.6, the llama.cpp build, the model symlink, and `ocs-llama.service` were all in place.

| Check | Result |
|---|---|
| GPUs | 8: 1 × GTX 1080 Ti (11 GB, GPU 0) + 7 × GTX 1070 (8 GB). Driver 550.163.01 |
| GPU memory | 7 MiB used on every card: no model loaded |
| `ocs-llama.service` | Crash-looping, restart counter at **4,531** |
| Worker log | `start: couldn't bind HTTP server socket, hostname: 127.0.0.1, port: 8081` |
| Who held `:8081` | `python3 -m http.server 8081 --bind 0.0.0.0`, user `ocs`, started 10:25 from a GNOME Terminal, cwd `/home/ocs/ai2-site` (an `index.html` containing `hi`) |
| Placeholder's log | 194 requests from EC2 (`100.75.172.167`), first at 10:35 (`HTTP/1.1`), last at 17:43 (`HTTP/1.0`, which is what Nginx `proxy_pass` sends by default). Also 15 from `Yash WSL` and 243 from `127.0.0.1` |
| Public `https://ai2.opencodingsociety.com/` | Valid Let's Encrypt cert (`CN=ai2.opencodingsociety.com`, issuer `YE2`), but answers `301` to itself |
| llama.cpp | commit `b76b13379` (`b11670`) |

The placeholder bound `0.0.0.0:8081`, so llama-server could never bind `127.0.0.1:8081`. It was also reachable from every NetBird peer that could reach the rig.

## What was changed

1. Killed the placeholder (`kill 82859`). `/home/ocs/ai2-site/` was left in place.
2. `systemctl restart ocs-llama`. Healthy after ~2 min:

   ```text
   load_model: initializing, n_slots = 1, n_ctx_slot = 262144, kv_unified = 'false'
   llama_server: listening on http://127.0.0.1:8081
   ```

   VRAM after load: 5.0–5.8 GiB per card (GPU 0: 5,607 of 11,264 MiB; GPUs 1–7: 5,053–5,757 of 8,192 MiB).
3. Deployed the orchestrator from this repo's `orchestrator/` (with the optional-Worker-B change in this commit) to `/opt/ocs-orchestrator/`. Venv from **PyPI** (Rig 2 can reach `pypi.org` and `github.com`, unlike Rig 1): FastAPI 0.143.2, uvicorn 0.54.0, httpx 0.28.1. Env from [`infra/rig2/orchestrator.env.template`](../../infra/rig2/orchestrator.env.template) with `GROUP_B_MODEL_ALIAS=` empty. Unit: [`infra/rig2/ocs-orchestrator.service`](../../infra/rig2/ocs-orchestrator.service), enabled.
4. `PUBLIC_API_KEYS` on Rig 2 is a **temporary random key** generated on the rig (`/root/ocs-deploy/temp-public-key`), not the student key. An empty value would accept any Bearer token from any peer that can reach `:9000`.

## Measured

Worker direct, one request, 65-token prompt, 214 generated tokens, cold cache:

| Metric | Value |
|---|---:|
| Prompt processing | 24.4 tok/s |
| Generation | **8.8 tok/s** |

About the same as Rig 1's Worker A (8.7 tok/s, [deployment log](./2026-09-18-rig1-deployment-log.md)), with 8 GPUs instead of 5. One request isn't a benchmark.

Through the Rig 2 orchestrator at `http://100.75.127.192:9000`:

```text
/readyz                                  {"status":"ready"}
/v1/models                               {"object":"list","data":[{"id":"qwen3.8:27b",...}]}
/v1/models, wrong key                    401
/v1/chat/completions stream=true         data: {... "model":"qwen3.8:27b","system_fingerprint":"b11670-b76b13379" ...}
/v1/chat/completions model=qwen2.5:0.5b  404
```

## Model switch to Qwen3.6-35B-A3B (18:49–19:06)

Why: [decision 0009](../../docs/decisions/0009-rig2-moe-behind-open-webui.md). Config chosen without benchmarking, at the team's request.

- Downloaded `unsloth/Qwen3.6-35B-A3B-GGUF` → `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf` straight from Hugging Face at ~44–54 MB/s, into `/srv/ocs-intelligence/models/qwen3.6-35b-a3b-ud-q4_k_xl.gguf`. Size 22,360,456,160 B. SHA-256 `707a55a8a4397ecde44de0c499d3e68c1ad1d240d1da65826b4949d1043f4450`, matching the Hugging Face LFS object.
- A `Qwen3-Coder-Next-UD-Q4_K_XL` download was started and cancelled (partial file deleted).
- PCIe links, from `nvidia-smi`: all 8 cards at **gen 1, ×1**.
- A `llama-bench` run was started and then interrupted by the operator (Ctrl-C) before it printed results. No numbers from it.
- `worker.env` changed (old copy: `/root/ocs-deploy/worker.env.bak-qwen3.8`): `DEFAULT_MODEL_ID=qwen3.6:35b-a3b`, `CONTEXT_SIZE=524288`, `PARALLEL=2`, `TENSOR_SPLIT=11,8,8,8,8,8,8,8`, `LLAMA_EXTRA_ARGS=-ub 1024`. The unit was updated from [`infra/rig2/ocs-llama.service`](../../infra/rig2/ocs-llama.service) to take `PARALLEL` and `LLAMA_EXTRA_ARGS`. Orchestrator `GROUP_A_MODEL_ALIAS=qwen3.6:35b-a3b`.
- Loaded: `n_slots = 2, n_ctx_slot = 262144`. VRAM 5.5–7.2 GiB per card (GPU 0: 7,189 of 11,264 MiB).

Through the orchestrator, one request each:

```text
/v1/models   {"object":"list","data":[{"id":"qwen3.6:35b-a3b",...}]}
"Say hi."    200; content in reasoning_content (the model thinks first by default); finish_reason "length" at max_tokens=200
prompt eval  13 tokens, 13.8 tok/s
generation   200 tokens, 27.24 tok/s
```

The first chat request after the restart returned a body without `choices`. It wasn't captured, and the next request worked.

## Also checked: Open WebUI on Rig 1 (read only)

- Container `open-webui` (`ghcr.io/open-webui/open-webui:main`, 0.11.3), Docker bridge network, port 3000 → 8080.
- Saved connections (Open WebUI's `config` table): one enabled OpenAI connection to `https://ai.opencodingsociety.com/v1`. The Ollama connections are disabled.
- From inside the container, `http://100.75.127.192:9000/readyz` → `{"status":"ready"}` (after the rigs-to-rigs NetBird policy in `c2ac00d`). From the Rig 1 host, `nc -vz 100.75.127.192 9000` succeeds.
- In `routers/openai.py`, `get_merged_models` keeps the first connection's entry when two connections offer the same model ID.
- Nothing in Open WebUI was changed.

## Not done here

- EC2 wasn't touched. The teammate's `ai2` cert and Nginx site are still there.
- Open WebUI wasn't connected to Rig 2.
