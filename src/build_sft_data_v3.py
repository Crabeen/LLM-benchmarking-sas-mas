"""v3 SFT data: rejection-sampled reasoning traces from the frozen model.

Motivation (v1/v2 error analysis). All previous arms supervise a fixed,
short stop point: the training completion is

    <short templated trace>\n</think>\n\n<answer><eos>

so token-level cross-entropy directly rewards emitting </think> right after
~100 trace tokens. The tuned model learns "stop thinking at the demonstrated
length"; the budget cap stops binding (think_tok 112 vs frozen 690, trunc 0,
cap 1000->2000 inert). Completion-only masking (v2a) does not touch this —
it removes prompt-token loss but keeps the same short-stop supervision — and
v2b changes trace *content* while keeping the same stop geometry.

v3 fix: let the frozen model generate its own traces under the paper's SAS
prompt (Appendix D.1, oracle context, identical chat layout to engine.py),
and keep only candidates that
  (a) close </think> on their own BEFORE the generation cap (natural stop;
      candidates truncated by the cap are discarded, never supervised), and
  (b) produce an answer that passes the gold/alias normalized-substring
      check (same rule as judge.py's string-match fallback).
The supervised stop position is then the model's own natural one, traces are
naturally grounded in the context, and correctness is verified — the SFT
objective is aligned with the evaluated quantity.

Known selection bias (report in thesis): questions the frozen model never
solves within k samples are dropped, so the kept set skews easier. Log
coverage; raising --k tightens this at linear cost.

Output jsonl rows: {"prompt", "completion", "id", "think_tokens"} where
  prompt      = chat prelude ending with the opened <think> tag, exactly as
                engine.py lays it out at inference time;
  completion  = trace + "\n</think>\n\n" + answer + eos_token
                (mirrors engine.py phase-2 concatenation byte-for-byte).

Run on a GPU node (needs vLLM):
  python -m src.build_sft_data_v3 --out data/sft_train_v3.jsonl --k 4
"""

from __future__ import annotations

import argparse
import json
import random
import re
import string
from pathlib import Path

from datasets import load_dataset
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams

from . import prompts

THINK_CLOSE = "</think>"
CTX_KEYWORDS = ("context", "passage", "mention", "paragraph")


