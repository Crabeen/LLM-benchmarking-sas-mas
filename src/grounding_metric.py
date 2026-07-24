"""Grounding metrics for SAS traces.

Why not keyword matching: the v1/v2a lexical proxy ("context"/"passage"/
"mention") is meaningless for v2b, whose trace template itself contains such
words. And a model can mimic the citation template while fabricating content.

Measures reported per run (SAS, budget 1000):
  lex-ref      keyword proxy; comparable across v1/v2a only, kept for continuity
  cited        fraction of questions whose thinking emits >=1 "From [T]: span" line
  title-ok     of all citations, fraction whose title matches a paragraph title
               actually present in that question's context
  span-ok      of all citations, fraction whose quoted span is genuinely a
               substring of THAT paragraph  <- copying real evidence, not
               fabricating it
Titles/spans are normalised (whitespace collapsed, ellipsis stripped) before
comparison. span-ok is the load-bearing number: passing it requires attending
to the supplied context. It does NOT establish that the evidence entails the
step's answer - that would need an entailment check.

Context is re-fetched from MuSiQue by question id, so this works on result
files written before context was logged.

Usage:
  python -m src.grounding_metric results/pilot_token results/finetuned_token \
      results/v2a_token results/v2b_token
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from datasets import load_dataset

KEYWORDS = ("context", "passage", "mention")
CITE_RE = re.compile(r"(?m)^From \[([^\]\n]+)\]:\s*(.+)$")


def _norm(s: str) -> str:
    return " ".join(s.replace("...", " ").replace("…", " ").split()).lower()


def load_contexts(ids: set[str]) -> dict[str, dict[str, str]]:
    """id -> {normalised paragraph title: normalised paragraph text}."""
    va = load_dataset("dgslibisey/MuSiQue", split="validation")
    out = {}
    for ex in va:
        if ex["id"] in ids:
            out[ex["id"]] = {_norm(p["title"]): _norm(p["paragraph_text"])
                             for p in ex["paragraphs"] if p.get("is_supporting")}
    return out


def main() -> None:
    dirs = sys.argv[1:]
    ids = set()
    for d in dirs:
        p = Path(d) / "sas_b1000.judged.jsonl"
        if p.exists():
            ids |= {json.loads(l)["id"] for l in p.read_text().splitlines()}
    ctxs = load_contexts(ids)

    print(f"{'run':<20}{'acc':>7}{'lex-ref':>9}{'cited':>7}"
          f"{'title-ok':>10}{'span-ok':>9}{'cites/q':>9}{'think_tok':>11}")
    for d in dirs:
        p = Path(d) / "sas_b1000.judged.jsonl"
        if not p.exists():
            print(f"{Path(d).name:<20}  (missing sas_b1000.judged.jsonl)")
            continue
        rows = [json.loads(l) for l in p.read_text().splitlines()]
        lex = cited = n_cite = title_ok = span_ok = 0
        for r in rows:
            th = r["trace"].get("thinking", "")
            if any(k in th.lower() for k in KEYWORDS):
                lex += 1
            cites = CITE_RE.findall(th)
            if cites:
                cited += 1
            paras = ctxs.get(r["id"], {})
            for title, span in cites:
                n_cite += 1
                t, s = _norm(title), _norm(span)
                if t in paras:
                    title_ok += 1
                    if s and s in paras[t]:
                        span_ok += 1
        n = len(rows)
        acc = sum(r["judge_correct"] for r in rows) / n
        tok = sum(r["budget"]["thinking_tokens_total"] for r in rows) / n
        t_ok = f"{title_ok/n_cite:.0%}" if n_cite else "n/a"
        s_ok = f"{span_ok/n_cite:.0%}" if n_cite else "n/a"
        print(f"{Path(d).name:<20}{acc:>7.3f}{lex/n:>9.0%}{cited/n:>7.0%}"
              f"{t_ok:>10}{s_ok:>9}{n_cite/n:>9.1f}{tok:>11.0f}")


if __name__ == "__main__":
    main()
