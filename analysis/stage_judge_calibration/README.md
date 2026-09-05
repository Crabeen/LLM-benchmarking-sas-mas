# Intermediate-stage judge calibration

This directory contains the deterministic 200-stage calibration sample used to
validate semantic judging of intermediate SAS/MAS traces.

## Files

- `stage_calibration_200.jsonl`: unblinded machine-readable sample with source,
  transition, truncation, lexical and timing metadata.
- `stage_calibration_summary.json`: sampling balance and quota audit.
- Human labels are entered in
  `outputs/stage-judge-calibration/intermediate_stage_human_labels.xlsx`.

## Required order

1. Complete all 200 labels in the workbook's `Blind Review` sheet without
   inspecting this directory's unblinded JSONL.
2. Export the workbook's `CSV Export` sheet as UTF-8 CSV to
   `analysis/stage_judge_calibration/human_stage_labels.csv`.
3. On the HPC, run:

   ```bash
   sbatch scripts/mistral_stage_judge_calibration.sbatch
   ```

   The current script writes a dual-label file named
   `stage_calibration_200.mistral_dual_v4.jsonl`. Each row contains both semantic
   discovery and final endorsement labels.

4. After copying the Mistral output back, calibrate semantic discovery with:

   ```bash
   python -m src.analyze_stage_discovery_calibration
   ```

   The default analysis applies the provisional decisions in
   `discovery_adjudication_overrides.json`. These overrides must be confirmed
   by the human researcher before they replace blind human gold labels.

Do not run full semantic trace rejudging until
`STAGE_DISCOVERY_CALIBRATION_REPORT.md` has been inspected for aggregate
agreement and subgroup asymmetry, especially transition types and truncated
versus non-truncated stages. Final endorsement is a separate construct and
requires its own human-confirmed calibration labels.
