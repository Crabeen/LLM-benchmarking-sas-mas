"""Parallel-roles MAS with the four roles specified in the paper."""

from __future__ import annotations

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


ROLES = [
    {
        "name": "Solver",
        "instructions": (
            "Solve the question directly. Connect the necessary facts and "
            "provide your best candidate answer."
        ),
    },
    {
        "name": "Fact Extractor",
        "instructions": (
            "Identify the key entities, constraints, relations, and "
            "intermediate facts needed to answer the question."
        ),
    },
    {
        "name": "Skeptic",
        "instructions": (
            "Highlight possible pitfalls, unsupported jumps, missing "
            "constraints, and alternative interpretations."
        ),
    },
    {
        "name": "Second Solver",
        "instructions": (
            "Independently solve the full question without relying on another "
            "solver's answer."
        ),
    },
]


def run_parallel_roles(
    engine: "Engine",
    question: str,
    context: str | None,
    budget: BudgetController,
    answer_max_tokens: int = 256,
    temperature: float = 0.0,
    architecture_cfg: dict | None = None,
) -> dict:
    architecture_cfg = architecture_cfg or {}
    budget.start()
    worker_question = question_with_context(question, context)
    messages = [
        [
            {"role": "system", "content": prompts.ROLE_WORKER_SYSTEM},
            {
                "role": "user",
                "content": prompts.role_worker_user(
                    worker_question, role["name"], role["instructions"]
                ),
            },
        ]
        for role in ROLES
    ]
    workers = run_parallel(
        engine,
        messages,
        budget,
        [f"role_{role['name'].lower().replace(' ', '_')}" for role in ROLES],
        logical_slots=len(ROLES),
        parallel_group="role_workers",
        answer_max_tokens=192,
        temperature=temperature,
        seeds=[
            int(architecture_cfg.get("seed", 0)) + i
            for i in range(len(ROLES))
        ],
    )
    outputs, thinking = trace_results(workers)

    prediction = outputs[-1] if outputs else ""
    timeout = not bool(outputs)
    if outputs and not deadline_passed(budget):
        aggregator_messages = [
            {"role": "system", "content": prompts.ROLE_AGGREGATOR_SYSTEM},
            {
                "role": "user",
                "content": prompts.role_aggregator_user(
                    question, ROLES[:len(outputs)], outputs
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
        prediction = aggregator.answer
        timeout = False
    elif deadline_passed(budget):
        timeout = True

    return {
        "prediction": prediction,
        "timeout": timeout,
        "trace": {
            "roles": ROLES,
            "role_outputs": outputs,
            "worker_thinking": thinking,
            "parallel_execution": True,
        },
        "budget": budget.summary(),
    }

