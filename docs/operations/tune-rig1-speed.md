---
status: draft
last_verified: 2026-11-02
---

# How to tune Rig 1 inference speed

By the end, Rig 1's two workers will run the fastest settings you measured, using the GGUFs already on the rig and with no new downloads or rebuilds.

Checked against the repo's unit and env copies on 2026-11-02. **None of this has been run on the rig yet.** Flag names and log strings come from upstream llama.cpp and may differ on the commit Rig 1 runs ([deploy the rig](./deploy-rig.md)), so step 1 checks them. Treat every expected gain here as a hypothesis until you've measured it.

## What limits speed

| Limit | Why | What it means for tuning |
|---|---|---|
| VRAM bandwidth on `qwen3.8:27b` | It's a dense model, so every token reads all its weights. A GTX 1070 moves about 256 GB/s and the [model file](../reference/hosts.md#model-files) is about 16.8 GB, so the ceiling is about 15 tok/s | Expect modest generation gains. Reaching 10–12 tok/s would be a good result |
| Layer split runs one card at a time | More cards add memory, not speed. Rig 2 ran this same model at about the [same speed on 8 GPUs](../../evidence/captures/2026-10-15-rig2-inference-fix.md) as Rig 1 did on 5 | Moving cards between workers won't speed up a request |
| Prompt prefill | This is where layer split can use several cards at once (pipeline parallelism), if VRAM allows it | This is probably the biggest gain, and it shortens the wait for the first token |
| Rig CPU and RAM ([hardware](../architecture/hardware.md#platform)) | Two cores and 16 GB are shared by both workers, the orchestrator, and Open WebUI | Don't let host caches or thread counts fight each other |

`gemma4:26b` isn't bound by the same ceiling. Its A4B name suggests a mixture-of-experts model that reads only part of its weights per token. Its speed has [never been recorded](../status.md#components), so measure it before comparing the two.

## Before you start

- SSH access to Rig 1 over NetBird ([how](../guides/netbird-access.md)) and `sudo`.
- A time when the class isn't using the service. The benchmark calls the workers directly, so it skips the wait line and competes with students for slots.
- Each worker restart reloads its model and drops any requests in progress.

## Steps

### 1. Measure a baseline

1. Install the benchmark script:

   ```bash
   sudo tee /root/bench-worker.py >/dev/null <<'EOF'
   #!/usr/bin/env python3
   """Usage: bench-worker.py a|b PROMPT_SIZE [cache]"""
   import json, re, statistics as st, sys, urllib.request as u, uuid

   ENV = "/etc/ocs-intelligence/worker-{}.env"
   w, size = sys.argv[1], int(sys.argv[2])
   port = {"a": 8081, "b": 8082}[w]
   key = re.search(r"^WORKER_API_KEY=(.*)$", open(ENV.format(w)).read(), re.M).group(1)


   def code():
       # A unique first line keeps a repeat run from matching an old cached prompt.
       body = "".join(f"def f{i}(x):\n    return x * {i} + {i % 7}\n" for i in range(size // 20))
       return f"# {uuid.uuid4()}\n{body}"


   def run(prompt, n_predict=256, cache=False):
       body = {"prompt": prompt, "n_predict": n_predict, "temperature": 0, "cache_prompt": cache, "ignore_eos": True}
       req = u.Request(f"http://127.0.0.1:{port}/completion", json.dumps(body).encode(),
                       {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
       return json.load(u.urlopen(req, timeout=1800))["timings"]


   if sys.argv[3:] == ["cache"]:
       a, b = code(), code()
       for label, prompt in [("A cold", a), ("A repeat", a), ("B cold", b), ("A after B", a)]:
           t = run(prompt, n_predict=16, cache=True)
           print(label, "prompt_tokens", t["prompt_n"], "prompt_ms", round(t["prompt_ms"]))
   else:
       base = code()
       for name, tail in [("new", "\n# Explain what this module does:\n#"), ("echo", "\n# The same code, copied exactly:\n")]:
           t = [run(base + tail) for _ in range(3)]
           print(name, "prompt_tokens", t[0]["prompt_n"],
                 "prefill_tok_s", round(st.median(x["prompt_per_second"] for x in t), 1),
                 "gen_tok_s", round(st.median(x["predicted_per_second"] for x in t), 1))
   EOF
   ```

2. In a second terminal, watch the cards:

   ```bash
   nvidia-smi --query-gpu=index,pstate,clocks.gr,clocks.mem,utilization.gpu,power.draw,temperature.gpu,clocks_throttle_reasons.active --format=csv -l 1
   ```

3. Run the benchmark on each worker and save the output:

   ```bash
   sudo python3 /root/bench-worker.py a 2000
   sudo python3 /root/bench-worker.py b 2000
   ```

   `new` is ordinary generation. `echo` copies existing code, which is the case step 6 is meant to speed up. To see how speed changes with long prompts, repeat with a larger size such as `20000`.

4. Capture the current state:

   ```bash
   for w in a b; do
     systemctl cat ocs-llama-$w | grep -n ExecStart
     sudo journalctl -u ocs-llama-$w --no-pager | grep -iE 'pipeline parallel|compute pp|retrying|flash.attn|failed to allocate|full prompt|checkpoint' | tail -25
   done
   /opt/llama.cpp/bin/llama-server --version
   /opt/llama.cpp/bin/llama-server --help | grep -E -- '--spec-type|--cache-ram|--cache-reuse|--ubatch-size|--threads '
   free -h; swapon --show; vmstat 1 5
   nvidia-smi --query-gpu=index,memory.used,memory.total --format=csv
   ```

5. Use what you found to choose the next steps:

   | If you see | It means | Do this |
   |---|---|---|
   | `retrying without pipeline parallelism`, or a compute buffer failure | Prefill has lost its multi-GPU speedup | [Step 3](#3-restore-pipeline-parallelism) |
   | Swap in use, or very little free RAM | Host memory is slowing things down | [Step 5](#5-tune-the-prompt-cache) |
   | `full prompt` re-processing on every turn | The prompt cache isn't being reused | [Step 5](#5-tune-the-prompt-cache) |
   | Memory clock well below about 3800 MHz, or an active throttle reason | The GPU itself is limiting generation | Fix cooling or power first. Clock settings on a headless GeForce are awkward, and no step here covers them |
   | `Flash Attention` shown as disabled on Worker B | `--flash-attn auto` turned it off | Try `on` in Worker B's unit and compare |
   | A flag missing from `--help` | This build doesn't have it | Skip the step that uses it |

### 2. Add a place for extra flags

The Rig 1 units have no `$LLAMA_EXTRA_ARGS` hook, unlike [Rig 2's](../../infra/rig2/ocs-llama.service). Add one:

```bash
for w in a b; do
  sudo cp /etc/systemd/system/ocs-llama-$w.service /root/ocs-llama-$w.service.bak
  sudo sed -i 's|^  --warmup$|  --warmup \\\n  $LLAMA_EXTRA_ARGS|' /etc/systemd/system/ocs-llama-$w.service
done
sudo systemctl daemon-reload
systemctl cat ocs-llama-a | grep -A1 -- --warmup
```

The last command should print `--warmup \` and then `$LLAMA_EXTRA_ARGS`. Keep the variable unbraced: systemd splits `$VAR` into separate arguments, but passes `${VAR}` as one.

For each test in steps 3–7, follow this loop. It shows Worker A on port 8081. For Worker B, use `worker-b.env`, `ocs-llama-b`, port 8082, and `b`.

```bash
sudo nano /etc/ocs-intelligence/worker-a.env   # add or edit LLAMA_EXTRA_ARGS or CONTEXT_SIZE
sudo systemctl restart ocs-llama-a
curl -s http://127.0.0.1:8081/health           # repeat until it reports ok
sudo python3 /root/bench-worker.py a 2000
```

Change one thing at a time. Keep a change only if the median improves by at least 5% and the log shows no allocation errors.

### 3. Restore pipeline parallelism

Do this only if step 1 showed the fallback. An [older Worker A setup](../archive/worker-a-context-window.md) hit it at startup when context filled the cards' VRAM.

Lower `CONTEXT_SIZE` one value at a time, until the log shows pipeline parallelism enabled and the `retrying` line is gone. Current values: [configuration](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env).

| Worker | Try in order |
|---|---|
| A (1 slot) | `131072`, `98304`, `65536` |
| B (2 slots) | `196608`, `131072` |

Context size only changes memory use, so this helps speed by freeing VRAM. The cost is that longer prompts get rejected, and each of Worker B's slots gets half its total. Check what your coding clients actually send before going low, and lower their `maxInputTokens` to match ([using the API](../guides/using-the-api.md)).

### 4. Increase the prefill batch size

Do this only if the cards have VRAM to spare. It should raise `prefill_tok_s` and leave `gen_tok_s` alone.

```bash
LLAMA_EXTRA_ARGS=-ub 1024
```

If that helps and VRAM still has room, try `-ub 2048 -b 2048`. Reject a value if you see allocation errors or the pipeline fallback returns.

### 5. Tune the prompt cache

Coding agents resend a long prefix on every turn, so this affects them most. The upstream default lets each worker keep up to 8 GB of prompt states in host RAM, which is too much for two workers on this rig. Add these flags to whatever you kept from the earlier steps:

```bash
LLAMA_EXTRA_ARGS=--cache-ram 2048 --cache-reuse 256
```

The normal benchmark turns caching off, so use cache mode here:

```bash
sudo python3 /root/bench-worker.py a 20000 cache
```

| Line | Good result |
|---|---|
| `A repeat` | Few `prompt_tokens`, and `prompt_ms` far below `A cold`. Otherwise the cache isn't being reused |
| `A after B` | Below `A cold`. `B cold` evicted A from Worker A's only slot, so this measures restoring from RAM |

Then repeat on Worker A with `--cache-ram 0`. Restoring a large cached state crosses the PCIe ×1 risers, so it can cost more than prefilling again when students take turns. Keep whichever gives the lower `A after B`. Worker B has two slots, so B may land in the other slot and this eviction test tells you less there.

### 6. Try speculative decoding

This needs no extra model, and it suits code rewrites and edits, which repeat text already in the prompt. Add to what you kept:

```bash
LLAMA_EXTRA_ARGS=--spec-type ngram-mod --spec-ngram-size-n 24 --draft-min 48 --draft-max 64
```

`echo` should jump. Keep this only if `new` drops by less than about 5%, because wasted drafts slow normal generation.

### 7. Test CPU threads

Do this only if `top` shows the CPU pinned during generation.

```bash
LLAMA_EXTRA_ARGS=-t 1 -tb 1
```

## Leave these alone

- **The 4 + 4 GPU split.** Moving cards adds no speed per request, and neither model has room for a second copy on the cards left over.
- **Worker A's `--parallel 1`.** A second slot might raise total throughput, but it would slow each request and split the context. The gateway's [in-flight limits](../architecture/gateway.md) would have to change with it.
- **NCCL.** As far as we know, layer split doesn't use it, and the speeds above show hop count isn't the limit. This hasn't been tested ([open issue](../status.md#open-issue-worker-a-is-slower-than-baseline)).
- **`GGML_CUDA_P2P`.** Keep it unset ([why](../architecture/workers.md#flags-that-matter)).

## Check it worked

1. Run `sudo python3 /root/bench-worker.py a 2000` and the same for `b`. The numbers should match your best runs.
2. Confirm both workers and the orchestrator are up:

   ```bash
   systemctl is-active ocs-llama-a ocs-llama-b ocs-orchestrator
   curl -s http://127.0.0.1:9000/readyz
   ```

3. From your own machine, send one real request through the public path: `./scripts/request.sh "Reply with exactly: ok"`.
4. Record the result:
   - Save the before and after numbers in a new dated file under [`evidence/`](../../evidence/evidence.md).
   - Copy the final settings into [`infra/rig/`](../../infra/rig/) and the [configuration reference](../reference/configuration.md#workers-rig-etcocs-intelligenceworker-env).
   - Update [status](../status.md).
   - Log the work in the [pending playbook](../../evidence/pending-playbook.md).

## If something goes wrong

| Symptom | Likely cause | Fix |
|---|---|---|
| Worker crash-loops after a change | A flag this build doesn't accept, or VRAM ran out | Read `journalctl -u ocs-llama-a -n 50`, then remove the last change |
| `exceed_context_size_error` for real requests | `CONTEXT_SIZE` went too low | Raise it one value and retune |
| Benchmark hangs | A student request holds the slot, or the worker is still loading | Check `curl -s -H "Authorization: Bearer $KEY" http://127.0.0.1:8081/slots` and wait |
| Numbers vary widely between runs | Other traffic, or the cards are throttling | Rerun when the service is idle, and watch the `nvidia-smi` terminal |

To roll back everything:

```bash
for w in a b; do
  sudo cp /root/ocs-llama-$w.service.bak /etc/systemd/system/ocs-llama-$w.service
done
sudo systemctl daemon-reload
# Remove LLAMA_EXTRA_ARGS from both env files and restore their CONTEXT_SIZE, then:
sudo systemctl restart ocs-llama-a ocs-llama-b
```

## Related

- [Reducing prefill time and TTFT](../architecture/prefill-and-ttft.md)
- [Workers](../architecture/workers.md)
- [Benchmarks](../testing/benchmarks.md) measure through the public API, including the network and the gateway
