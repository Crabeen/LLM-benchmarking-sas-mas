"""Aggregate judged results: accuracy with 95% bootstrap CI, diagnostics,
the SAS-vs-MAS gap per budget level, and a PAIRED bootstrap CI for the gap
(both systems answer the same questions, so the paired test is the correct
one for the thesis's main quantity).

Usage: python -m src.analyze results/pilot_token
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def bootstrap_ci(values: list[int], n_boot: int = 10000, seed: int = 0):
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=float)
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    means = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return arr.mean(), *np.percentile(means, [2.5, 97.5])


def main() -> None:
    out_dir = Path(sys.argv[1])
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for path in sorted(out_dir.glob(os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl"))):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            groups[(row["system"], row["budget_level"])].append(row)

    header = (f"{'system':<12}{'budget':>8}{'acc':>7}{'95% CI':>17}"
              f"{'strmatch':>9}{'think_tok':>10}{'calls':>7}"
              f"{'sec/q':>7}{'timeout':>8}{'trunc':>7}{'planfail':>9}")
    print(header)
    print("-" * len(header))

    acc_by = {}
    for (system, level), rows in sorted(groups.items()):
        acc, lo, hi = bootstrap_ci([int(r["judge_correct"]) for r in rows])
        acc_by[(system, level)] = acc
        sm = np.mean([int(r["string_match"]) for r in rows])
        tok = np.mean([r["budget"]["thinking_tokens_total"] for r in rows])
        calls = np.mean([r["budget"]["n_calls"] for r in rows])
        sec = np.mean([r["wall_seconds"] for r in rows])
        to = np.mean([int(r["timeout"]) for r in rows])
        tr = np.mean([int(r["budget"]["any_truncated"]) for r in rows])
        pf = np.mean([
            int(r.get("trace", {}).get("plan_parse_mode", "json")
                not in ("json", "yaml"))
            for r in rows]) if system != "sas" else 0.0
        print(f"{system:<12}{level:>8}{acc:>7.3f}"
              f"{f'[{lo:.3f},{hi:.3f}]':>17}{sm:>9.3f}{tok:>10.0f}"
              f"{calls:>7.1f}{sec:>7.1f}{to:>8.2f}{tr:>7.2f}{pf:>9.2f}")

    levels = sorted({lvl for (_, lvl) in acc_by})
    print("\nGap = Acc(SAS) - Acc(Sequential):")
    for lvl in levels:
        s, m = acc_by.get(("sas", lvl)), acc_by.get(("sequential", lvl))
        if s is not None and m is not None:
            print(f"  budget {lvl}: {s - m:+.3f}")

    print("\nPaired bootstrap for the gap (same questions, per-question diff):")
    rng2 = np.random.default_rng(0)
    for lvl in levels:
        s_rows = {r["id"]: int(r["judge_correct"])
                  for r in groups.get(("sas", lvl), [])}
        m_rows = {r["id"]: int(r["judge_correct"])
                  for r in groups.get(("sequential", lvl), [])}
        ids = sorted(set(s_rows) & set(m_rows))
        if not ids:
            continue
        d = np.array([s_rows[i] - m_rows[i] for i in ids], dtype=float)
        boots = rng2.choice(d, size=(10000, len(d)), replace=True).mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        sig = "significant" if lo > 0 or hi < 0 else "not significant"
        print(f"  budget {lvl}: gap {d.mean():+.3f}, "
              f"paired 95% CI [{lo:+.3f}, {hi:+.3f}]  ({sig})")


if __name__ == "__main__":
    main()
