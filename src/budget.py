"""Budget controllers.

The core abstraction of this scaffold. Both SAS and MAS ask the controller
"how many thinking tokens may my next model call use?" before every call,
and report actual usage afterwards. This makes the budget definition
(token cap vs wall-clock deadline) orthogonal to the system architecture.

Token mode reproduces Tran & Kiela (arXiv:2604.02460): the budget is an
UPPER CAP on intermediate reasoning tokens; systems are not forced to use it.

Wall-clock mode is the thesis extension: a per-question deadline in seconds.
Remaining time is converted to a max-token allocation via an online
tokens-per-second estimate, and the deadline is checked between calls.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CallRecord:
    role: str                 # e.g. "sas", "planner", "worker_2", "aggregator"
    thinking_tokens: int
    answer_tokens: int
    seconds: float
    truncated: bool           # thinking hit its per-call cap


class BudgetController(ABC):
    """Per-question budget. Create one fresh instance per question."""

    def __init__(self) -> None:
        self.calls: list[CallRecord] = []
        self._t0: float | None = None

    def start(self) -> None:
        self._t0 = time.monotonic()

    @property
    def elapsed(self) -> float:
        return 0.0 if self._t0 is None else time.monotonic() - self._t0

    @abstractmethod
    def allocate(self, fraction: float = 1.0) -> int:
        """Max thinking tokens permitted for the next call.

        `fraction` lets an architecture split its budget, e.g. Sequential MAS
        gives each of k workers fraction=1/k of the *original* budget
        (paper-style static split), while allocate(1.0) hands over whatever
        remains. Returns 0 if the budget is exhausted.
        """

    @abstractmethod
    def exhausted(self) -> bool:
        ...

    def consume(self, record: CallRecord) -> None:
        self.calls.append(record)

    # ---- diagnostics (logged for every question regardless of mode) ----
    def summary(self) -> dict:
        return {
            "n_calls": len(self.calls),
            "thinking_tokens_total": sum(c.thinking_tokens for c in self.calls),
            "answer_tokens_total": sum(c.answer_tokens for c in self.calls),
            "wall_seconds_total": round(self.elapsed, 3),
            "any_truncated": any(c.truncated for c in self.calls),
            "per_call": [vars(c) for c in self.calls],
        }


class TokenBudget(BudgetController):
    """Paper-faithful mode: global cap B on thinking tokens per question."""

    def __init__(self, total_thinking_tokens: int):
        super().__init__()
        self.total = total_thinking_tokens
        self.used = 0

    def allocate(self, fraction: float = 1.0) -> int:
        remaining = self.total - self.used
        if remaining <= 0:
            return 0
        # static split is relative to the ORIGINAL budget (paper behaviour),
        # but never exceed what actually remains.
        alloc = int(self.total * fraction) if fraction < 1.0 else remaining
        return max(0, min(alloc, remaining))

    def exhausted(self) -> bool:
        return self.used >= self.total

    def consume(self, record: CallRecord) -> None:
        super().consume(record)
        self.used += record.thinking_tokens


class WallClockBudget(BudgetController):
    """Thesis-extension mode: per-question deadline in seconds.

    Converts remaining seconds -> max thinking tokens using an EMA of
    observed decode throughput. Conservative by design (safety_factor < 1)
    so a call is unlikely to overshoot the deadline; the runner additionally
    marks the question as a timeout if the deadline passes before a final
    answer exists.
    """

    def __init__(
        self,
        total_seconds: float,
        init_tokens_per_sec: float = 40.0,
        safety_factor: float = 0.85,
        answer_reserve_seconds: float = 5.0,
        min_alloc: int = 16,
    ):
        super().__init__()
        self.total_seconds = total_seconds
        self.tps = init_tokens_per_sec
        self.safety = safety_factor
        self.answer_reserve = answer_reserve_seconds
        self.min_alloc = min_alloc

    def _remaining_seconds(self) -> float:
        return self.total_seconds - self.elapsed

    def allocate(self, fraction: float = 1.0) -> int:
        # reserve time for the final answer phase
        budgetable = self._remaining_seconds() - self.answer_reserve
        if budgetable <= 0:
            return 0
        secs = budgetable * (fraction if fraction < 1.0 else 1.0)
        alloc = int(secs * self.tps * self.safety)
        return 0 if alloc < self.min_alloc else alloc

    def exhausted(self) -> bool:
        return self._remaining_seconds() <= 0

    def reserve_breached(self) -> bool:
        """True once only the answer reserve remains: no new worker may start,
        but budget-neutral finalisation (aggregator) still may."""
        return self._remaining_seconds() <= self.answer_reserve

    def overran(self) -> bool:
        """Deadline passed at any point. The deadline is SOFT: an in-flight
        vLLM call cannot be interrupted, so a call started before the deadline
        may finish after it."""
        return self.elapsed > self.total_seconds

    def consume(self, record: CallRecord) -> None:
        super().consume(record)
        total_tokens = record.thinking_tokens + record.answer_tokens
        if record.seconds > 0.2 and total_tokens > 0:
            observed = total_tokens / record.seconds
            self.tps = 0.7 * self.tps + 0.3 * observed  # EMA update


def make_budget(cfg: dict) -> BudgetController:
    mode = cfg["budget"]["mode"]
    if mode == "token":
        return TokenBudget(int(cfg["budget"]["thinking_tokens"]))
    if mode == "wallclock":
        wc = cfg["budget"]
        return WallClockBudget(
            total_seconds=float(wc["seconds"]),
            init_tokens_per_sec=float(wc.get("init_tokens_per_sec", 40.0)),
            safety_factor=float(wc.get("safety_factor", 0.85)),
            answer_reserve_seconds=float(wc.get("answer_reserve_seconds", 5.0)),
        )
    raise ValueError(f"unknown budget mode: {mode}")
