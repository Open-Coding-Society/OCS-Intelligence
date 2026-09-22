"""Streaming metrics aligned with Artificial Analysis performance methodology v2.2.

Output speed counts OpenAI o200k_base tokens received after the first token
chunk, divided by the time from that chunk to the last. Time to first token
is the send-relative time of the first reasoning or answer text. Mean
inter-token latency is the reciprocal of that output speed.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    """One SSE line, timestamped in seconds after the request was sent."""

    t: float
    comment: str | None = None
    delta: dict | None = None
    timings: dict | None = None


@dataclass
class Sample:
    includes_queue: bool
    ttft_s: float | None
    time_to_first_answer_token_s: float | None
    output_tokens_per_second: float | None
    tokens_after_first_chunk: int
    mean_inter_token_latency_s: float | None
    inter_chunk_latency_p50_s: float | None
    inter_chunk_latency_p95_s: float | None
    response_time_100_output_tokens_s: float | None
    native_predicted_per_second: float | None
    chunk_gaps_s: list[float] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "includes_queue": self.includes_queue,
            "ttft_s": self.ttft_s,
            "time_to_first_answer_token_s": self.time_to_first_answer_token_s,
            "output_tokens_per_second": self.output_tokens_per_second,
            "tokens_after_first_chunk": self.tokens_after_first_chunk,
            "mean_inter_token_latency_s": self.mean_inter_token_latency_s,
            "inter_chunk_latency_p50_s": self.inter_chunk_latency_p50_s,
            "inter_chunk_latency_p95_s": self.inter_chunk_latency_p95_s,
            "response_time_100_output_tokens_s": self.response_time_100_output_tokens_s,
            "native_predicted_per_second": self.native_predicted_per_second,
        }


def chunk_text(delta: dict | None) -> str:
    if not delta:
        return ""
    parts: list[str] = []
    reasoning = delta.get("reasoning_content")
    content = delta.get("content")
    if isinstance(reasoning, str) and reasoning:
        parts.append(reasoning)
    if isinstance(content, str) and content:
        parts.append(content)
    return "".join(parts)


def parse_sse_line(line: str, t: float) -> Chunk | None:
    """Parse one SSE line. Comments such as ': queued' are kept."""
    text = line.strip()
    if not text:
        return None
    if text.startswith(":"):
        return Chunk(t=t, comment=text[1:].strip())
    if not text.startswith("data:"):
        return None
    data = text[len("data:") :].strip()
    if data == "[DONE]":
        return Chunk(t=t, comment="DONE")
    payload = json.loads(data)
    choices = payload.get("choices") or []
    delta = {}
    if choices and isinstance(choices[0], dict):
        delta = choices[0].get("delta") or {}
    timings = payload.get("timings")
    if timings is None and choices and isinstance(choices[0], dict):
        timings = choices[0].get("timings")
    return Chunk(t=t, delta=delta, timings=timings if isinstance(timings, dict) else None)


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return ordered[int(k)]
    return ordered[lo] * (hi - k) + ordered[hi] * (k - lo)


def measure(chunks: list[Chunk], encode) -> Sample:
    """Measure one streamed completion.

    `encode` maps text to a sequence of token ids (tiktoken o200k_base).
    Tokens inside the first text chunk are excluded from output speed, matching
    "tokens received after the first chunk."
    """
    includes_queue = any(
        chunk.comment is not None and "queued" in chunk.comment for chunk in chunks
    )
    token_chunks: list[tuple[Chunk, str]] = []
    for chunk in chunks:
        text = chunk_text(chunk.delta)
        if text:
            token_chunks.append((chunk, text))

    native = None
    for chunk in chunks:
        if chunk.timings and chunk.timings.get("predicted_per_second") is not None:
            native = float(chunk.timings["predicted_per_second"])

    if not token_chunks:
        return Sample(
            includes_queue=includes_queue,
            ttft_s=None,
            time_to_first_answer_token_s=None,
            output_tokens_per_second=None,
            tokens_after_first_chunk=0,
            mean_inter_token_latency_s=None,
            inter_chunk_latency_p50_s=None,
            inter_chunk_latency_p95_s=None,
            response_time_100_output_tokens_s=None,
            native_predicted_per_second=native,
        )

    ttft = token_chunks[0][0].t
    answer_t = None
    for chunk, _text in token_chunks:
        content = (chunk.delta or {}).get("content")
        if isinstance(content, str) and content:
            answer_t = chunk.t
            break

    counts = [len(encode(text)) for _chunk, text in token_chunks]
    tokens_after = sum(counts[1:])
    t_last = token_chunks[-1][0].t
    elapsed = t_last - ttft
    speed = None
    mean_itl = None
    if tokens_after > 0 and elapsed > 0:
        speed = tokens_after / elapsed
        mean_itl = elapsed / tokens_after

    gaps = [
        token_chunks[i][0].t - token_chunks[i - 1][0].t
        for i in range(1, len(token_chunks))
    ]
    response_100 = None
    if speed is not None and speed > 0 and ttft is not None:
        # First token arrives at TTFT; the next 99 take 99 / output speed.
        response_100 = ttft + 99.0 / speed

    return Sample(
        includes_queue=includes_queue,
        ttft_s=ttft,
        time_to_first_answer_token_s=answer_t,
        output_tokens_per_second=speed,
        tokens_after_first_chunk=tokens_after,
        mean_inter_token_latency_s=mean_itl,
        inter_chunk_latency_p50_s=percentile(gaps, 50),
        inter_chunk_latency_p95_s=percentile(gaps, 95),
        response_time_100_output_tokens_s=response_100,
        native_predicted_per_second=native,
        chunk_gaps_s=gaps,
    )
