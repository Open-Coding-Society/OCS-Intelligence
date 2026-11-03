---
date: 2026-11-03
---

# Rig 1 speed tuning (2026-11-03)

Run over NetBird SSH (`root@ocs-intelligence-rig`, `100.75.123.203`) from about 10:10 to 11:32 PST, following [the tuning guide](../../docs/operations/tune-rig1-speed.md). llama.cpp `0.4.1-dev`, commit `972d231`. Benchmarks call the workers directly. This is a record: don't edit it. The operator asked to stop early, so some steps weren't run (see [Not tested](#not-tested)).

## What changed on the rig

| Change | Where |
|---|---|
| Added `$LLAMA_EXTRA_ARGS` after `--warmup` | `/etc/systemd/system/ocs-llama-{a,b}.service` (old copies: `/root/ocs-llama-{a,b}.service.bak`) |
| Worker A: `LLAMA_EXTRA_ARGS=--cache-ram 4096 --spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64` | `/etc/ocs-intelligence/worker-a.env` (old copy: `/root/worker-a.env.bak`) |
| Worker B: `LLAMA_EXTRA_ARGS=--cache-ram 4096` | `/etc/ocs-intelligence/worker-b.env` (old copy: `/root/worker-b.env.bak`) |
| Left on the rig | `/root/bench-worker.py`, `/root/bench-cache-wall.py`, `/root/bench-real.py`, `/root/tune-results.log` |

`CONTEXT_SIZE` ended where it started: 163840 (A) and 256000 (B). Worker A ran at 131072 for about 15 minutes during a test.

## Results

| Setting (Worker A) | Prompt tokens | Prefill tok/s | Gen tok/s | Verdict |
|---|---:|---:|---:|---|
| Baseline, `-ub 512` | 1,825 | 193.6 | 8.7 (`echo` 8.6) | Baseline |
| Baseline after a clean restart | 1,826 | 193.5 | 8.7 (`echo` 8.7) | No speed change |
| `-ub 1024`, ctx 163840 | 1,825 | 137.4 | 8.7 | Rejected. Log shows `retrying without pipeline parallelism` |
| `-ub 1024`, ctx 131072 | 1,823 | 138.1 | 8.7 | Rejected. No fallback line, and just as slow |
| `-ub 512` | 7,823 | 335.2 | 8.3 | Baseline at this size |
| `-ub 1024`, ctx 131072 | 7,825 | 286.2 | 8.6 | Rejected |
| `ngram-mod` speculative decoding | 1,824 | 193.1 | `new` 12.8, `echo` 37.2 | **Kept** |

`new` rose because the benchmark's prompt is repetitive. It doesn't show normal generation speeding up. Free generation on varied prompts, with temperature 0.7 and 200 tokens, was **8.83 tok/s with speculation and 8.75 without**. Those short prompts produced no drafts at all, so this test shows that having it on costs nothing when nothing matches. It doesn't measure wasted drafts when a match is partly wrong. On the repetitive runs, draft acceptance was 0.98–1.00.

**Prompt cache, Worker A, 20k tokens** (`bench-cache-wall.py`; wall-clock time includes 16 generated tokens):

| `--cache-ram` | A cold | A repeat | A after B | B after A | RSS after |
|---|---:|---:|---:|---:|---:|
| 8192 (default) | 65.8 s | 3.7 s | 19.3 s | 19.3 s | 7.4 GB |
| 2048 | 59.3 s | 3.7 s | 66.0 s | 66.2 s | 3.1 GB |
| **4096 (kept)** | 59.4 s | 3.7 s | 19.4 s | 19.3 s | 3.2 GB |

A state of this size takes 1,688.6 MiB (log: `removing oldest entry (size = 1688.645 MiB)`), so 2 GB holds only one. For a restore, `prompt_ms` reported about 1.9 s while the request took 19.3 s, so it leaves out the restore. `--cache-reuse 256` logged `cache_reuse is not supported by this context, it will be disabled`, so it wasn't kept. `--cache-ram 0` wasn't run: the 2048 row already shows what a cache miss costs.

**Worker B** (`gemma4:26b`, 1.9k tokens): baseline 436.5 tok/s prefill and 27.5 tok/s generation. After `--cache-ram 4096`, 442.3 and 27.4, so no regression. A restore at this size took 3.4 s against 6.6–6.8 s cold.

## Host memory

The kernel's OOM killer stopped `llama-server` 8 times:

```text
Oct 20 09:49:01 Killed process 285308 (llama-server) anon-rss:11306312kB
Oct 20 12:18:06 Killed process 347469 (llama-server) anon-rss:11732900kB
Oct 20 17:50:56 Killed process 158284 (llama-server) anon-rss:7541128kB
Oct 20 18:58:05 Killed process 354098 (llama-server) anon-rss:12570172kB
Oct 24 12:54:03 Killed process 371898 (llama-server) anon-rss:12636652kB
Oct 27 10:33:11 Killed process 623309 (llama-server) anon-rss:11578904kB
Oct 30 13:44:41 Killed process 368697 (llama-server) anon-rss:4984148kB
Nov 02 18:26:00 Killed process 811977 (llama-server) anon-rss:7198400kB
```

The units logged `Failed with result 'oom-kill'` 2 times for Worker A and 5 times for Worker B since 2026-10-20. At 10:10 the rig had 10 GiB of RAM used and 2.5 GiB of swap used. Restarting Worker A alone took used RAM from 11 GiB to 3.5 GiB. At the end of the run, 6.8 GiB was used, with 8.7 GiB available. The link between the default cache and the kills is an inference from these numbers: the new cap hasn't yet been through a busy class.

## Other observations

- **Pipeline parallelism:** the journal has no line that confirms it's on. The only sign is the `retrying without` warning when it fails, which appeared only with `-ub 1024` at ctx 163840 in this run.
- **GPU clocks:** memory reached 3802 MHz on every active card. Worker A's cards intermittently reported `0x4` (software power cap) at about 190 W, and Worker B's never did. The hottest card reached 72 °C. The effect on speed wasn't tested.
- **Real prompts seen since 2026-10-20** (from `prompt eval time` lines): Worker A median 1,348, p90 4,766, max 25,358 tokens over 102 requests. Worker B median 404, p90 3,864, max 101,071 over 216 requests.
- **Traffic:** one real request reached Worker A (10:40:17, HTTP 200), about 3 seconds before a benchmark started. No restart hit a request in progress: after that request, each restart first checked that the slots were idle and no request had arrived in the last 3 minutes. Restarts before it weren't guarded that way, but the orchestrator journal shows no `POST` from 09:50 until that request.

## Not tested

`-ub` below 512 on Worker A. `-ub` and speculative decoding on Worker B. CPU threads (step 7; one `top` sample during generation showed 13% idle). `--flash-attn on` on Worker B: the log doesn't say what `auto` chose. The speculative gain on real agent traffic.

## Check it worked

```text
systemctl is-active ocs-llama-a ocs-llama-b ocs-orchestrator  ->  active active active
curl -s http://127.0.0.1:9000/readyz                          ->  {"status":"ready"}
./scripts/request.sh -m qwen3.8:27b "Reply with exactly: ok"  ->  content "ok"
./scripts/request.sh -m gemma4:26b  "Reply with exactly: ok"  ->  content "ok"
```

## Wall-clock cache script

```python
#!/usr/bin/env python3
"""Usage: bench-cache-wall.py a|b PROMPT_SIZE. Like bench-worker.py cache mode, plus wall-clock time per request."""
import json, re, sys, time, urllib.request as u, uuid
w, size = sys.argv[1], int(sys.argv[2])
port = {"a": 8081, "b": 8082}[w]
key = re.search(r"^WORKER_API_KEY=(.*)$", open(f"/etc/ocs-intelligence/worker-{w}.env").read(), re.M).group(1)
def code():
    body = "".join(f"def f{i}(x):\n    return x * {i} + {i % 7}\n" for i in range(size // 20))
    return f"# {uuid.uuid4()}\n{body}"
def run(prompt):
    req = u.Request(f"http://127.0.0.1:{port}/completion", json.dumps({"prompt": prompt, "n_predict": 16, "temperature": 0, "cache_prompt": True, "ignore_eos": True}).encode(),
                    {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time(); t = json.load(u.urlopen(req, timeout=1800))["timings"]
    return t, time.time() - t0
a, b = code(), code()
for label, p in [("A cold", a), ("A repeat", a), ("B cold", b), ("A after B", a), ("B after A", b)]:
    t, wall = run(p)
    print(label, "prompt_tokens", t["prompt_n"], "prompt_ms", round(t["prompt_ms"]), "gen_ms", round(t["predicted_ms"]), "wall_ms", round(wall * 1000))
```

## Varied-prompt script

```python
#!/usr/bin/env python3
"""Usage: bench-real.py a|b. Free generation from varied prompts at temperature 0.7, where speculative drafts rarely match."""
import json, re, statistics as st, sys, urllib.request as u
w = sys.argv[1]
port = {"a": 8081, "b": 8082}[w]
key = re.search(r"^WORKER_API_KEY=(.*)$", open(f"/etc/ocs-intelligence/worker-{w}.env").read(), re.M).group(1)
PROMPTS = [
    "Write a Python class implementing an LRU cache with type hints and a short docstring for each method.\n\n",
    "Explain, for a high school student, why binary search needs a sorted list and what its running time is.\n\n",
    "Write a JavaScript function that debounces another function, then describe two bugs people often hit with debouncing.\n\n",
    "Compare TCP and UDP for a multiplayer game, and say which you would choose for player movement and why.\n\n",
]
speeds = []
for i, p in enumerate(PROMPTS):
    body = {"prompt": p, "n_predict": 200, "temperature": 0.7, "seed": 42 + i, "cache_prompt": False, "ignore_eos": True}
    req = u.Request(f"http://127.0.0.1:{port}/completion", json.dumps(body).encode(), {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t = json.load(u.urlopen(req, timeout=900))["timings"]
    speeds.append(t["predicted_per_second"])
    print("prompt", i, "gen_tok_s", round(t["predicted_per_second"], 2), "draft", t.get("draft_n", 0), "accepted", t.get("draft_n_accepted", 0))
print("median_gen_tok_s", round(st.median(speeds), 2))
```

## Raw log

`/root/tune-results.log`, as written during the run. Its `new`/`echo` lines come from `bench-worker.py`, and its `gpu` lines come from `nvidia-smi` samples taken while each card was above 10% utilization.

```text
### 10:11:17 base-a2k worker=a size=2000
new prompt_tokens 1825 prefill_tok_s 193.6 gen_tok_s 8.7
echo prompt_tokens 1825 prefill_tok_s 194.5 gen_tok_s 8.6
gpu 1 samples 96 memclk 3802 gr_min 1607 util_max 100 mem 6949 W_max 189.01 T_max 38 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 97 memclk 3802 gr_min 1759 util_max 100 mem 7689 W_max 194.55 T_max 46 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 97 memclk 3802 gr_min 1607 util_max 100 mem 7205 W_max 190.97 T_max 52 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 103 memclk 3802 gr_min 1607 util_max 100 mem 7367 W_max 188.44 T_max 38 throttle ['0x0000000000000000']
### 10:15:27 base-b2k worker=b size=2000
new prompt_tokens 1925 prefill_tok_s 436.5 gen_tok_s 27.5
echo prompt_tokens 1925 prefill_tok_s 440.3 gen_tok_s 27.3
gpu 0 samples 31 memclk 3802 gr_min 1607 util_max 96 mem 6063 W_max 154.33 T_max 32 throttle ['0x0000000000000000']
gpu 2 samples 34 memclk 3802 gr_min 2012 util_max 76 mem 5883 W_max 165.33 T_max 31 throttle ['0x0000000000000000']
gpu 4 samples 32 memclk 3802 gr_min 1607 util_max 100 mem 6063 W_max 152.44 T_max 30 throttle ['0x0000000000000000']
gpu 6 samples 37 memclk 3802 gr_min 1607 util_max 100 mem 7055 W_max 160.33 T_max 31 throttle ['0x0000000000000000']
--- a extra='' ctx=163840 ready after 124s health={"status":"ok"} restarts=0
2.00.840.776 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 10:20:34 fresh-a2k worker=a size=2000
new prompt_tokens 1826 prefill_tok_s 193.5 gen_tok_s 8.7
echo prompt_tokens 1826 prefill_tok_s 193.9 gen_tok_s 8.7
gpu 1 samples 96 memclk 3802 gr_min 1607 util_max 100 mem 6949 W_max 192.76 T_max 39 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 98 memclk 3802 gr_min 1961 util_max 100 mem 7689 W_max 189.05 T_max 50 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 95 memclk 3802 gr_min 1607 util_max 100 mem 7205 W_max 189.63 T_max 53 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 99 memclk 3802 gr_min 1607 util_max 100 mem 7367 W_max 183.1 T_max 39 throttle ['0x0000000000000000', '0x0000000000000004']
--- a extra='-ub 1024' ctx=163840 ready after 117s health={"status":"ok"} restarts=0
1.53.304.536 E ggml_gallocr_reserve_n_impl: failed to allocate CUDA0 buffer of size 1682047488
1.53.304.537 E graph_reserve: failed to allocate compute buffers
1.53.304.548 W sched_reserve: compute buffer allocation failed, retrying without pipeline parallelism
1.54.139.934 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6687;2, 5883;3, 7427;4, 6063;5, 6943;6, 7055;7, 7105;### 10:29:01 a-ub1024 worker=a size=2000
new prompt_tokens 1825 prefill_tok_s 137.4 gen_tok_s 8.7
echo prompt_tokens 1825 prefill_tok_s 137.8 gen_tok_s 8.7
gpu 1 samples 99 memclk 3802 gr_min 1607 util_max 100 mem 6735 W_max 189.5 T_max 40 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 99 memclk 3802 gr_min 1936 util_max 100 mem 7475 W_max 194.6 T_max 48 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 100 memclk 3802 gr_min 1607 util_max 100 mem 6991 W_max 187.22 T_max 55 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 98 memclk 3802 gr_min 1607 util_max 100 mem 7153 W_max 189.39 T_max 40 throttle ['0x0000000000000000', '0x0000000000000004']
--- a extra='-ub 1024' ctx=131072 ready after 115s health={"status":"ok"} restarts=0
1.52.899.124 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 131072, kv_unified = 'false'
0, 6063;1, 6961;2, 5883;3, 7701;4, 6063;5, 7217;6, 7055;7, 7379;### 10:35:42 a-ub1024-ctx131k worker=a size=2000
new prompt_tokens 1823 prefill_tok_s 138.1 gen_tok_s 8.7
echo prompt_tokens 1823 prefill_tok_s 138.2 gen_tok_s 8.7
gpu 1 samples 100 memclk 3802 gr_min 1607 util_max 100 mem 7009 W_max 196.51 T_max 40 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 97 memclk 3802 gr_min 1771 util_max 100 mem 7749 W_max 186.72 T_max 49 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 101 memclk 3802 gr_min 1607 util_max 100 mem 7265 W_max 195.67 T_max 55 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 99 memclk 3802 gr_min 1607 util_max 100 mem 7427 W_max 190.77 T_max 39 throttle ['0x0000000000000000', '0x0000000000000004']
### 10:40:20 a-ub1024-ctx131k-8k worker=a size=8000
new prompt_tokens 7825 prefill_tok_s 286.2 gen_tok_s 8.6
echo prompt_tokens 7825 prefill_tok_s 286.4 gen_tok_s 8.6
gpu 1 samples 166 memclk 3802 gr_min 1822 util_max 100 mem 7009 W_max 199.57 T_max 44 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 157 memclk 3802 gr_min 1771 util_max 100 mem 7749 W_max 201.22 T_max 58 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 166 memclk 3802 gr_min 1923 util_max 100 mem 7265 W_max 202.91 T_max 72 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 167 memclk 3802 gr_min 1949 util_max 100 mem 7427 W_max 198.94 T_max 44 throttle ['0x0000000000000000', '0x0000000000000004']
--- a extra='' ctx=163840 ready after 117s health={"status":"ok"} restarts=0
1.54.591.469 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 10:50:13 a-ub512-8k worker=a size=8000
new prompt_tokens 7823 prefill_tok_s 335.2 gen_tok_s 8.3
echo prompt_tokens 7823 prefill_tok_s 334.8 gen_tok_s 8.3
gpu 1 samples 137 memclk 3802 gr_min 1607 util_max 100 mem 6949 W_max 195.04 T_max 42 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 137 memclk 3802 gr_min 1936 util_max 100 mem 7689 W_max 193.86 T_max 57 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 139 memclk 3802 gr_min 1607 util_max 100 mem 7205 W_max 194.85 T_max 68 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 139 memclk 3802 gr_min 1771 util_max 100 mem 7367 W_max 191.73 T_max 44 throttle ['0x0000000000000000', '0x0000000000000004']
### 10:55:55 CACHE a-default worker=a size=20000
A cold prompt_tokens 19812 prompt_ms 55720
A repeat prompt_tokens 4 prompt_ms 1859
B cold prompt_tokens 19813 prompt_ms 55878
A after B prompt_tokens 4 prompt_ms 1888
rss=4.1G swap=0.17G avail=9166M
### 10:58:44 WALLCACHE a-default worker=a size=20000
A cold prompt_tokens 19813 prompt_ms 55836 gen_ms 1851 wall_ms 65830
A repeat prompt_tokens 4 prompt_ms 1843 gen_ms 1847 wall_ms 3705
B cold prompt_tokens 19814 prompt_ms 55905 gen_ms 1851 wall_ms 65910
A after B prompt_tokens 4 prompt_ms 1875 gen_ms 1850 wall_ms 19286
B after A prompt_tokens 4 prompt_ms 1875 gen_ms 1850 wall_ms 19286
rss=7.4G swap=0.17G avail=5815M
--- a extra='--cache-ram 2048 --cache-reuse 256' ctx=163840 ready after 117s health={"status":"ok"} restarts=0
1.54.167.011 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 11:03:52 WALLCACHE a-cram2048 worker=a size=20000
A cold prompt_tokens 19814 prompt_ms 57289 gen_ms 1884 wall_ms 59250
A repeat prompt_tokens 4 prompt_ms 1843 gen_ms 1848 wall_ms 3706
B cold prompt_tokens 19814 prompt_ms 55794 gen_ms 1852 wall_ms 66185
A after B prompt_tokens 19814 prompt_ms 55895 gen_ms 1849 wall_ms 66023
B after A prompt_tokens 19814 prompt_ms 55934 gen_ms 1851 wall_ms 66190
rss=3.1G swap=0.17G avail=10148M
--- a extra='--cache-ram 4096' ctx=163840 ready after 115s health={"status":"ok"} restarts=0
1.52.047.130 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 11:10:31 WALLCACHE a-cram4096 worker=a size=20000
A cold prompt_tokens 19817 prompt_ms 57384 gen_ms 1880 wall_ms 59360
A repeat prompt_tokens 4 prompt_ms 1842 gen_ms 1847 wall_ms 3704
B cold prompt_tokens 19814 prompt_ms 55837 gen_ms 1851 wall_ms 65819
A after B prompt_tokens 4 prompt_ms 1919 gen_ms 1851 wall_ms 19415
B after A prompt_tokens 4 prompt_ms 1895 gen_ms 1851 wall_ms 19299
rss=3.2G swap=0.18G avail=10161M
--- a extra='--cache-ram 4096 --spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64' ctx=163840 ready after 118s health={"status":"ok"} restarts=0
1.54.173.519 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 11:15:32 a-spec worker=a size=2000
new prompt_tokens 1824 prefill_tok_s 193.1 gen_tok_s 12.8
echo prompt_tokens 1824 prefill_tok_s 194.5 gen_tok_s 37.2
gpu 1 samples 45 memclk 3802 gr_min 1607 util_max 100 mem 6949 W_max 194.11 T_max 40 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 3 samples 51 memclk 3802 gr_min 1949 util_max 100 mem 7689 W_max 189.43 T_max 49 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 5 samples 46 memclk 3802 gr_min 1607 util_max 100 mem 7205 W_max 194.56 T_max 60 throttle ['0x0000000000000000', '0x0000000000000004']
gpu 7 samples 51 memclk 3802 gr_min 1607 util_max 100 mem 7367 W_max 196.87 T_max 41 throttle ['0x0000000000000000', '0x0000000000000004']
### 11:18:24 REAL a-spec worker=a
prompt 0 gen_tok_s 8.89 draft 0 accepted 0
prompt 1 gen_tok_s 8.79 draft 0 accepted 0
prompt 2 gen_tok_s 8.86 draft 0 accepted 0
prompt 3 gen_tok_s 8.76 draft 0 accepted 0
median_gen_tok_s 8.83
--- a extra='--cache-ram 4096' ctx=163840 ready after 117s health={"status":"ok"} restarts=0
1.53.139.354 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;### 11:22:03 REAL a-nospec worker=a
prompt 0 gen_tok_s 8.74 draft 0 accepted 0
prompt 1 gen_tok_s 8.75 draft 0 accepted 0
prompt 2 gen_tok_s 8.77 draft 0 accepted 0
prompt 3 gen_tok_s 8.72 draft 0 accepted 0
median_gen_tok_s 8.75
--- a extra='--cache-ram 4096 --spec-type ngram-mod --spec-ngram-mod-n-match 24 --spec-ngram-mod-n-min 48 --spec-ngram-mod-n-max 64' ctx=163840 ready after 119s health={"status":"ok"} restarts=0
1.56.253.270 I srv    load_model: initializing, n_slots = 1, n_ctx_slot = 163840, kv_unified = 'false'
0, 6063;1, 6925;2, 5883;3, 7665;4, 6063;5, 7181;6, 7055;7, 7343;--- b extra='--cache-ram 4096' ctx=256000 ready after 130s health={"status":"ok"} restarts=0
2.06.129.532 I srv    load_model: initializing, n_slots = 2, n_ctx_slot = 128000, kv_unified = 'false'
0, 6017;1, 6925;2, 5837;3, 7665;4, 6017;5, 7181;6, 7009;7, 7343;### 11:28:29 final-b2k worker=b size=2000
new prompt_tokens 1926 prefill_tok_s 442.3 gen_tok_s 27.4
echo prompt_tokens 1926 prefill_tok_s 445.0 gen_tok_s 27.4
gpu 0 samples 35 memclk 3802 gr_min 1607 util_max 96 mem 6063 W_max 113.76 T_max 34 throttle ['0x0000000000000000']
gpu 2 samples 34 memclk 3802 gr_min 2012 util_max 60 mem 5883 W_max 164.1 T_max 34 throttle ['0x0000000000000000']
gpu 4 samples 32 memclk 3802 gr_min 1607 util_max 96 mem 6063 W_max 114.54 T_max 31 throttle ['0x0000000000000000']
gpu 6 samples 35 memclk 3802 gr_min 2012 util_max 100 mem 7055 W_max 157.3 T_max 34 throttle ['0x0000000000000000']
### 11:29:53 WALLCACHE final-b worker=b size=2000
A cold prompt_tokens 1915 prompt_ms 4266 gen_ms 549 wall_ms 6574
A repeat prompt_tokens 1 prompt_ms 1172 gen_ms 544 wall_ms 1719
B cold prompt_tokens 1917 prompt_ms 4306 gen_ms 548 wall_ms 6818
A after B prompt_tokens 1 prompt_ms 1190 gen_ms 548 wall_ms 3416
B after A prompt_tokens 1 prompt_ms 1175 gen_ms 544 wall_ms 1723
rss=4.5G swap=0.19G avail=8882M
```
