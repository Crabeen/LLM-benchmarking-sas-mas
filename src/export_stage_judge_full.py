"""Export every intermediate MAS stage used by the semantic diagnosis."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .rejudge_external import atomic_write_jsonl
from .rejudge_stages_external import row_identity
from .sample_stage_judge_calibration import RUNS, candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, default=Path("results"))
    parser.add_argument(
        "--diagnostics-root", type=Path, default=Path("analysis/diagnostics")
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("analysis/stage_judge_full/all_stages.jsonl"),
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    manifest_path = args.manifest or args.output.with_name("all_stages.manifest.json")
    existing = [path for path in (args.output, manifest_path) if path.exists()]
    if existing and not args.force:
        parser.error(
            "refusing to overwrite existing files: "
            + ", ".join(str(path) for path in existing)
        )

    rows = candidates(args.results_root, args.diagnostics_root)
    rows.sort(
        key=lambda row: (
            row["source_run"], row["system"], int(row["budget"]),
            str(row["id"]), int(row["stage_index"]),
        )
    )
    identities = [row_identity(row) for row in rows]
    if len(identities) != len(set(identities)):
        raise SystemExit("full-stage export contains duplicate source_uid values")
    actual_runs = {row["source_run"] for row in rows}
    missing_runs = set(RUNS) - actual_runs
    if missing_runs:
        raise SystemExit(f"full-stage export is missing runs: {sorted(missing_runs)}")

    atomic_write_jsonl(rows, args.output)
    manifest = {
        "row_count": len(rows),
        "unique_identity_count": len(set(identities)),
        "runs": dict(sorted(Counter(row["source_run"] for row in rows).items())),
        "datasets": dict(sorted(Counter(row["dataset"] for row in rows).items())),
        "model_variants": dict(
            sorted(Counter(row["model_variant"] for row in rows).items())
        ),
        "systems": dict(sorted(Counter(row["system"] for row in rows).items())),
        "budgets": dict(
            sorted(Counter(str(row["budget"]) for row in rows).items())
        ),
        "stage_truncated": dict(
            sorted(Counter(str(bool(row["stage_truncated"])).lower() for row in rows).items())
        ),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"written: {args.output}")
    print(f"written: {manifest_path}")


if __name__ == "__main__":
    main()
