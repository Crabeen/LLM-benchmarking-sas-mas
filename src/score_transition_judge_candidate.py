#!/usr/bin/env python3
"""Score a candidate stage judge against the fixed human transition audit."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


LABEL_MAP = {"correct": "C", "incorrect": "W", "uncertain": "U"}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def kappa(pairs: list[tuple[str, str]], labels: list[str]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(left == right for left, right in pairs) / n
    left = Counter(value for value, _ in pairs)
    right = Counter(value for _, value in pairs)
    expected = sum((left[label] / n) * (right[label] / n) for label in labels)
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def metric(pairs: list[tuple[str, str]], labels: list[str]) -> dict:
    return {
        "n": len(pairs),
        "accuracy": sum(left == right for left, right in pairs) / len(pairs) if pairs else None,
        "kappa": kappa(pairs, labels),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--judged", type=Path, required=True)
    parser.add_argument(
        "--human-key",
        type=Path,
        default=Path("analysis/semantic_transition_sensitivity/strong_judge_human_key.jsonl"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    judged = read_jsonl(args.judged)
    human = read_jsonl(args.human_key)
    judged_by_id = {str(row["source_uid"]): row for row in judged}
    if len(judged_by_id) != len(judged):
        raise SystemExit("candidate output contains duplicate source_uid values")
    if len(human) != 200:
        raise SystemExit(f"expected 200 human-key rows, got {len(human)}")

    stage_records = []
    missing = []
    for truth in human:
        uid = str(truth["source_uid"])
        candidate = judged_by_id.get(uid)
        if candidate is None:
            missing.append(uid)
            continue
        raw_label = str(candidate.get("judge_gold_discovered_label", "")).strip().lower()
        candidate_label = LABEL_MAP.get(raw_label, "E")
        stage_records.append(
            {
                **truth,
                "candidate_label": candidate_label,
                "raw_label": raw_label,
                "question": candidate.get("question", ""),
                "stage_text": candidate.get("stage_text", ""),
                "candidate_evidence": candidate.get("judge_discovery_evidence", ""),
                "candidate_reason": candidate.get("judge_discovery_reason_code", ""),
                "dataset": candidate.get("dataset", ""),
                "model_variant": candidate.get("model_variant", ""),
                "system": candidate.get("system", ""),
                "budget": candidate.get("budget", ""),
            }
        )
    unexpected = sorted(set(judged_by_id) - {str(row["source_uid"]) for row in human})
    if missing or unexpected:
        raise SystemExit(f"identity mismatch: missing={len(missing)} unexpected={len(unexpected)}")

    resolved_stage = [
        (row["candidate_label"], row["human_label"])
        for row in stage_records
        if row["candidate_label"] in {"C", "W"} and row["human_label"] in {"C", "W"}
    ]
    stage_metrics = metric(resolved_stage, ["C", "W"])
    stage_metrics["parse_or_uncertain"] = len(stage_records) - len(resolved_stage)
    by_position = {}
    for position in ("source", "destination"):
        selected = [
            (row["candidate_label"], row["human_label"])
            for row in stage_records
            if row["audit_position"] == position
            and row["candidate_label"] in {"C", "W"}
            and row["human_label"] in {"C", "W"}
        ]
        by_position[position] = metric(selected, ["C", "W"])

    pairs: dict[str, dict[str, dict]] = defaultdict(dict)
    for row in stage_records:
        pairs[str(row["audit_pair_blind_id"])][str(row["audit_position"])] = row
    transition_records = []
    for blind_id, positions in pairs.items():
        if set(positions) != {"source", "destination"}:
            raise SystemExit(f"incomplete pair: {blind_id}")
        source, destination = positions["source"], positions["destination"]
        transition_records.append(
            {
                "blind_id": blind_id,
                "audit_stratum": source["audit_stratum"],
                "candidate_transition": f"{source['candidate_label']}>{destination['candidate_label']}",
                "human_transition": f"{source['human_label']}>{destination['human_label']}",
                "candidate_source": source["candidate_label"],
                "candidate_destination": destination["candidate_label"],
                "human_source": source["human_label"],
                "human_destination": destination["human_label"],
                "question": source["question"],
                "source_text": source["stage_text"],
                "destination_text": destination["stage_text"],
                "source_candidate_evidence": source["candidate_evidence"],
                "destination_candidate_evidence": destination["candidate_evidence"],
            }
        )
    resolved_transitions = [
        (row["candidate_transition"], row["human_transition"])
        for row in transition_records
        if "U" not in row["candidate_transition"]
        and "E" not in row["candidate_transition"]
        and "U" not in row["human_transition"]
    ]
    transition_metrics = metric(resolved_transitions, ["C>C", "C>W", "W>C", "W>W"])
    transition_metrics["parse_or_uncertain"] = len(transition_records) - len(resolved_transitions)

    by_stratum = {}
    for stratum in sorted({str(row["audit_stratum"]) for row in transition_records}):
        selected = [
            (row["candidate_transition"], row["human_transition"])
            for row in transition_records
            if row["audit_stratum"] == stratum
            and "U" not in row["candidate_transition"]
            and "E" not in row["candidate_transition"]
            and "U" not in row["human_transition"]
        ]
        by_stratum[stratum] = metric(selected, ["C>C", "C>W", "W>C", "W>W"])

    passed = (
        stage_metrics["accuracy"] is not None
        and stage_metrics["accuracy"] >= 0.90
        and stage_metrics["kappa"] is not None
        and stage_metrics["kappa"] >= 0.75
        and transition_metrics["accuracy"] is not None
        and transition_metrics["accuracy"] >= 0.80
        and transition_metrics["kappa"] is not None
        and transition_metrics["kappa"] >= 0.75
        and all(value["accuracy"] is not None and value["accuracy"] >= 0.70 for value in by_stratum.values())
    )
    result = {
        "judged_file": str(args.judged),
        "stage": stage_metrics,
        "by_position": by_position,
        "transition": transition_metrics,
        "by_stratum": by_stratum,
        "preregistered_pass_rule": {
            "stage_accuracy_min": 0.90,
            "stage_kappa_min": 0.75,
            "transition_accuracy_min": 0.80,
            "transition_kappa_min": 0.75,
            "each_stratum_accuracy_min": 0.70,
        },
        "passed": passed,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        stage_disagreements = [
            row for row in stage_records
            if row["human_label"] in {"C", "W"} and row["candidate_label"] != row["human_label"]
        ]
        transition_disagreements = [
            row for row in transition_records
            if "U" not in row["human_transition"] and row["candidate_transition"] != row["human_transition"]
        ]
        for suffix, rows in (
            ("stage_disagreements.csv", stage_disagreements),
            ("transition_disagreements.csv", transition_disagreements),
        ):
            path = args.output.with_name(args.output.stem + "." + suffix)
            if rows:
                with path.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)


if __name__ == "__main__":
    main()
