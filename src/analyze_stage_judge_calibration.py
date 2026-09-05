"""Compare the stage judge and lexical rules against blind human labels."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

from .analyze_judge_calibration import BINARY_LABELS, binary_metrics, fmt, normalize_label


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_human(path: Path) -> dict[str, str | None]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row.get("blind_id", "")).strip(): normalize_label(row.get("human_label")) for row in rows}


def labels(rows: list[dict], evaluator: str) -> list[str | None]:
    if evaluator == "Mistral-24B-stage":
        return [normalize_label(row.get("judge_label")) for row in rows]
    field = "lexical_contain" if evaluator == "lexical-contain" else "normalized_em"
    return ["correct" if row.get(field) is True else "incorrect" for row in rows]


def metric_lines(rows: list[dict], human: list[str | None]) -> tuple[list[str], dict]:
    lines = [
        "| evaluator | decided/eligible | coverage | accuracy (95% CI) | precision | recall | F1 | specificity | kappa |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    results = {}
    for name in ["Mistral-24B-stage", "lexical-contain", "normalized-EM"]:
        result = binary_metrics(human, labels(rows, name))
        results[name] = result
        ci = f"{fmt(result['accuracy'])} [{fmt(result['accuracy_lo'])}, {fmt(result['accuracy_hi'])}]"
        lines.append(f"| {name} | {result['decided']}/{result['eligible']} | {fmt(result['coverage'])} | {ci} | {fmt(result['precision'])} | {fmt(result['recall'])} | {fmt(result['f1'])} | {fmt(result['specificity'])} | {fmt(result['kappa'])} |")
    return lines, results


def subgroup(rows: list[dict], human: list[str | None], field: str) -> list[str]:
    machine = labels(rows, "Mistral-24B-stage")
    lines = [f"| {field} | n human-binary | accuracy | false positive | false negative |", "|---|---:|---:|---:|---:|"]
    for value in sorted({str(row.get(field, "unknown")) for row in rows}):
        idx = [i for i, row in enumerate(rows) if str(row.get(field, "unknown")) == value]
        result = binary_metrics([human[i] for i in idx], [machine[i] for i in idx])
        lines.append(f"| {value} | {result['eligible']} | {fmt(result['accuracy'])} | {result['fp']} | {result['fn']} |")
    return lines


def write_queue(path: Path, rows: list[dict], human: list[str | None]) -> None:
    fields = ["blind_id","human_label","mistral_label","lexical_contain","normalized_em","selection_stratum","dataset","model_variant","system","budget","stage_name","stage_truncated","question","gold","stage_text","judge_reason_code","judge_extracted_answer"]
    machine = labels(rows, "Mistral-24B-stage")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for i, row in enumerate(rows):
            if human[i] not in BINARY_LABELS or machine[i] not in BINARY_LABELS or human[i] != machine[i]:
                writer.writerow({
                    "blind_id":row["blind_id"],"human_label":human[i] or "","mistral_label":machine[i] or "",
                    "lexical_contain":row.get("lexical_contain"),"normalized_em":row.get("normalized_em"),
                    "selection_stratum":row.get("selection_stratum"),"dataset":row.get("dataset"),"model_variant":row.get("model_variant"),
                    "system":row.get("system"),"budget":row.get("budget"),"stage_name":row.get("stage_name"),"stage_truncated":row.get("stage_truncated"),
                    "question":row.get("question"),"gold":row.get("gold"),"stage_text":row.get("stage_text"),
                    "judge_reason_code":row.get("judge_reason_code"),"judge_extracted_answer":row.get("judge_extracted_answer"),
                })


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--judged",type=Path,default=Path("analysis/stage_judge_calibration/stage_calibration_200.mistral.jsonl"))
    parser.add_argument("--human-csv",type=Path,default=Path("analysis/stage_judge_calibration/human_stage_labels.csv"))
    parser.add_argument("--report",type=Path,default=Path("analysis/stage_judge_calibration/STAGE_CALIBRATION_REPORT.md"))
    parser.add_argument("--review-queue",type=Path,default=Path("analysis/stage_judge_calibration/stage_adjudication_queue.csv"))
    parser.add_argument("--force",action="store_true")
    args=parser.parse_args()
    for output in [args.report,args.review_queue]:
        if output.exists() and not args.force: parser.error(f"refusing to overwrite {output}; pass --force")
    rows=read_jsonl(args.judged); human_by=load_human(args.human_csv)
    missing=[r["blind_id"] for r in rows if r["blind_id"] not in human_by]
    if missing: parser.error(f"human CSV missing {len(missing)} blind IDs")
    human=[human_by[r["blind_id"]] for r in rows]
    n_binary=sum(v in BINARY_LABELS for v in human)
    if not n_binary: parser.error("no binary human labels; complete the blind workbook and export CSV")
    table,metrics=metric_lines(rows,human)
    report=["# Intermediate-Stage Judge Calibration","",f"- Sampled stage outputs: {len(rows)}",f"- Human binary labels: {n_binary}",f"- Human label counts: `{dict(Counter(v or 'blank_or_invalid' for v in human))}`",f"- Mistral label counts: `{dict(Counter(labels(rows,'Mistral-24B-stage')))}`","","## Agreement with blind human labels","",*table,"","## Mistral audit by selection stratum","",*subgroup(rows,human,"selection_stratum"),"","## Mistral audit by stage truncation","",*subgroup(rows,human,"stage_truncated"),"","## Mistral audit by system","",*subgroup(rows,human,"system"),"","## Promotion rule","","Promote the stage judge only if aggregate agreement is acceptable and false-positive/false-negative asymmetry is not concentrated in transition or truncation strata. A final-answer judge calibration does not satisfy this requirement.",""]
    args.report.parent.mkdir(parents=True,exist_ok=True); args.report.write_text("\n".join(report),encoding="utf-8")
    write_queue(args.review_queue,rows,human)
    print(f"written: {args.report}"); print(f"written: {args.review_queue}")


if __name__ == "__main__":
    main()
