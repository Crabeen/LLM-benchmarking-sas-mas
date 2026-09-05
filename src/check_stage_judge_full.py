"""Check completeness and evidence invariants for full stage judgments."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .rejudge_external import read_jsonl
from .rejudge_stages_external import row_identity


def duplicates(rows: list[dict]) -> list[str]:
    counts = Counter(row_identity(row) for row in rows)
    return [key for key, count in counts.items() if count > 1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--judged", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    source = read_jsonl(args.input)
    judged = read_jsonl(args.judged)
    source_keys = {row_identity(row) for row in source}
    judged_keys = {row_identity(row) for row in judged}
    positive = [
        row for row in judged
        if row.get("judge_gold_discovered_label") == "correct"
    ]
    ungrounded = [
        row_identity(row) for row in positive
        if row.get("judge_discovery_evidence_grounded") is not True
    ]
    summary = {
        "input_rows": len(source),
        "judged_rows": len(judged),
        "missing_rows": len(source_keys - judged_keys),
        "unexpected_rows": len(judged_keys - source_keys),
        "duplicate_input_identities": len(duplicates(source)),
        "duplicate_judged_identities": len(duplicates(judged)),
        "discovery_labels": dict(
            sorted(Counter(row.get("judge_gold_discovered_label", "missing") for row in judged).items())
        ),
        "unresolved_discovery_rows": sum(
            row.get("judge_gold_discovered_label") not in {"correct", "incorrect"}
            for row in judged
        ),
        "discovery_positive_rows": len(positive),
        "ungrounded_discovery_positive_rows": len(ungrounded),
    }
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    structural_failures = [
        summary["missing_rows"],
        summary["unexpected_rows"],
        summary["duplicate_input_identities"],
        summary["duplicate_judged_identities"],
        summary["ungrounded_discovery_positive_rows"],
    ]
    if any(structural_failures):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
