"""CLI for the OCS GPU benchmark.

  python3 -m benchmark run --out benchmark/results/latest.json
  python3 -m benchmark plot --results benchmark/results/latest.json --out benchmark/results/pareto.png
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from benchmark.models import MODELS, model_by_id
from benchmark.pareto import points_from_results, render
from benchmark.runner import default_encode, load_dotenv, openai_stream, run_benchmark, write_results

REPO = Path(__file__).resolve().parents[1]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="benchmark")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="measure both models and write JSON")
    run.add_argument("--out", type=Path, default=Path("benchmark/results/latest.json"))
    run.add_argument("--repeats", type=int, default=5)
    run.add_argument("--max-output-tokens", type=int, default=None)
    run.add_argument(
        "--models",
        nargs="*",
        default=None,
        help="model ids to run (default: both workers)",
    )

    plot = sub.add_parser("plot", help="Pareto chart from a results JSON file")
    plot.add_argument("--results", type=Path, required=True)
    plot.add_argument("--out", type=Path, required=True)
    return parser


def _cmd_run(args: argparse.Namespace) -> int:
    load_dotenv(REPO / ".env")
    base_url = os.environ.get("OCS_BASE_URL", "https://ai.opencodingsociety.com/v1").rstrip("/")
    api_key = os.environ.get("OCS_API_KEY", "")
    if not api_key:
        print("OCS_API_KEY is not set. Copy .env.example to .env.", file=sys.stderr)
        return 2
    if args.models:
        specs = [model_by_id(model_id) for model_id in args.models]
    else:
        specs = list(MODELS)
    payload = run_benchmark(
        models=specs,
        repeats=args.repeats,
        max_output_tokens_override=args.max_output_tokens,
        stream_fn=openai_stream(base_url, api_key),
        encode=default_encode(),
    )
    payload["base_url"] = base_url
    write_results(payload, args.out)
    print(args.out)
    return 0


def _cmd_plot(args: argparse.Namespace) -> int:
    results = json.loads(args.results.read_text(encoding="utf-8"))
    points = points_from_results(results)
    frontier = render(points, args.out)
    print(
        f"{args.out}  points={len(points)}  frontier={len(frontier)}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "plot":
        return _cmd_plot(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
