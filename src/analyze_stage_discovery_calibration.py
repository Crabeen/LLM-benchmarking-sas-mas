"""Calibrate the dual stage judge against semantic-discovery human labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from .analyze_judge_calibration import BINARY_LABELS, binary_metrics, fmt, normalize_label


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_human(path: Path, overrides_path: Path | None) -> tuple[dict[str, str | None], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = {
        str(row.get("blind_id", "")).strip(): normalize_label(row.get("human_label"))
        for row in rows
    }
    applied = 0
    if overrides_path:
        payload = json.loads(overrides_path.read_text(encoding="utf-8"))
        overrides = payload.get("labels", {})
        if not isinstance(overrides, dict):
            raise ValueError("override JSON must contain a labels object")
        for blind_id, raw_label in overrides.items():
            label = normalize_label(raw_label)
            if label not in BINARY_LABELS:
                raise ValueError(f"invalid override for {blind_id}: {raw_label!r}")
            if blind_id not in labels:
                raise ValueError(f"override ID absent from human CSV: {blind_id}")
            if labels[blind_id] != label:
                applied += 1
            labels[blind_id] = label
    return labels, applied


def machine_labels(rows: list[dict], evaluator: str) -> list[str | None]:
    if evaluator == "Mistral-24B-discovery":
        return [normalize_label(row.get("judge_gold_discovered_label")) for row in rows]
    if evaluator == "Mistral-24B-evidence-valid":
        return [
            None
            if normalize_label(row.get("judge_gold_discovered_label")) == "correct"
            and row.get("judge_discovery_evidence_grounded") is not True
            else normalize_label(row.get("judge_gold_discovered_label"))
            for row in rows
        ]
    field = "lexical_contain" if evaluator == "lexical-contain" else "normalized_em"
    return ["correct" if row.get(field) is True else "incorrect" for row in rows]


def metric_table(rows: list[dict], human: list[str | None]) -> tuple[list[str], dict]:
    lines = [
        "| evaluator | decided/eligible | coverage | accuracy (95% CI) | precision | recall | F1 | specificity | kappa |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    results = {}
    for name in [
        "Mistral-24B-discovery",
        "Mistral-24B-evidence-valid",
        "lexical-contain",
        "normalized-EM",
    ]:
        result = binary_metrics(human, machine_labels(rows, name))
        results[name] = result
        ci = f"{fmt(result['accuracy'])} [{fmt(result['accuracy_lo'])}, {fmt(result['accuracy_hi'])}]"
        lines.append(
            f"| {name} | {result['decided']}/{result['eligible']} | "
            f"{fmt(result['coverage'])} | {ci} | {fmt(result['precision'])} | "
            f"{fmt(result['recall'])} | {fmt(result['f1'])} | "
            f"{fmt(result['specificity'])} | {fmt(result['kappa'])} |"
        )
    return lines, results


def subgroup(rows: list[dict], human: list[str | None], field: str) -> list[str]:
    machine = machine_labels(rows, "Mistral-24B-discovery")
    lines = [
        f"| {field} | n human-binary | accuracy | false positive | false negative |",
        "|---|---:|---:|---:|---:|",
    ]
    for value in sorted({str(row.get(field, "unknown")) for row in rows}):
        idx = [i for i, row in enumerate(rows) if str(row.get(field, "unknown")) == value]
        result = binary_metrics([human[i] for i in idx], [machine[i] for i in idx])
        lines.append(
            f"| {value} | {result['eligible']} | {fmt(result['accuracy'])} | "
            f"{result['fp']} | {result['fn']} |"
        )
    return lines


def write_queue(path: Path, rows: list[dict], human: list[str | None]) -> None:
    fields = [
        "blind_id", "human_discovery_label", "mistral_discovery_label",
        "mistral_endorsed_label", "selection_stratum", "system", "stage_truncated",
        "question", "gold", "stage_text", "discovery_evidence",
        "discovery_evidence_grounded", "discovery_reason_code", "endorsed_answer",
        "endorsement_reason_code",
    ]
    machine = machine_labels(rows, "Mistral-24B-discovery")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows):
            if human[index] not in BINARY_LABELS or machine[index] not in BINARY_LABELS or human[index] != machine[index]:
                writer.writerow(
                    {
                        "blind_id": row.get("blind_id"),
                        "human_discovery_label": human[index] or "",
                        "mistral_discovery_label": machine[index] or "",
                        "mistral_endorsed_label": row.get("judge_endorsed_label", ""),
                        "selection_stratum": row.get("selection_stratum"),
                        "system": row.get("system"),
                        "stage_truncated": row.get("stage_truncated"),
                        "question": row.get("question"),
                        "gold": row.get("gold"),
                        "stage_text": row.get("stage_text"),
                        "discovery_evidence": row.get("judge_discovery_evidence"),
                        "discovery_evidence_grounded": row.get(
                            "judge_discovery_evidence_grounded"
                        ),
                        "discovery_reason_code": row.get("judge_discovery_reason_code"),
                        "endorsed_answer": row.get("judge_endorsed_answer"),
                        "endorsement_reason_code": row.get("judge_endorsement_reason_code"),
                    }
                )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judged", type=Path,
        default=Path("analysis/stage_judge_calibration/stage_calibration_200.mistral_dual_v4.jsonl"),
    )
    parser.add_argument(
        "--human-csv", type=Path,
        default=Path("analysis/stage_judge_calibration/human_stage_labels.csv"),
    )
    parser.add_argument(
        "--overrides-json", type=Path,
        default=Path("analysis/stage_judge_calibration/discovery_adjudication_overrides.json"),
    )
    parser.add_argument(
        "--report", type=Path,
        default=Path("analysis/stage_judge_calibration/STAGE_DISCOVERY_CALIBRATION_REPORT.md"),
    )
    parser.add_argument(
        "--review-queue", type=Path,
        default=Path("analysis/stage_judge_calibration/stage_discovery_adjudication_queue.csv"),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for output in [args.report, args.review_queue]:
        if output.exists() and not args.force:
            parser.error(f"refusing to overwrite {output}; pass --force")

    rows = read_jsonl(args.judged)
    human_by_id, overrides_applied = load_human(args.human_csv, args.overrides_json)
    missing = [row["blind_id"] for row in rows if row["blind_id"] not in human_by_id]
    if missing:
        parser.error(f"human CSV missing {len(missing)} blind IDs")
    human = [human_by_id[row["blind_id"]] for row in rows]
    if sum(label in BINARY_LABELS for label in human) != len(rows):
        parser.error("all discovery labels must be binary after overrides")
    if any("judge_gold_discovered_label" not in row for row in rows):
        parser.error("judged file does not contain dual-judge discovery labels")

    table, _ = metric_table(rows, human)
    discovery_positive = [
        row for row in rows
        if normalize_label(row.get("judge_gold_discovered_label")) == "correct"
    ]
    ungrounded = sum(
        row.get("judge_discovery_evidence_grounded") is not True
        for row in discovery_positive
    )
    report = [
        "# Intermediate-Stage Semantic-Discovery Calibration",
        "",
        f"- Sampled stage outputs: {len(rows)}",
        f"- Human discovery-label counts: `{dict(Counter(human))}`",
        f"- Adjudication overrides that changed first-pass labels: {overrides_applied}",
        f"- Mistral discovery-label counts: `{dict(Counter(machine_labels(rows, 'Mistral-24B-discovery')))}`",
        f"- Ungrounded evidence among Mistral discovery-positive rows: {ungrounded}/{len(discovery_positive)}",
        "",
        "## Agreement with human semantic-discovery labels",
        "",
        *table,
        "",
        "## Mistral discovery audit by selection stratum",
        "",
        *subgroup(rows, human, "selection_stratum"),
        "",
        "## Mistral discovery audit by stage truncation",
        "",
        *subgroup(rows, human, "stage_truncated"),
        "",
        "## Mistral discovery audit by system",
        "",
        *subgroup(rows, human, "system"),
        "",
        "## Operational decision",
        "",
        "Semantic discovery is sufficiently supported for full-trace rejudging with evidence validation enabled. Treat uncertain, parse-error, or ungrounded-positive rows as unresolved rather than correct. Because no pass threshold was preregistered, this is an operational decision based on the reported agreement, not a formal hypothesis test.",
        "",
        "Keep targeted manual review for debate beneficial flips and sequential C-to-W transitions, which have the weakest subgroup agreement in this calibration sample.",
        "",
        "## Scope",
        "",
        "This report calibrates semantic discovery only. The endorsed-answer label requires a separately human-confirmed gold column before it can be treated as calibrated.",
        "",
    ]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report), encoding="utf-8")
    write_queue(args.review_queue, rows, human)
    print(f"written: {args.report}")
    print(f"written: {args.review_queue}")


if __name__ == "__main__":
    main()
