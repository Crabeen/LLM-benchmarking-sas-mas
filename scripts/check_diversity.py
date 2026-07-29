"""Empirical diversity diagnostic for parallel-branch MAS architectures.

Measures pairwise exact-duplicate rates among parallel agent outputs, using
fields already present in each architecture's trace dict (no rerun needed).
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path


def _norm(s: str) -> str:
    return " ".join(s.split()).strip().lower()


def _pairwise_dup_rate(items: list[str]) -> float | None:
    if len(items) < 2:
        return None
    pairs = list(combinations(items, 2))
    dups = sum(1 for a, b in pairs if _norm(a) == _norm(b))
    return dups / len(pairs)


def check(path: str) -> None:
    rows = [json.loads(l) for l in Path(path).read_text().splitlines()
            if l.strip()]
    if not rows:
        print(f"{path}: EMPTY")
        return
    system = rows[0].get("system", "?")
    n = len(rows)

    if system == "debate":
        deb_rates, crit_rates = [], []
        for r in rows:
            t = r.get("trace", {})
            ia = t.get("initial_answers", [])
            ca = t.get("improved_answers", [])
            if len(ia) == 2:
                deb_rates.append(_norm(ia[0]) == _norm(ia[1]))
            if len(ca) == 2:
                crit_rates.append(_norm(ca[0]) == _norm(ca[1]))
        dtemp = rows[0].get("trace", {}).get("debater_temperature", "n/a")
        print(f"{path} (n={n}, debater_temperature={dtemp}):")
        if deb_rates:
            print(f"  debater exact-dup rate: "
                  f"{sum(deb_rates)/len(deb_rates):.1%} "
                  f"({sum(deb_rates)}/{len(deb_rates)})")
        else:
            print("  debater exact-dup rate: n/a")
        if crit_rates:
            print(f"  critic exact-dup rate:  "
                  f"{sum(crit_rates)/len(crit_rates):.1%} "
                  f"({sum(crit_rates)}/{len(crit_rates)})")
        else:
            print("  critic exact-dup rate: n/a")

    elif system == "ensemble":
        rates = [_pairwise_dup_rate(r.get("trace", {}).get("candidates", []))
                 for r in rows]
        rates = [x for x in rates if x is not None]
        if rates:
            print(f"{path} (n={n}): mean pairwise candidate dup rate = "
                  f"{sum(rates)/len(rates):.1%}")
        else:
            print(f"{path}: n/a")

    elif system in ("parallel_roles", "subtask_parallel"):
        key = "role_outputs" if system == "parallel_roles" else "task_outputs"
        rates = [_pairwise_dup_rate(r.get("trace", {}).get(key, []))
                 for r in rows]
        rates = [x for x in rates if x is not None]
        if rates:
            print(f"{path} (n={n}): mean pairwise {key} dup rate = "
                  f"{sum(rates)/len(rates):.1%}")
        else:
            print(f"{path}: n/a")

    else:
        print(f"{path}: system={system!r} has no parallel-branch diversity "
              f"check defined")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    for p in sys.argv[1:]:
        check(p)
        print()
