"""Sequential MAS: planner -> k sequential workers -> aggregator.

Paper-faithful version (Appendix D.2). Plan steps are structured objects
{id, name, instruction}. The parser accepts strict JSON, YAML-style output
(the paper's structure example is typeset ambiguously), a regex fallback
extracting instruction strings, and finally a fixed generic 3-step plan.
parse_mode is logged per question: json | yaml | regex | fallback.
"""

from __future__ import annotations

import json
import re

import yaml

from ..budget import BudgetController, CallRecord, TokenBudget
from ..engine import Engine
from .. import prompts

_FALLBACK_PLAN = [
    {"id": 1, "name": "Identify entities",
     "instruction": "Identify the entities and relations the question asks about."},
    {"id": 2, "name": "Find intermediate facts",
     "instruction": "Find the intermediate facts needed to connect them."},
    {"id": 3, "name": "Derive answer",
     "instruction": "Derive the final answer from the intermediate facts."},
]


def _normalize_steps(raw, max_steps: int) -> list[dict] | None:
    if isinstance(raw, dict):
        raw = raw.get("steps")
    if not isinstance(raw, list) or not raw:
        return None
    steps = []
    for i, item in enumerate(raw[:max_steps]):
        if isinstance(item, dict) and item.get("instruction"):
            steps.append({
                "id": item.get("id", i + 1),
                "name": str(item.get("name", f"Step {i + 1}")),
                "instruction": str(item["instruction"]),
            })
        elif isinstance(item, str) and item.strip():
            steps.append({"id": i + 1, "name": f"Step {i + 1}",
                          "instruction": item.strip()})
    return steps or None


def _parse_plan(text: str, max_steps: int = 5) -> tuple[list[dict], str]:
    cleaned = re.sub(r"```(?:json|yaml)?|```", "", text).strip()
    try:
        steps = _normalize_steps(json.loads(cleaned), max_steps)
        if steps:
            return steps, "json"
    except (json.JSONDecodeError, TypeError):
        pass
    try:
        steps = _normalize_steps(yaml.safe_load(cleaned), max_steps)
        if steps:
            return steps, "yaml"
    except (yaml.YAMLError, TypeError, AttributeError):
        pass
    found = re.findall(r'"?instruction"?\s*:\s*"([^"]{5,})"', cleaned)
    if found:
        return [{"id": i + 1, "name": f"Step {i + 1}", "instruction": f}
                for i, f in enumerate(found[:max_steps])], "regex"
    return list(_FALLBACK_PLAN), "fallback"


def run_sequential(
    engine: Engine,
    question: str,
    context: str | None,
    budget: BudgetController,
    answer_max_tokens: int = 256,
    temperature: float = 0.0,
) -> dict:
    budget.start()

    plan_msgs = [
        {"role": "system", "content": prompts.PLANNER_SYSTEM},
        {"role": "user", "content": prompts.planner_user(question)},
    ]
    pr = engine.generate(plan_msgs, think_budget=0, answer_max_tokens=384,
                         temperature=temperature)
    budget.consume(CallRecord("planner", pr.thinking_tokens, pr.answer_tokens,
                              pr.seconds, pr.truncated))
    steps, parse_mode = _parse_plan(pr.answer)
    k = len(steps)

    outputs: list[str] = []
    worker_thinking: list[str] = []   # kept for grounding analysis; NOT passed
                                      # between agents (only outputs are)
    worker_truncated = False
    for i in range(k):
        if budget.exhausted():
            break
        if isinstance(budget, TokenBudget):
            frac = 1.0 / k
        else:
            frac = 1.0 / (k - i)
        alloc = budget.allocate(frac)
        # in wall-clock mode, stop starting workers once only the answer
        # reserve remains, so the aggregator actually gets its reserved time
        if hasattr(budget, "reserve_breached") and budget.reserve_breached():
            break
        if alloc <= 0 and budget.exhausted():
            break
        msgs = [
            {"role": "system", "content": prompts.WORKER_SYSTEM},
            {"role": "user",
             "content": prompts.worker_user(question, steps, i, outputs, context)},
        ]
        r = engine.generate(msgs, alloc, answer_max_tokens=192,
                            temperature=temperature)
        budget.consume(CallRecord(f"worker_{i+1}", r.thinking_tokens,
                                  r.answer_tokens, r.seconds, r.truncated))
        worker_truncated |= r.truncated
        outputs.append(r.answer)
        worker_thinking.append(r.thinking)

    prediction, timeout = "", False
    # The aggregator is budget-neutral (think_budget=0), so an exhausted
    # THINKING budget must not skip it -- only a wall-clock deadline can.
    deadline_passed = (not isinstance(budget, TokenBudget)) and budget.exhausted()
    if outputs and not deadline_passed:
        agg_msgs = [
            {"role": "system", "content": prompts.AGGREGATOR_SYSTEM},
            {"role": "user",
             "content": prompts.aggregator_user(question, steps, outputs)},
        ]
        ar = engine.generate(agg_msgs, think_budget=0,
                             answer_max_tokens=answer_max_tokens,
                             temperature=temperature)
        budget.consume(CallRecord("aggregator", ar.thinking_tokens,
                                  ar.answer_tokens, ar.seconds, ar.truncated))
        prediction = ar.answer
    else:
        prediction = outputs[-1] if outputs else ""
        timeout = True

    return {
        "prediction": prediction,
        "timeout": timeout,
        "trace": {
            "plan": steps,
            "plan_parse_mode": parse_mode,
            "findings": outputs,
            "worker_thinking": worker_thinking,
            "worker_truncated": worker_truncated,
        },
        "budget": budget.summary(),
    }
