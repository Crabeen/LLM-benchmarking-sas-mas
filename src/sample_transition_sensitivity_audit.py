"""Create a deterministic blinded sensitivity sample of semantic transitions."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from pathlib import Path

from .rejudge_external import read_jsonl


QUOTAS = {
    "debate_beneficial_w_to_c": 25,
    "debate_harmful_c_to_w": 25,
    "sequential_harmful_c_to_w": 25,
    "stable_control": 25,
}
CONTROL_QUOTAS = {
    "debate_c_to_c": 7,
    "debate_w_to_w": 6,
    "sequential_c_to_c": 6,
    "sequential_w_to_w": 6,
}


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def stage_key(row: dict, stage_name: str) -> tuple[str, str, int, str, str]:
    return (
        str(row["source_run"]), str(row["system"]), int(row["budget"]),
        str(row["id"]), str(stage_name),
    )


def item_key(row: dict) -> tuple[str, str, int, str]:
    return (
        str(row["source_run"]), str(row["system"]),
        int(row["budget"]), str(row["id"]),
    )


def stratum(row: dict) -> str | None:
    transition_type = row["transition_type"]
    flip = row["flip"]
    if transition_type == "debate_revision" and flip == "W>C":
        return "debate_beneficial_w_to_c"
    if transition_type == "debate_revision" and flip == "C>W":
        return "debate_harmful_c_to_w"
    if transition_type == "sequential_worker" and flip == "C>W":
        return "sequential_harmful_c_to_w"
    if transition_type == "debate_revision" and flip == "C>C":
        return "debate_c_to_c"
    if transition_type == "debate_revision" and flip == "W>W":
        return "debate_w_to_w"
    if transition_type == "sequential_worker" and flip == "C>C":
        return "sequential_c_to_c"
    if transition_type == "sequential_worker" and flip == "W>W":
        return "sequential_w_to_w"
    return None


def balanced_pick(
    pool: list[dict], quota: int, used_items: set[tuple], rng: random.Random
) -> list[dict]:
    pool = [row for row in pool if item_key(row) not in used_items]
    rng.shuffle(pool)
    counts = Counter()
    picked = []
    while pool and len(picked) < quota:
        def score(row: dict) -> tuple:
            cells = [
                ("run", row["source_run"]),
                ("dataset", row["dataset"]),
                ("model", row["model_variant"]),
                ("budget", row["budget"]),
                ("truncated", row["destination_truncated"]),
            ]
            return (sum(counts[cell] for cell in cells), max(counts[cell] for cell in cells))

        best = min(range(len(pool)), key=lambda index: score(pool[index]))
        row = pool.pop(best)
        picked.append(row)
        selected_item = item_key(row)
        used_items.add(selected_item)
        pool = [candidate for candidate in pool if item_key(candidate) != selected_item]
        for cell in [
            ("run", row["source_run"]),
            ("dataset", row["dataset"]),
            ("model", row["model_variant"]),
            ("budget", row["budget"]),
            ("truncated", row["destination_truncated"]),
        ]:
            counts[cell] += 1
    return picked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transitions", type=Path,
        default=Path("analysis/semantic_diagnostics/semantic_transitions.csv"),
    )
    parser.add_argument(
        "--stages", type=Path,
        default=Path("analysis/stage_judge_full/all_stages.mistral_dual_v4.jsonl"),
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("analysis/semantic_transition_sensitivity"),
    )
    parser.add_argument("--seed", type=int, default=29)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    blind_path = args.out / "blind_review_100.csv"
    key_path = args.out / "sensitivity_audit_key.jsonl"
    summary_path = args.out / "sample_manifest.json"
    if not args.force and any(path.exists() for path in (blind_path, key_path, summary_path)):
        parser.error("sample outputs already exist; pass --force")

    transitions = read_csv(args.transitions)
    stages = read_jsonl(args.stages)
    stage_map = {
        stage_key(row, str(row["stage_name"])): row
        for row in stages
    }
    eligible = []
    for row in transitions:
        group = stratum(row)
        if not group:
            continue
        source = stage_map[stage_key(row, row["source_stage"])]
        destination = stage_map[stage_key(row, row["destination_stage"])]
        eligible.append({
            **row,
            "audit_stratum": group,
            "question": source["question"],
            "gold": source["gold"],
            "gold_aliases": source.get("gold_aliases") or [],
            "source_output": source["stage_text"],
            "destination_output": destination["stage_text"],
            "source_machine_label": source["judge_gold_discovered_label"],
            "destination_machine_label": destination["judge_gold_discovered_label"],
            "source_evidence": source.get("judge_discovery_evidence", ""),
            "destination_evidence": destination.get("judge_discovery_evidence", ""),
        })

    rng = random.Random(args.seed)
    used_items: set[tuple] = set()
    selected = []
    for group in (
        "debate_beneficial_w_to_c",
        "debate_harmful_c_to_w",
        "sequential_harmful_c_to_w",
    ):
        picked = balanced_pick(
            [row for row in eligible if row["audit_stratum"] == group],
            QUOTAS[group], used_items, rng,
        )
        if len(picked) != QUOTAS[group]:
            raise SystemExit(f"sampling shortage for {group}: {len(picked)}")
        selected.extend(picked)
    for group, quota in CONTROL_QUOTAS.items():
        picked = balanced_pick(
            [row for row in eligible if row["audit_stratum"] == group],
            quota, used_items, rng,
        )
        if len(picked) != quota:
            raise SystemExit(f"sampling shortage for {group}: {len(picked)}")
        for row in picked:
            row["control_substratum"] = group
            row["audit_stratum"] = "stable_control"
        selected.extend(picked)
    if len(selected) != sum(QUOTAS.values()):
        raise SystemExit(f"expected 100 rows, got {len(selected)}")
    if len({item_key(row) for row in selected}) != len(selected):
        raise SystemExit("sample contains repeated item-configurations")
    rng.shuffle(selected)
    for index, row in enumerate(selected, start=1):
        row["blind_id"] = f"SEN-{index:04d}"

    args.out.mkdir(parents=True, exist_ok=True)
    blind_fields = [
        "blind_id", "question", "reference_answer", "reference_aliases",
        "source_output", "destination_output",
    ]
    with blind_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=blind_fields)
        writer.writeheader()
        for row in selected:
            writer.writerow({
                "blind_id": row["blind_id"],
                "question": row["question"],
                "reference_answer": row["gold"],
                "reference_aliases": json.dumps(row["gold_aliases"], ensure_ascii=False),
                "source_output": row["source_output"],
                "destination_output": row["destination_output"],
            })
    with key_path.open("w", encoding="utf-8") as handle:
        for row in selected:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    manifest = {
        "n": len(selected),
        "seed": args.seed,
        "quota": QUOTAS,
        "control_quota": CONTROL_QUOTAS,
        "audit_stratum": dict(sorted(Counter(row["audit_stratum"] for row in selected).items())),
        "source_run": dict(sorted(Counter(row["source_run"] for row in selected).items())),
        "dataset": dict(sorted(Counter(row["dataset"] for row in selected).items())),
        "model_variant": dict(sorted(Counter(row["model_variant"] for row in selected).items())),
        "budget": dict(sorted(Counter(str(row["budget"]) for row in selected).items())),
        "destination_truncated": dict(sorted(Counter(row["destination_truncated"] for row in selected).items())),
        "unique_item_count": len({item_key(row) for row in selected}),
    }
    summary_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"written: {blind_path}")
    print(f"written: {key_path}")


if __name__ == "__main__":
    main()
