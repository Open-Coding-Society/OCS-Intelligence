---
status: current
last_verified: 2026-09-29
---

# Benchmarks

How to measure speed on the live API and plot the speed vs intelligence chart. Code: [`benchmark/`](../../benchmark/). Checked against the code on 2026-09-29.

## Run it

```bash
python3 -m pip install -r benchmark/requirements.txt
python3 -m benchmark run --out benchmark/results/latest.json        # needs .env
python3 -m benchmark plot --results benchmark/results/latest.json --out benchmark/results/pareto.png
```

Options for `run`: `--repeats N` (default 5), `--max-output-tokens N`, `--models qwen2.5:0.5b qwen3.8:27b`.

`benchmark/results/` is gitignored. **To keep a run, copy the JSON and PNG into `evidence/benchmarks/YYYY-MM-DD-…`** and add a line to the [evidence log](../../evidence/evidence.md).

## What it measures

Streaming metrics based on the Artificial Analysis performance methodology ([`metrics.py`](../../benchmark/metrics.py)):

| Metric | Definition |
|---|---|
| Time to first token | From sending the request to the first reasoning **or** answer text |
| Time to first answer token | From sending the request to the first `content` text (after any reasoning) |
| Output speed | o200k_base tokens received after the first chunk ÷ time from that chunk to the last |
| Mean inter-token latency | 1 ÷ output speed |
| Inter-chunk latency p50 / p95 | Gaps between SSE chunks |
| Native speed | llama.cpp's own `predicted_per_second`, for comparison |

The requests go through the public API. A sample that got a gateway `: queued` comment is flagged `includes_queue`. It stays in the raw repeats but is **left out of the aggregates** (counted as `excluded_queue`). Benchmark when the class isn't using the service, or most samples will be excluded.

## Workloads

Prompts of 1k, 10k, and 100k input tokens (o200k_base), built from original filler text ([`workloads.py`](../../benchmark/workloads.py)). A workload is **skipped, not shortened**, when input + `max_tokens` exceeds the model's context (4096 for 27B, 8192 for 0.5B), so today only 1k runs.

## The chart

X is median output speed measured on our rig (1k input). Y is the **published** Artificial Analysis Intelligence Index for Qwen3.8 27B (score 28, published 2026-09-22). That score is their API evaluation, not a measurement of our Q4_K_M quant. Qwen2.5 0.5B has no published index. See [`models.py`](../../benchmark/models.py).

## Other speed tools

`llama-bench` is installed on the rig (`/opt/llama.cpp/bin/`). It measures raw decode speed without the network or queue, and it's the planned next step for [Worker A's slowness](../architecture/workers.md#performance).
