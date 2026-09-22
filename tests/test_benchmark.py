"""Offline tests for the GPU benchmark. No network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmark.metrics import Chunk, measure, parse_sse_line
from benchmark.models import MODELS, model_by_id
from benchmark.pareto import CAPTION, Point, pareto_frontier, points_from_results, render
from benchmark.runner import aggregate, run_benchmark
from benchmark.workloads import WORKLOADS, Workload, build_prompt, skip_reason


def encode_words(text: str) -> list[str]:
    return text.split()


def test_ttft_ignores_empty_role_and_counts_reasoning_first():
    chunks = [
        Chunk(t=0.2, delta={"role": "assistant", "content": None}),
        Chunk(t=1.0, delta={"reasoning_content": "think hard"}),
        Chunk(t=1.5, delta={"reasoning_content": "now"}),
        Chunk(t=3.0, delta={"content": "answer here"}),
        Chunk(t=3.1, delta={}, timings={"predicted_per_second": 9.5}),
    ]
    sample = measure(chunks, encode_words)
    assert sample.ttft_s == 1.0
    assert sample.time_to_first_answer_token_s == 3.0
    assert sample.tokens_after_first_chunk == 3  # "now" + "answer here"
    assert sample.output_tokens_per_second == 1.5
    assert sample.mean_inter_token_latency_s == 2.0 / 3.0
    assert sample.inter_chunk_latency_p50_s == 1.0
    assert sample.inter_chunk_latency_p95_s == pytest.approx(1.45)
    assert sample.response_time_100_output_tokens_s == 1.0 + 99.0 / 1.5
    assert sample.native_predicted_per_second == 9.5
    assert sample.includes_queue is False


def test_queued_comment_is_flagged_and_not_a_token():
    chunks = [
        Chunk(t=0.05, comment="queued"),
        Chunk(t=1.0, delta={"content": "hello there"}),
        Chunk(t=2.0, delta={"content": "friend"}),
    ]
    sample = measure(chunks, encode_words)
    assert sample.includes_queue is True
    assert sample.ttft_s == 1.0
    assert sample.tokens_after_first_chunk == 1
    assert sample.output_tokens_per_second == 1.0


def test_usage_shaped_sse_reasoning_stream():
    import tiktoken

    encode = tiktoken.get_encoding("o200k_base").encode
    lines = [
        (
            0.4,
            'data: {"choices":[{"finish_reason":null,"index":0,"delta":{"role":"assistant","content":null}}],'
            '"object":"chat.completion.chunk"}',
        ),
        (
            1.0,
            'data: {"choices":[{"finish_reason":null,"index":0,"delta":{"reasoning_content":"We need"}}],'
            '"object":"chat.completion.chunk"}',
        ),
        (
            1.2,
            'data: {"choices":[{"finish_reason":null,"index":0,"delta":{"reasoning_content":" answer"}}],'
            '"object":"chat.completion.chunk"}',
        ),
        (
            2.0,
            'data: {"choices":[{"finish_reason":null,"index":0,"delta":{"content":"Quick"}}],'
            '"object":"chat.completion.chunk"}',
        ),
        (
            2.2,
            'data: {"choices":[{"finish_reason":null,"index":0,"delta":{"content":" sort"}}],'
            '"object":"chat.completion.chunk"}',
        ),
        (
            2.3,
            'data: {"choices":[{"finish_reason":"stop","index":0,"delta":{}}],'
            '"timings":{"predicted_n":28,"predicted_per_second":8.831}}',
        ),
        (2.4, "data: [DONE]"),
    ]
    chunks = []
    for t, line in lines:
        parsed = parse_sse_line(line, t)
        assert parsed is not None
        chunks.append(parsed)
    chunks.insert(0, parse_sse_line(": queued", 0.1))

    sample = measure(chunks, encode)
    assert sample.includes_queue is True
    assert sample.ttft_s == 1.0
    assert sample.time_to_first_answer_token_s == 2.0
    expected_after = len(encode(" answer")) + len(encode("Quick")) + len(encode(" sort"))
    assert sample.tokens_after_first_chunk == expected_after
    assert sample.output_tokens_per_second == expected_after / (2.2 - 1.0)
    assert sample.native_predicted_per_second == 8.831


def test_single_chunk_has_no_output_speed():
    sample = measure([Chunk(t=0.5, delta={"content": "only"})], encode_words)
    assert sample.ttft_s == 0.5
    assert sample.output_tokens_per_second is None
    assert sample.tokens_after_first_chunk == 0


def test_context_skip_for_both_workers():
    for spec in MODELS:
        assert skip_reason(WORKLOADS[0], spec, 1000) is None
        reason_10 = skip_reason(WORKLOADS[1], spec, 1500)
        reason_100 = skip_reason(WORKLOADS[2], spec, 2000)
        assert reason_10 is not None and "exceeds context" in reason_10
        assert reason_100 is not None and "exceeds context" in reason_100
        assert str(spec.context) in reason_10


def test_runner_skips_long_workloads_and_medians_without_queue():
    calls: list[str] = []

    def stream_fn(spec, prompt, max_tokens):
        calls.append(spec.model_id)
        if prompt.startswith("Run 0."):
            return [
                Chunk(t=0.05, comment="queued"),
                Chunk(t=1.0, delta={"content": "aa bb"}),
                Chunk(t=2.0, delta={"content": "cc"}),
            ]
        if prompt.startswith("Run 1."):
            return [
                Chunk(t=1.0, delta={"content": "aa bb"}),
                Chunk(t=3.0, delta={"content": "cc dd"}),
            ]
        return [
            Chunk(t=2.0, delta={"content": "aa bb"}),
            Chunk(t=6.0, delta={"content": "cc dd"}),
        ]

    tiny = (Workload("1k", 64, 4),)
    payload = run_benchmark(
        models=[model_by_id("qwen2.5:0.5b")],
        repeats=3,
        max_output_tokens_override=None,
        stream_fn=stream_fn,
        encode=encode_words,
        workloads=tiny,
    )
    row = payload["models"][0]
    assert row["workloads"][0]["status"] == "measured"
    median = row["workloads"][0]["median"]
    assert median["excluded_queue"] == 1
    assert median["used"] == 2
    assert median["output_tokens_per_second"] == 0.75
    assert median["ttft_s"] == 1.5
    assert calls == ["qwen2.5:0.5b", "qwen2.5:0.5b", "qwen2.5:0.5b"]


def test_runner_does_not_call_the_model_for_skipped_shapes():
    calls: list[str] = []

    def stream_fn(spec, prompt, max_tokens):
        calls.append(f"{spec.model_id}:{max_tokens}")
        return [
            Chunk(t=0.0, delta={"content": "one two"}),
            Chunk(t=1.0, delta={"content": "three four"}),
        ]

    payload = run_benchmark(
        models=list(MODELS),
        repeats=1,
        max_output_tokens_override=None,
        stream_fn=stream_fn,
        encode=encode_words,
        workloads=WORKLOADS,
    )
    assert calls == ["qwen2.5:0.5b:1000", "qwen3.8:27b:1000"]
    for row in payload["models"]:
        by_name = {item["name"]: item for item in row["workloads"]}
        assert by_name["1k"]["status"] == "measured"
        assert by_name["10k"]["status"] == "skipped"
        assert by_name["100k"]["status"] == "skipped"
        assert "exceeds context" in by_name["10k"]["skipped_reason"]
        assert "skipped_reason" not in by_name["1k"]


def test_prompts_hit_the_token_target_and_differ_per_repeat():
    import tiktoken

    encode = tiktoken.get_encoding("o200k_base").encode
    workload = WORKLOADS[0]
    first = build_prompt(workload, 0, encode)
    second = build_prompt(workload, 1, encode)
    assert abs(len(encode(first)) - 1000) <= 1
    assert abs(len(encode(second)) - 1000) <= 1
    assert first != second


def test_pareto_line_keeps_the_two_undominated_points():
    slow = Point("slow-smart", 10, 40)
    fast = Point("fast", 90, 12)
    dominated = Point("dominated", 20, 12)
    line = pareto_frontier([fast, dominated, slow])
    assert [point.model_id for point in line] == ["slow-smart", "fast"]


def test_chart_omits_the_unscored_small_model(tmp_path: Path):
    results = {
        "models": [
            {
                "model": "qwen2.5:0.5b",
                "workloads": [
                    {
                        "name": "1k",
                        "status": "measured",
                        "median": {"output_tokens_per_second": 80},
                    }
                ],
            },
            {
                "model": "qwen3.8:27b",
                "workloads": [
                    {
                        "name": "1k",
                        "status": "measured",
                        "median": {"output_tokens_per_second": 9},
                    }
                ],
            },
        ]
    }
    points = points_from_results(results)
    assert [point.model_id for point in points] == ["qwen3.8:27b"]
    assert points[0].intelligence == 28
    assert points[0].speed == 9
    out = tmp_path / "pareto.png"
    frontier = render(points, out)
    assert frontier == points
    assert out.stat().st_size > 0
    assert "Q4_K_M" in CAPTION
    assert "28" in CAPTION
    assert "qwen2.5:0.5b" in CAPTION
    assert "not Alibaba" in CAPTION


def test_two_point_chart_draws(tmp_path: Path):
    points = [Point("slow-smart", 10, 40), Point("fast", 90, 12)]
    out = tmp_path / "line.png"
    frontier = render(points, out)
    assert [point.model_id for point in frontier] == ["slow-smart", "fast"]
    assert out.stat().st_size > 0


def test_aggregate_drops_errors():
    stats = aggregate(
        [
            {"error": "RuntimeError: down", "output_tokens_per_second": 1},
            {"includes_queue": False, "output_tokens_per_second": 10, "ttft_s": 2},
        ]
    )
    assert stats["errors"] == 1
    assert stats["used"] == 1
    assert stats["output_tokens_per_second"] == 10
    assert stats["ttft_s"] == 2


def test_plot_command_reads_results_json(tmp_path: Path):
    results = {
        "models": [
            {
                "model": "qwen3.8:27b",
                "workloads": [
                    {
                        "name": "1k",
                        "status": "measured",
                        "median": {"output_tokens_per_second": 8.7},
                    }
                ],
            }
        ]
    }
    src = tmp_path / "results.json"
    src.write_text(json.dumps(results), encoding="utf-8")
    out = tmp_path / "pareto.png"
    from benchmark.__main__ import main

    code = main(["plot", "--results", str(src), "--out", str(out)])
    assert code == 0
    assert out.exists()
