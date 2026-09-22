"""Model table for the two OCS workers.

Intelligence is a published Artificial Analysis score, not something this
suite measures. Qwen2.5 0.5B has no published Intelligence Index.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    context: int
    temperature: float
    reasoning: bool
    intelligence: float | None
    intelligence_note: str


TOP_P = 1.0

# Published 2026-09-22 at
# https://artificialanalysis.ai/models/qwen3-8-27b-medium
QWEN38_MEDIUM_INTELLIGENCE = 28.0
QWEN38_INTELLIGENCE_NOTE = (
    "Artificial Analysis Intelligence Index for Qwen3.8 27B (medium), "
    "score 28, as published on 2026-09-22 at "
    "https://artificialanalysis.ai/models/qwen3-8-27b-medium. "
    "That score is their API evaluation of the model, not a re-run of "
    "Intelligence Index v4.3 / v4.3.2 and not a measurement of this Q4_K_M quant."
)

MODELS: tuple[ModelSpec, ...] = (
    ModelSpec(
        model_id="qwen2.5:0.5b",
        context=8192,
        temperature=0.0,
        reasoning=False,
        intelligence=None,
        intelligence_note=(
            "Artificial Analysis does not publish an Intelligence Index for Qwen2.5 0.5B."
        ),
    ),
    ModelSpec(
        model_id="qwen3.8:27b",
        context=4096,
        temperature=0.6,
        reasoning=True,
        intelligence=QWEN38_MEDIUM_INTELLIGENCE,
        intelligence_note=QWEN38_INTELLIGENCE_NOTE,
    ),
)


def model_by_id(model_id: str) -> ModelSpec:
    for spec in MODELS:
        if spec.model_id == model_id:
            return spec
    known = ", ".join(spec.model_id for spec in MODELS)
    raise KeyError(f"unknown model {model_id!r} (known: {known})")
