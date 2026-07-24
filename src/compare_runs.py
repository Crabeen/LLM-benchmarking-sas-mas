"""Cross-run comparison: is DeltaGap = Gap_finetuned - Gap_frozen significant?

Per question i (same 200 questions in all four runs, same data seed):
    delta_i = (SAS_ft_i - Seq_ft_i) - (SAS_fr_i - Seq_fr_i)
Paired bootstrap over questions gives a CI for the mean delta.

Usage: python -m src.compare_runs results/pilot_token results/finetuned_token
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def load(dir_path: str) -> dict:
    by = defaultdict(dict)   # (system, level) -> {id: correct}
    for p in sorted(Path(dir_path).glob(os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl"))):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            by[(r["system"], r["budget_level"])][r["id"]] = int(r["judge_correct"])
    return by


def main() -> None:
    frozen, tuned = load(sys.argv[1]), load(sys.argv[2])
    levels = sorted({lvl for (_, lvl) in frozen} & {lvl for (_, lvl) in tuned})
    rng = np.random.default_rng(0)

    print(f"{'level':>8}{'Gap_frozen':>12}{'Gap_tuned':>12}{'DeltaGap':>10}"
          f"{'95% CI':>20}{'':>4}")
    for lvl in levels:
        ids = sorted(
            set(frozen[("sas", lvl)]) & set(frozen[("sequential", lvl)])
            & set(tuned[("sas", lvl)]) & set(tuned[("sequential", lvl)]))
        if not ids:
            continue
        d = np.array([
            (tuned[("sas", lvl)][i] - tuned[("sequential", lvl)][i])
            - (frozen[("sas", lvl)][i] - frozen[("sequential", lvl)][i])
            for i in ids], dtype=float)
        gf = np.mean([frozen[("sas", lvl)][i] - frozen[("sequential", lvl)][i]
                      for i in ids])
        gt = np.mean([tuned[("sas", lvl)][i] - tuned[("sequential", lvl)][i]
                      for i in ids])
        boots = rng.choice(d, size=(10000, len(d)), replace=True).mean(axis=1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        sig = "significant" if lo > 0 or hi < 0 else "not significant"
        print(f"{lvl:>8}{gf:>+12.3f}{gt:>+12.3f}{d.mean():>+10.3f}"
              f"{f'[{lo:+.3f},{hi:+.3f}]':>20}  ({sig}, n={len(ids)})")


if __name__ == "__main__":
    main()
