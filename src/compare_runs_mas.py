"""Compare how fine-tuning changes every MAS-vs-SAS paired gap.

For architecture m and question i:

    delta_i = (m_tuned_i - sas_tuned_i) - (m_frozen_i - sas_frozen_i)

A positive DeltaGap means fine-tuning moved that MAS architecture upward
relative to SAS. It does not by itself imply that either system improved.

Usage:
    python -m src.compare_runs results/frozen_all_mas_token \
        results/v3b_all_mas_token
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np


def load(dir_path: str) -> dict:
    by = defaultdict(dict)
    suffix = os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl")
    for path in sorted(Path(dir_path).glob(suffix)):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            by[(row["system"], row["budget_level"])][row["id"]] = int(
                row["judge_correct"]
            )
    return by


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("frozen_dir")
    parser.add_argument("tuned_dir")
    parser.add_argument("--n-boot", type=int, default=10000)
    args = parser.parse_args()
    frozen, tuned = load(args.frozen_dir), load(args.tuned_dir)
    levels = sorted(
        {level for _, level in frozen} & {level for _, level in tuned}
    )
    systems = sorted(
        ({system for system, _ in frozen} & {system for system, _ in tuned})
        - {"sas"}
    )

    print(
        f"{'system':<18}{'level':>8}{'n':>6}{'gap frozen':>12}"
        f"{'gap tuned':>12}{'DeltaGap':>11}{'paired 95% CI':>22}"
        f"{'result':>18}"
    )
    for level in levels:
        for system in systems:
            ids = sorted(
                set(frozen.get(("sas", level), {}))
                & set(frozen.get((system, level), {}))
                & set(tuned.get(("sas", level), {}))
                & set(tuned.get((system, level), {}))
            )
            if not ids:
                continue
            gap_frozen = np.array([
                frozen[(system, level)][i] - frozen[("sas", level)][i]
                for i in ids
            ], dtype=float)
            gap_tuned = np.array([
                tuned[(system, level)][i] - tuned[("sas", level)][i]
                for i in ids
            ], dtype=float)
            delta = gap_tuned - gap_frozen
            rng = np.random.default_rng(0)
            boots = rng.choice(
                delta, size=(args.n_boot, len(delta)), replace=True
            ).mean(axis=1)
            lo, hi = np.percentile(boots, [2.5, 97.5])
            result = (
                "MAS relative gain" if lo > 0
                else "MAS relative loss" if hi < 0
                else "not resolved"
            )
            print(
                f"{system:<18}{level:>8}{len(ids):>6}"
                f"{gap_frozen.mean():>+12.3f}{gap_tuned.mean():>+12.3f}"
                f"{delta.mean():>+11.3f}"
                f"{f'[{lo:+.3f},{hi:+.3f}]':>22}{result:>18}"
            )


if __name__ == "__main__":
    main()
