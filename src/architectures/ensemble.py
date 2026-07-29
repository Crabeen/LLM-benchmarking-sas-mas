"""Ensemble MAS: parallel stochastic candidates -> deterministic judge."""

from __future__ import annotations

import re

from typing import TYPE_CHECKING

from .. import prompts
from ..budget import BudgetController
from .common import (
    deadline_passed,
    question_with_context,
    record_for,
    run_parallel,
    trace_results,
)

if TYPE_CHECKING:
    from ..engine import Engine


_AGGREGATOR_LABEL_RE = re.compile(
    r"(?:candidate)?\s*[:#-]?\s*(\d+)\s*[.)]?",
    re.IGNORECASE,
)


def _resolve_aggregator_answer(
    raw_answer: str,
    candidates: list[str],
) -> tuple[str, str | None]:
    """Map a label-only aggregator response ("Candidate 3", "2.", ...)
    back to the selected candidate text. 1-indexed to match the prompt
    (prompts.ensemble_aggregator_user enumerates "Candidate 1: ...").
    """
    normalized = re.sub(r"[*_`]", "", raw_answer).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    match = _AGGREGATOR_LABEL_RE.fullmatch(normalized)
    if match:
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(candidates):
            return candidates[idx], str(idx + 1)
    return raw_answer, None


def run_ensemble(
    engine: "Engine",
    question: str,
    context: str | None,
    budget: BudgetController,
    answer_max_tokens: int = 256,
    temperature: float = 0.0,
    architecture_cfg: dict | None = None,
) -> dict:
    architecture_cfg = architecture_cfg or {}
    ensemble_size = int(architecture_cfg.get("ensemble_size", 4))
    if ensemble_size < 2:
        raise ValueError("ensemble_size must be at least 2")
    candidate_temperature = float(
        architecture_cfg.get("ensemble_temperature", 0.7)
    )
    base_seed = int(architecture_cfg.get("seed", 0))
    budget.start()
    worker_question = question_with_context(question, context)
    messages = [
        [
            {"role": "system", "content": prompts.ENSEMBLE_WORKER_SYSTEM},
            {"role": "user", "content": worker_question},
        ]
        for _ in range(ensemble_size)
    ]
    candidates_r = run_parallel(
        engine,
        messages,
        budget,
        [f"candidate_{i + 1}" for i in range(ensemble_size)],
        logical_slots=ensemble_size,
        parallel_group="ensemble_candidates",
        answer_max_tokens=192,
        temperature=candidate_temperature,
        seeds=[base_seed + i for i in range(ensemble_size)],
    )
    candidates, thinking = trace_results(candidates_r)

    prediction = candidates[0] if candidates else ""
    aggregator_raw: str | None = None
    aggregator_selected_candidate: str | None = None
    timeout = not bool(candidates)
    if candidates and not deadline_passed(budget):
        aggregator_messages = [
            {"role": "system", "content": prompts.ENSEMBLE_AGGREGATOR_SYSTEM},
            {
                "role": "user",
                "content": prompts.ensemble_aggregator_user(
                    question, candidates
                ),
            },
        ]
        aggregator = engine.generate(
            aggregator_messages,
            think_budget=0,
            answer_max_tokens=answer_max_tokens,
            temperature=0.0,
        )
        budget.consume(record_for("aggregator", aggregator))
        aggregator_raw = aggregator.answer
        prediction, aggregator_selected_candidate = (
            _resolve_aggregator_answer(aggregator_raw, candidates)
        )
        timeout = False
    elif deadline_passed(budget):
        timeout = True

    return {
        "prediction": prediction,
        "timeout": timeout,
        "trace": {
            "candidates": candidates,
            "aggregator_raw": aggregator_raw,
            "aggregator_selected_candidate": aggregator_selected_candidate,
            "aggregator_label_resolved": (
                aggregator_selected_candidate is not None
            ),
            "candidate_thinking": thinking,
            "ensemble_size": ensemble_size,
            "candidate_temperature": candidate_temperature,
            "parallel_execution": True,
        },
        "budget": budget.summary(),
    }

