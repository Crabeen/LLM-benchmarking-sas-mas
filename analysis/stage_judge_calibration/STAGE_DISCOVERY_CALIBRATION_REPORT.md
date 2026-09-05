# Intermediate-Stage Semantic-Discovery Calibration

- Sampled stage outputs: 200
- Human discovery-label counts: `{'correct': 117, 'incorrect': 83}`
- Adjudication overrides that changed first-pass labels: 21
- Mistral discovery-label counts: `{'correct': 127, 'incorrect': 72, 'uncertain': 1}`
- Ungrounded evidence among Mistral discovery-positive rows: 2/127

## Agreement with human semantic-discovery labels

| evaluator | decided/eligible | coverage | accuracy (95% CI) | precision | recall | F1 | specificity | kappa |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mistral-24B-discovery | 199/200 | 0.995 | 0.910 [0.862, 0.942] | 0.890 | 0.966 | 0.926 | 0.829 | 0.810 |
| Mistral-24B-evidence-valid | 197/200 | 0.985 | 0.919 [0.872, 0.949] | 0.904 | 0.966 | 0.934 | 0.850 | 0.829 |
| lexical-contain | 200/200 | 1.000 | 0.860 [0.805, 0.901] | 0.856 | 0.915 | 0.884 | 0.783 | 0.708 |
| normalized-EM | 200/200 | 1.000 | 0.475 [0.407, 0.544] | 1.000 | 0.103 | 0.186 | 1.000 | 0.087 |

## Mistral discovery audit by selection stratum

| selection_stratum | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| aggregation_failure | 25 | 0.920 | 1 | 1 |
| debate_beneficial_flip | 20 | 0.700 | 5 | 1 |
| debate_harmful_flip | 20 | 0.895 | 2 | 0 |
| drop_after_discovery | 25 | 1.000 | 0 | 0 |
| final_correct_control | 30 | 0.900 | 3 | 0 |
| non_truncated | 20 | 1.000 | 0 | 0 |
| sequential_c_to_w | 20 | 0.800 | 3 | 1 |
| sequential_w_to_c | 20 | 0.950 | 0 | 1 |
| truncated | 20 | 1.000 | 0 | 0 |

## Mistral discovery audit by stage truncation

| stage_truncated | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| False | 89 | 0.910 | 5 | 3 |
| True | 111 | 0.909 | 9 | 1 |

## Mistral discovery audit by system

| system | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| debate | 64 | 0.873 | 7 | 1 |
| ensemble | 24 | 1.000 | 0 | 0 |
| parallel_roles | 23 | 0.913 | 2 | 0 |
| sequential | 64 | 0.891 | 5 | 2 |
| subtask_parallel | 25 | 0.960 | 0 | 1 |

## Operational decision

Semantic discovery is sufficiently supported for full-trace rejudging with evidence validation enabled. Treat uncertain, parse-error, or ungrounded-positive rows as unresolved rather than correct. Because no pass threshold was preregistered, this is an operational decision based on the reported agreement, not a formal hypothesis test.

Keep targeted manual review for debate beneficial flips and sequential C-to-W transitions, which have the weakest subgroup agreement in this calibration sample.

## Scope

This report calibrates semantic discovery only. The endorsed-answer label requires a separately human-confirmed gold column before it can be treated as calibrated.
