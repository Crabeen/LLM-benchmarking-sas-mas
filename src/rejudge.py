"""Re-judge existing predictions with ONE fixed judge model across all arms.

Why: run_experiment.py judges with whatever model produced the predictions, so
frozen results were judged by frozen, v2b results by v2b, and so on. Every
cross-arm claim (Gap, DeltaGap) therefore relies on comparing scores from
different graders. This script re-scores the SAME predictions with a single
judge so the comparison uses one ruler.

No inference is re-run: raw *.jsonl prediction files are read as-is. Output
goes to *.rejudged.jsonl, leaving the original *.judged.jsonl untouched, so
both gradings stay on disk and can be compared (agreement is reported).

Judge prompt/rubric: identical to src/prompts.py (paper Appendix D.7), parsed
for Decision: TRUE/FALSE, with the same lenient fallback as src/judge.py.

Usage
-----
  # default judge = the frozen base model
  python -m src.rejudge results/pilot_token results/finetuned_token \
      results/v2a_token results/v2aa_token results/v2b_token

  # alternative fixed judge (report agreement as a robustness check)
  python -m src.rejudge --judge_model Qwen/Qwen3-8B results/*_token

  # inspect disagreements between the original and the unified judge
  python -m src.rejudge --report_only results/pilot_token

Notes
-----
* The judge runs with think_budget=0 and temperature 0, matching src/judge.py.
* Empty predictions score False without calling the model (same as judge.py).
* Outputs are written atomically (tmp + replace), so --skip_existing is
  safe: an existing .rejudged.jsonl is always a complete file.
* The judge sees only the canonical gold answer, matching src/judge.py;
  gold_aliases feed the string-match diagnostic only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .engine import Engine
from .judge import string_match
from . import prompts

JUDGED_SUFFIX = ".judged.jsonl"
REJUDGED_SUFFIX = ".rejudged.jsonl"


def parse_decision(raw: str) -> tuple[bool, str]:
    """Same parsing rule as src/judge.py, plus how the verdict was obtained.

    parse_mode: 'explicit'  Decision: TRUE/FALSE field present
                'fallback'  no Decision field; whole-text TRUE/FALSE heuristic
                'invalid'   nothing parseable -> scored False
    """
    m = re.search(r"Decision\s*[:=]\s*[\"']?\s*(TRUE|FALSE)", raw, re.I)
    if m:
        return m.group(1).upper() == "TRUE", "explicit"
    has_t = bool(re.search(r"\bTRUE\b", raw, re.I))
    has_f = bool(re.search(r"\bFALSE\b", raw, re.I))
    if has_t or has_f:
        return (has_t and not has_f), "fallback"
    return False, "invalid"


def prediction_files(d: Path) -> list[Path]:
    """Raw prediction files (exclude judged/rejudged outputs)."""
    return sorted(p for p in d.glob("*.jsonl")
                  if not p.name.endswith(JUDGED_SUFFIX)
                  and not p.name.endswith(REJUDGED_SUFFIX))


def report(dirs: list[str]) -> None:
    """Compare original per-arm judging with the unified judging."""
    print(f"{'run':<24}{'file':<28}{'n':>5}{'acc_orig':>10}"
          f"{'acc_uni':>9}{'agree':>8}{'flips':>18}")
    for d in dirs:
        for raw in prediction_files(Path(d)):
            uni = raw.with_name(raw.stem + REJUDGED_SUFFIX)
            old = raw.with_name(raw.stem + JUDGED_SUFFIX)
            if not uni.exists() or not old.exists():
                continue
            o_rows = [json.loads(l) for l in old.read_text().splitlines() if l.strip()]
            u_rows = [json.loads(l) for l in uni.read_text().splitlines() if l.strip()]
            o = {r["id"]: r for r in o_rows}
            u = {r["id"]: r for r in u_rows}
            if len(o) != len(o_rows) or len(u) != len(u_rows):
                raise RuntimeError(f"duplicate ids in {raw.stem}: "
                                   f"orig {len(o_rows)}->{len(o)}, uni {len(u_rows)}->{len(u)}")
            if set(o) != set(u):
                raise RuntimeError(f"id mismatch in {raw.stem}: orig={len(o)}, "
                                   f"unified={len(u)}, shared={len(set(o) & set(u))}")
            ids = sorted(o)
            if not ids:
                continue
            ao = sum(o[i]["judge_correct"] for i in ids) / len(ids)
            au = sum(u[i]["judge_correct"] for i in ids) / len(ids)
            agree = sum(o[i]["judge_correct"] == u[i]["judge_correct"] for i in ids) / len(ids)
            t2f = sum(o[i]["judge_correct"] and not u[i]["judge_correct"] for i in ids)
            f2t = sum(not o[i]["judge_correct"] and u[i]["judge_correct"] for i in ids)
            print(f"{Path(d).name:<24}{raw.stem:<28}{len(ids):>5}{ao:>10.3f}"
                  f"{au:>9.3f}{agree:>8.1%}{f'  T->F {t2f}, F->T {f2t}':>18}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+", help="results directories to re-judge")
    ap.add_argument("--judge_model", default="Qwen/Qwen3-4B",
                    help="single fixed judge for every arm (default: frozen base model)")
    ap.add_argument("--max_model_len", type=int, default=16384)
    ap.add_argument("--gpu_memory_utilization", type=float, default=0.90)
    ap.add_argument("--enforce_eager", action="store_true",
                    help="skip torch.compile (avoids the stdatomic issue on "
                         "un-warmed checkpoints; judging speed is irrelevant)")
    ap.add_argument("--answer_max_tokens", type=int, default=256)
    ap.add_argument("--skip_existing", action="store_true",
                help="skip files whose .rejudged.jsonl already exists "
                     "(outputs are written atomically, so an existing "
                     "file is always complete)")
    ap.add_argument("--report_only", action="store_true")
    args = ap.parse_args()

    if args.report_only:
        report(args.dirs)
        return

    targets = []
    for d in args.dirs:
        for raw in prediction_files(Path(d)):
            out = raw.with_name(raw.stem + REJUDGED_SUFFIX)
            if args.skip_existing and out.exists():
                print(f"skip (exists): {out}")
                continue
            targets.append((raw, out))
    if not targets:
        print("nothing to do")
        return
    print(f"judging {len(targets)} files with {args.judge_model}\n")

    engine = Engine(model=args.judge_model,
                    max_model_len=args.max_model_len,
                    gpu_memory_utilization=args.gpu_memory_utilization,
                    enforce_eager=args.enforce_eager)

    for raw, out in targets:
        rows = [json.loads(l) for l in raw.read_text().splitlines() if l.strip()]
        todo = [r for r in rows if r.get("prediction", "").strip()]
        msgs = [[{"role": "system", "content": prompts.JUDGE_SYSTEM},
                 {"role": "user", "content": prompts.judge_user(
                     r["question"], r["prediction"], r["gold"])}] for r in todo]
        results = engine.generate_batch(
            msgs, think_budget=0, answer_max_tokens=args.answer_max_tokens,
            temperature=0.0) if msgs else []
        verdicts = {id(r): g for r, g in zip(todo, results)}

        n_true = 0
        modes: dict[str, int] = {}
        tmp = out.with_name(out.name + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            for r in rows:
                g = verdicts.get(id(r))
                if g is None:
                    correct, mode = False, "empty_prediction"
                else:
                    correct, mode = parse_decision(g.answer)
                n_true += correct
                modes[mode] = modes.get(mode, 0) + 1
                r["judge_correct"] = correct
                r["judge_raw"] = g.answer if g else ""
                r["judge_model"] = args.judge_model
                r["judge_parse_mode"] = mode
                r["string_match"] = string_match(
                    r.get("prediction", ""), r.get("gold_aliases", [r["gold"]]))
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        tmp.replace(out)   # atomic: a .rejudged.jsonl only ever means "complete"
        print(f"{out}  n={len(rows)}  acc={n_true/max(1,len(rows)):.3f}  "
              f"parse={modes}")

    print("\n--- original vs unified judge ---")
    report(args.dirs)


if __name__ == "__main__":
    main()
