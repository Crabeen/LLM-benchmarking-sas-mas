# Cloud Revision Completion Checklist — 2026-09-05

Authority for this pass: `Crabeen/sas-mas-repro` commit
`a73783bbe2f97e5e7b5a0bd253ea8f55a3578152`, especially
`CLOUD_REVISION_PACKAGE.md` and `CLOUD_HANDOFF.md`, read through the authenticated
GitHub connector.

## Completed in this revision pass

| Supervisor / handoff request | Status | Dissertation or repository location |
|---|---|---|
| Define SAS and MAS operationally rather than rhetorically | Complete | `dissertation/latex/chapters/01_introduction.tex` |
| Name the five evaluated MAS architectures and explain Ensemble | Complete | `dissertation/latex/chapters/01_introduction.tex`; `02_related_work.tex` |
| Add an architecture comparison table | Complete | `dissertation/latex/chapters/02_related_work.tex` |
| Show the same question instantiated across all six architectures | Complete | `dissertation/latex/figures/architecture_example.pdf`; `02_related_work.tex` |
| Distinguish multi-hop questions from multi-step computational pipelines | Complete | `dissertation/latex/chapters/02_related_work.tex` |
| Separate deterministic benchmark evidence, machine screening, and human audit | Complete | `dissertation/latex/figures/analysis_pipeline.pdf`; `03_framework.tex`; Chapters 6–8 |
| Define exact match and token F1 and provide concrete examples | Complete | `dissertation/latex/chapters/05_evaluation_methodology.tex` |
| Explain the distinct roles of containment, LLM judging, and human audit | Complete | `dissertation/latex/chapters/05_evaluation_methodology.tex` |
| Freeze and disclose the Mistral screening prompt and settings | Complete | `analysis/cloud_revision_package/FROZEN_MISTRAL_SCREENING_PROMPT.md`; `dissertation/latex/appendices/screening_materials.tex` |
| Include one complete machine-judge output example | Complete | `dissertation/latex/appendices/screening_materials.tex` |
| Report v3b data preparation, objective, retained/discarded counts, and fine-tuning hyperparameters | Complete | `dissertation/latex/chapters/04_experimental_design.tex`; `appendices/reproducibility.tex` |
| Report first-error architecture counts as rates with denominators | Complete | `dissertation/latex/chapters/07_machine_screening_results.tex` |
| Present all 15 human-audit fields in readable groups | Complete | `dissertation/latex/chapters/08_human_audit_results.tex` |
| Restore missing truncation metadata without converting unknown values to false | Complete | `src/repair_final_audit_truncation_metadata.py`; `analysis/final_transition_endorsement_audit/unblind/item_level_unblinded_160.csv` |
| Clarify the 160 distinct item-configurations, 400 non-repeat stages, and 20 hidden repeats | Complete | Abstract; Chapters 1, 4, 5, and 8; audit-codebook appendix |
| Update date, word count, build, and visually inspect the final PDF | Complete | `dissertation/latex/main.tex`; `dissertation/latex/README.md`; `output/pdf/DISSERTATION_FINAL_ENGLISH.pdf` |

## Evidence-dependent work deliberately left open

| Requested extension | Why it remains open |
|---|---|
| Apply the frozen Mistral process-screening pipeline to SAS and compare SAS with MAS process behavior | No stored SAS-equivalent process-screening output exists in the handoff package; this requires a new authenticated model run. |
| Compare SAS and MAS using matched human process annotations | The current human audit covers selected MAS traces only; no matched SAS human audit exists. |
| Replicate process-screening findings with a second model family | This requires new inference and new evidence; no second-family output was supplied. |
| Add a second annotator or extend human audit coverage to the remaining MAS architectures | This requires new annotation rather than editorial revision. |
| Reconstruct the final 160-item unblinding and weighted-summary pipeline as one standalone script | The final derived artifacts are present, but the older 100-pair script is not claimed as their generator; provenance reconstruction remains packaging work. |

## Integrity constraints applied

- Deterministic benchmark metrics, machine-screening labels, and human-audit labels are kept as separate evidence layers.
- Human transition rates are reported only for the audited Debate and Sequential final-boundary samples; they are not used to claim that SAS is superior.
- The repaired `final_truncated` field remains unknown (`NA`) for all 160 audited items because the frozen key contains no final truncation values.
- No quantitative claim was changed without a stored artifact or a transparent derivation from stored data.
