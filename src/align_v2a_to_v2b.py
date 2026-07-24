"""Restrict v2a to exactly the ids AND order kept by v2b, asserting that both
arms show the model an identical prompt for each id. Any difference in kept
examples means v2a must be retrained on the aligned file, otherwise the
train/validation split itself differs between arms.

Usage:
  python -m src.align_v2a_to_v2b --v2a data/sft_train_v2a.jsonl \
      --v2b data/sft_train_v2b.jsonl --out data/sft_train_v2a_aligned.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2a", default="data/sft_train_v2a.jsonl")
    ap.add_argument("--v2b", default="data/sft_train_v2b.jsonl")
    ap.add_argument("--out", default="data/sft_train_v2a_aligned.jsonl")
    args = ap.parse_args()

    v2a = {r["id"]: r for r in read(args.v2a)}
    v2b = read(args.v2b)

    missing = [r["id"] for r in v2b if r["id"] not in v2a]
    if missing:
        raise RuntimeError(
            f"{len(missing)} v2b ids absent from v2a (e.g. {missing[:3]}). "
            "Rebuild v2b restricted to the v2a id pool instead of letting it "
            "pull in replacement examples.")
    for r in v2b:
        if v2a[r["id"]]["prompt"] != r["prompt"]:
            raise RuntimeError(f"Prompt mismatch for {r['id']}: the two arms "
                               "would not see identical inputs")

    with Path(args.out).open("w", encoding="utf-8") as f:
        for r in v2b:
            f.write(json.dumps(v2a[r["id"]], ensure_ascii=False) + "\n")
    print(f"wrote {len(v2b)} aligned v2a examples -> {args.out}")
    print(f"(v2a original: {len(v2a)}; dropped {len(v2a) - len(v2b)})")


if __name__ == "__main__":
    main()
