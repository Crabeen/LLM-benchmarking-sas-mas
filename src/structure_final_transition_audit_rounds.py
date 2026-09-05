"""Split the frozen 420-row blind audit into four independent review rounds.

The sample itself is never redrawn. Rows from the same item are assigned to
different rounds, including hidden intra-rater duplicates. The private round
key retains the machine metadata; the four blind CSV files retain only the five
annotation-facing fields.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import random
from collections import Counter, defaultdict
from pathlib import Path


BLIND_FIELDS = (
    "blind_stage_id",
    "question",
    "reference_answer",
    "reference_aliases",
    "stage_output",
)
ROUND_COUNT = 4


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_blind(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=BLIND_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row[field] for field in BLIND_FIELDS})


def main() -> None:
    parser = argparse.ArgumentParser()
    base = Path("analysis/final_transition_endorsement_audit")
    parser.add_argument("--blind", type=Path, default=base / "blind_stage_review_400.csv")
    parser.add_argument("--key", type=Path, default=base / "final_transition_audit_key.jsonl")
    parser.add_argument("--pilot", type=Path, default=base / "pilot_stage_review_20.csv")
    parser.add_argument("--sample-manifest", type=Path, default=base / "sample_manifest.json")
    parser.add_argument("--out", type=Path, default=base / "rounds")
    parser.add_argument("--round-seed", type=int, default=4104)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    round_paths = [
        args.out / f"blind_stage_review_round_{index}.csv"
        for index in range(1, ROUND_COUNT + 1)
    ]
    round_key_path = args.out / "round_assignment_key.jsonl"
    round_manifest_path = args.out / "round_manifest.json"
    accurate_pilot_path = args.pilot.with_name("pilot_stage_review_18.csv")
    outputs = (*round_paths, round_key_path, round_manifest_path, accurate_pilot_path)
    if not args.force and any(path.exists() for path in outputs):
        parser.error("round outputs already exist; pass --force")

    with args.blind.open(encoding="utf-8-sig", newline="") as handle:
        blind_rows = list(csv.DictReader(handle))
    key_rows = read_jsonl(args.key)
    blind_by_id = {row["blind_stage_id"]: row for row in blind_rows}
    key_by_id = {row["blind_stage_id"]: row for row in key_rows}
    if len(blind_rows) != 420 or len(blind_by_id) != 420:
        raise SystemExit(f"expected 420 unique blind rows, found {len(blind_rows)}")
    if set(blind_by_id) != set(key_by_id):
        raise SystemExit("blind CSV and private key contain different blind_stage_id sets")

    grouped: dict[str, list[dict]] = defaultdict(list)
    for blind_id, key in key_by_id.items():
        grouped[str(key["item_blind_id"])].append(key | blind_by_id[blind_id])
    if len(grouped) != 160:
        raise SystemExit(f"expected 160 items, found {len(grouped)}")

    rng = random.Random(args.round_seed)
    item_ids = sorted(grouped)
    rng.shuffle(item_ids)
    total_load = Counter({round_no: 0 for round_no in range(1, ROUND_COUNT + 1)})
    duplicate_load = Counter({round_no: 0 for round_no in range(1, ROUND_COUNT + 1)})
    position_load = Counter()
    assignments: dict[str, int] = {}

    for item_id in item_ids:
        rows = sorted(grouped[item_id], key=lambda row: row["blind_stage_id"])
        rng.shuffle(rows)
        permutations = list(itertools.permutations(range(1, ROUND_COUNT + 1), len(rows)))
        rng.shuffle(permutations)

        def score(permutation: tuple[int, ...]) -> tuple[int, int, int, int]:
            totals = dict(total_load)
            duplicates = dict(duplicate_load)
            positions = dict(position_load)
            for row, round_no in zip(rows, permutation):
                totals[round_no] = totals.get(round_no, 0) + 1
                if not row["in_item_analysis"]:
                    duplicates[round_no] = duplicates.get(round_no, 0) + 1
                cell = (round_no, str(row["position"]))
                positions[cell] = positions.get(cell, 0) + 1
            position_squares = 0
            for position in {str(row["position"]) for row in key_rows}:
                counts = [positions.get((round_no, position), 0) for round_no in range(1, 5)]
                position_squares += sum(value * value for value in counts)
            return (
                max(totals.values()),
                sum(value * value for value in totals.values()),
                position_squares,
                sum(value * value for value in duplicates.values()),
            )

        chosen = min(permutations, key=score)
        for row, round_no in zip(rows, chosen):
            blind_id = str(row["blind_stage_id"])
            assignments[blind_id] = round_no
            total_load[round_no] += 1
            if not row["in_item_analysis"]:
                duplicate_load[round_no] += 1
            position_load[(round_no, str(row["position"]))] += 1

    round_rows: dict[int, list[dict]] = defaultdict(list)
    for blind_id, blind in blind_by_id.items():
        round_rows[assignments[blind_id]].append(blind)
    for round_no in range(1, ROUND_COUNT + 1):
        random.Random(args.round_seed + round_no).shuffle(round_rows[round_no])
        write_blind(round_paths[round_no - 1], round_rows[round_no])

    round_order = {}
    for round_no, rows in round_rows.items():
        for index, row in enumerate(rows, start=1):
            round_order[row["blind_stage_id"]] = index
    with round_key_path.open("w", encoding="utf-8") as handle:
        for key in sorted(key_rows, key=lambda row: row["blind_stage_id"]):
            record = dict(key)
            record["audit_round"] = assignments[key["blind_stage_id"]]
            record["round_order"] = round_order[key["blind_stage_id"]]
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    with args.pilot.open(encoding="utf-8-sig", newline="") as handle:
        pilot_rows = list(csv.DictReader(handle))
    if len(pilot_rows) != 18:
        raise SystemExit(f"expected the structurally feasible 18-row pilot, found {len(pilot_rows)}")
    write_blind(accurate_pilot_path, pilot_rows)

    duplicate_same_round = 0
    for key in key_rows:
        origin = key.get("is_duplicate_of")
        if origin and assignments[key["blind_stage_id"]] == assignments[origin]:
            duplicate_same_round += 1
    max_same_item_per_round = max(
        Counter(assignments[row["blind_stage_id"]] for row in rows).most_common(1)[0][1]
        for rows in grouped.values()
    )
    round_summary = {}
    for round_no in range(1, ROUND_COUNT + 1):
        ids = {row["blind_stage_id"] for row in round_rows[round_no]}
        keys = [key_by_id[blind_id] for blind_id in ids]
        round_summary[str(round_no)] = {
            "rows": len(ids),
            "analysis_rows": sum(bool(row["in_item_analysis"]) for row in keys),
            "hidden_duplicate_rows": sum(not bool(row["in_item_analysis"]) for row in keys),
            "unique_items": len({row["item_blind_id"] for row in keys}),
            "systems": dict(sorted(Counter(row["system"] for row in keys).items())),
            "positions": dict(sorted(Counter(row["position"] for row in keys).items())),
            "csv_sha256": sha256(round_paths[round_no - 1]),
        }
    manifest = {
        "round_seed": args.round_seed,
        "round_count": ROUND_COUNT,
        "source_blind_csv": str(args.blind),
        "source_blind_csv_sha256": sha256(args.blind),
        "source_key": str(args.key),
        "source_key_sha256": sha256(args.key),
        "rows_total": len(blind_rows),
        "items_total": len(grouped),
        "max_same_item_rows_within_round": max_same_item_per_round,
        "hidden_duplicate_same_round_as_origin": duplicate_same_round,
        "rounds": round_summary,
        "pilot_requested_rows": 20,
        "pilot_actual_rows": len(pilot_rows),
        "pilot_shortfall_rows": 20 - len(pilot_rows),
        "pilot_shortfall_reason": (
            "debate_picker_w_to_c contains one eligible item with three stage outputs"
        ),
        "notes": [
            "The frozen 160-item sample and all 420 blind rows are unchanged.",
            "Each item contributes at most one row to any review round.",
            "Stage positions are randomly permuted across rounds and balanced; round is not a stage identity.",
            "Hidden duplicates are assigned to a different round from their originals.",
            "The private round key must remain unopened until all four rounds are complete.",
        ],
    }
    round_manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    sample_manifest = json.loads(args.sample_manifest.read_text(encoding="utf-8"))
    sample_manifest.update({
        "pilot_requested_rows": 20,
        "pilot_actual_rows": len(pilot_rows),
        "pilot_shortfall_rows": 20 - len(pilot_rows),
        "pilot_shortfall_reason": manifest["pilot_shortfall_reason"],
        "authoritative_pilot_file": str(accurate_pilot_path),
        "presentation_structure": {
            "round_count": ROUND_COUNT,
            "round_seed": args.round_seed,
            "round_manifest": str(round_manifest_path),
            "max_same_item_rows_within_round": max_same_item_per_round,
            "hidden_duplicate_same_round_as_origin": duplicate_same_round,
        },
    })
    args.sample_manifest.write_text(
        json.dumps(sample_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
