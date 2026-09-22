"""Intelligence vs output speed, with the Artificial Analysis Pareto rule.

Higher intelligence and higher speed are both better. A point stays on the
frontier when no other point is at least as good on both axes and strictly
better on one. Frontier points are sorted by speed and connected when there
are two or more.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from benchmark.models import MODELS, ModelSpec

CAPTION = (
    "X is median output speed measured on this OCS GPU rig "
    "(1k input, OpenAI o200k_base tokens/s), not Alibaba's published speed. "
    "Y is the published Artificial Analysis Intelligence Index for Qwen3.8 27B "
    "(medium), score 28 as of 2026-09-22. That score is their API evaluation, "
    "not a re-run of the index and not a measurement of this Q4_K_M quant. "
    "qwen2.5:0.5b is omitted because Artificial Analysis does not publish an "
    "Intelligence Index for it."
)


@dataclass(frozen=True)
class Point:
    model_id: str
    speed: float
    intelligence: float


def pareto_frontier(points: list[Point]) -> list[Point]:
    kept: list[Point] = []
    for point in points:
        dominated = False
        for other in points:
            if other is point:
                continue
            as_good = other.speed >= point.speed and other.intelligence >= point.intelligence
            strictly_better = other.speed > point.speed or other.intelligence > point.intelligence
            if as_good and strictly_better:
                dominated = True
                break
        if not dominated:
            kept.append(point)
    kept.sort(key=lambda point: (point.speed, point.intelligence))
    return kept


def points_from_results(
    results: dict,
    models: tuple[ModelSpec, ...] = MODELS,
) -> list[Point]:
    """1k median output speed for models that have a pinned intelligence score."""
    intelligence = {spec.model_id: spec.intelligence for spec in models}
    points: list[Point] = []
    for row in results.get("models", []):
        score = intelligence.get(row.get("model"))
        if score is None:
            continue
        for workload in row.get("workloads", []):
            if workload.get("name") != "1k" or workload.get("status") != "measured":
                continue
            speed = (workload.get("median") or {}).get("output_tokens_per_second")
            if speed is None:
                continue
            points.append(Point(row["model"], float(speed), float(score)))
    return points


def render(points: list[Point], out_path: Path) -> list[Point]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frontier = pareto_frontier(points)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    if points:
        ax.scatter(
            [point.speed for point in points],
            [point.intelligence for point in points],
            zorder=3,
        )
        for point in points:
            ax.annotate(
                point.model_id,
                (point.speed, point.intelligence),
                textcoords="offset points",
                xytext=(6, 6),
                fontsize=8,
            )
    if len(frontier) >= 2:
        ax.plot(
            [point.speed for point in frontier],
            [point.intelligence for point in frontier],
            zorder=2,
            label="Pareto line",
        )
        ax.legend(loc="best", frameon=False)
    ax.set_xlabel("Output speed (tokens/s)")
    ax.set_ylabel("Artificial Analysis Intelligence Index")
    ax.set_title("Intelligence vs output speed")
    fig.text(0.08, 0.01, CAPTION, fontsize=7, ha="left", va="bottom", wrap=True)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.28)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return frontier
