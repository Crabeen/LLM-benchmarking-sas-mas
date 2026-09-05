# Final transition endorsement audit — first unblind report

Generated: 2026-08-21 (Europe/London)  
Codebook: rev.4  
Analysis set: 400 stage rows / 160 items; hidden-repeat QA set: 20 rows. The 20 repeats are excluded from every machine-agreement, transition and population estimate.

## 1. Blind-set integrity

- All four workbooks contained 105/105 Complete rows. All C labels had verbatim evidence inside the corresponding stage output.
- Across all 420 annotated rows: Discovery C/W/U = 240/180/0; Endorsement C/W/U = 225/192/3.
- Discovery=C and Endorsement=W occurred 14/420 (3.3%). Endorsement=C while Discovery!=C occurred 0 times.
- Round 4's static final-check counts were corrected from a wildcard-COUNTIF display defect to the audited values: truncation in background = 2; truncation inside answer-bearing statement = 3. No human label changed.

## 2. Hidden-repeat intra-rater consistency

| Axis | Exact agreement | Cohen's κ | Bootstrap 95% CI |
|---|---:|---:|---:|
| Discovery | 20/20 (100.0%) | 1.000 | [1.000, 1.000] |
| Endorsement | 20/20 (100.0%) | 1.000 | [1.000, 1.000] |

This measures one annotator's internal repeatability, not independent inter-annotator validity.

## 3. Human–Mistral stage-label agreement (400 analysis rows)

| Axis | Exact agreement | Cohen's κ | Bootstrap 95% CI |
|---|---:|---:|---:|
| Discovery | 330/400 (82.5%) | 0.632 | [0.557, 0.705] |
| Endorsement | 322/400 (80.5%) | 0.617 | [0.541, 0.691] |

The workbook reports disagreement directions separately: human C / Mistral W is an over-strict machine decision; human W / Mistral C is an over-broad decision. Breakdowns are provided by architecture, stage position and frozen machine sampling stratum.

## 4. Human transition estimates, weighted by frozen stratum pool size

Primary sensitivity rule: U→W (conservative). The source state is the endorsement oracle over rev_A/rev_B for Debate and the last worker's endorsement for Sequential. The target is the human final endorsement.

| Architecture | Harmful C→W | Approx. 95% CI | Beneficial W→C | Approx. 95% CI |
|---|---:|---:|---:|---:|
| Debate | 5.4% | [3.0%, 7.9%] | 0.0% | [0.0%, 0.0%] |
| Sequential | 0.6% | [0.3%, 0.9%] | 5.8% | [2.3%, 9.4%] |

Weighted harmful-rate contrast (Debate − Sequential): 4.9%; approximate 95% CI [2.4%, 7.3%].

The raw audited item transitions were: Debate C→C 35, C→W 19, W→C 0, W→W 25, U→W 1; Sequential C→C 40, C→W 4, W→C 6, W→W 29, U→W 1. The sole item in the machine-defined Debate W→C census stratum was human C→C, so the machine's apparent beneficial picker event did not survive unblinding.

Using source Discovery rather than source Endorsement, the weighted probability that a discovered answer is not endorsed by the final output is 7.1% for Debate and 4.0% for Sequential. This separates failure to preserve already-present answer content from failure to endorse it before aggregation.

## 5. Sensitivity and reason harmonisation

- All weighted transition tables are repeated under three U rules: U→W, exclude U-bearing items, and U→C. Only three stage rows contain U, all on Endorsement and all caused by answer-bearing truncation.
- Harmful C→W remains higher for Debate in every U sensitivity: Debate 5.4% / 5.5% / 6.6% versus Sequential 0.6% / 0.6% / 2.2% under U→W / exclude U / U→C.
- The derived field `harmonized_reason_rev4` changes reason codes only: FTS-0211 and FTS-0218 → `contentless_option_reference`; FTS-0140 → `wrong_relation`. Human C/W/U labels are unchanged, so agreement and transition estimates are invariant to this harmonisation.
- Confidence intervals use the usual finite-population stratified variance formula. They are approximate because the within-stratum sample was greedily balanced rather than a pure simple-random sample. Treat the weighted point estimates as the primary result and the intervals as descriptive uncertainty, not confirmatory inference.

## 6. Research decision

The unblind step is complete. The next analysis should use these audited human labels to identify which MAS component loses a human-correct source state: Debate revision oracle → picker, and Sequential last worker → final aggregator. Do not substitute Mistral labels for the human labels in this transition analysis; its measured agreement and κ are reported above and its errors are not ignorable.
