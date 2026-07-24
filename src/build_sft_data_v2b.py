"""v2b ablation: evidence-grounded reasoning traces.

Difference from v1/v2a: each step cites the supporting paragraph title and a
short span copied from that paragraph, e.g.

    Step 1: Atalia >> country
    From [Atalia (film)]: ...the 1984 Israeli drama film...
    The answer is Israel.

Rationale (motivation, not a proven mechanism): the v1/v2a objective does not
directly reward reproducing context-specific evidence, so minimising the loss
does not require attending to the supplied paragraphs. v2b puts copied
evidence spans in the target, making prediction more directly dependent on the
context.

Strictness: a step is emitted only if its supporting paragraph resolves via
paragraph_support_idx AND the literal answer occurs (with word boundaries)
inside the quoted window. Examples failing this are dropped rather than given
fabricated evidence.

The prompt-masking policy is held constant against v2a, but completion length
and supervised-token count are NOT matched: v2b traces are longer. Attributing
accuracy changes to grounding specifically would need a length-matched control
(same citation lines, mismatched evidence).

Usage:
  python -m src.build_sft_data_v2b --out data/sft_train_v2b.jsonl --n 4000
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

MAX_QUOTE_CHARS = 180


def _snippet(paragraph: str, answer: str) -> str | None:
    """Window around the literal answer (<=MAX_QUOTE_CHARS plus ellipses).

    Word boundaries stop short answers matching inside longer words.
    Returns None when the answer does not occur literally.
    """
    text, answer = paragraph.strip(), answer.strip()
    if not text or not answer:
        return None
    pat = re.escape(answer)
    if answer[0].isalnum():
        pat = r"(?<!\w)" + pat
    if answer[-1].isalnum():
        pat = pat + r"(?!\w)"
    m = re.search(pat, text, flags=re.IGNORECASE)
    if m is None:
        return None
    span = m.end() - m.start()
    pad = max(0, MAX_QUOTE_CHARS - span)
    start = max(0, m.start() - pad // 2)
    end = min(len(text), start + MAX_QUOTE_CHARS)
    start = max(0, end - MAX_QUOTE_CHARS)
    snip = text[start:end].strip()
    if answer.lower() not in snip.lower():
        return None
    if start > 0:
        snip = "..." + snip
    if end < len(text):
        snip += "..."
    return snip


def build_trace_grounded(ex: dict) -> str | None:
    by_idx = {}
    for p in ex["paragraphs"]:
        i = p.get("idx")
        if isinstance(i, int):
            by_idx[i] = p
    lines = ["Let me work through this step by step using the given paragraphs."]
    answers = {}
    for n, step in enumerate(ex["question_decomposition"], 1):
        idx = step.get("paragraph_support_idx")
        if not isinstance(idx, int) or idx < 0 or idx not in by_idx:
            return None
        para = by_idx[idx]
        if not para.get("is_supporting"):
            return None
        a = step["answer"]
        snip = _snippet(para["paragraph_text"], a)
        if snip is None:
            return None
        q = re.sub(r"#(\d+)",
                   lambda m: answers.get(int(m.group(1)), m.group(0)),
                   step["question"])
        answers[n] = a
        lines.append(f"Step {n}: {q}")
        lines.append(f"From [{para['title']}]: {snip}")
        lines.append(f"The answer is {a}.")
    lines.append(f"So the final answer is {ex['answer']}.")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sft_train_v2b.jsonl")
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--hops", choices=["4hop", "all"], default="4hop")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_tokens", type=int, default=4096)
    args = ap.parse_args()
    # context is always oracle: grounded targets require the cited paragraphs
    # to be visible in the input.

    tok = AutoTokenizer.from_pretrained(args.model)
    ds = load_dataset("dgslibisey/MuSiQue", split="train")
    items = [ex for ex in ds
             if args.hops == "all" or str(ex["id"]).startswith(args.hops)]
    total = len(items)
    random.Random(args.seed).shuffle(items)   # same seed/order as v1 & v2a

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = skip_bad = skip_ground = skip_len = 0

    with out_path.open("w", encoding="utf-8") as f:
        for ex in items:
            if kept >= args.n:
                break
            decomp = ex.get("question_decomposition") or []
            if not decomp or not all(s.get("answer") for s in decomp):
                skip_bad += 1
                continue
            trace = build_trace_grounded(ex)
            if trace is None:
                skip_ground += 1
                continue

            sup = [p for p in ex["paragraphs"] if p.get("is_supporting")]
            context = "\n\n".join(
                f"[{p['title']}] {p['paragraph_text']}" for p in sup) or None
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
            prompt = (prelude if prelude.rstrip().endswith("<think>")
                      else prelude + "<think>")
            completion = "\n" + trace + "\n</think>\n\n" + ex["answer"] + tok.eos_token

            if len(tok.encode(prompt + completion)) > args.max_tokens:
                skip_len += 1
                continue
            f.write(json.dumps({"prompt": prompt, "completion": completion,
                                "id": ex["id"]}, ensure_ascii=False) + "\n")
            kept += 1

    print(f"4-hop candidates {total} | kept {kept} "
          f"(retention {kept/total:.1%}) | skipped: bad-decomp {skip_bad}, "
          f"ungroundable {skip_ground}, too-long {skip_len} -> {out_path}")
    if not kept:
        raise RuntimeError("No usable v2b examples were produced")
    with out_path.open(encoding="utf-8") as f:
        print("\n--- COMPLETION sample ---\n" + json.loads(next(f))["completion"][:900])


if __name__ == "__main__":
    main()
