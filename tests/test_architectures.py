from __future__ import annotations

import unittest
from types import SimpleNamespace

from src.architectures import (
    run_debate,
    run_ensemble,
    run_parallel_roles,
    run_sas,
    run_sequential,
    run_subtask_parallel,
)
from src.budget import TokenBudget


class FakeEngine:
    def __init__(self):
        self.batch_calls = []

    @staticmethod
    def _result(answer: str, think_budget: int, seconds: float = 0.01):
        return SimpleNamespace(
            thinking=f"thinking-{answer}" if think_budget else "",
            answer=answer,
            thinking_tokens=think_budget,
            answer_tokens=2,
            prompt_tokens=10,
            answer_prompt_tokens=10 + think_budget,
            seconds=seconds,
            truncated=think_budget > 0,
        )

    def generate(
        self,
        messages,
        think_budget,
        answer_max_tokens=512,
        temperature=0.0,
        seed=0,
    ):
        system = messages[0]["content"]
        if "careful planner" in system:
            answer = (
                '{"steps": ['
                '{"id": 1, "name": "A", "instruction": "find A"},'
                '{"id": 2, "name": "B", "instruction": "find B"}]}'
            )
        elif "Decompose the question" in system:
            answer = (
                '{"tasks": ['
                '{"id": 1, "name": "A", "instruction": "find A",'
                '"deliverable": "fact A"},'
                '{"id": 2, "name": "B", "instruction": "find B",'
                '"deliverable": "fact B"}]}'
            )
        elif any(
            marker in system
            for marker in ("aggregator", "reducer", "judge")
        ):
            answer = "FINAL"
        else:
            answer = "WORK"
        return self._result(answer, think_budget)

    def generate_batch(
        self,
        batch_messages,
        think_budget,
        answer_max_tokens=512,
        temperature=0.0,
        seed=0,
    ):
        self.batch_calls.append(
            {
                "n": len(batch_messages),
                "think_budget": think_budget,
                "temperature": temperature,
                "seed": seed,
            }
        )
        return [
            self._result(f"WORK-{i}", think_budget, seconds=0.02)
            for i in range(len(batch_messages))
        ]


class ArchitectureBudgetTests(unittest.TestCase):
    def run_architecture(
        self, run_fn, total=100, cfg=None, expected_prediction="FINAL"
    ):
        engine = FakeEngine()
        result = run_fn(
            engine,
            "Who?",
            "[Doc] Evidence.",
            TokenBudget(total),
            architecture_cfg={"seed": 7, **(cfg or {})},
        )
        self.assertEqual(result["prediction"], expected_prediction)
        self.assertLessEqual(
            result["budget"]["thinking_tokens_total"], total
        )
        return engine, result

    def test_sas_uses_whole_budget(self):
        _, result = self.run_architecture(
            run_sas, expected_prediction="WORK"
        )
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 1)
        self.assertEqual(result["budget"]["n_model_invocations"], 1)

    def test_sequential_static_split_is_unchanged(self):
        _, result = self.run_architecture(run_sequential)
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 4)
        self.assertEqual(result["budget"]["n_model_invocations"], 4)
        self.assertEqual(result["trace"]["plan_parse_mode"], "json")

    def test_subtask_workers_are_one_parallel_group(self):
        engine, result = self.run_architecture(run_subtask_parallel)
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 4)
        self.assertEqual(result["budget"]["n_model_invocations"], 3)
        self.assertEqual(engine.batch_calls[0]["n"], 2)
        self.assertEqual(engine.batch_calls[0]["think_budget"], 50)

    def test_parallel_roles_are_four_equal_workers(self):
        engine, result = self.run_architecture(run_parallel_roles)
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 5)
        self.assertEqual(result["budget"]["n_model_invocations"], 2)
        self.assertEqual(engine.batch_calls[0]["n"], 4)
        self.assertEqual(engine.batch_calls[0]["think_budget"], 25)

    def test_debate_has_two_parallel_rounds(self):
        engine, result = self.run_architecture(run_debate)
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 5)
        self.assertEqual(result["budget"]["n_model_invocations"], 3)
        self.assertEqual([call["n"] for call in engine.batch_calls], [2, 2])
        self.assertEqual(
            [call["think_budget"] for call in engine.batch_calls], [25, 25]
        )

    def test_ensemble_uses_configured_size_temperature_and_seeds(self):
        engine, result = self.run_architecture(
            run_ensemble,
            cfg={"ensemble_size": 4, "ensemble_temperature": 0.7},
        )
        self.assertEqual(result["budget"]["thinking_tokens_total"], 100)
        self.assertEqual(result["budget"]["n_calls"], 5)
        self.assertEqual(result["budget"]["n_model_invocations"], 2)
        call = engine.batch_calls[0]
        self.assertEqual(call["n"], 4)
        self.assertEqual(call["think_budget"], 25)
        self.assertEqual(call["temperature"], 0.7)
        self.assertEqual(call["seed"], [7, 8, 9, 10])


if __name__ == "__main__":
    unittest.main()
