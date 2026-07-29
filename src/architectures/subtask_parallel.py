"""Subtask-parallel MAS: planner -> parallel independent tasks -> reducer."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import yaml

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


_FALLBACK_TASKS = [
    {
        "id": 1,
        "name": "Evidence extraction",
        "instruction": "Extract the entities, relations, and constraints relevant to the question.",
        "deliverable": "A concise list of relevant facts.",
    },
    {
        "id": 2,
        "name": "Independent solution",
        "instruction": "Solve the full question independently from the supplied evidence.",
        "deliverable": "A candidate answer with the essential reasoning.",
    },
    {
        "id": 3,
        "name": "Verification",
        "instruction": "Look for ambiguities, missing constraints, and likely answer errors.",
        "deliverable": "A concise verification report and corrected candidate if needed.",
    },
]


def _normalize_tasks(raw, max_tasks: int) -> list[dict] | None:
    if isinstance(raw, dict):
        raw = raw.get("tasks")
    if not isinstance(raw, list) or not raw:
        return None
    tasks = []
    for i, item in enumerate(raw[:max_tasks]):
        if not isinstance(item, dict) or not item.get("instruction"):
            continue
        tasks.append(
            {
                "id": item.get("id", i + 1),
                "name": str(item.get("name", f"Task {i + 1}")),
                "instruction": str(item["instruction"]),
                "deliverable": str(
                    item.get("deliverable", "Return the useful result.")
                ),
            }
        )
    return tasks or None


def _parse_tasks(text: str, max_tasks: int = 4) -> tuple[list[dict], str]:
    cleaned = re.sub(r"```(?:json|yaml)?|```", "", text).strip()
    try:
        tasks = _normalize_tasks(json.loads(cleaned), max_tasks)
        if tasks:
            return tasks, "json"
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        tasks = _normalize_tasks(yaml.safe_load(cleaned), max_tasks)
        if tasks:
            return tasks, "yaml"
    except (yaml.YAMLError, TypeError, AttributeError):
        pass
    instructions = re.findall(
        r'"?instruction"?\s*:\s*"([^"]{5,})"', cleaned
    )
    if instructions:
        return [
            {
                "id": i + 1,
                "name": f"Task {i + 1}",
                "instruction": instruction,
                "deliverable": "Return the useful result.",
            }
            for i, instruction in enumerate(instructions[:max_tasks])
        ], "regex"
    return list(_FALLBACK_TASKS[:max_tasks]), "fallback"


def run_subtask_parallel(
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

    planner_messages = [
        {"role": "system", "content": prompts.SUBTASK_PLANNER_SYSTEM},
        {"role": "user", "content": question},
    ]
    planner = engine.generate(
        planner_messages,
        think_budget=0,
        answer_max_tokens=384,
        temperature=temperature,
    )
    budget.consume(record_for("planner", planner))
    tasks, parse_mode = _parse_tasks(
        planner.answer,
        max_tasks=int(architecture_cfg.get("max_parallel_tasks", 4)),
    )

    worker_question = question_with_context(question, context)
    worker_messages = [
        [
            {"role": "system", "content": prompts.SUBTASK_WORKER_SYSTEM},
            {
                "role": "user",
                "content": prompts.subtask_worker_user(worker_question, task),
            },
        ]
        for task in tasks
    ]
    workers = run_parallel(
        engine,
        worker_messages,
        budget,
        [f"subtask_{i + 1}" for i in range(len(tasks))],
        logical_slots=len(tasks),
        parallel_group="subtask_workers",
        answer_max_tokens=192,
        temperature=temperature,
        seeds=[
            int(architecture_cfg.get("seed", 0)) + i
            for i in range(len(tasks))
        ],
    )
    outputs, thinking = trace_results(workers)

    prediction = outputs[-1] if outputs else ""
    timeout = not bool(outputs)
    if outputs and not deadline_passed(budget):
        aggregator_messages = [
            {"role": "system", "content": prompts.SUBTASK_AGGREGATOR_SYSTEM},
            {
                "role": "user",
                "content": prompts.subtask_aggregator_user(
                    question, tasks[:len(outputs)], outputs
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
            "tasks": tasks,
            "plan_parse_mode": parse_mode,
            "task_outputs": outputs,
            "worker_thinking": thinking,
            "parallel_execution": True,
        },
        "budget": budget.summary(),
    }

