# Cloud dissertation revision package

Prepared on 2026-09-05 for the cloud `Thesis` workspace.

`CLOUD_REVISION_CHECKSUMS.sha256` records SHA-256 hashes for the largest and
most claim-critical artifacts.

## Start here

1. Read `CLOUD_HANDOFF.md` for the dissertation status and agreed scope.
2. Build `dissertation/latex/main.tex` and inspect the PDF page by page.
3. Use only the evidence listed below when revising quantitative claims.
4. Keep a completion checklist mapped to the supervisor's comments.

## Included evidence

### Dissertation source

- `dissertation/latex/`: complete current LaTeX project, including bibliography,
  generated figures, the University logo, appendices, and build/quality scripts.
- `dissertation/DISSERTATION_CURRENT_DRAFT.md`: the prose source from which the
  LaTeX version was developed.
- `output/pdf/DISSERTATION_FINAL_ENGLISH.pdf`: the current compiled baseline for
  page-by-page comparison; rebuild it after revisions.

### Breadth results and real prediction records

- `analysis/semantic_diagnostics/*.csv`: machine-screened breadth tables used by
  the current figures and results chapters.
- `analysis/diagnostics/*/metrics.csv` and `debate_transitions.csv`: run-level
  diagnostic outputs for the frozen and v3b evaluations.
- `analysis/diagnostics/frozen_all_mas_token/samples/`: three small, real trace
  samples covering an SAS discovery drop, a Debate aggregation failure, and a
  Sequential aggregator loss.
- `src/analyze_semantic_failures.py`, `src/diagnose_traces.py`, and related
  analysis/export/checking scripts: code used to derive and check the result
  tables.

### Frozen Mistral screening materials

- `analysis/cloud_revision_package/FROZEN_MISTRAL_SCREENING_PROMPT.md`: a
  readable frozen copy of the v4 prompt and inference settings.
- `src/rejudge_stages_external.py`: authoritative executable prompt source;
  prompt version `stage_discovery_and_endorsement_v4_indexed_evidence`, with
  temperature 0.
- `analysis/stage_judge_full/all_stages.mistral_dual_v4.jsonl`: full
  intermediate-stage screening output.
- `analysis/stage_judge_full/finals_mistral_discovery_v4.jsonl`: final-stage
  screening output.
- Adjacent manifest and check JSON files preserve counts and integrity checks.
- `analysis/stage_judge_calibration/`: compact calibration input, v4 machine
  output, human labels, adjudication notes, and summary reports.

Mistral labels are screening and sampling evidence, not ground truth for the
primary human-transition claims.

### Human audit

- `analysis/final_transition_endorsement_audit/CODEBOOK_REV4.md`: final label
  definitions and decision rules.
- `analysis/final_transition_endorsement_audit/blind_stage_review_400.csv` and
  `rounds/`: completed blind labels, including the hidden-repeat design.
- `analysis/final_transition_endorsement_audit/final_transition_audit_key.jsonl`:
  frozen key linking blind records to items, roles, architectures, and sampling
  strata.
- `analysis/final_transition_endorsement_audit/unblind/`: the 160-item table,
  420-stage table, agreement statistics, weighted transition estimates, and
  analysis summary.
- `src/sample_final_transition_endorsement_audit.py` and
  `src/structure_final_transition_audit_rounds.py`: sampling and blinding code.
- `src/score_transition_judge_candidate.py` and
  `src/analyze_transition_sensitivity_audit.py`: judge-comparison and earlier
  transition-audit statistical code.

Reproducibility caveat: the final 160-item output tables are present, but the
local workspace did not contain a standalone script named for the final
endorsement-audit unblinding/weighted summary. Do not describe the earlier
100-pair sensitivity script as though it generated the final 160-item tables.
This missing standalone derivation script should be reported as a packaging
gap unless reconstructed and verified against every committed output.

### v3b construction and training

- `data/sft_train_v3.jsonl` and its `.stats.json`: constructed v3 training set
  and frozen construction statistics.
- `src/build_sft_data_v3.py`, `src/train_lora_v3.py`, and
  `src/merge_lora_v3.py`: data construction, LoRA training, and model merge.
- `configs/*v3b*`, `configs/v3b_mas_split/`, and
  `configs/v3b_mas_split_full/`: v3b evaluation configurations.
- `scripts/sft_v3.sbatch` and `docs/FINETUNE_V3*.md`: training command/config
  and experiment notes.

Model checkpoints and adapters are deliberately excluded.

## Evidence boundaries for revision

- The breadth screen covers five MAS architectures, 8,000 item-configurations,
  and 26,873 intermediate stages. Treat these machine labels as screening
  evidence only.
- The confirmatory human audit contains 160 unique Debate/Sequential items,
  400 non-repeat stage records, and 20 hidden repeats (420 stage records total).
- The primary final-boundary outcomes must come from human Discovery and
  Endorsement labels; machine strata are for sampling and population weighting.
- The human audit does not provide an SAS-equivalent final coordination
  boundary. A second model family and an SAS-equivalent human audit remain
  explicit experiment gaps and must not be presented as completed.

## Deliberately excluded

- the 524 MB whole-workspace snapshot;
- model checkpoints, LoRA adapters, virtual environments, caches, and logs;
- full raw benchmark result directories not needed for the present evidence;
- audio recordings and transcription environments.
