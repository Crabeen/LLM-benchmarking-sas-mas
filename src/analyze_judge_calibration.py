"""Compare Mistral, Qwen, and lexical evaluators against blind human labels."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path


BINARY_LABELS = {"correct", "incorrect"}


def normalize_label(value: object) -> str | None:
    if value is None:
        return None
    label = str(value).strip().lower()
    aliases = {
        "c": "correct",
        "true": "correct",
        "1": "correct",
        "i": "incorrect",
        "false": "incorrect",
        "0": "incorrect",
        "u": "uncertain",
        "?": "uncertain",
        "skip": "uncertain",
    }
    label = aliases.get(label, label)
    return label if label in {"correct", "incorrect", "uncertain", "parse_error"} else None


def bool_label(value: object) -> str | None:
    if value is True:
        return "correct"
    if value is False:
        return "incorrect"
    return None


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_human(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result = {}
    for row in rows:
        blind_id = str(row.get("blind_id", "")).strip()
        if not blind_id:
            continue
        if blind_id in result:
            raise ValueError(f"duplicate blind_id in human CSV: {blind_id}")
        row["normalized_human_label"] = normalize_label(row.get("human_label"))
        result[blind_id] = row
    return result


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return math.nan, math.nan
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    spread = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total))
    return centre - spread / denominator, centre + spread / denominator


def binary_metrics(human: list[str], evaluator: list[str]) -> dict:
    pairs = [
        (h, e)
        for h, e in zip(human, evaluator)
        if h in BINARY_LABELS and e in BINARY_LABELS
    ]
    eligible = sum(h in BINARY_LABELS for h in human)
    tp = sum(h == "correct" and e == "correct" for h, e in pairs)
    tn = sum(h == "incorrect" and e == "incorrect" for h, e in pairs)
    fp = sum(h == "incorrect" and e == "correct" for h, e in pairs)
    fn = sum(h == "correct" and e == "incorrect" for h, e in pairs)
    decided = len(pairs)
    accuracy = (tp + tn) / decided if decided else math.nan
    precision = tp / (tp + fp) if tp + fp else math.nan
    recall = tp / (tp + fn) if tp + fn else math.nan
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall and not math.isnan(precision + recall)
        else math.nan
    )
    specificity = tn / (tn + fp) if tn + fp else math.nan
    coverage = decided / eligible if eligible else math.nan
    lo, hi = wilson_interval(tp + tn, decided)

    if decided:
        human_correct = (tp + fn) / decided
        eval_correct = (tp + fp) / decided
        expected = human_correct * eval_correct + (1 - human_correct) * (1 - eval_correct)
        kappa = (accuracy - expected) / (1 - expected) if expected < 1 else math.nan
    else:
        kappa = math.nan
    return {
        "eligible": eligible,
        "decided": decided,
        "coverage": coverage,
        "accuracy": accuracy,
        "accuracy_lo": lo,
        "accuracy_hi": hi,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
        "kappa": kappa,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def fmt(value: float) -> str:
    return "NA" if math.isnan(value) else f"{value:.3f}"


def evaluator_labels(rows: list[dict], name: str) -> list[str | None]:
    if name == "Mistral-24B":
        return [normalize_label(row.get("judge_label")) for row in rows]
    if name == "Qwen-unified":
        return [bool_label(row.get("qwen_judge_correct")) for row in rows]
    if name == "legacy-contain":
        return [bool_label(row.get("legacy_string_match")) for row in rows]
    if name == "boundary-contain":
        return [bool_label(row.get("boundary_string_match")) for row in rows]
    if name == "normalized-EM":
        return [bool_label(row.get("normalized_em")) for row in rows]
    raise KeyError(name)


def metric_table(rows: list[dict], human_labels: list[str]) -> tuple[list[str], dict]:
    names = [
        "Mistral-24B",
        "Qwen-unified",
        "legacy-contain",
        "boundary-contain",
        "normalized-EM",
    ]
    lines = [
        "| evaluator | decided/eligible | coverage | accuracy (95% CI) | precision | recall | F1 | specificity | kappa |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    metrics = {}
    for name in names:
        labels = evaluator_labels(rows, name)
        result = binary_metrics(human_labels, labels)
        metrics[name] = result
        ci = f"{fmt(result['accuracy'])} [{fmt(result['accuracy_lo'])}, {fmt(result['accuracy_hi'])}]"
        lines.append(
            f"| {name} | {result['decided']}/{result['eligible']} | "
            f"{fmt(result['coverage'])} | {ci} | {fmt(result['precision'])} | "
            f"{fmt(result['recall'])} | {fmt(result['f1'])} | "
            f"{fmt(result['specificity'])} | {fmt(result['kappa'])} |"
        )
    return lines, metrics


def subgroup_lines(rows: list[dict], human: list[str], field: str) -> list[str]:
    lines = [
        f"| {field} | n human-binary | decided | accuracy | false positive | false negative |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    values = sorted({str(row.get(field, "unknown")) for row in rows})
    mistral = evaluator_labels(rows, "Mistral-24B")
    for value in values:
        indices = [i for i, row in enumerate(rows) if str(row.get(field, "unknown")) == value]
        result = binary_metrics([human[i] for i in indices], [mistral[i] for i in indices])
        lines.append(
            f"| {value} | {result['eligible']} | {result['decided']} | "
            f"{fmt(result['accuracy'])} | {result['fp']} | {result['fn']} |"
        )
    return lines


def flip_summary(rows: list[dict], human: list[str]) -> tuple[list[str], dict]:
    qwen = evaluator_labels(rows, "Qwen-unified")
    mistral = evaluator_labels(rows, "Mistral-24B")
    comparable = [
        i
        for i in range(len(rows))
        if qwen[i] in BINARY_LABELS and mistral[i] in BINARY_LABELS
    ]
    transitions = Counter(f"{qwen[i]}->{mistral[i]}" for i in comparable)
    disagreements = [i for i in comparable if qwen[i] != mistral[i]]
    adjudicated = [i for i in disagreements if human[i] in BINARY_LABELS]
    arbitration = Counter()
    for i in adjudicated:
        q_right = qwen[i] == human[i]
        m_right = mistral[i] == human[i]
        if q_right and not m_right:
            arbitration["qwen_right"] += 1
        elif m_right and not q_right:
            arbitration["mistral_right"] += 1
        elif q_right and m_right:
            arbitration["both_right"] += 1
        else:
            arbitration["both_wrong"] += 1
    lines = [
        f"- Comparable Qwen/Mistral binary labels: {len(comparable)}",
        f"- Qwen/Mistral disagreements: {len(disagreements)}",
        f"- Incorrect -> correct: {transitions['incorrect->correct']}",
        f"- Correct -> incorrect: {transitions['correct->incorrect']}",
        f"- On human-adjudicated disagreements, Mistral right: {arbitration['mistral_right']}",
        f"- On human-adjudicated disagreements, Qwen right: {arbitration['qwen_right']}",
    ]
    return lines, {"transitions": transitions, "arbitration": arbitration}


def write_queue(path: Path, rows: list[dict], human: list[str]) -> None:
    fields = [
        "blind_id",
        "human_label",
        "mistral_label",
        "qwen_label",
        "legacy_string_match",
        "dataset",
        "model_variant",
        "system",
        "budget",
        "question",
        "reference_answer",
        "reference_aliases",
        "candidate_answer",
        "mistral_reason_code",
        "mistral_extracted_answer",
    ]
    qwen = evaluator_labels(rows, "Qwen-unified")
    mistral = evaluator_labels(rows, "Mistral-24B")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, row in enumerate(rows):
            needs_queue = (
                mistral[index] not in BINARY_LABELS
                or human[index] not in BINARY_LABELS
                or mistral[index] != human[index]
                or (qwen[index] in BINARY_LABELS and qwen[index] != mistral[index])
            )
            if not needs_queue:
                continue
            writer.writerow(
                {
                    "blind_id": row["blind_id"],
                    "human_label": human[index] or "",
                    "mistral_label": mistral[index] or "",
                    "qwen_label": qwen[index] or "",
                    "legacy_string_match": row.get("legacy_string_match"),
                    "dataset": row.get("dataset"),
                    "model_variant": row.get("model_variant"),
                    "system": row.get("system"),
                    "budget": row.get("budget"),
                    "question": row.get("question"),
                    "reference_answer": row.get("gold"),
                    "reference_aliases": json.dumps(
                        row.get("gold_aliases") or [], ensure_ascii=False
                    ),
                    "candidate_answer": row.get("prediction"),
                    "mistral_reason_code": row.get("judge_reason_code"),
                    "mistral_extracted_answer": row.get("judge_extracted_answer"),
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--judged",
        type=Path,
        default=Path("analysis/judge_calibration/calibration_250.mistral.jsonl"),
    )
    parser.add_argument(
        "--human-csv",
        type=Path,
        default=Path("analysis/judge_calibration/human_labels.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("analysis/judge_calibration/CALIBRATION_REPORT.md"),
    )
    parser.add_argument(
        "--review-queue",
        type=Path,
        default=Path("analysis/judge_calibration/adjudication_queue.csv"),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    for output in (args.report, args.review_queue):
        if output.exists() and not args.force:
            parser.error(f"refusing to overwrite {output}; pass --force")
        output.parent.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(args.judged)
    human_by_id = load_human(args.human_csv)
    blind_ids = [str(row.get("blind_id", "")) for row in rows]
    if len(set(blind_ids)) != len(blind_ids):
        parser.error("duplicate blind_id in judged JSONL")
    missing = [blind_id for blind_id in blind_ids if blind_id not in human_by_id]
    if missing:
        parser.error(f"human CSV is missing {len(missing)} blind IDs")

    human = [human_by_id[blind_id]["normalized_human_label"] for blind_id in blind_ids]
    n_labelled = sum(label is not None for label in human)
    n_binary = sum(label in BINARY_LABELS for label in human)
    if not n_labelled:
        parser.error("no valid human labels; fill human_label before analysis")

    metric_lines, _ = metric_table(rows, human)
    flip_lines, _ = flip_summary(rows, human)
    mistral_counts = Counter(normalize_label(row.get("judge_label")) or "invalid" for row in rows)
    human_counts = Counter(label or "blank_or_invalid" for label in human)
    report = [
        "# External Judge Calibration",
        "",
        f"- Total sampled answers: {len(rows)}",
        f"- Human labels present: {n_labelled}",
        f"- Human binary labels used for performance metrics: {n_binary}",
        f"- Human label counts: `{dict(human_counts)}`",
        f"- Mistral label counts: `{dict(mistral_counts)}`",
        "",
        "## Agreement with blind human labels",
        "",
        *metric_lines,
        "",
        "The 95% interval is a Wilson interval for accuracy among decided binary cases. "
        "Coverage excludes evaluator abstentions (`uncertain`/`parse_error`).",
        "",
        "## Mistral subgroup audit: dataset",
        "",
        *subgroup_lines(rows, human, "dataset"),
        "",
        "## Mistral subgroup audit: SAS versus MAS",
        "",
        *subgroup_lines(rows, human, "system_class"),
        "",
        "## Qwen-to-Mistral label transitions",
        "",
        *flip_lines,
        "",
        "## Interpretation rule",
        "",
        "Do not promote Mistral to the primary judge solely from aggregate accuracy. "
        "Check coverage and false-positive/false-negative asymmetry across SAS/MAS and datasets, "
        "then adjudicate the generated review queue.",
        "",
    ]
    args.report.write_text("\n".join(report), encoding="utf-8")
    write_queue(args.review_queue, rows, human)
    print(f"written: {args.report}")
    print(f"written: {args.review_queue}")


if __name__ == "__main__":
    main()
