"""Shared helpers for budgeted single- and multi-agent architectures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..budget import (
    BudgetController,
    CallRecord,
    TokenBudget,
    WallClockBudget,
)

if TYPE_CHECKING:
    from ..engine import Engine, GenResult


def question_with_context(question: str, context: str | None) -> str:
    """Apply the repository's documented oracle/full-context extension."""
    if context:
        return f"Context:\n{context}\n\nQuestion: {question}"
    return f"Question: {question}"


def record_for(
    role: str, result: "GenResult", parallel_group: str | None = None
) -> CallRecord:
    return CallRecord(
        role=role,
        thinking_tokens=result.thinking_tokens,
        answer_tokens=result.answer_tokens,
        seconds=result.seconds,
        truncated=result.truncated,
        prompt_tokens=getattr(result, "prompt_tokens", 0),
        answer_prompt_tokens=getattr(result, "answer_prompt_tokens", 0),
        parallel_group=parallel_group,
    )


def deadline_passed(budget: BudgetController) -> bool:
    return isinstance(budget, WallClockBudget) and budget.exhausted()


def reserve_breached(budget: BudgetController) -> bool:
    return (
        isinstance(budget, WallClockBudget)
        and budget.reserve_breached()
    )


def parallel_allocation(
    budget: BudgetController,
    logical_slots: int,
    wallclock_fraction: float = 1.0,
) -> int:
    """Allocate one equal cap used by every member of a parallel batch.

    In token mode, ``logical_slots`` partitions the global thinking-token cap.
    In wall-clock mode, parallel workers share time, so they receive the same
    cap derived from the fraction of remaining wall-clock time.
    """
    if logical_slots <= 0:
        raise ValueError("logical_slots must be positive")
    if isinstance(budget, TokenBudget):
        return budget.allocate(1.0 / logical_slots)
    return budget.allocate(wallclock_fraction)


def run_parallel(
    engine: "Engine",
    batch_messages: list[list[dict]],
    budget: BudgetController,
    roles: list[str],
    *,
    logical_slots: int,
    parallel_group: str,
    wallclock_fraction: float = 1.0,
    answer_max_tokens: int = 192,
    temperature: float = 0.0,
    seeds: list[int] | int | None = 0,
) -> list["GenResult"]:
    if len(batch_messages) != len(roles):
        raise ValueError("batch_messages and roles must have equal length")
    if not batch_messages or budget.exhausted() or reserve_breached(budget):
        return []
    alloc = parallel_allocation(budget, logical_slots, wallclock_fraction)
    if alloc <= 0 and budget.exhausted():
        return []
    results = engine.generate_batch(
        batch_messages,
        think_budget=alloc,
        answer_max_tokens=answer_max_tokens,
        temperature=temperature,
        seed=seeds,
    )
    records = [
        record_for(role, result, parallel_group)
        for role, result in zip(roles, results)
    ]
    batch_seconds = max((r.seconds for r in results), default=0.0)
    budget.consume_batch(records, batch_seconds)
    return results


def trace_results(results: list["GenResult"]) -> tuple[list[str], list[str]]:
    return (
        [result.answer for result in results],
        [result.thinking for result in results],
    )
