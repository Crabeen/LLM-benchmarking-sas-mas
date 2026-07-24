"""Error-case analysis: which questions did fine-tuning break (or fix)?

Compares two runs of the SAME system at the SAME budget level and dumps
side-by-side traces for regressions (frozen correct -> tuned wrong) and,
optionally, fixes (frozen wrong -> tuned correct).

Heuristic pre-labels per regression case (to speed up manual annotation):
  gold-in-thinking   gold string appears in tuned thinking but not the answer
                     -> extraction/format problem, not reasoning
  short-answer       tuned prediction much shorter than frozen's
  judge-vs-strmatch  judge and string match disagree on the tuned prediction
                     -> possible measurement artifact

Usage:
  python -m src.error_cases results/pilot_token results/finetuned_token \
      --system sas --level 1000 --out analysis/sas_regressions_b1000.txt
"""

from __future__ import annotations

import argparse
import json
import re
import string
from collections import Counter
from pathlib import Path


def _norm(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", s).split())


def load(dir_path: str, system: str, level) -> dict:
    rows = {}
    for p in Path(dir_path).glob(f"{system}_b{level}.judged.jsonl"):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def fmt_case(fr: dict, ft: dict, labels: list[str]) -> str:
    bar = "=" * 78
    return "\n".join([
        bar,
        f"ID: {fr['id']}   pre-labels: {', '.join(labels) or '(none)'}",
        f"Q: {fr['question']}",
        f"GOLD: {fr['gold']}  (aliases: {fr['gold_aliases']})",
        "-" * 78,
        f"[FROZEN | correct={fr['judge_correct']} | think_tok="
        f"{fr['budget']['thinking_tokens_total']}]",
        "THINKING:", fr["trace"].get("thinking", "")[:1500],
        f"PREDICTION: {fr['prediction']}",
        "-" * 78,
        f"[TUNED  | correct={ft['judge_correct']} | think_tok="
        f"{ft['budget']['thinking_tokens_total']}]",
        "THINKING:", ft["trace"].get("thinking", "")[:1500],
        f"PREDICTION: {ft['prediction']}",
        f"JUDGE RAW (tuned): {ft.get('judge_raw', '')[:300]}",
        "",
    ])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("frozen_dir")
    ap.add_argument("tuned_dir")
    ap.add_argument("--system", default="sas")
    ap.add_argument("--level", default="1000")
    ap.add_argument("--out", default=None)
    ap.add_argument("--show_fixes", action="store_true",
                    help="also dump frozen-wrong -> tuned-correct cases")
    args = ap.parse_args()

    fr = load(args.frozen_dir, args.system, args.level)
    ft = load(args.tuned_dir, args.system, args.level)
    ids = sorted(set(fr) & set(ft))

    regressions, fixes = [], []
    label_counts = Counter()
    for i in ids:
        a, b = fr[i], ft[i]
        if a["judge_correct"] and not b["judge_correct"]:
            labels = []
            gold_norms = [_norm(g) for g in b["gold_aliases"] if g.strip()]
            think_n = _norm(b["trace"].get("thinking", ""))
            if any(g and g in think_n for g in gold_norms):
                labels.append("gold-in-thinking")
            if len(b["prediction"]) < 0.4 * max(1, len(a["prediction"])):
                labels.append("short-answer")
            if b.get("string_match") != b["judge_correct"]:
                labels.append("judge-vs-strmatch")
            label_counts.update(labels or ["(none)"])
            regressions.append(fmt_case(a, b, labels))
        elif not a["judge_correct"] and b["judge_correct"]:
            fixes.append((a, b))

    n_both = sum(1 for i in ids
                 if fr[i]["judge_correct"] and ft[i]["judge_correct"])
    n_neither = sum(1 for i in ids
                    if not fr[i]["judge_correct"] and not ft[i]["judge_correct"])
    summary = (
        f"system={args.system} level={args.level} n={len(ids)}\n"
        f"both correct: {n_both} | both wrong: {n_neither} | "
        f"REGRESSIONS (frozen ok -> tuned wrong): {len(regressions)} | "
        f"fixes (frozen wrong -> tuned ok): {len(fixes)}\n"
        f"pre-label counts among regressions: {dict(label_counts)}\n"
    )
    print(summary)

    body = summary + "\n" + "\n".join(regressions)
    if args.show_fixes:
        body += "\n\n" + "#" * 78 + "\n# FIXES\n" + "#" * 78 + "\n"
        body += "\n".join(fmt_case(a, b, []) for a, b in fixes)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(body)
        print(f"full dump -> {out}")


if __name__ == "__main__":
    main()
