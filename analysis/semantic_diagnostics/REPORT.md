# Semantic Stage-Level Failure Localisation

This report uses the calibrated Mistral v4 semantic-discovery label for both intermediate stages and final predictions. It does not use Qwen self-judgment or the uncalibrated endorsement field.

**Reliability update (human sensitivity audit):** a completed blind audit of 100 deliberately difficult Debate/Sequential transition pairs found 73.9% agreement across 199 resolved stage labels (Cohen's kappa 0.478) and 50.5% exact agreement across 99 resolved transitions (multiclass kappa 0.364). Therefore the full-trace transition counts below are machine-labelled screening estimates, not error-free ground truth. See `../semantic_transition_sensitivity/AUDIT_REPORT.md` and `../semantic_transition_sensitivity/audit_disagreements.csv`.

- MAS item-configurations: 8000
- Intermediate stages: 26873
- Final labels reused from identical stage text: 2297
- Final labels judged separately by Mistral: 5703
- Uncertain intermediate labels excluded pairwise: 6
- First-error-stage counts: `{'final_aggregator': 857, 'final_picker': 173, 'none': 5876, 'proposal': 946, 'revision': 73, 'worker_chain': 75}`

## Headline semantic metrics

| dataset | model | system | budget | final | oracle | regret | discovery | preserve | drop | semantic diversity |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2wiki | frozen | debate | 1000 | 0.930 | 0.965 | 0.035 | 0.980 | 0.949 | 0.051 | 0.065 |
| 2wiki | frozen | debate | 2000 | 0.880 | 0.930 | 0.050 | 0.965 | 0.912 | 0.088 | 0.050 |
| 2wiki | frozen | ensemble | 1000 | 0.885 | 0.970 | 0.085 | 0.970 | 0.912 | 0.088 | 0.105 |
| 2wiki | frozen | ensemble | 2000 | 0.855 | 0.955 | 0.100 | 0.955 | 0.895 | 0.105 | 0.075 |
| 2wiki | frozen | parallel_roles | 1000 | 0.890 | 0.990 | 0.100 | 0.990 | 0.899 | 0.101 | 0.145 |
| 2wiki | frozen | parallel_roles | 2000 | 0.890 | 0.980 | 0.090 | 0.980 | 0.908 | 0.092 | 0.140 |
| 2wiki | frozen | sequential | 1000 | 0.865 | 0.805 | -0.060 | 0.805 | 0.950 | 0.050 | 0.380 |
| 2wiki | frozen | sequential | 2000 | 0.825 | 0.810 | -0.015 | 0.810 | 0.901 | 0.099 | 0.410 |
| 2wiki | frozen | subtask_parallel | 1000 | 0.860 | 0.673 | -0.187 | 0.673 | 0.963 | 0.037 | 0.261 |
| 2wiki | frozen | subtask_parallel | 2000 | 0.850 | 0.670 | -0.180 | 0.670 | 0.948 | 0.052 | 0.285 |
| 2wiki | v3b | debate | 1000 | 0.915 | 0.970 | 0.055 | 0.990 | 0.924 | 0.076 | 0.085 |
| 2wiki | v3b | debate | 2000 | 0.890 | 0.950 | 0.060 | 0.965 | 0.922 | 0.078 | 0.055 |
| 2wiki | v3b | ensemble | 1000 | 0.885 | 0.955 | 0.070 | 0.955 | 0.927 | 0.073 | 0.085 |
| 2wiki | v3b | ensemble | 2000 | 0.875 | 0.960 | 0.085 | 0.960 | 0.906 | 0.094 | 0.100 |
| 2wiki | v3b | parallel_roles | 1000 | 0.900 | 0.975 | 0.075 | 0.975 | 0.923 | 0.077 | 0.125 |
| 2wiki | v3b | parallel_roles | 2000 | 0.905 | 0.970 | 0.065 | 0.970 | 0.933 | 0.067 | 0.135 |
| 2wiki | v3b | sequential | 1000 | 0.840 | 0.805 | -0.035 | 0.805 | 0.901 | 0.099 | 0.380 |
| 2wiki | v3b | sequential | 2000 | 0.840 | 0.805 | -0.035 | 0.805 | 0.925 | 0.074 | 0.415 |
| 2wiki | v3b | subtask_parallel | 1000 | 0.830 | 0.663 | -0.167 | 0.663 | 0.947 | 0.053 | 0.286 |
| 2wiki | v3b | subtask_parallel | 2000 | 0.835 | 0.630 | -0.205 | 0.630 | 0.952 | 0.048 | 0.230 |
| musique | frozen | debate | 1000 | 0.720 | 0.845 | 0.125 | 0.930 | 0.774 | 0.226 | 0.230 |
| musique | frozen | debate | 2000 | 0.695 | 0.880 | 0.185 | 0.945 | 0.735 | 0.265 | 0.255 |
| musique | frozen | ensemble | 1000 | 0.660 | 0.960 | 0.300 | 0.960 | 0.688 | 0.312 | 0.400 |
| musique | frozen | ensemble | 2000 | 0.635 | 0.945 | 0.310 | 0.945 | 0.672 | 0.328 | 0.370 |
| musique | frozen | parallel_roles | 1000 | 0.600 | 0.915 | 0.315 | 0.915 | 0.634 | 0.366 | 0.650 |
| musique | frozen | parallel_roles | 2000 | 0.580 | 0.900 | 0.320 | 0.900 | 0.622 | 0.378 | 0.585 |
| musique | frozen | sequential | 1000 | 0.475 | 0.625 | 0.150 | 0.625 | 0.696 | 0.304 | 0.525 |
| musique | frozen | sequential | 2000 | 0.465 | 0.545 | 0.080 | 0.545 | 0.734 | 0.266 | 0.455 |
| musique | frozen | subtask_parallel | 1000 | 0.605 | 0.645 | 0.040 | 0.645 | 0.822 | 0.178 | 0.605 |
| musique | frozen | subtask_parallel | 2000 | 0.595 | 0.620 | 0.025 | 0.620 | 0.863 | 0.137 | 0.575 |
| musique | v3b | debate | 1000 | 0.680 | 0.865 | 0.185 | 0.920 | 0.739 | 0.261 | 0.270 |
| musique | v3b | debate | 2000 | 0.675 | 0.845 | 0.170 | 0.920 | 0.734 | 0.266 | 0.205 |
| musique | v3b | ensemble | 1000 | 0.660 | 0.940 | 0.280 | 0.940 | 0.692 | 0.308 | 0.350 |
| musique | v3b | ensemble | 2000 | 0.635 | 0.970 | 0.335 | 0.970 | 0.655 | 0.345 | 0.385 |
| musique | v3b | parallel_roles | 1000 | 0.580 | 0.925 | 0.345 | 0.925 | 0.622 | 0.378 | 0.685 |
| musique | v3b | parallel_roles | 2000 | 0.590 | 0.915 | 0.325 | 0.915 | 0.645 | 0.355 | 0.600 |
| musique | v3b | sequential | 1000 | 0.480 | 0.565 | 0.085 | 0.565 | 0.770 | 0.230 | 0.485 |
| musique | v3b | sequential | 2000 | 0.485 | 0.525 | 0.040 | 0.525 | 0.771 | 0.229 | 0.465 |
| musique | v3b | subtask_parallel | 1000 | 0.555 | 0.605 | 0.050 | 0.605 | 0.777 | 0.223 | 0.575 |
| musique | v3b | subtask_parallel | 2000 | 0.565 | 0.563 | -0.002 | 0.563 | 0.830 | 0.170 | 0.528 |

For Subtask Parallel, task outputs are partial findings rather than fully comparable answer candidates; interpret its oracle and regret separately.

## Where failure first appears

| system | n | proposal | revision | worker chain | final picker | final aggregator | final correct | failure rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| all | 8000 | 946 | 73 | 75 | 173 | 857 | 5876 | 0.266 |
| debate | 1600 | 77 | 73 | 0 | 173 | 0 | 1277 | 0.202 |
| ensemble | 1600 | 66 | 0 | 0 | 0 | 316 | 1218 | 0.239 |
| parallel_roles | 1600 | 77 | 0 | 0 | 0 | 336 | 1187 | 0.258 |
| sequential | 1600 | 376 | 0 | 75 | 0 | 94 | 1055 | 0.341 |
| subtask_parallel | 1600 | 350 | 0 | 0 | 0 | 111 | 1139 | 0.288 |

Across Debate, the machine labels classify 73 terminal errors as revision loss and 173 as final-picker failure; they count 278 harmful revision flips and 169 beneficial flips. In the targeted human audit, 13/24 resolved sampled harmful flips and 11/25 beneficial flips were exactly confirmed. A descriptive sensitivity projection gives about 150.6 harmful versus 74.4 beneficial flips, so the direction `harmful > beneficial` survives at the point estimate, but the original counts must not be presented as exact human-validated totals.

Across Sequential, the machine labels say that the worker chain ended wrong after earlier discovery in 142 items and that the final aggregator lost a correct last-worker answer in 94 items. Only 8/25 sampled machine-labelled Sequential C-to-W transitions were exactly confirmed by the targeted human audit, mainly because the judge over-called correctness at the source stage. Treat the worker-chain counts as preliminary until a stronger calibrated judge or full human adjudication replaces these labels. The first-error classification counts only terminally incorrect items, whereas these architecture counters can also include losses later recovered by the final output.

## Debate revision versus picker and Sequential chain versus aggregator

| run | system | budget | revision destroyed | picker failures | W→C | C→W | chain destroyed | aggregator losses | seq W→C | seq C→W |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2wiki_frozen_token | debate | 1000 | 3 | 7 | 12 | 15 | — | — | — | — |
| 2wiki_frozen_token | debate | 2000 | 7 | 10 | 6 | 18 | — | — | — | — |
| 2wiki_frozen_token | sequential | 1000 | — | — | — | — | 14 | 4 | 62 | 15 |
| 2wiki_frozen_token | sequential | 2000 | — | — | — | — | 16 | 10 | 66 | 16 |
| 2wiki_v3b_token | debate | 1000 | 4 | 11 | 12 | 13 | — | — | — | — |
| 2wiki_v3b_token | debate | 2000 | 3 | 12 | 10 | 12 | — | — | — | — |
| 2wiki_v3b_token | sequential | 1000 | — | — | — | — | 17 | 9 | 59 | 17 |
| 2wiki_v3b_token | sequential | 2000 | — | — | — | — | 19 | 6 | 64 | 19 |
| frozen_all_mas_token | debate | 1000 | 17 | 25 | 34 | 58 | — | — | — | — |
| frozen_all_mas_token | debate | 2000 | 13 | 37 | 32 | 55 | — | — | — | — |
| frozen_all_mas_token | sequential | 1000 | — | — | — | — | 25 | 23 | 86 | 29 |
| frozen_all_mas_token | sequential | 2000 | — | — | — | — | 19 | 14 | 81 | 20 |
| v3b_all_mas_token | debate | 1000 | 11 | 37 | 32 | 55 | — | — | — | — |
| v3b_all_mas_token | debate | 2000 | 15 | 34 | 31 | 52 | — | — | — | — |
| v3b_all_mas_token | sequential | 1000 | — | — | — | — | 19 | 13 | 84 | 22 |
| v3b_all_mas_token | sequential | 2000 | — | — | — | — | 13 | 15 | 85 | 13 |

## Resource and truncation associations

| analysis | n | strata | adjusted OR | 95% low | 95% high | p |
|---|---:|---:|---:|---:|---:|---:|
| higher wall time -> semantic discovery | 7997 | 40 | 0.657 | 0.574 | 0.753 | 0.000 |
| higher wall time -> drop after discovery | 6677 | 40 | 1.768 | 1.529 | 2.044 | 0.000 |
| more thinking tokens -> semantic discovery | 7997 | 30 | 0.529 | 0.456 | 0.613 | 0.000 |
| more thinking tokens -> drop after discovery | 6677 | 30 | 2.679 | 2.153 | 3.334 | 0.000 |
| destination truncation -> C-to-W transition | 3338 | 16 | 1.268 | 0.926 | 1.736 | 0.139 |

Higher wall time and token indicators are defined relative to the median within dataset × model variant × budget × system cells. Odds ratios are fixed-effect stratified estimates. They are observational associations, not causal effects.

The truncation analysis is conditional on a semantically correct source stage and covers Debate revision and Sequential worker transitions. OR > 1 means the destination is more likely to lose correctness.

Observed destination truncation had OR=1.2676 (95% CI 0.9258–1.7355, p=0.139136) for a C-to-W transition. The interval includes 1, so these data do not establish that truncation increases semantic loss.

The targeted human audit also found lower exact machine-human transition agreement for truncated destinations (0.412) than non-truncated destinations (0.604). Because that audit is a designed case-control sample, this does not estimate a truncation effect; it instead shows that Mistral's labels are less dependable on truncated intermediate outputs. This further weakens any causal interpretation of the full-trace truncation association.

## Budget-paired tests

| group | outcome | pairs | b1000 | b2000 | W→C | C→W | McNemar p | Δ wall s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all | semantic_gold_discovered | 3997 | 0.842 | 0.828 | 138 | 192 | 0.003 | 4.827 |
| all | semantic_final_correct | 4000 | 0.741 | 0.728 | 241 | 291 | 0.034 | 4.825 |
| debate | semantic_gold_discovered | 800 | 0.955 | 0.949 | 18 | 23 | 0.533 | 7.537 |
| debate | semantic_final_correct | 800 | 0.811 | 0.785 | 66 | 87 | 0.106 | 7.537 |
| ensemble | semantic_gold_discovered | 800 | 0.956 | 0.958 | 16 | 15 | 1.000 | 3.312 |
| ensemble | semantic_final_correct | 800 | 0.772 | 0.750 | 34 | 52 | 0.066 | 3.312 |
| parallel_roles | semantic_gold_discovered | 800 | 0.951 | 0.941 | 21 | 29 | 0.322 | 4.845 |
| parallel_roles | semantic_final_correct | 800 | 0.743 | 0.741 | 55 | 56 | 1.000 | 4.845 |
| sequential | semantic_gold_discovered | 800 | 0.700 | 0.671 | 46 | 69 | 0.040 | 4.693 |
| sequential | semantic_final_correct | 800 | 0.665 | 0.654 | 46 | 55 | 0.426 | 4.693 |
| subtask_parallel | semantic_gold_discovered | 797 | 0.646 | 0.622 | 37 | 56 | 0.061 | 3.743 |
| subtask_parallel | semantic_final_correct | 800 | 0.713 | 0.711 | 40 | 41 | 1.000 | 3.738 |

Across matched items, b2000 changed discovery from 0.8419 to 0.8284 (McNemar p=0.003465) and final accuracy from 0.7408 to 0.7282 (p=0.033537). Thus the larger token budget did not improve the aggregate semantic outcomes in these frozen runs.

## Wall-clock and token accounting

| system | budget | n | mean wall s | median wall s | p25 | p75 | total wall s | mean thinking tokens | truncation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| debate | 1000 | 800 | 15.385 | 15.338 | 13.146 | 17.809 | 12307.802 | 968.574 | 0.970 |
| debate | 2000 | 800 | 22.922 | 24.855 | 17.917 | 28.261 | 18337.728 | 1621.539 | 0.761 |
| ensemble | 1000 | 800 | 7.571 | 7.449 | 6.272 | 9.409 | 6056.986 | 920.564 | 0.762 |
| ensemble | 2000 | 800 | 10.883 | 12.216 | 6.829 | 14.470 | 8706.707 | 1469.162 | 0.569 |
| parallel_roles | 1000 | 800 | 9.943 | 9.742 | 9.572 | 10.068 | 7954.725 | 968.569 | 0.996 |
| parallel_roles | 2000 | 800 | 14.789 | 14.860 | 14.595 | 15.236 | 11830.804 | 1628.051 | 0.794 |
| sequential | 1000 | 800 | 17.890 | 17.524 | 12.380 | 23.112 | 14312.281 | 644.310 | 0.480 |
| sequential | 2000 | 800 | 22.583 | 18.316 | 12.006 | 31.965 | 18066.337 | 884.393 | 0.314 |
| subtask_parallel | 1000 | 800 | 11.660 | 11.746 | 8.821 | 13.692 | 9327.772 | 718.311 | 0.591 |
| subtask_parallel | 2000 | 800 | 15.398 | 16.337 | 8.683 | 19.784 | 12318.274 | 1093.908 | 0.471 |

`wall_seconds` is observed end-to-end elapsed time per item (critical-path time for parallel systems). Summing it gives observed item wall-time, not GPU-seconds. Exact GPU-seconds require scheduler/job telemetry or non-overlapped device accounting and cannot be reconstructed from these trace fields.

## Output files

- `semantic_metrics.csv`: grouped semantic accuracy and failure metrics.
- `per_item_semantic.jsonl`: one row per item/configuration, including `first_error_stage`.
- `semantic_transitions.csv`: Debate and Sequential stage transitions.
- `budget_wallclock.csv`: wall-clock, token and truncation summaries for each run/system/budget.
- `budget_wallclock_overall.csv`: compact system × budget wall-clock table.
- `resource_associations.csv`: adjusted odds-ratio analyses.
- `budget_pair_tests.csv`: matched b1000 versus b2000 tests.
- `first_error_stage.csv`: first semantic failure location by architecture.
- `unresolved_stage_review.csv`: the six uncertain stage judgments.

## Calibration caveat

**Post-audit update:** the original general calibration result did not transfer to the critical transition strata. The completed targeted audit found stage-label accuracy 0.739 (kappa 0.478) and exact transition accuracy 0.505 (multiclass kappa 0.364). By stratum, exact confirmation was 11/25 for Debate W-to-C, 13/24 resolved for Debate C-to-W, 8/25 for Sequential C-to-W, and 18/25 for stable controls. The main systematic error was false source-stage discovery, especially in Sequential, plus false destination-stage correctness in Debate beneficial flips. This post-audit result supersedes the pre-audit calibration statement below for transition-level inference. Mistral's transition labels should now be used for screening and sensitivity analysis only, not as semantic ground truth.

A stronger Qwen2.5-72B-Instruct-GPTQ-Int4 judge was rescored against the rev. 3 human labels after applying the v4 discovery rule consistently to `SEN-0051` and `SEN-0081`. It achieved 0.870 stage accuracy across 200 resolved labels (kappa 0.723) and 0.790 exact transition accuracy across 100 resolved pairs (multiclass kappa 0.701), with no parse or grounding failures. It still failed the fixed acceptance thresholds, so it is not used to replace the human audit or to certify all 26,873 stage labels; it may be used only as a secondary screen for targeted human adjudication.

For provenance, the earlier general calibration had reported 0.919 evidence-valid accuracy and kappa 0.829 overall, with lower accuracy for Debate beneficial flips (0.700) and Sequential C-to-W cases (0.800). The targeted audit above is the controlling reliability result for the present failure-localisation claims.
