"""Reuse identical stage labels and export only unseen final predictions."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from .rejudge_external import atomic_write_jsonl, read_jsonl


IDENTITY_FIELDS = ("source_run", "system", "budget", "id")
JUDGE_FIELDS = (
    "judge_gold_discovered_label",
    "judge_gold_discovered",
    "judge_discovery_evidence_ids",
    "judge_discovery_evidence",
    "judge_discovery_evidence_grounded",
    "judge_discovery_reason_code",
    "judge_prompt_version",
    "judge_model",
    "judge_parse_mode",
    "judge_attempts",
    "judge_error",
)
ENDORSEMENT_FIELDS = (
    "judge_endorsed_label",
    "judge_endorsed_correct",
    "judge_endorsed_answer",
    "judge_endorsement_reason_code",
)


def item_key(row: dict) -> tuple[str, str, int, str]:
    return (
        str(row["source_run"]), str(row["system"]),
        int(row["budget"]), str(row["id"]),
    )


def final_row(rows: list[dict]) -> dict:
    first = rows[0]
    prediction = str(first.get("final_prediction", ""))
    return {
        "source_uid": "/".join((*map(str, item_key(first)), "final")),
        "source_run": first["source_run"],
        "source_file": first.get("source_file", ""),
        "id": str(first["id"]),
        "dataset": first["dataset"],
        "model_variant": first["model_variant"],
        "system": first["system"],
        "budget": int(first["budget"]),
        "question": first["question"],
        "gold": first["gold"],
        "gold_aliases": first.get("gold_aliases") or [],
        "stage_name": "final",
        "stage_index": max(int(row["stage_index"]) for row in rows) + 1,
        "stage_text": prediction,
        "producing_role": "final_aggregator",
        "stage_truncated": None,
        "question_any_truncated": bool(first.get("question_any_truncated")),
        "wall_seconds": first.get("wall_seconds"),
        "thinking_tokens_total": first.get("thinking_tokens_total"),
        "final_prediction": prediction,
    }


def split_final_rows(stage_rows: list[dict]) -> tuple[list[dict], list[dict]]:
    groups: dict[tuple[str, str, int, str], list[dict]] = defaultdict(list)
    for row in stage_rows:
        groups[item_key(row)].append(row)
    reused, to_judge = [], []
    for key in sorted(groups):
        rows = groups[key]
        final = final_row(rows)
        matches = [
            row for row in rows
            if str(row.get("stage_text", "")).strip()
            == final["stage_text"].strip()
        ]
        labels = {
            row.get("judge_gold_discovered_label") for row in matches
            if row.get("judge_gold_discovered_label")
        }
        if matches and len(labels) == 1:
            source = matches[0]
            final.update({field: source.get(field) for field in JUDGE_FIELDS})
            final["final_label_source"] = "identical_intermediate"
            final["reused_stage_name"] = source.get("stage_name")
            # The endorsement axis is reused only when every text-identical
            # intermediate stage carries the same endorsement label. The judge
            # is not perfectly self-consistent on byte-identical inputs, so a
            # disagreement here would otherwise copy an arbitrary label.
            endorsement_labels = {
                row.get("judge_endorsed_label") for row in matches
                if row.get("judge_endorsed_label")
            }
            if len(endorsement_labels) == 1:
                final.update(
                    {field: source.get(field) for field in ENDORSEMENT_FIELDS}
                )
                final["endorsement_label_source"] = "identical_intermediate"
            else:
                final.update({field: None for field in ENDORSEMENT_FIELDS})
                final["endorsement_label_source"] = (
                    "reuse_conflict" if endorsement_labels else "reuse_missing"
                )
                final["endorsement_reuse_conflict_labels"] = sorted(
                    str(label) for label in endorsement_labels
                )
            reused.append(final)
        else:
            final["final_label_source"] = "mistral_pending"
            if matches:
                final["reuse_conflict_labels"] = sorted(str(label) for label in labels)
            to_judge.append(final)
    return reused, to_judge


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stages", type=Path,
        default=Path("analysis/stage_judge_full/all_stages.mistral_dual_v4.jsonl"),
    )
    parser.add_argument(
        "--out-dir", type=Path,
        default=Path("analysis/stage_judge_full"),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    reused_path = args.out_dir / "finals_reused_from_stages.jsonl"
    pending_path = args.out_dir / "finals_to_judge.jsonl"
    manifest_path = args.out_dir / "finals_export.manifest.json"
    outputs = (reused_path, pending_path, manifest_path)
    if not args.force and any(path.exists() for path in outputs):
        parser.error("final export outputs already exist; pass --force")
    stages = read_jsonl(args.stages)
    reused, pending = split_final_rows(stages)
    atomic_write_jsonl(reused, reused_path)
    atomic_write_jsonl(pending, pending_path)
    endorsement_conflicts = [
        row for row in reused
        if row.get("endorsement_label_source") != "identical_intermediate"
    ]
    manifest = {
        "unique_items": len(reused) + len(pending),
        "reused_identical_intermediate": len(reused),
        "requires_mistral_judgment": len(pending),
        "reused_by_system": dict(sorted(Counter(row["system"] for row in reused).items())),
        "pending_by_system": dict(sorted(Counter(row["system"] for row in pending).items())),
        "endorsement_reused": len(reused) - len(endorsement_conflicts),
        "endorsement_reuse_conflicts": len(endorsement_conflicts),
        "endorsement_conflicts_by_system": dict(
            sorted(Counter(row["system"] for row in endorsement_conflicts).items())
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"written: {reused_path}")
    print(f"written: {pending_path}")


if __name__ == "__main__":
    main()
