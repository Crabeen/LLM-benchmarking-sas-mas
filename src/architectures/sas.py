"""Single-Agent System: one two-phase call, entire budget in one allocation."""

from __future__ import annotations

from ..budget import BudgetController, CallRecord
from ..engine import Engine
from .. import prompts


def run_sas(
    engine: Engine,
    question: str,
    context: str | None,
    budget: BudgetController,
    answer_max_tokens: int = 256,
    temperature: float = 0.0,
) -> dict:
    budget.start()
    alloc = budget.allocate(1.0)
    messages = [
        {"role": "system", "content": prompts.SAS_SYSTEM},
        {"role": "user", "content": prompts.sas_user(question, context)},
    ]
    r = engine.generate(messages, alloc, answer_max_tokens, temperature)
    budget.consume(
        CallRecord("sas", r.thinking_tokens, r.answer_tokens, r.seconds, r.truncated)
    )
    return {
        "prediction": r.answer,
        "timeout": budget.exhausted() and not r.answer,
        "trace": {"thinking": r.thinking},
        "budget": budget.summary(),
    }
