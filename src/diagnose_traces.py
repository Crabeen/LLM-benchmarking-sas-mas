"""Stage-level failure-mode diagnosis of SAS/MAS traces.

Applies ONE fixed evaluator (official SQuAD/HotpotQA-style normalized EM, token
F1, and gold-containment "string match" -- the repo's operative string metric)
to every meaningful intermediate answer in each trace, then computes:

  oracle_candidate_accuracy   any final-stage candidate correct
  final_accuracy              final prediction correct
  aggregation_regret          oracle - final
  gold_discovery_rate         gold appears at ANY intermediate stage
  preservation_rate           final correct | gold previously discovered
  drop_rate                   1 - preservation_rate
  candidate agreement/diversity, correlated-error rate
  beneficial / harmful flips

Deep-dive on Sequential (per-stage worker chain) and Debate
((A0,B0) -> (A1,B1) -> F transition counts); common oracle/aggregation
measures only for Ensemble, Parallel Roles, Subtask Parallel.

Correctness criteria computed per answer text:
  em_strict   normalized text == normalized gold/alias (official EM)
  f1          max token-F1 over gold + aliases (official definition)
  contain     normalized gold/alias is a substring of normalized text
              (== src.judge.string_match; primary stage-level criterion,
              since intermediate answers are full sentences)

Secondary semantic metric: judge_correct from *.rejudged.jsonl (unified
judge), joined by id -- final answers only (no stage-level judge exists).

Usage:
  python -m src.diagnose_traces results/2wiki_frozen_token [more dirs ...] \
      [--out analysis/diagnostics] [--criterion contain|em_strict] \
      [--n-samples 10]
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import string as _string
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------- evaluator

_ARTICLES = re.compile(r"\b(a|an|the)\b")


def normalize(s: str) -> str:
    """Official SQuAD/HotpotQA/2Wiki/MuSiQue answer normalization."""
    s = s.lower()
    s = "".join(ch for ch in s if ch not in _string.punctuation)
    s = _ARTICLES.sub(" ", s)
    return " ".join(s.split())


def em_strict(text: str, golds: list[str]) -> bool:
    n = normalize(text)
    return any(n == normalize(g) for g in golds if g.strip())


def contain(text: str, golds: list[str]) -> bool:
    n = normalize(text)
    return any(normalize(g) in n for g in golds if g.strip())


def f1(text: str, golds: list[str]) -> float:
    pt = normalize(text).split()
    best = 0.0
    for g in golds:
        gt = normalize(g).split()
        if not gt or not pt:
            continue
        common = Counter(pt) & Counter(gt)
        n_same = sum(common.values())
        if n_same == 0:
            continue
        p, r = n_same / len(pt), n_same / len(gt)
        best = max(best, 2 * p * r / (p + r))
    return best


# ------------------------------------------------------------ stage parsing


def stages_of(row: dict) -> dict:
    """Extract per-architecture stage texts.

    Returns dict with:
      candidates    list[str]  final-stage answer candidates (oracle pool)
      intermediates list[(name, text)]  every meaningful intermediate answer
      thinking      list[str]  raw reasoning texts (extraction-failure check)
      extra         dict       arch-specific fields
    """
    t = row.get("trace") or {}
    sysname = row["system"]
    th = []

    if sysname == "sas":
        th = [t.get("thinking", "")]
        return dict(candidates=[], intermediates=[], thinking=th, extra={})

    if sysname == "sequential":
        finds = t.get("findings") or []
        th = t.get("worker_thinking") or []
        inter = [(f"worker_{i+1}", x) for i, x in enumerate(finds)]
        # candidates for the aggregator = all worker findings
        return dict(candidates=list(finds), intermediates=inter, thinking=th,
                    extra=dict(n_steps=len(finds)))

    if sysname == "debate":
        init = t.get("initial_answers") or []
        imp = t.get("improved_answers") or []
        th = (t.get("debater_thinking") or []) + (t.get("critic_thinking") or [])
        inter = [(f"init_{'AB'[i]}", x) for i, x in enumerate(init[:2])] + \
                [(f"rev_{'AB'[i]}", x) for i, x in enumerate(imp[:2])]
        return dict(candidates=list(imp), intermediates=inter, thinking=th,
                    extra=dict(initial=init, improved=imp,
                               selected=t.get("aggregator_selected_candidate"),
                               label_resolved=t.get("aggregator_label_resolved")))

    if sysname == "ensemble":
        cands = t.get("candidates") or []
        th = t.get("candidate_thinking") or []
        inter = [(f"cand_{i+1}", x) for i, x in enumerate(cands)]
        return dict(candidates=list(cands), intermediates=inter, thinking=th,
                    extra={})

    if sysname == "parallel_roles":
        outs = t.get("role_outputs") or []
        roles = [r.get("name", f"role_{i+1}") if isinstance(r, dict) else str(r)
                 for i, r in enumerate(t.get("roles") or [])]
        while len(roles) < len(outs):
            roles.append(f"role_{len(roles)+1}")
        th = t.get("worker_thinking") or []
        inter = list(zip(roles, outs))
        return dict(candidates=list(outs), intermediates=inter, thinking=th,
                    extra=dict(roles=roles))

    if sysname == "subtask_parallel":
        outs = t.get("task_outputs") or []
        th = t.get("worker_thinking") or []
        inter = [(f"subtask_{i+1}", x) for i, x in enumerate(outs)]
        return dict(candidates=list(outs), intermediates=inter, thinking=th,
                    extra={})

    return dict(candidates=[], intermediates=[], thinking=[], extra={})


# ------------------------------------------------------------- per-item diag


def diagnose_item(row: dict, criterion: str) -> dict:
    golds = [row.get("gold", "")] + list(row.get("gold_aliases") or [])
    golds = [g for g in golds if isinstance(g, str) and g.strip()]
    crit = contain if criterion == "contain" else em_strict

    st = stages_of(row)
    pred = row.get("prediction") or ""

    d: dict = dict(
        id=row["id"], system=row["system"], budget=row["budget_level"],
        final_contain=contain(pred, golds), final_em=em_strict(pred, golds),
        final_f1=round(f1(pred, golds), 4),
    )
    d["final_ok"] = d["final_contain"] if criterion == "contain" else d["final_em"]

    inter_ok = [(name, crit(x, golds)) for name, x in st["intermediates"]]
    cand_ok = [crit(x, golds) for x in st["candidates"]]
    think_ok = any(contain(x, golds) for x in st["thinking"])

    d["stage_ok"] = inter_ok
    d["oracle"] = any(cand_ok) if cand_ok else None
    d["gold_discovered"] = any(ok for _, ok in inter_ok) or think_ok
    d["gold_in_thinking"] = think_ok

    # interpretation labels (user's table)
    labels = []
    if d["oracle"] and not d["final_ok"]:
        labels.append("aggregation_failure")
    if d["gold_discovered"] and not d["final_ok"]:
        labels.append("drop_after_discovery")
    if d["gold_discovered"] and d["final_ok"] and not (inter_ok and inter_ok[0][1]):
        labels.append("late_discovery_preserved")
    if think_ok and not d["final_ok"] and not any(ok for _, ok in inter_ok):
        labels.append("extraction_failure")  # gold only ever in reasoning
    if not d["gold_discovered"] and not d["final_ok"]:
        labels.append("gold_never_found")

    # candidate agreement / diversity (final-stage candidates)
    if st["candidates"]:
        norms = [normalize(x) for x in st["candidates"]]
        n_distinct = len(set(norms))
        d["n_candidates"] = len(norms)
        d["n_distinct"] = n_distinct
        d["all_agree"] = n_distinct == 1
        d["correlated_error"] = (n_distinct == 1 and not any(cand_ok))
        if len(cand_ok) >= 2 and any(cand_ok) != all(cand_ok):
            labels.append("productive_diversity" if d["final_ok"]
                          else "diversity_wasted")
        if d["correlated_error"]:
            labels.append("correlated_error")

    # ---- architecture-specific transitions
    if row["system"] == "sequential":
        oks = [ok for _, ok in inter_ok]
        d["seq_first_correct_stage"] = (oks.index(True) + 1) if any(oks) else None
        d["seq_last_worker_ok"] = oks[-1] if oks else None
        d["seq_c_to_w"] = sum(1 for a, b in zip(oks, oks[1:]) if a and not b)
        d["seq_w_to_c"] = sum(1 for a, b in zip(oks, oks[1:]) if not a and b)
        if oks and oks[-1] and not d["final_ok"]:
            labels.append("aggregator_lost_final_worker")
        if d["seq_c_to_w"]:
            labels.append("worker_chain_loss")

    if row["system"] == "debate":
        init, imp = st["extra"]["initial"], st["extra"]["improved"]
        i_ok = [crit(x, golds) for x in init[:2]]
        r_ok = [crit(x, golds) for x in imp[:2]]
        while len(i_ok) < 2: i_ok.append(False)
        while len(r_ok) < 2: r_ok.append(False)
        cw = "".join("C" if x else "W" for x in i_ok)
        rw = "".join("C" if x else "W" for x in r_ok)
        fin = "C" if d["final_ok"] else "W"
        d["debate_transition"] = f"{cw}->{rw}->{fin}"
        per = []
        for a, b in zip(i_ok, r_ok):
            per.append(("C" if a else "W") + ">" + ("C" if b else "W"))
        d["debate_per_debater"] = per
        d["debate_beneficial_flips"] = per.count("W>C")
        d["debate_harmful_flips"] = per.count("C>W")
        if "C>W" in per:
            labels.append("harmful_revision_flip")
        if "W>C" in per:
            labels.append("beneficial_revision_flip")
        sel = st["extra"].get("selected")
        d["debate_selected"] = sel
        if r_ok[0] != r_ok[1] and sel in ("A", "B"):
            picked_ok = r_ok[0] if sel == "A" else r_ok[1]
            d["debate_pick_when_split"] = "correct" if picked_ok else "wrong"
            if not picked_ok:
                labels.append("aggregator_picked_wrong_side")

    d["labels"] = labels
    return d


# ------------------------------------------------------------------ metrics


def rate(xs):
    xs = list(xs)
    return round(sum(xs) / len(xs), 4) if xs else None


def summarize(items: list[dict], judge: dict) -> dict:
    n = len(items)
    disc = [d for d in items if d["gold_discovered"]]
    orc = [d for d in items if d["oracle"] is not None]
    out = dict(
        n=n,
        final_accuracy=rate(d["final_ok"] for d in items),
        final_em_strict=rate(d["final_em"] for d in items),
        final_f1=rate(d["final_f1"] for d in items),
        judge_accuracy=rate(judge[d["id"]] for d in items if d["id"] in judge)
        if judge else None,
        oracle_candidate_accuracy=rate(d["oracle"] for d in orc),
        gold_discovery_rate=rate(d["gold_discovered"] for d in items),
        preservation_rate=rate(d["final_ok"] for d in disc),
        drop_rate=rate(not d["final_ok"] for d in disc),
        extraction_failure_rate=rate("extraction_failure" in d["labels"]
                                     for d in items),
    )
    if out["oracle_candidate_accuracy"] is not None and out["final_accuracy"] is not None:
        out["aggregation_regret"] = round(
            out["oracle_candidate_accuracy"] - out["final_accuracy"], 4)
    cand = [d for d in items if "n_candidates" in d]
    if cand:
        out["mean_distinct_candidates"] = rate(d["n_distinct"] for d in cand)
        out["all_agree_rate"] = rate(d["all_agree"] for d in cand)
        out["correlated_error_rate"] = rate(d["correlated_error"] for d in cand)
        out["productive_diversity_rate"] = rate(
            "productive_diversity" in d["labels"] for d in cand)
    sysname = items[0]["system"] if items else ""
    if sysname == "sequential":
        out["seq_c_to_w_total"] = sum(d["seq_c_to_w"] for d in items)
        out["seq_w_to_c_total"] = sum(d["seq_w_to_c"] for d in items)
        out["seq_last_worker_acc"] = rate(d["seq_last_worker_ok"] for d in items
                                          if d["seq_last_worker_ok"] is not None)
        out["seq_aggregator_lost_final_worker"] = sum(
            "aggregator_lost_final_worker" in d["labels"] for d in items)
    if sysname == "debate":
        out["debate_beneficial_flips"] = sum(d["debate_beneficial_flips"] for d in items)
        out["debate_harmful_flips"] = sum(d["debate_harmful_flips"] for d in items)
        per = Counter(p for d in items for p in d["debate_per_debater"])
        out.update({f"debate_{k.replace('>','_to_')}": v for k, v in per.items()})
        split = [d for d in items if "debate_pick_when_split" in d]
        out["debate_split_cases"] = len(split)
        out["debate_pick_correct_when_split"] = rate(
            d["debate_pick_when_split"] == "correct" for d in split)
    return out


# --------------------------------------------------------------------- main


def load_judge(run_dir: Path, sysname: str, level: int) -> dict:
    """id -> judge_correct from the unified rejudged file (fallback: judged)."""
    for suf in (".rejudged.jsonl", ".judged.jsonl"):
        p = run_dir / f"{sysname}_b{level}{suf}"
        if p.exists():
            return {r["id"]: bool(r["judge_correct"])
                    for r in map(json.loads, p.read_text().splitlines())}
    return {}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dirs", nargs="+")
    ap.add_argument("--out", default="analysis/diagnostics")
    ap.add_argument("--criterion", default="contain",
                    choices=["contain", "em_strict"])
    ap.add_argument("--n-samples", type=int, default=10)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    for run in map(Path, args.run_dirs):
        out_dir = Path(args.out) / run.name
        out_dir.mkdir(parents=True, exist_ok=True)
        raw_files = sorted(p for p in run.glob("*.jsonl")
                           if ".judged" not in p.name and ".rejudged" not in p.name)
        groups: dict[tuple, list[dict]] = defaultdict(list)
        for p in raw_files:
            for line in p.read_text().splitlines():
                r = json.loads(line)
                groups[(r["system"], r["budget_level"])].append(r)

        summary_rows, debate_rows, item_rows = [], [], []
        samples: dict[str, list] = defaultdict(list)
        for (sysname, level), rows in sorted(groups.items()):
            judge = load_judge(run, sysname, level)
            diags = [diagnose_item(r, args.criterion) for r in rows]
            s = summarize(diags, judge)
            s.update(system=sysname, budget=level)
            summary_rows.append(s)
            for d in diags:
                item_rows.append(d)
                for lab in d["labels"]:
                    samples[f"{sysname}_{lab}"].append(d)
            if sysname == "debate":
                cnt = Counter(d["debate_transition"] for d in diags)
                for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
                    debate_rows.append(dict(budget=level, transition=k, count=v))

        # ---- write outputs
        cols = ["system", "budget"] + sorted(
            {k for s in summary_rows for k in s} - {"system", "budget"})
        with open(out_dir / "metrics.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(summary_rows)
        if debate_rows:
            with open(out_dir / "debate_transitions.csv", "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=["budget", "transition", "count"])
                w.writeheader()
                w.writerows(debate_rows)
        with open(out_dir / "per_item.jsonl", "w") as fh:
            for d in item_rows:
                fh.write(json.dumps(d, default=str) + "\n")
        sample_dir = out_dir / "samples"
        sample_dir.mkdir(exist_ok=True)
        raw_by_key = {(r["system"], r["budget_level"], r["id"]): r
                      for rows in groups.values() for r in rows}
        for cat, ds in samples.items():
            pick = rng.sample(ds, min(args.n_samples, len(ds)))
            with open(sample_dir / f"{cat}.jsonl", "w") as fh:
                for d in pick:
                    raw = raw_by_key[(d["system"], d["budget"], d["id"])]
                    fh.write(json.dumps(dict(diag=d, question=raw["question"],
                                             gold=raw["gold"],
                                             gold_aliases=raw["gold_aliases"],
                                             prediction=raw["prediction"],
                                             trace=raw["trace"]),
                                        default=str) + "\n")

        # ---- console table
        print(f"\n=== {run.name}  (criterion: {args.criterion}) ===")
        keyed = ["final_accuracy", "judge_accuracy", "oracle_candidate_accuracy",
                 "aggregation_regret", "gold_discovery_rate",
                 "preservation_rate", "drop_rate", "extraction_failure_rate"]
        hdr = f"{'system':<18}{'budget':>7}" + "".join(f"{k[:12]:>13}" for k in keyed)
        print(hdr); print("-" * len(hdr))
        for s in summary_rows:
            print(f"{s['system']:<18}{s['budget']:>7}" + "".join(
                f"{(s.get(k) if s.get(k) is not None else '-'):>13}" for k in keyed))
        print(f"written: {out_dir}/")


if __name__ == "__main__":
    main()
