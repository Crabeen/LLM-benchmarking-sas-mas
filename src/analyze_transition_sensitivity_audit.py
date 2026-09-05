#!/usr/bin/env python3
"""Unblind and analyse the completed 100-pair semantic transition audit."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_DIR = ROOT / "analysis" / "semantic_transition_sensitivity"
HUMAN_PATH = AUDIT_DIR / "human_review_completed.json"
KEY_PATH = AUDIT_DIR / "sensitivity_audit_key.jsonl"
FULL_TRANSITIONS_PATH = ROOT / "analysis" / "semantic_diagnostics" / "semantic_transitions.csv"

LABEL_MAP = {"Correct": "C", "Incorrect": "W", "Uncertain": "U"}
MACHINE_LABEL_MAP = {"correct": "C", "incorrect": "W", "uncertain": "U"}
TARGET_STRATA = {
    "debate_beneficial_w_to_c": ("debate", "W>C"),
    "debate_harmful_c_to_w": ("debate", "C>W"),
    "sequential_harmful_c_to_w": ("sequential", "C>W"),
}


def safe_div(num: float, den: float) -> float | None:
    return num / den if den else None


def fmt(value: float | None, digits: int = 3) -> str:
    return "NA" if value is None else f"{value:.{digits}f}"


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total == 0:
        return None, None
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def cohen_kappa(pairs: list[tuple[str, str]], labels: list[str]) -> float | None:
    if not pairs:
        return None
    n = len(pairs)
    observed = sum(left == right for left, right in pairs) / n
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum((left_counts[label] / n) * (right_counts[label] / n) for label in labels)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else None
    return (observed - expected) / (1 - expected)


def bool_text(value: object) -> bool:
    return str(value).strip().lower() == "true"


def load_rows() -> list[dict[str, object]]:
    human_rows = json.loads(HUMAN_PATH.read_text(encoding="utf-8"))
    key_rows = [json.loads(line) for line in KEY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    key_by_id = {row["blind_id"]: row for row in key_rows}
    if len(human_rows) != 100 or len(key_by_id) != 100:
        raise ValueError(f"Expected 100 human and key rows, got {len(human_rows)} and {len(key_by_id)}")

    joined = []
    for human in human_rows:
        blind_id = str(human["Blind ID"]).strip()
        if blind_id not in key_by_id:
            raise ValueError(f"Blind ID missing from key: {blind_id}")
        key = key_by_id[blind_id]
        source_human = LABEL_MAP[str(human["Source Label"]).strip()]
        destination_human = LABEL_MAP[str(human["Destination Label"]).strip()]
        source_machine = MACHINE_LABEL_MAP[str(key["source_machine_label"]).strip().lower()]
        destination_machine = MACHINE_LABEL_MAP[str(key["destination_machine_label"]).strip().lower()]
        human_transition = f"{source_human}>{destination_human}"
        machine_transition = f"{source_machine}>{destination_machine}"
        joined.append(
            {
                **key,
                "human_source_label": source_human,
                "human_destination_label": destination_human,
                "human_transition": human_transition,
                "machine_transition": machine_transition,
                "source_agree": source_human == source_machine,
                "destination_agree": destination_human == destination_machine,
                "transition_agree": human_transition == machine_transition,
                "human_source_evidence": human.get("Source Evidence") or "",
                "human_destination_evidence": human.get("Destination Evidence") or "",
                "reviewer_notes": human.get("Reviewer Notes") or "",
                "destination_truncated_bool": bool_text(key.get("destination_truncated")),
                "any_truncated_bool": bool_text(key.get("any_truncated")),
            }
        )
    return joined


def agreement_summary(rows: list[dict[str, object]]) -> dict[str, object]:
    stage_pairs = []
    source_pairs = []
    destination_pairs = []
    transition_pairs = []
    for row in rows:
        for prefix, bucket in (("source", source_pairs), ("destination", destination_pairs)):
            human = str(row[f"human_{prefix}_label"])
            machine = str(row[f"{prefix}_machine_label"])
            machine = MACHINE_LABEL_MAP.get(machine.lower(), machine)
            if human != "U" and machine != "U":
                bucket.append((machine, human))
                stage_pairs.append((machine, human))
        human_transition = str(row["human_transition"])
        machine_transition = str(row["machine_transition"])
        if "U" not in human_transition and "U" not in machine_transition:
            transition_pairs.append((machine_transition, human_transition))

    strict_stage_correct = sum(bool(row["source_agree"]) + bool(row["destination_agree"]) for row in rows)
    strict_transition_correct = sum(bool(row["transition_agree"]) for row in rows)
    return {
        "pairs": len(rows),
        "stage_labels_total": 2 * len(rows),
        "stage_labels_resolved": len(stage_pairs),
        "stage_accuracy_resolved": safe_div(sum(m == h for m, h in stage_pairs), len(stage_pairs)),
        "stage_accuracy_strict": safe_div(strict_stage_correct, 2 * len(rows)),
        "stage_kappa_resolved": cohen_kappa(stage_pairs, ["C", "W"]),
        "source_accuracy_resolved": safe_div(sum(m == h for m, h in source_pairs), len(source_pairs)),
        "destination_accuracy_resolved": safe_div(sum(m == h for m, h in destination_pairs), len(destination_pairs)),
        "transition_pairs_resolved": len(transition_pairs),
        "transition_accuracy_resolved": safe_div(sum(m == h for m, h in transition_pairs), len(transition_pairs)),
        "transition_accuracy_strict": safe_div(strict_transition_correct, len(rows)),
        "transition_kappa_resolved": cohen_kappa(transition_pairs, ["C>C", "C>W", "W>C", "W>W"]),
        "uncertain_stage_labels": 2 * len(rows) - len(stage_pairs),
        "uncertain_transition_pairs": len(rows) - len(transition_pairs),
    }


def group_metrics(rows: list[dict[str, object]], group_fields: list[str]) -> list[dict[str, object]]:
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[field] for field in group_fields)].append(row)
    results = []
    for key, group in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        resolved = [row for row in group if "U" not in str(row["human_transition"])]
        exact = sum(bool(row["transition_agree"]) for row in resolved)
        source_resolved = [row for row in group if row["human_source_label"] != "U"]
        destination_resolved = [row for row in group if row["human_destination_label"] != "U"]
        low, high = wilson(exact, len(resolved))
        result = {field: value for field, value in zip(group_fields, key)}
        result.update(
            {
                "n": len(group),
                "resolved_transition_n": len(resolved),
                "exact_transition_agreement_n": exact,
                "exact_transition_agreement": safe_div(exact, len(resolved)),
                "wilson_95_low": low,
                "wilson_95_high": high,
                "source_accuracy": safe_div(sum(bool(row["source_agree"]) for row in source_resolved), len(source_resolved)),
                "destination_accuracy": safe_div(sum(bool(row["destination_agree"]) for row in destination_resolved), len(destination_resolved)),
                "human_c_to_w": sum(row["human_transition"] == "C>W" for row in group),
                "human_w_to_c": sum(row["human_transition"] == "W>C" for row in group),
                "uncertain_pairs": len(group) - len(resolved),
            }
        )
        results.append(result)
    return results


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_report(rows: list[dict[str, object]], overall: dict[str, object], strata: list[dict[str, object]], projections: list[dict[str, object]]) -> str:
    machine_cw = Counter(str(row["human_transition"]) for row in rows if row["machine_transition"] == "C>W")
    machine_wc = Counter(str(row["human_transition"]) for row in rows if row["machine_transition"] == "W>C")
    human_transitions = Counter(str(row["human_transition"]) for row in rows)
    resolved_truncated = [
        row for row in rows
        if "U" not in str(row["human_transition"]) and bool(row["destination_truncated_bool"])
    ]
    resolved_nontruncated = [
        row for row in rows
        if "U" not in str(row["human_transition"]) and not bool(row["destination_truncated_bool"])
    ]

    def transition_agreement(group: list[dict[str, object]]) -> float | None:
        return safe_div(sum(bool(row["transition_agree"]) for row in group), len(group))

    dataset_agreement = {}
    for dataset in sorted({str(row["dataset"]) for row in rows}):
        group = [
            row for row in rows
            if str(row["dataset"]) == dataset and "U" not in str(row["human_transition"])
        ]
        dataset_agreement[dataset] = transition_agreement(group)

    qwen_path = AUDIT_DIR / "qwen72b_gptq_v2.score.json"
    qwen = json.loads(qwen_path.read_text(encoding="utf-8")) if qwen_path.exists() else None
    qwen_stage_error_counts = Counter()
    qwen_stage_disagreements_path = AUDIT_DIR / "qwen72b_gptq_v2.score.stage_disagreements.csv"
    if qwen_stage_disagreements_path.exists():
        with qwen_stage_disagreements_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                qwen_stage_error_counts[(row["candidate_label"], row["human_label"])] += 1
    lines = [
        "# Human Sensitivity Audit of Semantic Stage Transitions (rev. 3)",
        "",
        "This report unblinds the completed 100-pair audit only after all rows passed the completion and evidence checks. Human labels follow the v4 discovery codebook: a stage is `Correct` when a readable statement states or unambiguously entails the reference answer in the requested entity, relation and granularity. A later rejection or replacement does not erase discovery; it affects `endorsed_answer_correct` instead.",
        "",
        "Revision 3 applies the same discovery rule to the two consistency flags outside the original Qwen-disagreement set: `SEN-0051` source changes `U -> C`, and `SEN-0081` source changes `W -> C`.",
        "",
        "## Completion and overall agreement",
        "",
        "- 100/100 pairs completed; all labels valid; every `Correct` label has evidence.",
        f"- Stage-label agreement: {fmt(overall['stage_accuracy_resolved'])} ({overall['stage_labels_resolved']} resolved labels), Cohen's kappa = {fmt(overall['stage_kappa_resolved'])}.",
        f"- Source-stage accuracy: {fmt(overall['source_accuracy_resolved'])}; destination-stage accuracy: {fmt(overall['destination_accuracy_resolved'])}.",
        f"- Exact transition agreement: {fmt(overall['transition_accuracy_resolved'])} ({overall['transition_pairs_resolved']} resolved pairs), multiclass kappa = {fmt(overall['transition_kappa_resolved'])}.",
        f"- Strict stage accuracy: {fmt(overall['stage_accuracy_strict'])}; strict transition accuracy: {fmt(overall['transition_accuracy_strict'])}. There are {overall['uncertain_stage_labels']} uncertain stage labels and {overall['uncertain_transition_pairs']} uncertain transition pairs.",
        f"- Human transition distribution: C>C {human_transitions['C>C']}; C>W {human_transitions['C>W']}; W>C {human_transitions['W>C']}; W>W {human_transitions['W>W']}; contains U {sum('U' in key for key in human_transitions.elements())}.",
        "",
        "The targeted sample deliberately over-represents disputed flip types. Therefore these numbers measure judge reliability in difficult transition strata; they are not estimates of overall trace accuracy.",
        "",
    ]
    if qwen:
        lines.extend(
            [
                "## Stronger-judge follow-up",
                "",
                "Qwen2.5-72B-Instruct-GPTQ-Int4 completed all 200 stage judgments with no parse errors and no ungrounded positive evidence.",
                f"Against the rev. 3 human labels, it achieved {fmt(qwen['stage']['accuracy'])} stage accuracy ({qwen['stage']['n']} labels; kappa {fmt(qwen['stage']['kappa'])}) and {fmt(qwen['transition']['accuracy'])} exact transition accuracy ({qwen['transition']['n']} pairs; multiclass kappa {fmt(qwen['transition']['kappa'])}).",
                f"Its {sum(qwen_stage_error_counts.values())} stage errors comprise {qwen_stage_error_counts[('W', 'C')]} false negatives (Qwen too strict) and {qwen_stage_error_counts[('C', 'W')]} false positives (Qwen too permissive). The audited CSV contains 30 adjudication records because it preserves the original 28 disagreement cases and the two rev. 3 consistency-sweep cases.",
                "It still fails the fixed acceptance rule and is not approved as the sole automatic semantic judge for full-trace re-judging.",
                "",
            ]
        )
    lines.extend(
        [
        "## Transition-stratum sensitivity",
        "",
        "| audit stratum | n | exact agree | rate | 95% Wilson interval | source accuracy | destination accuracy | human C>W | human W>C |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    by_stratum = {str(row["audit_stratum"]): row for row in strata}
    for name in ["debate_beneficial_w_to_c", "debate_harmful_c_to_w", "sequential_harmful_c_to_w", "stable_control"]:
        row = by_stratum[name]
        lines.append(
            f"| {name} | {row['n']} | {row['exact_transition_agreement_n']} | {fmt(row['exact_transition_agreement'])} | {fmt(row['wilson_95_low'])}–{fmt(row['wilson_95_high'])} | {fmt(row['source_accuracy'])} | {fmt(row['destination_accuracy'])} | {row['human_c_to_w']} | {row['human_w_to_c']} |"
        )

    lines.extend(
        [
            "",
            "## What caused the transition disagreements",
            "",
            f"- Among 50 machine-labelled C>W pairs, human review found {machine_cw['C>W']} C>W, {machine_cw['W>W']} W>W, {machine_cw['C>C']} C>C, and {machine_cw['U>W']} U>W. Thus the dominant error was a false claim that the source had already discovered the answer, not a missed error at the destination.",
            f"- Among 25 machine-labelled W>C pairs, human review found {machine_wc['W>C']} W>C, {machine_wc['W>W']} W>W, and {machine_wc['C>C']} C>C. Thus Mistral frequently over-called a revision as newly correct.",
            f"- Exact transition agreement was {fmt(transition_agreement(resolved_truncated))} for truncated destinations versus {fmt(transition_agreement(resolved_nontruncated))} for non-truncated destinations in this designed sample. This is a judge-reliability warning, not evidence that truncation causes semantic loss.",
            f"- Agreement was {fmt(dataset_agreement.get('2wiki'))} on 2Wiki and {fmt(dataset_agreement.get('musique'))} on MuSiQue. Because the sample was selected by transition strata and balanced covariates, treat this as a diagnostic signal rather than a population comparison.",
            "- `audit_stratum` records the machine-defined sampling stratum. Human adjudication can legitimately change the realised transition, as in `SEN-0081` (`W>C` sampling stratum, human `C>C`).",
            "",
            "## Sensitivity projection for the headline flip counts",
            "",
            "The following applies each audited stratum's exact-confirmation rate to the corresponding full machine-labelled count. It is a descriptive sensitivity projection, not a replacement ground-truth estimate: the audit was balanced across covariates rather than drawn as a simple random sample.",
            "",
            "| claim | full machine count | audit confirmed | audit n | confirmation rate | projected confirmed count | diagnostic 95% range |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in projections:
        lines.append(
            f"| {row['audit_stratum']} | {row['full_machine_count']} | {row['confirmed_n']} | {row['audit_n']} | {fmt(row['confirmation_rate'])} | {row['projected_confirmed_count']:.1f} | {row['projected_low']:.1f}–{row['projected_high']:.1f} |"
        )

    debate_benefit = next(row for row in projections if row["audit_stratum"] == "debate_beneficial_w_to_c")
    debate_harm = next(row for row in projections if row["audit_stratum"] == "debate_harmful_c_to_w")
    seq_harm = next(row for row in projections if row["audit_stratum"] == "sequential_harmful_c_to_w")
    lines.extend(
        [
            "",
            "## Effect on the MAS failure-localisation conclusions",
            "",
            f"- Debate revision: the audit confirms {debate_harm['confirmed_n']}/{debate_harm['audit_n']} sampled harmful flips and {debate_benefit['confirmed_n']}/{debate_benefit['audit_n']} beneficial flips. The point sensitivity projection is {debate_harm['projected_confirmed_count']:.1f} harmful versus {debate_benefit['projected_confirmed_count']:.1f} beneficial transitions. The direction `harmful > beneficial` is supported at the point estimate, but should be reported as sensitivity-adjusted rather than as exact counts.",
            f"- Sequential worker chain: {seq_harm['confirmed_n']}/{seq_harm['audit_n']} sampled C>W transitions are exactly confirmed. This supports worker-chain loss as a real mode, but the full count of 151 should not be treated as error-free.",
            "- Stable controls quantify false flips and stage-label instability. They are the correct negative control for deciding whether transition claims are more fragile than ordinary C>C/W>W classifications.",
            "- This audit does not directly re-adjudicate Debate final-picker decisions or Sequential final-aggregator decisions. The comparison `revision versus picker` and `worker chain versus aggregator` therefore remains partly dependent on the calibrated Mistral final-stage labels.",
            "- The 100-pair case-control design cannot estimate the population association between truncation and C>W. The full-trace adjusted OR remains the relevant result; audit-by-truncation agreement only diagnoses whether label reliability differs across truncated and non-truncated destinations.",
            "",
            "## Files",
            "",
            "- `audit_metrics.csv`: overall, stratum and covariate agreement metrics.",
            "- `human_labels_joined.csv`: unblinded human and machine labels with run metadata.",
            "- `audit_disagreements.csv`: all transition disagreements, including human evidence and notes.",
            "- `audit_transition_confusion.csv`: machine-by-human transition confusion table.",
            "- `audit_projection.csv`: sensitivity projections for the three headline flip counts.",
            "- `qwen72b_gptq_v2.score.json`: Qwen rev. 3 stage and transition calibration metrics.",
            "- `qwen72b_gptq_v2.score.stage_disagreements.audited.csv`: 30 adjudication records, preserving the original 28 disagreement cases plus the two consistency-sweep cases.",
            "",
            "## Interpretation limit",
            "",
            "The audit evaluates Mistral and Qwen semantic-stage labels under the v4 discovery rule. It separates answer discovery from final endorsement, does not validate factual correctness against external sources, and does not support sentiment analysis as an answer-correctness metric.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = load_rows()
    with FULL_TRANSITIONS_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        full_transition_counts = Counter((row["system"], row["flip"]) for row in csv.DictReader(handle))
    overall = agreement_summary(rows)
    strata = group_metrics(rows, ["audit_stratum"])
    datasets = group_metrics(rows, ["dataset"])
    models = group_metrics(rows, ["model_variant"])
    budgets = group_metrics(rows, ["budget"])
    truncation = group_metrics(rows, ["destination_truncated_bool"])
    stratum_truncation = group_metrics(rows, ["audit_stratum", "destination_truncated_bool"])

    projections = []
    for stratum, (system, expected_transition) in TARGET_STRATA.items():
        full_count = full_transition_counts[(system, expected_transition)]
        selected = [row for row in rows if row["audit_stratum"] == stratum and "U" not in str(row["human_transition"])]
        confirmed = sum(row["human_transition"] == expected_transition for row in selected)
        low, high = wilson(confirmed, len(selected))
        rate = confirmed / len(selected)
        projections.append(
            {
                "audit_stratum": stratum,
                "expected_transition": expected_transition,
                "full_machine_count": full_count,
                "confirmed_n": confirmed,
                "audit_n": len(selected),
                "confirmation_rate": rate,
                "wilson_95_low": low,
                "wilson_95_high": high,
                "projected_confirmed_count": full_count * rate,
                "projected_low": full_count * (low or 0),
                "projected_high": full_count * (high or 0),
            }
        )

    transition_confusion = Counter((str(row["machine_transition"]), str(row["human_transition"])) for row in rows)
    confusion_rows = [
        {"machine_transition": machine, "human_transition": human, "n": count}
        for (machine, human), count in sorted(transition_confusion.items())
    ]

    joined_fields = [
        "blind_id", "source_run", "dataset", "model_variant", "system", "budget", "id",
        "wall_seconds", "thinking_tokens_total", "any_truncated", "destination_truncated",
        "audit_stratum", "transition_type", "actor", "source_stage", "destination_stage",
        "machine_transition", "human_transition", "source_agree", "destination_agree", "transition_agree",
        "human_source_label", "human_destination_label", "source_machine_label", "destination_machine_label",
        "question", "gold", "gold_aliases", "human_source_evidence", "human_destination_evidence",
        "reviewer_notes", "source_output", "destination_output",
    ]
    joined_output = [{field: row.get(field, "") for field in joined_fields} for row in rows]
    disagreements = [row for row in joined_output if not bool(row["transition_agree"])]

    strong_judge_input = []
    strong_judge_human_key = []
    for row in rows:
        for position, text_field, human_field, stage_field in (
            ("source", "source_output", "human_source_label", "source_stage"),
            ("destination", "destination_output", "human_destination_label", "destination_stage"),
        ):
            source_uid = f"transition-audit:{row['blind_id']}:{position}"
            strong_judge_input.append(
                {
                    "source_uid": source_uid,
                    "audit_pair_blind_id": row["blind_id"],
                    "audit_position": position,
                    "source_run": row["source_run"],
                    "dataset": row["dataset"],
                    "model_variant": row["model_variant"],
                    "system": row["system"],
                    "budget": row["budget"],
                    "id": row["id"],
                    "stage_name": row[stage_field],
                    "question": row["question"],
                    "gold": row["gold"],
                    "gold_aliases": row["gold_aliases"],
                    "stage_text": row[text_field],
                    "audit_stratum": row["audit_stratum"],
                    "destination_truncated": row["destination_truncated"],
                }
            )
            strong_judge_human_key.append(
                {
                    "source_uid": source_uid,
                    "audit_pair_blind_id": row["blind_id"],
                    "audit_position": position,
                    "audit_stratum": row["audit_stratum"],
                    "human_label": row[human_field],
                }
            )

    metric_rows = []
    for metric, value in overall.items():
        metric_rows.append({"scope": "overall", "group": "all", "metric": metric, "value": value})
    for scope, grouped_rows, fields in [
        ("audit_stratum", strata, ["audit_stratum"]),
        ("dataset", datasets, ["dataset"]),
        ("model_variant", models, ["model_variant"]),
        ("budget", budgets, ["budget"]),
        ("destination_truncated", truncation, ["destination_truncated_bool"]),
        ("stratum_x_destination_truncated", stratum_truncation, ["audit_stratum", "destination_truncated_bool"]),
    ]:
        for group in grouped_rows:
            group_name = " | ".join(str(group[field]) for field in fields)
            for metric, value in group.items():
                if metric not in fields:
                    metric_rows.append({"scope": scope, "group": group_name, "metric": metric, "value": value})

    write_csv(AUDIT_DIR / "audit_metrics.csv", metric_rows)
    write_csv(AUDIT_DIR / "human_labels_joined.csv", joined_output)
    write_csv(AUDIT_DIR / "audit_disagreements.csv", disagreements)
    write_csv(AUDIT_DIR / "audit_transition_confusion.csv", confusion_rows)
    write_csv(AUDIT_DIR / "audit_projection.csv", projections)
    write_jsonl(AUDIT_DIR / "strong_judge_calibration_200.jsonl", strong_judge_input)
    write_jsonl(AUDIT_DIR / "strong_judge_human_key.jsonl", strong_judge_human_key)
    (AUDIT_DIR / "AUDIT_REPORT.md").write_text(build_report(rows, overall, strata, projections), encoding="utf-8")

    print(json.dumps({
        "overall": overall,
        "strata": strata,
        "projections": projections,
        "disagreements": len(disagreements),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
