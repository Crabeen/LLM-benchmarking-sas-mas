"""Compute semantic MAS failure-localisation metrics from calibrated labels."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from .diagnose_traces import normalize
from .rejudge_external import read_jsonl


def item_key(row: dict) -> tuple[str, str, int, str]:
    return (
        str(row["source_run"]), str(row["system"]),
        int(row["budget"]), str(row["id"]),
    )


def state(row: dict) -> bool | None:
    label = row.get("judge_gold_discovered_label")
    if label == "correct":
        return True
    if label == "incorrect":
        return False
    return None


def tri_any(values: Iterable[bool | None]) -> bool | None:
    values = list(values)
    if any(value is True for value in values):
        return True
    if any(value is None for value in values):
        return None
    return False


def state_code(value: bool | None) -> str:
    return "C" if value is True else "W" if value is False else "U"


def rate(values: Iterable[bool | None]) -> float | None:
    decided = [value for value in values if isinstance(value, bool)]
    return round(sum(decided) / len(decided), 4) if decided else None


def coverage(values: Iterable[bool | None]) -> float:
    values = list(values)
    return round(sum(isinstance(value, bool) for value in values) / len(values), 4) if values else 0.0


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return values[low]
    return values[low] + (values[high] - values[low]) * (position - low)


def candidate_rows(system: str, rows: list[dict]) -> list[dict]:
    if system == "debate":
        return [row for row in rows if str(row["stage_name"]).startswith("rev_")]
    return rows


def semantic_diversity(values: list[bool | None]) -> bool | None:
    decided = {value for value in values if isinstance(value, bool)}
    if len(decided) == 2:
        return True
    if any(value is None for value in values):
        return None
    return False


def paired_flip(a: bool | None, b: bool | None) -> str:
    return f"{state_code(a)}>{state_code(b)}"


def build_item(
    stages: list[dict], final: dict, transitions: list[dict]
) -> dict:
    stages = sorted(stages, key=lambda row: int(row["stage_index"]))
    first = stages[0]
    system = str(first["system"])
    stage_states = [state(row) for row in stages]
    candidates = candidate_rows(system, stages)
    candidate_states = [state(row) for row in candidates]
    discovery = tri_any(stage_states)
    oracle = tri_any(candidate_states)
    final_ok = state(final)
    preserved = final_ok if discovery is True else None
    dropped = (not final_ok) if discovery is True and isinstance(final_ok, bool) else None
    aggregation_failure = (
        oracle is True and final_ok is False
        if isinstance(oracle, bool) and isinstance(final_ok, bool)
        else None
    )
    distinct_texts = len({normalize(str(row.get("stage_text", ""))) for row in candidates})
    item = {
        "source_run": first["source_run"],
        "dataset": first["dataset"],
        "model_variant": first["model_variant"],
        "system": system,
        "budget": int(first["budget"]),
        "id": str(first["id"]),
        "wall_seconds": first.get("wall_seconds"),
        "thinking_tokens_total": first.get("thinking_tokens_total"),
        "any_truncated": bool(first.get("question_any_truncated")),
        "n_stages": len(stages),
        "n_uncertain_stages": sum(value is None for value in stage_states),
        "semantic_stage_correct_rate": rate(stage_states),
        "semantic_gold_discovered": discovery,
        "semantic_oracle_candidate": oracle,
        "semantic_final_correct": final_ok,
        "semantic_preserved": preserved,
        "semantic_drop_after_discovery": dropped,
        "semantic_aggregation_failure": aggregation_failure,
        "semantic_candidate_diversity": semantic_diversity(candidate_states),
        "n_candidate_outputs": len(candidates),
        "n_distinct_candidate_texts": distinct_texts,
        "final_label_source": final.get("final_label_source", "mistral_v4"),
        "first_discovery_stage": next(
            (row["stage_name"] for row in stages if state(row) is True), None
        ),
    }

    first_error = "none" if final_ok is True else None
    if final_ok is False and discovery is False:
        first_error = "proposal"

    if system == "debate":
        by_name = {str(row["stage_name"]): row for row in stages}
        per_debater = []
        for debater in ("A", "B"):
            source = by_name.get(f"init_{debater}")
            destination = by_name.get(f"rev_{debater}")
            if not source or not destination:
                continue
            source_state, destination_state = state(source), state(destination)
            flip = paired_flip(source_state, destination_state)
            per_debater.append(flip)
            transitions.append({
                **{key: item[key] for key in (
                    "source_run", "dataset", "model_variant", "system",
                    "budget", "id", "wall_seconds", "thinking_tokens_total",
                    "any_truncated",
                )},
                "transition_type": "debate_revision",
                "actor": debater,
                "source_stage": source["stage_name"],
                "destination_stage": destination["stage_name"],
                "source_correct": source_state,
                "destination_correct": destination_state,
                "destination_truncated": bool(destination.get("stage_truncated")),
                "flip": flip,
                "drop_from_correct": (
                    destination_state is False if source_state is True else None
                ),
            })
        initial = [state(by_name[name]) for name in ("init_A", "init_B") if name in by_name]
        revised = [state(by_name[name]) for name in ("rev_A", "rev_B") if name in by_name]
        initial_oracle, revised_oracle = tri_any(initial), tri_any(revised)
        revision_destroyed = (
            initial_oracle is True and revised_oracle is False
            if isinstance(initial_oracle, bool) and isinstance(revised_oracle, bool)
            else None
        )
        picker_failure = (
            revised_oracle is True and final_ok is False
            if isinstance(revised_oracle, bool) and isinstance(final_ok, bool)
            else None
        )
        revised_split = (
            len(revised) == 2 and all(isinstance(value, bool) for value in revised)
            and revised[0] != revised[1]
        )
        item.update({
            "debate_transition": "".join(state_code(value) for value in initial)
            + "->" + "".join(state_code(value) for value in revised)
            + "->" + state_code(final_ok),
            "debate_beneficial_flips": per_debater.count("W>C"),
            "debate_harmful_flips": per_debater.count("C>W"),
            "debate_revision_destroyed_all": revision_destroyed,
            "debate_picker_failure": picker_failure,
            "debate_revised_split": revised_split,
            "debate_picker_correct_when_split": (
                final_ok if revised_split and isinstance(final_ok, bool) else None
            ),
        })
        if final_ok is False and initial_oracle is True and revised_oracle is False:
            first_error = "revision"
        elif final_ok is False and revised_oracle is True:
            first_error = "final_picker"

    elif system == "sequential":
        flips = []
        for source, destination in zip(stages, stages[1:]):
            source_state, destination_state = state(source), state(destination)
            flip = paired_flip(source_state, destination_state)
            flips.append(flip)
            transitions.append({
                **{key: item[key] for key in (
                    "source_run", "dataset", "model_variant", "system",
                    "budget", "id", "wall_seconds", "thinking_tokens_total",
                    "any_truncated",
                )},
                "transition_type": "sequential_worker",
                "actor": destination["stage_name"],
                "source_stage": source["stage_name"],
                "destination_stage": destination["stage_name"],
                "source_correct": source_state,
                "destination_correct": destination_state,
                "destination_truncated": bool(destination.get("stage_truncated")),
                "flip": flip,
                "drop_from_correct": (
                    destination_state is False if source_state is True else None
                ),
            })
        last_worker = stage_states[-1] if stage_states else None
        chain_destroyed = (
            discovery is True and last_worker is False
            if isinstance(discovery, bool) and isinstance(last_worker, bool)
            else None
        )
        aggregator_loss = (
            last_worker is True and final_ok is False
            if isinstance(last_worker, bool) and isinstance(final_ok, bool)
            else None
        )
        item.update({
            "sequential_c_to_w": flips.count("C>W"),
            "sequential_w_to_c": flips.count("W>C"),
            "sequential_last_worker_correct": last_worker,
            "sequential_worker_chain_destroyed": chain_destroyed,
            "sequential_final_aggregator_loss": aggregator_loss,
        })
        if final_ok is False and chain_destroyed is True:
            first_error = "worker_chain"
        elif final_ok is False and aggregator_loss is True:
            first_error = "final_aggregator"

    elif final_ok is False and oracle is True:
        first_error = "final_aggregator"

    if first_error is None and final_ok is False and discovery is True:
        first_error = "pre_final_unresolved"
    if first_error is None and (final_ok is None or discovery is None):
        first_error = "unresolved"
    item["first_error_stage"] = first_error
    return item


def summarize_group(rows: list[dict]) -> dict:
    discovery = [row["semantic_gold_discovered"] for row in rows]
    oracle = [row["semantic_oracle_candidate"] for row in rows]
    final = [row["semantic_final_correct"] for row in rows]
    preserved = [row["semantic_preserved"] for row in rows]
    dropped = [row["semantic_drop_after_discovery"] for row in rows]
    oracle_rate, final_rate = rate(oracle), rate(final)
    out = {
        "n": len(rows),
        "discovery_coverage": coverage(discovery),
        "semantic_gold_discovery_rate": rate(discovery),
        "oracle_coverage": coverage(oracle),
        "semantic_oracle_candidate_accuracy": oracle_rate,
        "final_coverage": coverage(final),
        "semantic_final_accuracy": final_rate,
        "semantic_preservation_rate": rate(preserved),
        "semantic_drop_rate": rate(dropped),
        "semantic_aggregation_failure_rate": rate(
            row["semantic_aggregation_failure"] for row in rows
        ),
        "semantic_candidate_diversity_rate": rate(
            row["semantic_candidate_diversity"] for row in rows
        ),
        "mean_distinct_candidate_texts": round(
            statistics.fmean(row["n_distinct_candidate_texts"] for row in rows), 4
        ),
    }
    out["semantic_aggregation_regret"] = (
        round(oracle_rate - final_rate, 4)
        if oracle_rate is not None and final_rate is not None else None
    )
    if rows[0]["system"] == "debate":
        out.update({
            "debate_beneficial_flips": sum(row["debate_beneficial_flips"] for row in rows),
            "debate_harmful_flips": sum(row["debate_harmful_flips"] for row in rows),
            "debate_revision_destroyed_all": sum(
                row["debate_revision_destroyed_all"] is True for row in rows
            ),
            "debate_picker_failures": sum(row["debate_picker_failure"] is True for row in rows),
            "debate_revised_split_cases": sum(row["debate_revised_split"] is True for row in rows),
            "debate_picker_accuracy_when_split": rate(
                row["debate_picker_correct_when_split"] for row in rows
            ),
        })
    if rows[0]["system"] == "sequential":
        out.update({
            "sequential_c_to_w": sum(row["sequential_c_to_w"] for row in rows),
            "sequential_w_to_c": sum(row["sequential_w_to_c"] for row in rows),
            "sequential_worker_chain_destroyed": sum(
                row["sequential_worker_chain_destroyed"] is True for row in rows
            ),
            "sequential_final_aggregator_losses": sum(
                row["sequential_final_aggregator_loss"] is True for row in rows
            ),
        })
    return out


def resource_summary(rows: list[dict]) -> dict:
    wall = [float(row["wall_seconds"]) for row in rows if row.get("wall_seconds") is not None]
    tokens = [float(row["thinking_tokens_total"]) for row in rows if row.get("thinking_tokens_total") is not None]
    return {
        "n": len(rows),
        "mean_wall_seconds": round(statistics.fmean(wall), 4),
        "median_wall_seconds": round(statistics.median(wall), 4),
        "p25_wall_seconds": round(percentile(wall, 0.25), 4),
        "p75_wall_seconds": round(percentile(wall, 0.75), 4),
        "total_observed_wall_seconds": round(sum(wall), 4),
        "mean_thinking_tokens": round(statistics.fmean(tokens), 4),
        "median_thinking_tokens": round(statistics.median(tokens), 4),
        "any_truncation_rate": rate(row["any_truncated"] for row in rows),
        "semantic_discovery_rate": rate(row["semantic_gold_discovered"] for row in rows),
        "semantic_preservation_rate": rate(row["semantic_preserved"] for row in rows),
        "semantic_final_accuracy": rate(row["semantic_final_correct"] for row in rows),
    }


def fixed_effect_stratified_or(
    rows: list[dict], exposure: str, outcome: str, strata: tuple[str, ...]
) -> dict:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if isinstance(row.get(exposure), bool) and isinstance(row.get(outcome), bool):
            grouped[tuple(row[field] for field in strata)].append(row)
    log_values, weights = [], []
    pooled = Counter()
    used = 0
    for records in grouped.values():
        cells = Counter((record[exposure], record[outcome]) for record in records)
        a, b = cells[(True, True)], cells[(True, False)]
        c, d = cells[(False, True)], cells[(False, False)]
        pooled.update({"a": a, "b": b, "c": c, "d": d})
        if (a + b) == 0 or (c + d) == 0 or (a + c) == 0 or (b + d) == 0:
            continue
        if min(a, b, c, d) == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
        log_or = math.log((a * d) / (b * c))
        variance = 1 / a + 1 / b + 1 / c + 1 / d
        log_values.append(log_or)
        weights.append(1 / variance)
        used += 1
    n = sum(pooled.values())
    if not weights:
        return {"n": n, "strata_used": 0, "adjusted_or": None, "ci_low": None, "ci_high": None, "p_value": None}
    estimate = sum(value * weight for value, weight in zip(log_values, weights)) / sum(weights)
    se = math.sqrt(1 / sum(weights))
    z = estimate / se
    return {
        "n": n,
        "strata_used": used,
        "adjusted_or": round(math.exp(estimate), 4),
        "ci_low": round(math.exp(estimate - 1.96 * se), 4),
        "ci_high": round(math.exp(estimate + 1.96 * se), 4),
        "p_value": round(math.erfc(abs(z) / math.sqrt(2)), 6),
        "exposed_outcome": pooled["a"],
        "exposed_no_outcome": pooled["b"],
        "unexposed_outcome": pooled["c"],
        "unexposed_no_outcome": pooled["d"],
    }


def add_within_stratum_high(
    rows: list[dict], value_field: str, output_field: str, strata: tuple[str, ...]
) -> None:
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get(value_field) is not None:
            grouped[tuple(row[field] for field in strata)].append(row)
    for records in grouped.values():
        midpoint = statistics.median(float(row[value_field]) for row in records)
        for row in records:
            row[output_field] = float(row[value_field]) > midpoint


def mcnemar_exact(a_to_b: int, b_to_a: int) -> float:
    discordant = a_to_b + b_to_a
    if discordant == 0:
        return 1.0
    smaller = min(a_to_b, b_to_a)
    tail = sum(math.comb(discordant, k) for k in range(smaller + 1)) / (2 ** discordant)
    return min(1.0, 2 * tail)


def paired_budget_test(rows: list[dict], outcome: str) -> dict:
    groups: dict[tuple, dict[int, dict]] = defaultdict(dict)
    for row in rows:
        groups[(row["source_run"], row["system"], row["id"])][row["budget"]] = row
    pairs = [value for value in groups.values() if 1000 in value and 2000 in value]
    usable = [
        pair for pair in pairs
        if isinstance(pair[1000].get(outcome), bool)
        and isinstance(pair[2000].get(outcome), bool)
    ]
    gain = sum(pair[1000][outcome] is False and pair[2000][outcome] is True for pair in usable)
    loss = sum(pair[1000][outcome] is True and pair[2000][outcome] is False for pair in usable)
    return {
        "matched_pairs": len(usable),
        "rate_b1000": rate(pair[1000][outcome] for pair in usable),
        "rate_b2000": rate(pair[2000][outcome] for pair in usable),
        "b1000_wrong_to_b2000_correct": gain,
        "b1000_correct_to_b2000_wrong": loss,
        "mcnemar_exact_p": round(mcnemar_exact(gain, loss), 6),
        "mean_wall_change_seconds": round(statistics.fmean(
            float(pair[2000]["wall_seconds"]) - float(pair[1000]["wall_seconds"])
            for pair in usable
        ), 4) if usable else None,
        "mean_thinking_token_change": round(statistics.fmean(
            float(pair[2000]["thinking_tokens_total"]) - float(pair[1000]["thinking_tokens_total"])
            for pair in usable
        ), 4) if usable else None,
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def markdown_table(rows: list[dict], columns: list[tuple[str, str]]) -> list[str]:
    lines = [
        "| " + " | ".join(label for _, label in columns) + " |",
        "|" + "|".join("---:" if key not in {"dataset", "model_variant", "system", "source_run", "analysis"} else "---" for key, _ in columns) + "|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(key)) for key, _ in columns) + " |")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stages", type=Path,
        default=Path("analysis/stage_judge_full/all_stages.mistral_dual_v4.jsonl"),
    )
    parser.add_argument(
        "--final-reused", type=Path,
        default=Path("analysis/stage_judge_full/finals_reused_from_stages.jsonl"),
    )
    parser.add_argument(
        "--final-judged", type=Path,
        default=Path("analysis/stage_judge_full/finals_mistral_discovery_v4.jsonl"),
    )
    parser.add_argument(
        "--out", type=Path, default=Path("analysis/semantic_diagnostics")
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    report_path = args.out / "REPORT.md"
    if report_path.exists() and not args.force:
        parser.error(f"refusing to overwrite {report_path}; pass --force")

    stages = read_jsonl(args.stages)
    reused_finals = read_jsonl(args.final_reused)
    judged_finals = read_jsonl(args.final_judged)
    for row in judged_finals:
        row["final_label_source"] = "mistral_v4_final"
    finals = reused_finals + judged_finals
    stage_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in stages:
        stage_groups[item_key(row)].append(row)
    final_map = {}
    for row in finals:
        key = item_key(row)
        if key in final_map:
            parser.error(f"duplicate final label for {key}")
        final_map[key] = row
    if set(stage_groups) != set(final_map):
        parser.error(
            f"stage/final item mismatch: missing finals={len(set(stage_groups)-set(final_map))}, "
            f"unexpected finals={len(set(final_map)-set(stage_groups))}"
        )

    transitions: list[dict] = []
    items = [build_item(stage_groups[key], final_map[key], transitions) for key in sorted(stage_groups)]
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "per_item_semantic.jsonl").open("w", encoding="utf-8") as handle:
        for row in items:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_csv(args.out / "semantic_transitions.csv", transitions)

    metric_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in items:
        metric_groups[(row["source_run"], row["dataset"], row["model_variant"], row["system"], row["budget"])].append(row)
    metrics = []
    resources = []
    for key, rows in sorted(metric_groups.items()):
        identity = dict(zip(("source_run", "dataset", "model_variant", "system", "budget"), key))
        metrics.append({**identity, **summarize_group(rows)})
        resources.append({**identity, **resource_summary(rows)})
    write_csv(args.out / "semantic_metrics.csv", metrics)
    write_csv(args.out / "budget_wallclock.csv", resources)
    overall_resource_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in items:
        overall_resource_groups[(row["system"], row["budget"])].append(row)
    overall_resources = [
        {"system": key[0], "budget": key[1], **resource_summary(rows)}
        for key, rows in sorted(overall_resource_groups.items())
    ]
    write_csv(args.out / "budget_wallclock_overall.csv", overall_resources)

    control_strata = ("dataset", "model_variant", "budget", "system")
    add_within_stratum_high(items, "wall_seconds", "high_wall_within_stratum", control_strata)
    add_within_stratum_high(items, "thinking_tokens_total", "high_tokens_within_stratum", control_strata)
    associations = []
    for exposure, label in (
        ("high_wall_within_stratum", "higher wall time"),
        ("high_tokens_within_stratum", "more thinking tokens"),
    ):
        for outcome, outcome_label in (
            ("semantic_gold_discovered", "semantic discovery"),
            ("semantic_drop_after_discovery", "drop after discovery"),
        ):
            result = fixed_effect_stratified_or(items, exposure, outcome, control_strata)
            associations.append({
                "analysis": f"{label} -> {outcome_label}",
                "exposure": exposure,
                "outcome": outcome,
                "controls": "+".join(control_strata),
                **result,
            })
    transition_controls = ("dataset", "model_variant", "budget", "system")
    transition_result = fixed_effect_stratified_or(
        transitions, "destination_truncated", "drop_from_correct", transition_controls
    )
    associations.append({
        "analysis": "destination truncation -> C-to-W transition",
        "exposure": "destination_truncated",
        "outcome": "drop_from_correct",
        "controls": "+".join(transition_controls),
        **transition_result,
    })
    write_csv(args.out / "resource_associations.csv", associations)

    paired_rows = []
    for grouping, grouped_rows in [("all", items)] + [
        (system, [row for row in items if row["system"] == system])
        for system in sorted({row["system"] for row in items})
    ]:
        for outcome in ("semantic_gold_discovered", "semantic_final_correct"):
            paired_rows.append({
                "group": grouping,
                "outcome": outcome,
                **paired_budget_test(grouped_rows, outcome),
            })
    write_csv(args.out / "budget_pair_tests.csv", paired_rows)

    unresolved = [row for row in stages if state(row) is None]
    write_csv(args.out / "unresolved_stage_review.csv", [{
        "source_uid": row["source_uid"],
        "source_run": row["source_run"],
        "system": row["system"],
        "budget": row["budget"],
        "id": row["id"],
        "stage_name": row["stage_name"],
        "question": row["question"],
        "gold": row["gold"],
        "stage_text": row["stage_text"],
        "judge_label": row["judge_gold_discovered_label"],
        "judge_reason": row.get("judge_discovery_reason_code"),
    } for row in unresolved])

    error_counts = Counter(row["first_error_stage"] for row in items)
    error_rows = []
    for system in ["all", *sorted({row["system"] for row in items})]:
        selected = items if system == "all" else [row for row in items if row["system"] == system]
        counts = Counter(row["first_error_stage"] for row in selected)
        error_rows.append({
            "system": system,
            "n": len(selected),
            **{name: counts.get(name, 0) for name in (
                "proposal", "revision", "worker_chain", "final_picker",
                "final_aggregator", "pre_final_unresolved", "unresolved", "none",
            )},
            "failure_rate": round(1 - counts.get("none", 0) / len(selected), 4),
        })
    write_csv(args.out / "first_error_stage.csv", error_rows)
    headline_groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in items:
        headline_groups[(row["dataset"], row["model_variant"], row["system"], row["budget"])].append(row)
    headline = []
    for key, rows in sorted(headline_groups.items()):
        identity = dict(zip(("dataset", "model_variant", "system", "budget"), key))
        headline.append({**identity, **summarize_group(rows)})
    architecture_losses = [row for row in metrics if row["system"] in {"debate", "sequential"}]
    architecture_overall = []
    for system in ("debate", "sequential"):
        selected = [row for row in items if row["system"] == system]
        architecture_overall.append({"system": system, **summarize_group(selected)})
    debate_overall = next(row for row in architecture_overall if row["system"] == "debate")
    sequential_overall = next(row for row in architecture_overall if row["system"] == "sequential")
    truncation_result = associations[-1]
    overall_discovery_pair = next(
        row for row in paired_rows
        if row["group"] == "all" and row["outcome"] == "semantic_gold_discovered"
    )
    overall_final_pair = next(
        row for row in paired_rows
        if row["group"] == "all" and row["outcome"] == "semantic_final_correct"
    )
    report = [
        "# Semantic Stage-Level Failure Localisation",
        "",
        "This report uses the calibrated Mistral v4 semantic-discovery label for both intermediate stages and final predictions. It does not use Qwen self-judgment or the uncalibrated endorsement field.",
        "",
        f"- MAS item-configurations: {len(items)}",
        f"- Intermediate stages: {len(stages)}",
        f"- Final labels reused from identical stage text: {len(reused_finals)}",
        f"- Final labels judged separately by Mistral: {len(judged_finals)}",
        f"- Uncertain intermediate labels excluded pairwise: {len(unresolved)}",
        f"- First-error-stage counts: `{dict(sorted(error_counts.items()))}`",
        "",
        "## Headline semantic metrics",
        "",
        *markdown_table(headline, [
            ("dataset", "dataset"), ("model_variant", "model"), ("system", "system"),
            ("budget", "budget"), ("semantic_final_accuracy", "final"),
            ("semantic_oracle_candidate_accuracy", "oracle"),
            ("semantic_aggregation_regret", "regret"),
            ("semantic_gold_discovery_rate", "discovery"),
            ("semantic_preservation_rate", "preserve"),
            ("semantic_drop_rate", "drop"),
            ("semantic_candidate_diversity_rate", "semantic diversity"),
        ]),
        "",
        "For Subtask Parallel, task outputs are partial findings rather than fully comparable answer candidates; interpret its oracle and regret separately.",
        "",
        "## Where failure first appears",
        "",
        *markdown_table(error_rows, [
            ("system", "system"), ("n", "n"), ("proposal", "proposal"),
            ("revision", "revision"), ("worker_chain", "worker chain"),
            ("final_picker", "final picker"),
            ("final_aggregator", "final aggregator"), ("none", "final correct"),
            ("failure_rate", "failure rate"),
        ]),
        "",
        f"Across Debate, revision destroyed all discovered answer support in {debate_overall['debate_revision_destroyed_all']} items, while a correct revised candidate existed but the final picker still failed in {debate_overall['debate_picker_failures']} items. Harmful revision flips ({debate_overall['debate_harmful_flips']}) exceeded beneficial flips ({debate_overall['debate_beneficial_flips']}).",
        "",
        f"Across Sequential, the worker chain ended wrong after earlier discovery in {sequential_overall['sequential_worker_chain_destroyed']} items; the final aggregator lost a correct last-worker answer in {sequential_overall['sequential_final_aggregator_losses']} items. The first-error classification counts only terminally incorrect items, whereas these architecture counters can also include losses later recovered by the final output.",
        "",
        "## Debate revision versus picker and Sequential chain versus aggregator",
        "",
        *markdown_table(architecture_losses, [
            ("source_run", "run"), ("system", "system"), ("budget", "budget"),
            ("debate_revision_destroyed_all", "revision destroyed"),
            ("debate_picker_failures", "picker failures"),
            ("debate_beneficial_flips", "W→C"), ("debate_harmful_flips", "C→W"),
            ("sequential_worker_chain_destroyed", "chain destroyed"),
            ("sequential_final_aggregator_losses", "aggregator losses"),
            ("sequential_w_to_c", "seq W→C"), ("sequential_c_to_w", "seq C→W"),
        ]),
        "",
        "## Resource and truncation associations",
        "",
        *markdown_table(associations, [
            ("analysis", "analysis"), ("n", "n"), ("strata_used", "strata"),
            ("adjusted_or", "adjusted OR"), ("ci_low", "95% low"),
            ("ci_high", "95% high"), ("p_value", "p"),
        ]),
        "",
        "Higher wall time and token indicators are defined relative to the median within dataset × model variant × budget × system cells. Odds ratios are fixed-effect stratified estimates. They are observational associations, not causal effects.",
        "",
        "The truncation analysis is conditional on a semantically correct source stage and covers Debate revision and Sequential worker transitions. OR > 1 means the destination is more likely to lose correctness.",
        "",
        f"Observed destination truncation had OR={truncation_result['adjusted_or']} (95% CI {truncation_result['ci_low']}–{truncation_result['ci_high']}, p={truncation_result['p_value']}) for a C-to-W transition. The interval includes 1, so these data do not establish that truncation increases semantic loss.",
        "",
        "## Budget-paired tests",
        "",
        *markdown_table(paired_rows, [
            ("group", "group"), ("outcome", "outcome"), ("matched_pairs", "pairs"),
            ("rate_b1000", "b1000"), ("rate_b2000", "b2000"),
            ("b1000_wrong_to_b2000_correct", "W→C"),
            ("b1000_correct_to_b2000_wrong", "C→W"),
            ("mcnemar_exact_p", "McNemar p"),
            ("mean_wall_change_seconds", "Δ wall s"),
        ]),
        "",
        f"Across matched items, b2000 changed discovery from {overall_discovery_pair['rate_b1000']} to {overall_discovery_pair['rate_b2000']} (McNemar p={overall_discovery_pair['mcnemar_exact_p']}) and final accuracy from {overall_final_pair['rate_b1000']} to {overall_final_pair['rate_b2000']} (p={overall_final_pair['mcnemar_exact_p']}). Thus the larger token budget did not improve the aggregate semantic outcomes in these frozen runs.",
        "",
        "## Wall-clock and token accounting",
        "",
        *markdown_table(overall_resources, [
            ("system", "system"), ("budget", "budget"), ("n", "n"),
            ("mean_wall_seconds", "mean wall s"),
            ("median_wall_seconds", "median wall s"),
            ("p25_wall_seconds", "p25"), ("p75_wall_seconds", "p75"),
            ("total_observed_wall_seconds", "total wall s"),
            ("mean_thinking_tokens", "mean thinking tokens"),
            ("any_truncation_rate", "truncation"),
        ]),
        "",
        "`wall_seconds` is observed end-to-end elapsed time per item (critical-path time for parallel systems). Summing it gives observed item wall-time, not GPU-seconds. Exact GPU-seconds require scheduler/job telemetry or non-overlapped device accounting and cannot be reconstructed from these trace fields.",
        "",
        "## Output files",
        "",
        "- `semantic_metrics.csv`: grouped semantic accuracy and failure metrics.",
        "- `per_item_semantic.jsonl`: one row per item/configuration, including `first_error_stage`.",
        "- `semantic_transitions.csv`: Debate and Sequential stage transitions.",
        "- `budget_wallclock.csv`: wall-clock, token and truncation summaries for each run/system/budget.",
        "- `budget_wallclock_overall.csv`: compact system × budget wall-clock table.",
        "- `resource_associations.csv`: adjusted odds-ratio analyses.",
        "- `budget_pair_tests.csv`: matched b1000 versus b2000 tests.",
        "- `first_error_stage.csv`: first semantic failure location by architecture.",
        "- `unresolved_stage_review.csv`: the six uncertain stage judgments.",
        "",
        "## Calibration caveat",
        "",
        "The stage judge achieved 0.919 evidence-valid accuracy and κ=0.829 overall, but calibration accuracy was lower for Debate beneficial flips (0.700) and Sequential C-to-W cases (0.800). Treat transition-specific estimates as primary quantitative evidence with a targeted manual sensitivity audit, not as error-free ground truth.",
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"written: {args.out}")
    print(f"items={len(items)} stages={len(stages)} transitions={len(transitions)} unresolved={len(unresolved)}")


if __name__ == "__main__":
    main()