def normalize(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def is_correct(pred: str, golds: list[str]) -> bool:
    p = normalize(pred)
    if not p:
        return False
    for g in golds:
        ng = normalize(g)
        if ng and ng in p:
            return True
    return False


def build_prelude(tok, question: str, context: str | None) -> str:
    """Identical construction to build_sft_data.py / engine.py."""
    messages = [
        {"role": "system", "content": prompts.SAS_SYSTEM},
        {"role": "user", "content": prompts.sas_user(question, context)},
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
    return prelude


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sft_train_v3.jsonl")
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--hops", default="4hop")
    ap.add_argument("--context", default="oracle", help="'oracle' | 'closed'")
    ap.add_argument("--k", type=int, default=4,
                    help="samples per question")
    ap.add_argument("--think_cap", type=int, default=1536,
                    help="generation cap for the thinking phase; chosen well "
                         "above frozen natural length (~690) so it rarely "
                         "binds. Truncated candidates are DISCARDED.")
    ap.add_argument("--answer_max", type=int, default=128)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top_p", type=float, default=0.95)
    ap.add_argument("--min_think", type=int, default=32,
                    help="drop degenerate ultra-short traces")
    ap.add_argument("--max_tokens", type=int, default=4096,
                    help="drop finished examples longer than this")
    ap.add_argument("--n", type=int, default=100000,
                    help="cap on kept examples (default: keep all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max_model_len", type=int, default=8192)
    ap.add_argument("--gpu_mem", type=float, default=0.90)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    ds = load_dataset("dgslibisey/MuSiQue", split="train")
    items = [ex for ex in ds
             if args.hops == "all" or str(ex["id"]).startswith(args.hops)]
    rng = random.Random(args.seed)
    rng.shuffle(items)

    preludes, meta = [], []
    for ex in items:
        if args.context == "oracle":
            paras = [p for p in ex["paragraphs"] if p.get("is_supporting")]
            context = "\n\n".join(
                f"[{p['title']}] {p['paragraph_text']}" for p in paras) or None
        else:
            context = None
        golds = [ex["answer"]] + list(ex.get("answer_aliases") or [])
        preludes.append(build_prelude(tok, ex["question"], context))
        meta.append({"id": ex["id"], "golds": golds})

    print(f"[gen] {len(preludes)} train questions, k={args.k}, "
          f"think_cap={args.think_cap}, T={args.temperature}")

    llm = LLM(model=args.model,
              max_model_len=args.max_model_len,
              gpu_memory_utilization=args.gpu_mem, enforce_eager=True)

    # ---- phase 1: sample k thinking candidates per question ----
    sp_think = SamplingParams(
        n=args.k, max_tokens=args.think_cap,
        temperature=args.temperature, top_p=args.top_p,
        stop=[THINK_CLOSE], seed=args.seed)
    outs = llm.generate(preludes, sp_think)

    cands = []           # (qi, sample_idx, thinking_text, n_think_tokens)
    n_trunc = n_short = 0
    for qi, o in enumerate(outs):
        for si, c in enumerate(o.outputs):
            if c.finish_reason == "length":      # hit the cap: unnatural stop
                n_trunc += 1
                continue
            if len(c.token_ids) < args.min_think:
                n_short += 1
                continue
            cands.append((qi, si, c.text, len(c.token_ids)))
    print(f"[gen] candidates kept {len(cands)} "
          f"(discarded: truncated {n_trunc}, too-short {n_short})")

    # ---- phase 2: deterministic answer for every candidate ----
    # Mirrors engine.py: answer prompt = prelude + thinking + "\n</think>\n\n"
    answer_prompts = [preludes[qi] + th + "\n" + THINK_CLOSE + "\n\n"
                      for qi, _, th, _ in cands]
    sp_ans = SamplingParams(max_tokens=args.answer_max, temperature=0.0,
                            seed=args.seed)
    outs2 = llm.generate(answer_prompts, sp_ans)

    # ---- rejection filter, first correct candidate per question ----
    best: dict[int, tuple[int, str, int, str]] = {}   # qi -> (si, th, ntok, ans)
    for (qi, si, th, ntok), o2 in zip(cands, outs2):
        ans = o2.outputs[0].text.strip()
        if not ans or not is_correct(ans, meta[qi]["golds"]):
            continue
        if qi not in best or si < best[qi][0]:
            best[qi] = (si, th, ntok, ans)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = skipped_len = 0
    think_lens, ctx_ref = [], 0
    with out_path.open("w") as f:
        for qi in sorted(best):
            if kept >= args.n:
                break
            si, th, ntok, ans = best[qi]
            completion = th + "\n" + THINK_CLOSE + "\n\n" + ans + tok.eos_token
            text = preludes[qi] + completion
            if len(tok.encode(text)) > args.max_tokens:
                skipped_len += 1
                continue
            f.write(json.dumps(
                {"prompt": preludes[qi], "completion": completion,
                 "id": meta[qi]["id"], "think_tokens": ntok},
                ensure_ascii=False) + "\n")
            kept += 1
            think_lens.append(ntok)
            if any(k in th.lower() for k in CTX_KEYWORDS):
                ctx_ref += 1

    think_lens.sort()
    def pct(p: float) -> int:
        return think_lens[min(len(think_lens) - 1,
                              int(p * len(think_lens)))] if think_lens else 0
    stats = {
        "questions": len(preludes),
        "kept": kept,
        "coverage": round(kept / max(1, len(preludes)), 3),
        "skipped_too_long": skipped_len,
        "discarded_truncated_candidates": n_trunc,
        "think_tokens_mean": round(sum(think_lens) / max(1, len(think_lens))),
        "think_tokens_p10_p50_p90": [pct(.10), pct(.50), pct(.90)],
        "ctx_keyword_rate": round(ctx_ref / max(1, kept), 3),
        "k": args.k, "think_cap": args.think_cap,
        "temperature": args.temperature, "seed": args.seed,
    }
    Path(str(out_path) + ".stats.json").write_text(json.dumps(stats, indent=2))
    print(f"[gen] kept {kept}/{len(preludes)} "
          f"(coverage {stats['coverage']:.0%}), "
          f"think_tok mean {stats['think_tokens_mean']} "
          f"p10/50/90 {stats['think_tokens_p10_p50_p90']}, "
          f"ctx-ref {stats['ctx_keyword_rate']:.0%} -> {out_path}")


if __name__ == "__main__":
    main()
