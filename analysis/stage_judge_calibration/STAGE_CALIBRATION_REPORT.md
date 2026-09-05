# Intermediate-Stage Judge Calibration

- Sampled stage outputs: 200
- Human binary labels: 200
- Human label counts: `{'correct': 124, 'incorrect': 76}`
- Mistral label counts: `{'correct': 105, 'incorrect': 95}`

## Agreement with blind human labels

| evaluator | decided/eligible | coverage | accuracy (95% CI) | precision | recall | F1 | specificity | kappa |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mistral-24B-stage | 200/200 | 1.000 | 0.805 [0.745, 0.854] | 0.905 | 0.766 | 0.830 | 0.868 | 0.605 |
| lexical-contain | 200/200 | 1.000 | 0.835 [0.777, 0.880] | 0.864 | 0.871 | 0.867 | 0.776 | 0.649 |
| normalized-EM | 200/200 | 1.000 | 0.440 [0.373, 0.509] | 1.000 | 0.097 | 0.176 | 1.000 | 0.075 |

## Mistral audit by selection stratum

| selection_stratum | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| aggregation_failure | 25 | 0.640 | 4 | 5 |
| debate_beneficial_flip | 20 | 0.650 | 1 | 6 |
| debate_harmful_flip | 20 | 0.750 | 2 | 3 |
| drop_after_discovery | 25 | 0.720 | 1 | 6 |
| final_correct_control | 30 | 0.933 | 0 | 2 |
| non_truncated | 20 | 1.000 | 0 | 0 |
| sequential_c_to_w | 20 | 0.950 | 1 | 0 |
| sequential_w_to_c | 20 | 0.850 | 0 | 3 |
| truncated | 20 | 0.750 | 1 | 4 |

## Mistral audit by stage truncation

| stage_truncated | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| False | 89 | 0.910 | 4 | 4 |
| True | 111 | 0.721 | 6 | 25 |

## Mistral audit by system

| system | n human-binary | accuracy | false positive | false negative |
|---|---:|---:|---:|---:|
| debate | 64 | 0.734 | 5 | 12 |
| ensemble | 24 | 0.875 | 0 | 3 |
| parallel_roles | 23 | 0.652 | 3 | 5 |
| sequential | 64 | 0.859 | 2 | 7 |
| subtask_parallel | 25 | 0.920 | 0 | 2 |

## Promotion rule

Promote the stage judge only if aggregate agreement is acceptable and false-positive/false-negative asymmetry is not concentrated in transition or truncation strata. A final-answer judge calibration does not satisfy this requirement.
