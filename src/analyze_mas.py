"""Accuracy, resource diagnostics, and paired SAS-vs-MAS comparisons.

Usage:
    python -m src.analyze results/v3b_all_mas_token
    JUDGE_SUFFIX='*.rejudged.jsonl' python -m src.analyze results/...
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np


def bootstrap_ci(
    values: list[int], n_boot: int = 10000, seed: int = 0
) -> tuple[float, float, float]:
    rng = np.random.default_rng(seed)
    arr = np.array(values, dtype=float)
    if len(arr) == 0:
        return 0.0, 0.0, 0.0
    means = rng.choice(arr, size=(n_boot, len(arr)), replace=True).mean(axis=1)
    return arr.mean(), *np.percentile(means, [2.5, 97.5])


def paired_ci(
    differences: np.ndarray, n_boot: int = 10000, seed: int = 0
) -> tuple[float, float, float]:
    if len(differences) == 0:
        return 0.0, 0.0, 0.0
    rng = np.random.default_rng(seed)
    boots = rng.choice(
        differences, size=(n_boot, len(differences)), replace=True
    ).mean(axis=1)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return float(differences.mean()), float(lo), float(hi)


def load_groups(out_dir: Path) -> dict[tuple, list[dict]]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    suffix = os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl")
    for path in sorted(out_dir.glob(suffix)):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            groups[(row["system"], row["budget_level"])].append(row)
    return groups


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("--n-boot", type=int, default=10000)
    args = parser.parse_args()
    groups = load_groups(Path(args.out_dir))
    if not groups:
        raise SystemExit(
            "No judged rows found. Run the judging pass or set JUDGE_SUFFIX."
        )

    header = (
        f"{'system':<18}{'budget':>8}{'n':>6}{'acc':>7}{'95% CI':>17}"
        f"{'strmatch':>9}{'think':>9}{'prompt':>9}{'calls':>7}{'invoc':>7}"
        f"{'sec/q':>8}{'timeout':>8}{'trunc':>7}{'planfail':>9}"
    )
    print(header)
    print("-" * len(header))

    acc_by = {}
    for (system, level), rows in sorted(groups.items()):
        acc, lo, hi = bootstrap_ci(
            [int(r["judge_correct"]) for r in rows],
            n_boot=args.n_boot,
        )
        acc_by[(system, level)] = acc
        sm = np.mean([int(r["string_match"]) for r in rows])
        tok = np.mean([
            r["budget"]["thinking_tokens_total"] for r in rows
        ])
        prompt = np.mean([
            r["budget"].get("prompt_tokens_total", 0) for r in rows
        ])
        calls = np.mean([r["budget"]["n_calls"] for r in rows])
        invocations = np.mean([
            r["budget"].get(
                "n_model_invocations", r["budget"]["n_calls"]
            )
            for r in rows
        ])
        sec = np.mean([r["wall_seconds"] for r in rows])
        timeout = np.mean([int(r["timeout"]) for r in rows])
        trunc = np.mean([
            int(r["budget"]["any_truncated"]) for r in rows
        ])
        has_planner = system in {"sequential", "subtask_parallel"}
        planfail = (
            np.mean([
                int(
                    r.get("trace", {}).get("plan_parse_mode", "json")
                    not in ("json", "yaml")
                )
                for r in rows
            ])
            if has_planner else 0.0
        )
        print(
            f"{system:<18}{level:>8}{len(rows):>6}{acc:>7.3f}"
            f"{f'[{lo:.3f},{hi:.3f}]':>17}{sm:>9.3f}{tok:>9.0f}"
            f"{prompt:>9.0f}{calls:>7.1f}{invocations:>7.1f}"
            f"{sec:>8.1f}{timeout:>8.2f}{trunc:>7.2f}"
            f"{planfail:>9.2f}"
        )

    levels = sorted({level for _, level in groups})
    systems = sorted({system for system, _ in groups if system != "sas"})
    print("\nPaired architecture effect: Acc(MAS) - Acc(SAS)")
    print(
        f"{'system':<18}{'budget':>8}{'n':>6}{'delta':>9}"
        f"{'paired 95% CI':>22}{'W/T/L':>16}{'result':>18}"
    )
    for level in levels:
        sas_rows = {
            row["id"]: int(row["judge_correct"])
            for row in groups.get(("sas", level), [])
        }
        for system in systems:
            mas_rows = {
                row["id"]: int(row["judge_correct"])
                for row in groups.get((system, level), [])
            }
            ids = sorted(set(sas_rows) & set(mas_rows))
            if not ids:
                continue
            differences = np.array(
                [mas_rows[i] - sas_rows[i] for i in ids], dtype=float
            )
            delta, lo, hi = paired_ci(
                differences, n_boot=args.n_boot
            )
            wins = int(np.sum(differences > 0))
            ties = int(np.sum(differences == 0))
            losses = int(np.sum(differences < 0))
            result = (
                "MAS higher" if lo > 0
                else "SAS higher" if hi < 0
                else "not resolved"
            )
            print(
                f"{system:<18}{level:>8}{len(ids):>6}{delta:>+9.3f}"
                f"{f'[{lo:+.3f},{hi:+.3f}]':>22}"
                f"{f'{wins}/{ties}/{losses}':>16}{result:>18}"
            )


if __name__ == "__main__":
    main()
