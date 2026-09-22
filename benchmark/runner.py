"""Run the benchmark and aggregate medians.

Queued samples (gateway ': queued' comments) stay in the raw repeats and are
left out of the GPU median. Concurrency is one request at a time.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmark.metrics import Chunk, Sample, measure, parse_sse_line
from benchmark.models import TOP_P, MODELS, ModelSpec
from benchmark.workloads import WORKLOADS, Workload, build_prompt, max_output_tokens, skip_reason

METHODOLOGY_URL = "https://artificialanalysis.ai/methodology/performance-benchmarking"
REQUEST_TIMEOUT_S = 1800.0

MEDIAN_FIELDS = (
    "ttft_s",
    "time_to_first_answer_token_s",
    "output_tokens_per_second",
    "mean_inter_token_latency_s",
    "inter_chunk_latency_p50_s",
    "inter_chunk_latency_p95_s",
    "response_time_100_output_tokens_s",
    "native_predicted_per_second",
)


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def median(values: list[float]) -> float | None:
    xs = sorted(values)
    if not xs:
        return None
    mid = len(xs) // 2
    if len(xs) % 2:
        return xs[mid]
    return (xs[mid - 1] + xs[mid]) / 2


def aggregate(samples: list[dict]) -> dict:
    """Median of samples that did not wait in the gateway queue and did not error."""
    usable = [
        sample
        for sample in samples
        if not sample.get("includes_queue") and not sample.get("error")
    ]
    out: dict = {
        "samples": len(samples),
        "used": len(usable),
        "excluded_queue": sum(1 for sample in samples if sample.get("includes_queue")),
        "errors": sum(1 for sample in samples if sample.get("error")),
    }
    for field in MEDIAN_FIELDS:
        nums = [sample[field] for sample in usable if sample.get(field) is not None]
        out[field] = median(nums)
    return out


def sample_record(
    *,
    repeat: int,
    prompt_tokens: int,
    max_tokens: int,
    sample: Sample,
) -> dict:
    row = {
        "repeat": repeat,
        "prompt_tokens": prompt_tokens,
        "max_tokens": max_tokens,
    }
    row.update(sample.as_dict())
    return row


def run_benchmark(
    *,
    models: list[ModelSpec],
    repeats: int,
    max_output_tokens_override: int | None,
    stream_fn,
    encode,
    workloads: tuple[Workload, ...] = WORKLOADS,
) -> dict:
    if repeats < 1:
        raise ValueError("--repeats must be at least 1")
    model_rows = []
    for spec in models:
        workloads_out = []
        for workload in workloads:
            limit = max_output_tokens(workload, max_output_tokens_override)
            reason = skip_reason(workload, spec, limit)
            if reason is not None:
                workloads_out.append(
                    {
                        "name": workload.name,
                        "input_tokens": workload.input_tokens,
                        "max_tokens": limit,
                        "status": "skipped",
                        "skipped_reason": reason,
                    }
                )
                continue
            samples = []
            for repeat in range(repeats):
                prompt = build_prompt(workload, repeat, encode)
                prompt_tokens = len(encode(prompt))
                try:
                    chunks = stream_fn(spec, prompt, limit)
                    measured = measure(chunks, encode)
                    samples.append(
                        sample_record(
                            repeat=repeat,
                            prompt_tokens=prompt_tokens,
                            max_tokens=limit,
                            sample=measured,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 — recorded, other repeats continue
                    samples.append(
                        {
                            "repeat": repeat,
                            "prompt_tokens": prompt_tokens,
                            "max_tokens": limit,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )
            usable = [s for s in samples if not s.get("includes_queue") and not s.get("error")]
            workloads_out.append(
                {
                    "name": workload.name,
                    "input_tokens": workload.input_tokens,
                    "max_tokens": limit,
                    "status": "measured" if usable else "error",
                    "repeats": samples,
                    "median": aggregate(samples),
                }
            )
        model_rows.append(
            {
                "model": spec.model_id,
                "context": spec.context,
                "temperature": spec.temperature,
                "top_p": TOP_P,
                "reasoning": spec.reasoning,
                "intelligence_index": spec.intelligence,
                "intelligence_note": spec.intelligence_note,
                "workloads": workloads_out,
            }
        )
    return {
        "created": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "source": METHODOLOGY_URL,
            "version": "2.2",
            "tokenizer": "o200k_base",
            "concurrency": 1,
            "repeats": repeats,
        },
        "models": model_rows,
    }


def write_results(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def openai_stream(base_url: str, api_key: str):
    """Stream one completion with the official OpenAI client. Returns Chunks."""
    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=api_key, timeout=REQUEST_TIMEOUT_S)

    def stream_fn(spec: ModelSpec, prompt: str, max_tokens: int) -> list[Chunk]:
        t0 = time.monotonic()
        chunks: list[Chunk] = []
        with client.chat.completions.with_streaming_response.create(
            model=spec.model_id,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=spec.temperature,
            top_p=TOP_P,
            stream=True,
        ) as response:
            if response.status_code >= 400:
                body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HTTP {response.status_code}: {body[:500]}")
            for raw in response.iter_lines():
                if isinstance(raw, bytes):
                    line = raw.decode("utf-8", errors="replace")
                else:
                    line = raw
                parsed = parse_sse_line(line, time.monotonic() - t0)
                if parsed is not None:
                    chunks.append(parsed)
        return chunks

    return stream_fn


def default_encode():
    import tiktoken

    enc = tiktoken.get_encoding("o200k_base")
    return enc.encode
