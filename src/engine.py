"""vLLM engine wrapper with two-phase (think -> answer) generation.

Budget enforcement follows the open-model protocol in Tran & Kiela:

  phase 1: build the chat prompt, ensure it ends with an open `<think>` tag,
           generate at most `think_budget` tokens, stopping early at </think>.
           If the cap is hit, the trace is hard-truncated.
  phase 2: append the truncated/complete thinking plus a closing `</think>`,
           then generate the final answer with a modest max_tokens that does
           NOT count against the thinking budget.

Works for Qwen3 (hybrid thinking) and DeepSeek-R1-Distill-Llama. Both chat
templates either already end the generation prompt with `<think>` or accept
us appending it manually; `_ensure_think_open` handles both cases.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from vllm import LLM, SamplingParams

THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


@dataclass
class GenResult:
    thinking: str
    answer: str
    thinking_tokens: int
    answer_tokens: int
    seconds: float
    truncated: bool  # thinking phase hit the cap without emitting </think>


class Engine:
    def __init__(
        self,
        model: str,
        tensor_parallel_size: int = 1,
        max_model_len: int = 16384,
        gpu_memory_utilization: float = 0.90,
        dtype: str = "bfloat16",
        seed: int = 0,
        enforce_eager: bool = False,
    ):
        self.llm = LLM(
            model=model,
            tensor_parallel_size=tensor_parallel_size,
            max_model_len=max_model_len,
            gpu_memory_utilization=gpu_memory_utilization,
            dtype=dtype,
            seed=seed,
            enforce_eager=enforce_eager,
        )
        self.tok = self.llm.get_tokenizer()

    # ------------------------------------------------------------------ #

    def _chat_prompt(self, messages: list[dict]) -> str:
        # enable_thinking is accepted by Qwen3's template; other templates
        # ignore unknown kwargs, so pass it defensively.
        try:
            return self.tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=True,
            )
        except TypeError:
            return self.tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
            )

    @staticmethod
    def _ensure_think_open(prompt: str) -> str:
        return prompt if prompt.rstrip().endswith(THINK_OPEN) else prompt + THINK_OPEN + "\n"

    def _count(self, text: str) -> int:
        return len(self.tok.encode(text, add_special_tokens=False))

    # ------------------------------------------------------------------ #

    def generate(
        self,
        messages: list[dict],
        think_budget: int,
        answer_max_tokens: int = 512,
        temperature: float = 0.0,
        seed: int | None = 0,
    ) -> GenResult:
        """Single-request two-phase generation. See generate_batch for SAS runs."""
        return self.generate_batch(
            [messages], think_budget, answer_max_tokens, temperature, seed
        )[0]

    def generate_batch(
        self,
        batch_messages: list[list[dict]],
        think_budget: int,
        answer_max_tokens: int = 512,
        temperature: float = 0.0,
        seed: int | None = 0,
    ) -> list[GenResult]:
        t0 = time.monotonic()
        prompts = [self._ensure_think_open(self._chat_prompt(m)) for m in batch_messages]

        # ---- phase 1: thinking, capped ----
        if think_budget > 0:
            sp_think = SamplingParams(
                max_tokens=think_budget,
                temperature=temperature,
                stop=[THINK_CLOSE],
                seed=seed,
            )
            outs = self.llm.generate(prompts, sp_think)
            thinkings, truncs, think_counts = [], [], []
            for o in outs:
                c = o.outputs[0]
                thinkings.append(c.text)
                think_counts.append(len(c.token_ids))
                # finish_reason == "length" means we hit the cap (hard truncation)
                truncs.append(c.finish_reason == "length")
        else:
            thinkings = ["" for _ in prompts]
            truncs = [False] * len(prompts)
            think_counts = [0] * len(prompts)

        # ---- phase 2: answer, outside the thinking budget ----
        answer_prompts = [
            p + th + "\n" + THINK_CLOSE + "\n\n" for p, th in zip(prompts, thinkings)
        ]
        sp_ans = SamplingParams(
            max_tokens=answer_max_tokens, temperature=temperature, seed=seed
        )
        outs2 = self.llm.generate(answer_prompts, sp_ans)

        elapsed = time.monotonic() - t0
        per = elapsed / max(1, len(prompts))  # coarse per-item time under batching
        results = []
        for th, tc, tr, o in zip(thinkings, think_counts, truncs, outs2):
            c = o.outputs[0]
            results.append(
                GenResult(
                    thinking=th.strip(),
                    answer=c.text.strip(),
                    thinking_tokens=tc,
                    answer_tokens=len(c.token_ids),
                    seconds=per,
                    truncated=tr,
                )
            )
        return results
