"""Build the two-layer final-transition endorsement audit sample.

Layer 1: 160 final-transition items (Debate picker / Sequential aggregator).
Layer 2: those items split into independent single-stage outputs, shuffled and
blinded, so a human labels discovery and endorsement without ever seeing which
stage is the source, which is the final, or how the two relate.

Debate source state is an oracle over BOTH revisions, never a single revision:

    revised_endorsement_oracle = rev_A endorsed correct OR rev_B endorsed correct
    picker_loss = revised_endorsement_oracle == C AND final_endorsement == W

Sequential source state is the highest-index worker:

    aggregator_loss = last_worker_endorsement == C AND final_endorsement == W

The C/W used here are Mistral labels and define the SAMPLING STRATUM only.
``machine_sampling_stratum`` is frozen into the key and must never be rewritten
after human labelling.

python -m src.sample_final_transition_endorsement_audit --seed 41
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from .rejudge_external import read_jsonl


# Quotas after the debate W->C rare-event shortage (requested 15, available 1).
# Shortage rule: take the beneficial stratum as a census first, then move the
# shortfall to the same architecture's primary harmful stratum.
QUOTAS = {
    "debate_picker_c_to_w": 39,
    "debate_picker_w_to_c": 1,
    "debate_picker_c_to_c": 20,
    "debate_picker_w_to_w": 20,
    "sequential_aggregator_c_to_w": 25,
    "sequential_aggregator_w_to_c": 15,
    "sequential_aggregator_c_to_c": 20,
    "sequential_aggregator_w_to_w": 20,
}
SHORTAGE_RECORD = {
    "stratum": "debate_picker_w_to_c",
    "requested_n": 15,
    "available_n": 1,
    "selected_n": 1,
    "shortfall_n": 14,
    "sampling_mode": "rare_event_census",
    "reallocated_to": "debate_picker_c_to_w",
    "reallocated_n": 14,
}
SHORTAGE_RULES = [
    "A beneficial stratum that is short is taken as a full census first.",
    "The shortfall moves to the primary harmful stratum of the same architecture.",
    "If that harmful stratum is also short, split the remainder evenly across the"
    " same architecture's C->C and W->W controls.",
    "Never move a shortfall across architectures unless every pool of that"
    " architecture is exhausted.",
    "Never duplicate an item, relax a label definition, or reuse a benchmark id"
    " to fill a quota.",
]
BALANCE_CELLS = (
    "source_run", "dataset", "model_variant", "budget",
    "question_any_truncated", "source_truncated", "final_label_source",
)
LABEL_MAP = {"correct": "C", "incorrect": "W"}


def item_key(row: dict) -> tuple[str, str, int, str]:
    return (
        str(row["source_run"]), str(row["system"]),
        int(row["budget"]), str(row["id"]),
    )


def binary_label(value: object) -> str | None:
    return LABEL_MAP.get(str(value))


def load_finals(reused_path: Path, judged_path: Path) -> dict[tuple, dict]:
    finals: dict[tuple, dict] = {}
    for row in read_jsonl(reused_path) + read_jsonl(judged_path):
        finals[item_key(row)] = row
    return finals


def load_stages(stages_path: Path) -> dict[tuple, dict[str, dict]]:
    stages: dict[tuple, dict[str, dict]] = defaultdict(dict)
    for row in read_jsonl(stages_path):
        stages[item_key(row)][str(row["stage_name"])] = row
    return stages


def build_candidates(
    finals: dict[tuple, dict],
    stages: dict[tuple, dict[str, dict]],
    excluded_ids: set[str],
) -> tuple[list[dict], Counter]:
    """Return one candidate record per eligible item, plus exclusion counts."""
    dropped: Counter = Counter()
    candidates: list[dict] = []
    for key in sorted(finals):
        final = finals[key]
        system = str(final["system"])
        if system not in ("debate", "sequential"):
            continue
        if str(final["id"]) in excluded_ids:
            dropped[f"{system}:prior_audit_id"] += 1
            continue
        if final.get("judge_error"):
            dropped[f"{system}:final_judge_error"] += 1
            continue
        if not str(final.get("stage_text", "")).strip():
            dropped[f"{system}:empty_final_output"] += 1
            continue
        final_state = binary_label(final.get("judge_endorsed_label"))
        if final_state is None:
            reason = (
                "final_endorsement_reuse_conflict"
                if final.get("endorsement_label_source") == "reuse_conflict"
                else "final_endorsement_uncertain_or_missing"
            )
            dropped[f"{system}:{reason}"] += 1
            continue
        item_stages = stages.get(key, {})
        if system == "debate":
            revision_a = item_stages.get("rev_A")
            revision_b = item_stages.get("rev_B")
            if not revision_a or not revision_b:
                dropped["debate:missing_revision_stage"] += 1
                continue
            sources = [revision_a, revision_b]
            endorsed = [binary_label(row.get("judge_endorsed_label")) for row in sources]
            discovered = [
                binary_label(row.get("judge_gold_discovered_label")) for row in sources
            ]
            if "C" in endorsed:
                source_state = "C"
            elif all(label == "W" for label in endorsed):
                source_state = "W"
            else:
                dropped["debate:revision_oracle_uncertain"] += 1
                continue
            discovery_oracle = (
                "C" if "C" in discovered
                else ("W" if all(label == "W" for label in discovered) else None)
            )
            positions = ["rev_A", "rev_B"]
        else:
            workers = [
                row for name, row in item_stages.items() if name.startswith("worker_")
            ]
            if not workers:
                dropped["sequential:missing_worker_stage"] += 1
                continue
            last_worker = max(workers, key=lambda row: int(row["stage_index"]))
            sources = [last_worker]
            source_state = binary_label(last_worker.get("judge_endorsed_label"))
            if source_state is None:
                dropped["sequential:last_worker_uncertain"] += 1
                continue
            discovery_oracle = binary_label(
                last_worker.get("judge_gold_discovered_label")
            )
            positions = ["last_worker"]
        if any(not str(row.get("stage_text", "")).strip() for row in sources):
            dropped[f"{system}:empty_source_output"] += 1
            continue
        if any(row.get("judge_error") for row in sources):
            dropped[f"{system}:source_judge_error"] += 1
            continue
        prefix = "debate_picker" if system == "debate" else "sequential_aggregator"
        candidates.append({
            "machine_sampling_stratum":
                f"{prefix}_{source_state.lower()}_to_{final_state.lower()}",
            "system": system,
            "source_run": str(final["source_run"]),
            "dataset": str(final["dataset"]),
            "model_variant": str(final["model_variant"]),
            "budget": int(final["budget"]),
            "original_id": str(final["id"]),
            "question": final["question"],
            "gold": final["gold"],
            "gold_aliases": final.get("gold_aliases") or [],
            "question_any_truncated": bool(final.get("question_any_truncated")),
            "source_truncated": any(bool(row.get("stage_truncated")) for row in sources),
            "final_label_source": str(final.get("final_label_source", "")),
            "machine_source_endorsement": source_state,
            "machine_source_discovery_oracle": discovery_oracle,
            "machine_final_endorsement": final_state,
            "machine_final_discovery":
                binary_label(final.get("judge_gold_discovered_label")),
            "item_key": list(key),
            "stage_rows": [
                {"position": position, "row": row}
                for position, row in zip(positions, sources)
            ] + [{"position": "final", "row": final}],
        })
    return candidates, dropped


def balanced_pick(
    pool: list[dict], quota: int, used_ids: set[str], rng: random.Random
) -> list[dict]:
    """Greedy pick that keeps covariate cells as even as the pool allows."""
    pool = [row for row in pool if row["original_id"] not in used_ids]
    rng.shuffle(pool)
    counts: Counter = Counter()
    picked: list[dict] = []
    while pool and len(picked) < quota:
        def cost(row: dict) -> tuple[int, int]:
            cells = [(name, str(row[name])) for name in BALANCE_CELLS]
            return (
                sum(counts[cell] for cell in cells),
                max(counts[cell] for cell in cells),
            )

        best = min(range(len(pool)), key=lambda index: cost(pool[index]))
        row = pool.pop(best)
        picked.append(row)
        used_ids.add(row["original_id"])
        pool = [other for other in pool if other["original_id"] != row["original_id"]]
        for cell in [(name, str(row[name])) for name in BALANCE_CELLS]:
            counts[cell] += 1
    return picked


def spread(rows: list[dict], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row[field]) for row in rows).items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    default_stage_dir = Path("analysis/stage_judge_full")
    parser.add_argument(
        "--stages", type=Path,
        default=default_stage_dir / "all_stages.mistral_dual_v4.jsonl",
    )
    parser.add_argument(
        "--finals-reused", type=Path,
        default=default_stage_dir / "finals_reused_from_stages.jsonl",
    )
    parser.add_argument(
        "--finals-judged", type=Path,
        default=default_stage_dir / "finals_mistral_discovery_v4.jsonl",
    )
    parser.add_argument(
        "--prior-audit-key", type=Path,
        default=Path(
            "analysis/semantic_transition_sensitivity/sensitivity_audit_key.jsonl"
        ),
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("analysis/final_transition_endorsement_audit"),
    )
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--duplicate-rows", type=int, default=20)
    parser.add_argument("--pilot-per-stratum", type=int, default=5)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    blind_path = args.out / "blind_stage_review_400.csv"
    key_path = args.out / "final_transition_audit_key.jsonl"
    item_path = args.out / "item_sample_160.jsonl"
    manifest_path = args.out / "sample_manifest.json"
    core_outputs = (blind_path, key_path, item_path, manifest_path)
    if not args.force and any(path.exists() for path in core_outputs):
        parser.error("sample outputs already exist; pass --force")

    excluded_ids = {
        str(row["id"]) for row in read_jsonl(args.prior_audit_key)
    }
    finals = load_finals(args.finals_reused, args.finals_judged)
    stages = load_stages(args.stages)
    candidates, dropped = build_candidates(finals, stages, excluded_ids)

    pools: dict[str, list[dict]] = defaultdict(list)
    for candidate in candidates:
        pools[candidate["machine_sampling_stratum"]].append(candidate)

    rng = random.Random(args.seed)
    used_ids: set[str] = set()
    selected: list[dict] = []
    stratum_report = {}
    # Benchmark ids are unique across the whole set, so a stratum drawn later
    # can be starved by one drawn earlier. Fill the scarcest pool first; the
    # order is a deterministic function of the pools, not of the quota table.
    fill_order = sorted(QUOTAS, key=lambda name: (len(pools.get(name, [])), name))
    for stratum in fill_order:
        quota = QUOTAS[stratum]
        pool = sorted(pools.get(stratum, []), key=lambda row: row["original_id"])
        picked = balanced_pick(pool, quota, used_ids, rng)
        if len(picked) != quota:
            raise SystemExit(
                f"sampling shortage for {stratum}: wanted {quota}, got {len(picked)}"
            )
        stratum_report[stratum] = {
            "pool_total": len(pool),
            "selected": len(picked),
            "machine_pool_share_of_architecture": None,
        }
        selected.extend(picked)
    if len({row["original_id"] for row in selected}) != len(selected):
        raise SystemExit("sample contains a repeated benchmark id")

    architecture_pool_totals = Counter()
    for candidate in candidates:
        architecture_pool_totals[candidate["system"]] += 1
    for stratum, report in stratum_report.items():
        system = "debate" if stratum.startswith("debate") else "sequential"
        report["machine_pool_share_of_architecture"] = (
            f"{report['pool_total']}/{architecture_pool_totals[system]}"
        )

    rng.shuffle(selected)
    for index, item in enumerate(selected, start=1):
        item["item_blind_id"] = f"FTI-{index:03d}"

    stage_rows = []
    for item in selected:
        for entry in item["stage_rows"]:
            row = entry["row"]
            stage_rows.append({
                "item_blind_id": item["item_blind_id"],
                "position": entry["position"],
                "system": item["system"],
                "source_run": item["source_run"],
                "dataset": item["dataset"],
                "model_variant": item["model_variant"],
                "budget": item["budget"],
                "original_id": item["original_id"],
                "machine_sampling_stratum": item["machine_sampling_stratum"],
                "source_uid": row["source_uid"],
                "stage_name": str(row["stage_name"]),
                "stage_index": int(row["stage_index"]),
                "stage_truncated": row.get("stage_truncated"),
                "question_any_truncated": item["question_any_truncated"],
                "final_label_source": item["final_label_source"],
                "question": item["question"],
                "reference_answer": item["gold"],
                "reference_aliases": item["gold_aliases"],
                "stage_output": row["stage_text"],
                "machine_discovery_label": row.get("judge_gold_discovered_label"),
                "machine_discovery_reason_code": row.get("judge_discovery_reason_code"),
                "machine_endorsement_label": row.get("judge_endorsed_label"),
                "machine_endorsed_answer": row.get("judge_endorsed_answer"),
                "machine_endorsement_reason_code":
                    row.get("judge_endorsement_reason_code"),
                "is_duplicate_of": None,
                "in_item_analysis": True,
            })

    duplicates = []
    if args.duplicate_rows:
        pool_for_duplicates = sorted(stage_rows, key=lambda row: row["source_uid"])
        for row in rng.sample(pool_for_duplicates, args.duplicate_rows):
            duplicate = dict(row)
            duplicate["is_duplicate_of"] = row["source_uid"]
            duplicate["in_item_analysis"] = False
            duplicates.append(duplicate)
    all_rows = stage_rows + duplicates
    rng.shuffle(all_rows)
    for index, row in enumerate(all_rows, start=1):
        row["blind_stage_id"] = f"FTS-{index:04d}"
    for row in all_rows:
        if row["is_duplicate_of"]:
            origin = next(
                other for other in all_rows
                if other["source_uid"] == row["is_duplicate_of"]
                and not other["is_duplicate_of"]
            )
            row["is_duplicate_of"] = origin["blind_stage_id"]

    args.out.mkdir(parents=True, exist_ok=True)
    blind_fields = [
        "blind_stage_id", "question", "reference_answer",
        "reference_aliases", "stage_output",
    ]

    def write_blind(path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=blind_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({
                    "blind_stage_id": row["blind_stage_id"],
                    "question": row["question"],
                    "reference_answer": row["reference_answer"],
                    "reference_aliases":
                        json.dumps(row["reference_aliases"], ensure_ascii=False),
                    "stage_output": row["stage_output"],
                })

    write_blind(blind_path, sorted(all_rows, key=lambda row: row["blind_stage_id"]))

    pilot_strata = [
        "debate_picker_c_to_w", "debate_picker_w_to_c",
        "sequential_aggregator_c_to_w", "sequential_aggregator_w_to_c",
    ]
    pilot_rows: list[dict] = []
    pilot_report = {}
    for stratum in pilot_strata:
        pool = sorted(
            (row for row in all_rows
             if row["machine_sampling_stratum"] == stratum
             and not row["is_duplicate_of"]),
            key=lambda row: row["blind_stage_id"],
        )
        take = min(args.pilot_per_stratum, len(pool))
        chosen = rng.sample(pool, take) if take else []
        pilot_report[stratum] = {"requested": args.pilot_per_stratum, "selected": take}
        pilot_rows.extend(chosen)
    pilot_rows.sort(key=lambda row: row["blind_stage_id"])
    pilot_path = args.out / f"pilot_stage_review_{len(pilot_rows)}.csv"
    if not args.force and pilot_path.exists():
        parser.error(f"pilot output already exists: {pilot_path}; pass --force")
    write_blind(pilot_path, pilot_rows)
    pilot_ids = {row["blind_stage_id"] for row in pilot_rows}
    for row in all_rows:
        row["in_pilot"] = row["blind_stage_id"] in pilot_ids

    key_fields = [
        "blind_stage_id", "item_blind_id", "system", "position", "source_run",
        "dataset", "model_variant", "budget", "original_id",
        "machine_sampling_stratum", "source_uid", "stage_name", "stage_index",
        "stage_truncated", "question_any_truncated", "final_label_source",
        "machine_discovery_label", "machine_discovery_reason_code",
        "machine_endorsement_label", "machine_endorsed_answer",
        "machine_endorsement_reason_code", "is_duplicate_of",
        "in_item_analysis", "in_pilot",
    ]
    with key_path.open("w", encoding="utf-8") as handle:
        for row in sorted(all_rows, key=lambda row: row["blind_stage_id"]):
            handle.write(json.dumps(
                {field: row[field] for field in key_fields}, ensure_ascii=False
            ) + "\n")

    with item_path.open("w", encoding="utf-8") as handle:
        for item in sorted(selected, key=lambda row: row["item_blind_id"]):
            record = {
                key: value for key, value in item.items() if key != "stage_rows"
            }
            record["stage_blind_ids"] = {
                entry["position"]: next(
                    row["blind_stage_id"] for row in all_rows
                    if row["source_uid"] == entry["row"]["source_uid"]
                    and not row["is_duplicate_of"]
                )
                for entry in item["stage_rows"]
            }
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "seed": args.seed,
        "items": len(selected),
        "stage_rows_for_analysis": len(stage_rows),
        "hidden_duplicate_rows": len(duplicates),
        "blind_rows_total": len(all_rows),
        "quotas": QUOTAS,
        "stratum_fill_order": fill_order,
        "stratum_pools": stratum_report,
        "shortage_records": [SHORTAGE_RECORD],
        "shortage_rules": SHORTAGE_RULES,
        "usable_items_by_architecture": dict(sorted(architecture_pool_totals.items())),
        "excluded_prior_audit_ids": len(excluded_ids),
        "exclusions": dict(sorted(dropped.items())),
        "balance_source_run": spread(selected, "source_run"),
        "balance_dataset": spread(selected, "dataset"),
        "balance_model_variant": spread(selected, "model_variant"),
        "balance_budget": spread(selected, "budget"),
        "balance_question_any_truncated": spread(selected, "question_any_truncated"),
        "balance_source_truncated": spread(selected, "source_truncated"),
        "balance_final_label_source": spread(selected, "final_label_source"),
        "unique_benchmark_ids": len({row["original_id"] for row in selected}),
        "pilot_requested_rows": len(pilot_strata) * args.pilot_per_stratum,
        "pilot_actual_rows": len(pilot_rows),
        "pilot_shortfall_rows": (
            len(pilot_strata) * args.pilot_per_stratum - len(pilot_rows)
        ),
        "pilot_shortfall_reason": (
            "debate_picker_w_to_c contains one eligible item with three stage outputs"
            if len(pilot_rows) < len(pilot_strata) * args.pilot_per_stratum
            else None
        ),
        "pilot": pilot_report,
        "notes": [
            "C/W in machine_sampling_stratum are Mistral labels and define the"
            " sampling stratum only; they are never a human gold label.",
            "Population rates must be computed from stratum_pools, not from the"
            " 160 sampled items; report stratified or macro figures.",
            "Hidden duplicate rows measure intra-rater consistency and are"
            " excluded from the 160-item analysis (in_item_analysis=false).",
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    for path in (*core_outputs, pilot_path):
        print(f"written: {path}")


if __name__ == "__main__":
    main()
