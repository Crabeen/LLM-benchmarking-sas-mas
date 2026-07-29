"""Debate MAS: two answers -> reciprocal critiques -> judge."""

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
    r"(?:(?:final\s+)?answer|option|candidate)?\s*[:#-]?\s*([AB])\s*[.)]?",
    re.IGNORECASE,
)


def _resolve_aggregator_answer(
    raw_answer: str,
    candidates: list[str],
) -> tuple[str, str | None]:
    """Map a label-only aggregator response to the selected candidate."""
    normalized = re.sub(r"[*_`]", "", raw_answer).strip()
    normalized = re.sub(r"\s+", " ", normalized)

    match = _AGGREGATOR_LABEL_RE.fullmatch(normalized)
    if match and len(candidates) == 2:
        label = match.group(1).upper()
        return candidates[0 if label == "A" else 1], label

    return raw_answer, None


def run_debate(
    engine: "Engine",
    question: str,
    context: str | None,
    budget: BudgetController,
    answer_max_tokens: int = 256,
    temperature: float = 0.0,
    architecture_cfg: dict | None = None,
) -> dict:
    architecture_cfg = architecture_cfg or {}
    base_seed = int(architecture_cfg.get("seed", 0))
    budget.start()
    debate_question = question_with_context(question, context)

    debater_messages = [
        [
            {"role": "system", "content": prompts.DEBATER_SYSTEM},
            {"role": "user", "content": debate_question},
        ]
        for _ in range(2)
    ]
    debaters = run_parallel(
        engine,
        debater_messages,
        budget,
        ["debater_a", "debater_b"],
        # Four budgeted reasoning roles: two debaters and two critics.
        logical_slots=4,
        parallel_group="debaters",
        wallclock_fraction=0.5,
        answer_max_tokens=192,
        temperature=temperature,
        seeds=[base_seed, base_seed + 1],
    )
    initial_answers, debater_thinking = trace_results(debaters)

    critics = []
    if len(initial_answers) == 2 and not deadline_passed(budget):
        critic_messages = [
            [
                {"role": "system", "content": prompts.CRITIC_SYSTEM},
                {
                    "role": "user",
                    "content": prompts.critique_user(
                        debate_question, initial_answers[1]
                    ),
                },
            ],
            [
                {"role": "system", "content": prompts.CRITIC_SYSTEM},
                {
                    "role": "user",
                    "content": prompts.critique_user(
                        debate_question, initial_answers[0]
                    ),
                },
            ],
        ]
        critics = run_parallel(
            engine,
            critic_messages,
            budget,
            ["critic_a", "critic_b"],
            logical_slots=4,
            parallel_group="critics",
            answer_max_tokens=192,
            temperature=temperature,
            seeds=[base_seed + 2, base_seed + 3],
        )
    improved_answers, critic_thinking = trace_results(critics)
    candidates = (
        improved_answers if len(improved_answers) == 2 else initial_answers
    )

    prediction = candidates[0] if candidates else ""
    aggregator_raw: str | None = None
    aggregator_selected_candidate: str | None = None
    timeout = not bool(candidates)
    if len(candidates) == 2 and not deadline_passed(budget):
        aggregator_messages = [
            {"role": "system", "content": prompts.DEBATE_AGGREGATOR_SYSTEM},
            {
                "role": "user",
                "content": prompts.debate_aggregator_user(
                    question, candidates[0], candidates[1]
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
            "initial_answers": initial_answers,
            "debater_thinking": debater_thinking,
            "improved_answers": improved_answers,
            "critic_thinking": critic_thinking,
            "aggregator_raw": aggregator_raw,
            "aggregator_selected_candidate": aggregator_selected_candidate,
            "aggregator_label_resolved": (
                aggregator_selected_candidate is not None
            ),
            "parallel_execution": True,
        },
        "budget": budget.summary(),
    }

