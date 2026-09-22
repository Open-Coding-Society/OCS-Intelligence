"""Artificial Analysis workload shapes, sized with the o200k_base tokenizer.

1k, 10k, and 100k are their input sizes. A shape is skipped, not shortened,
when input tokens plus max_tokens exceed the worker context.
"""

from __future__ import annotations

from dataclasses import dataclass

from benchmark.models import ModelSpec


@dataclass(frozen=True)
class Workload:
    name: str
    input_tokens: int
    min_answer_tokens: int


WORKLOADS: tuple[Workload, ...] = (
    Workload("1k", 1_000, 1_000),
    Workload("10k", 10_000, 1_500),
    Workload("100k", 100_000, 2_000),
)

# Original filler. Repeated and trimmed so each prompt hits the token target.
_FILLER = (
    "The night lab keeps a paper log beside the power strip. "
    "Each entry names the board, the fan speed, and the job that was running. "
    "Students trade notes about how a long prompt changes the wait before the first word. "
    "One page describes a sorting drill. Another describes a short translation. "
    "A third asks the writer to compare two ways of counting tokens. "
    "The log never copies an outside article. It only records what happened on this bench. "
)

_TASKS = (
    "Summarize the passage in a few paragraphs. Cover every section.",
    "Write questions a reader should be able to answer from the passage, then answer them.",
    "Compare the two approaches described in the passage. Say where they agree and where they differ.",
    "Translate the passage into simple English, keeping the same order of ideas.",
)


def max_output_tokens(workload: Workload, override: int | None) -> int:
    if override is not None:
        if override < 1:
            raise ValueError("--max-output-tokens must be at least 1")
        return override
    return workload.min_answer_tokens


def skip_reason(workload: Workload, model: ModelSpec, max_tokens: int) -> str | None:
    needed = workload.input_tokens + max_tokens
    if needed <= model.context:
        return None
    return (
        f"{workload.name}: input {workload.input_tokens} + max_tokens {max_tokens} "
        f"exceeds context {model.context}"
    )


def build_prompt(workload: Workload, repeat: int, encode) -> str:
    """Build a unique prompt whose o200k_base length is the workload target.

    The task and the repeat number stay at the front so trimming the filler
    cannot make two repeats identical.
    """
    task = _TASKS[repeat % len(_TASKS)]
    prefix = f"Run {repeat}. {task}\n\n"
    text = prefix
    while len(encode(text)) < workload.input_tokens:
        text += _FILLER
    best = _fit_token_length(text, workload.input_tokens, encode)
    if not best.startswith(prefix):
        raise RuntimeError("prompt prefix was trimmed; target is smaller than the task")
    return best


def _fit_token_length(text: str, target: int, encode) -> str:
    """Longest prefix of text whose token count is <= target, then closest."""
    lo = 0
    hi = len(text)
    best = ""
    best_n = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        n = len(encode(text[:mid]))
        if n <= target:
            best = text[:mid]
            best_n = n
            lo = mid + 1
        else:
            hi = mid - 1
    if best_n == target or best_n == 0:
        return best
    # Token boundaries can leave us a few tokens short. Step forward to the
    # closest count without going past the target when a later cut is exact.
    closest = best
    closest_gap = target - best_n
    i = len(best) + 1
    while i <= len(text):
        n = len(encode(text[:i]))
        if n > target:
            break
        gap = target - n
        if gap < closest_gap:
            closest = text[:i]
            closest_gap = gap
            if gap == 0:
                break
        i += 1
    return closest
