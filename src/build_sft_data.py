"""Build SFT data from MuSiQue train split.

Each example becomes one training string whose format EXACTLY matches the
inference-time layout produced by engine.py:

    <chat prelude ending in assistant turn> <think>\n TRACE \n</think>\n\n ANSWER <eos>

TRACE is templated from MuSiQue's own question_decomposition (sub-questions
with intermediate answers), so no model-generated data is needed for v1.
The system/user prompts reuse prompts.py (paper Appendix D.1), and context
uses the supporting paragraphs (align with your eval context_mode).

Usage:
    python -m src.build_sft_data --out data/sft_train.jsonl --n 4000 --hops 4hop
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from datasets import load_dataset
from transformers import AutoTokenizer

from . import prompts


def build_trace(decomp: list[dict]) -> str:
    """Template MuSiQue's decomposition into a thinking trace."""
    lines = ["Let me break this question into steps."]
    answers = {}
    for i, step in enumerate(decomp, 1):
        q = step["question"]
        # replace back-references like "#1" with the earlier answer
        q = re.sub(r"#(\d+)", lambda m: answers.get(int(m.group(1)), m.group(0)), q)
        a = step["answer"]
        answers[i] = a
        lines.append(f"Step {i}: {q} The answer is {a}.")
    lines.append(f"So the final answer is {decomp[-1]['answer']}.")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sft_train.jsonl")
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--hops", default="4hop", help="'4hop' | 'all'")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--context", default="oracle", help="'oracle' | 'closed'")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_tokens", type=int, default=4096,
                    help="drop examples longer than this after tokenization")
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    ds = load_dataset("dgslibisey/MuSiQue", split="train")
    items = [ex for ex in ds
             if args.hops == "all" or str(ex["id"]).startswith(args.hops)]
    rng = random.Random(args.seed)
    rng.shuffle(items)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept, skipped_len, skipped_bad = 0, 0, 0

    with out_path.open("w") as f:
        for ex in items:
            if kept >= args.n:
                break
            decomp = ex.get("question_decomposition") or []
            if not decomp or not all(s.get("answer") for s in decomp):
                skipped_bad += 1
                continue
            if args.context == "oracle":
                paras = [p for p in ex["paragraphs"] if p.get("is_supporting")]
                context = "\n\n".join(
                    f"[{p['title']}] {p['paragraph_text']}" for p in paras) or None
            else:
                context = None

            messages = [
                {"role": "system", "content": prompts.SAS_SYSTEM},
                {"role": "user", "content": prompts.sas_user(ex["question"], context)},
            ]
            try:
                prelude = tok.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True,
                    enable_thinking=True)
            except TypeError:
                prelude = tok.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True)
            if not prelude.rstrip().endswith("<think>"):
                prelude = prelude + "<think>\n"
            else:
                prelude = prelude + "\n"

            text = (prelude + build_trace(decomp) + "\n</think>\n\n"
                    + ex["answer"] + tok.eos_token)
            if len(tok.encode(text)) > args.max_tokens:
                skipped_len += 1
                continue
            f.write(json.dumps({"text": text, "id": ex["id"]},
                               ensure_ascii=False) + "\n")
            kept += 1

    print(f"kept {kept}, skipped(bad decomposition) {skipped_bad}, "
          f"skipped(too long) {skipped_len} -> {out_path}")


if __name__ == "__main__":
    main()
