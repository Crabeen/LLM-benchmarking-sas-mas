# Where Multi-Agent Reasoning Fails under Matched Budgets: A Stage-Level Study of Small Open-Weight Language Models

> **Working dissertation draft — evidence frozen on 22 August 2026.**  
> This document contains the sections that are currently supported by completed experiments and audits. Citation keys such as `[@tran-kiela-2026]` are placeholders for the final reference manager. Statements labelled **screening evidence** depend on automatic semantic labels and must not be rewritten as human-verified facts.

## Proposed dissertation structure

1. Introduction
2. Related Work
3. Research Questions and Analytical Framework
4. Experimental Design
5. Evaluation and Human Audit Methodology
6. Benchmark, Fine-tuning, and Budget Results
7. Machine-Screened Failure Analysis
8. Human Audit and Transition Results
9. Discussion
10. Limitations and Threats to Validity
11. Conclusion
12. Appendices

The central argument is not that multi-agent systems (MAS) are uniformly inferior to single-agent systems (SAS). The evidence supports a more specific account: decomposition can increase the probability that a trace contains a correct answer-bearing state, while also creating architecture-specific opportunities for that state to be revised, discarded, or incorrectly selected before the final response. The dissertation therefore treats final accuracy as the endpoint of a process and localises where correctness first appears and where it is subsequently lost.

---

# 1. Introduction

Large language model reasoning systems increasingly use multiple calls, specialised roles, parallel candidates, iterative criticism, and aggregation. These systems are often motivated by an intuitive division-of-labour argument: if individual calls explore different evidence or reasoning paths, a downstream component should be able to combine their complementary information into a better answer. This intuition, however, does not guarantee improved end-to-end correctness. Decomposition introduces additional interfaces at which information can be omitted, distorted, or selected incorrectly. A multi-agent system may therefore contain a correct answer at an intermediate stage and still produce an incorrect final response.

Existing matched-budget comparisons show that additional agent calls do not necessarily improve multi-hop question answering when total reasoning resources are controlled [@tran-kiela-2026]. Aggregate accuracy alone cannot explain why this occurs. A lower final score is compatible with at least three distinct mechanisms. First, no agent may discover the required answer. Second, an agent may discover it, but a later worker or critic may replace it with an incorrect alternative. Third, correct candidates may survive until the final stage, but the picker or aggregator may choose incorrectly. These mechanisms imply different interventions: improving candidate generation will not repair a selection failure, while improving an aggregator cannot recover an answer absent from every candidate.

This dissertation investigates these mechanisms using Qwen3-4B, two multi-hop question-answering datasets, frozen and fine-tuned model variants, five MAS architectures, and a single-agent baseline. The principal experiments impose matched thinking-token caps of 1,000 and 2,000 tokens. Observed wall-clock time, actual thinking-token use, and truncation are retained as resource variables rather than inferred from nominal budgets. The study combines three levels of evidence: lexical matching as a transparent robustness baseline; large-scale LLM-judged trace analysis as screening evidence; and a blinded human audit as the primary basis for claims about semantic stage transitions.

The study makes four contributions. First, it defines a stage-level framework that separates **answer discovery** from **answer endorsement**. Second, it maps those labels to architecture-specific correctness transitions, including Debate revision-to-picker transitions and Sequential last-worker-to-aggregator transitions. Third, it quantifies the reliability limits of LLM-as-a-judge evaluation on long, mixed intermediate outputs. Fourth, it shows through human-audited, stratum-weighted estimates that the final Debate picker loses a correct source state more often than the Sequential final aggregator in the present experimental population.

The scope of this conclusion is deliberately narrow. The experiments cover one base-model family, two datasets, two model variants, and one implementation of each architecture. The results do not establish that MAS is intrinsically ineffective, that all forms of MAS-specific training fail, or that the observed rates generalise to larger or closed-weight models.

![Figure 1. Research logic from matched-budget performance to stage-level failure localisation.](D:/thesis/dissertation/figures/fig_01_research_logic.png)

**Figure source and generation note:** this figure should be generated from the conceptual definitions in Sections 3 and 5. Target file: `D:/thesis/dissertation/figures/fig_01_research_logic.png`.

---

# 2. Related Work

## 2.1 Multi-agent reasoning under controlled resources

Multi-agent prompting architectures distribute reasoning across planners, workers, critics, role-specialised solvers, candidate generators, and aggregators. Their potential advantages include wider exploration, explicit critique, and complementary evidence coverage. Their costs include repeated computation, correlated errors, communication bottlenecks, and additional decision stages. The most relevant comparison is therefore not unconstrained MAS against a single short generation, but MAS and SAS under matched resource budgets [@tran-kiela-2026].

The present work follows this controlled-comparison principle but changes the analytical target. Instead of treating the system as a black box, it asks whether a correct answer was available at intermediate stages and whether subsequent operations preserved it. The resulting analysis connects end-to-end accuracy to trace-level mechanisms.

## 2.2 Fine-tuning and architecture-specific behaviour

Supervised fine-tuning may improve the base model without teaching it to operate reliably inside a multi-agent pipeline. The v3b checkpoint used in this study was trained on successful single-agent-style traces rather than architecture-conditioned Debate, Sequential, or aggregator episodes. Its results therefore test a narrow alternative explanation: whether MAS underperformance is solely an artefact of using an entirely frozen model. They do not test the stronger claim that architecture-conditioned rejection-sampled fine-tuning, preference optimisation, or multi-agent reinforcement learning cannot improve MAS.

## 2.3 Evaluating intermediate reasoning states

Intermediate outputs are longer and less structured than final answers. Exact match is consequently too strict, while substring containment can be too permissive when the gold string is attached to the wrong entity, relation, date, or comparison. LLM-as-a-judge evaluation offers semantic flexibility but introduces measurement error, including inconsistent decisions on identical text and systematic over-strict or over-broad interpretations. This dissertation treats judge calibration as part of the research method rather than as an implementation detail.

> **To complete before submission:** expand this chapter with peer-reviewed work on debate, self-consistency and ensembles, role-based MAS, LLM evaluators, multi-hop QA, and process supervision. Do not infer citations from filenames; add verified bibliography entries.

---

# 3. Research Questions and Analytical Framework

## 3.1 Research questions

The dissertation is organised around three connected research questions.

**RQ1 — Performance and resources.** Under matched thinking-token caps, how do architecture, dataset, model variant, and budget affect final answer correctness, semantic answer discovery, actual token use, and wall-clock time?

**RQ2 — Failure localisation.** When an MAS trace contains or endorses a correct answer, at which architecture-specific stage is correctness preserved, destroyed, or recovered?

**RQ3 — Measurement validity.** How reliably do lexical criteria and LLM judges identify semantic correctness in intermediate traces, particularly for harmful or beneficial transitions and truncated outputs?

These questions form a dependency chain. RQ1 establishes whether additional decomposition or budget improves the final outcome. RQ2 explains the mechanism behind the outcome. RQ3 determines how much confidence can be placed in the labels used to answer RQ2.

## 3.2 Discovery, endorsement, and transition states

Two labels are required because a trace can mention or entail the correct answer without ultimately supporting it.

**Discovery** is correct (`C`) when a readable stage output states or unambiguously entails the reference answer for the entity, relation, and granularity requested by the question. Later rejection does not erase discovery. A coincidental string match, a gold string attached to the wrong relation, or an answer at insufficient granularity does not count as discovery.

**Endorsement** is correct (`C`) when the stage ultimately commits to a semantically correct answer for the requested slot. A stage that first states the gold answer but later replaces it with an incorrect answer has Discovery=`C` and Endorsement=`W`. `U` is reserved for genuine semantic indeterminacy or answer-bearing truncation that prevents the final commitment from being recovered.

For a source stage (S) and destination stage (D), the primary endorsement transitions are:

- `C→C`: correct state preserved;
- `C→W`: harmful loss;
- `W→C`: beneficial recovery;
- `W→W`: no correct endorsed state at either boundary.

The source is architecture-specific. For Debate, it is an oracle over the two revised answers: the source is `C` if either `rev_A` or `rev_B` endorses the gold answer. The destination is the final picker output. For Sequential, the source is the last worker and the destination is the final aggregator. A parallel discovery-to-final analysis replaces source Endorsement with source Discovery to measure whether answer-bearing content was present even when it was not yet endorsed.

## 3.3 Evidence hierarchy

The dissertation uses the following hierarchy to prevent automatic labels from being overstated.

| Evidence level | Source | Permitted interpretation |
|---|---|---|
| Primary | Blinded human Discovery and Endorsement audit | Semantic transition claims for the audited and stratum-weighted Debate/Sequential population |
| Secondary | Mistral-24B full-trace labels | Screening estimates, sampling strata, and hypothesis generation |
| Robustness baseline | Normalised exact match, token F1, and containment | Transparent lexical sensitivity analysis; not semantic ground truth |

Machine-defined strata are used for sampling and weighting only. They are not treated as human truth after unblinding.

---

# 4. Experimental Design

## 4.1 Models and datasets

The experiments use Qwen3-4B in two forms: the frozen Qwen3-4B checkpoint and the merged v3b supervised fine-tuning checkpoint. The v3b model was trained on selected successful single-agent traces; it was not trained with explicit architecture or role conditions. This distinction matters when interpreting whether fine-tuning changes MAS behaviour.

Evaluation uses the validation splits of MuSiQue 4-hop and 2WikiMultiHopQA. Each experimental cell contains 200 items in a fixed order and uses oracle supporting context. Oracle context reduces retrieval variation and focuses the analysis on reasoning and orchestration. It also limits external validity to settings in which relevant evidence is available to the system.

The core matrix contains four dataset-by-model conditions, six systems, two budgets, and 200 items, yielding 9,600 system–item configurations. The five MAS systems account for 8,000 configurations and form the full stage-localisation corpus.

## 4.2 Systems

The comparison includes one single-agent system and five MAS architectures.

| System | Operational structure | Main failure interface |
|---|---|---|
| SAS | One solver call | Discovery and final extraction |
| Sequential | Planner → ordered workers → aggregator | Worker-chain propagation; final aggregation |
| Subtask Parallel | Planner → parallel subtask workers → reducer | Invalid independence assumptions; incomplete synthesis |
| Parallel Roles | Solver, fact extractor, sceptic, second solver → aggregator | Role redundancy and aggregation |
| Debate | Two initial answers → cross-critique/revision → picker | Harmful revision and final selection |
| Ensemble | Four sampled candidates → judge | Candidate diversity and final selection |

The ensemble uses four candidates as an explicit implementation choice because the reference study does not report the candidate count. Candidate generation uses temperature 0.7; final judges and the remaining deterministic system calls use temperature 0.

## 4.3 Budget protocol

The principal experiments use total thinking-token caps of 1,000 and 2,000 tokens. These are upper bounds rather than forced expenditures. Thinking tokens are divided across worker calls according to the architecture; planners and final aggregators receive no additional thinking-token allocation. The implementation records actual thinking-token use, truncation, logical agent calls, physical model invocations, and end-to-end wall-clock time.

Parallel workers are executed in a batch where applicable. Consequently, `wall_seconds` is the observed critical-path latency for an item, not the sum of per-worker latencies. Summed item wall time is not GPU-seconds. Exact GPU-seconds require scheduler or device telemetry and cannot be reconstructed from trace timing alone.

## 4.4 Units of analysis

Three units must remain distinct throughout the dissertation.

| Unit | N | Purpose |
|---|---:|---|
| MAS system–item configuration | 8,000 | Full-trace automatic screening and resource analysis |
| Unique human-audited item | 160 | Debate and Sequential item-level transition estimation |
| Non-repeat human-audited stage row | 400 | Human–Mistral stage-label agreement |
| Hidden repeat stage row | 20 | Intra-rater consistency only |

The 400 stage rows are not 400 independent benchmark questions. Debate contributes three relevant outputs per audited item (`rev_A`, `rev_B`, and final); Sequential contributes two (last worker and final). The 20 hidden repeats are excluded from machine agreement, transition estimation, and population weighting.

## 4.5 Trace corpus

The full MAS trace export contains 26,873 intermediate stages. Six Mistral Discovery labels were unresolved and are excluded pairwise where required. Final outputs comprise 2,297 cases reused from text-identical judged stage outputs and 5,703 separately judged final outputs. Reuse was permitted only when all identical matched stages had the same machine label; conflicting identical-stage labels were excluded from reuse.

---

# 5. Evaluation and Human Audit Methodology

## 5.1 Lexical baseline

The lexical analysis applies SQuAD/HotpotQA-style normalisation, strict exact match, maximum token F1 over the reference answer and aliases, and normalised containment. Containment is the principal lexical stage criterion because intermediate outputs are usually sentences rather than answer spans. It remains vulnerable to substring collisions, incorrect relations, name prefixes, and granularity errors. It is therefore reported as a robustness baseline rather than as the semantic outcome.

## 5.2 Automatic semantic screening

Mistral Small 3.2 24B Instruct labels intermediate stages for semantic Discovery. A general 200-stage calibration reported 91.9% evidence-valid accuracy and Cohen's κ=0.829. This aggregate calibration did not transfer to deliberately difficult transition strata. In a targeted 100-pair audit, Mistral achieved 74.0% stage accuracy (κ=0.481) and 51.0% exact transition accuracy (multiclass κ=0.366). A stronger Qwen2.5-72B-Instruct-GPTQ-Int4 judge improved to 87.0% stage accuracy and 79.0% exact transition accuracy, but still failed the frozen acceptance threshold. Neither model is therefore treated as a replacement for human transition labels.

## 5.3 Final-transition human audit

The primary audit sampled 160 unique items from Debate and Sequential machine transition strata. The sampling design intentionally over-represented transitions likely to be informative about finalisation failures. The Debate machine-defined `W→C` pool contained only one eligible item; it was taken as a census, and the 14-item quota shortfall was reallocated to Debate `C→W`. The full eligible pools contained 1,185 Debate items and 1,037 Sequential items.

Each stage was reviewed blind to architecture, position, model variant, dataset, budget, and machine label. Every `C` label required verbatim evidence copied from the output. Four review rounds were completed before the key was opened. The codebook was prospectively clarified between rounds, while earlier raw labels were not silently overwritten. A derived `harmonized_reason_rev4` field maps three legacy reason codes to the final vocabulary without changing any C/W/U label.

### 5.3.1 Correct interpretation of the 15 item-level fields

The phrase “15 labels” used during supervision refers to 15 columns in the item-level audit table, not to fifteen independent binary error indicators. They comprise four Boolean truncation descriptors (`question_any_truncated`, `source_truncated`, `final_truncated`, and the derived union `any_truncated`); four human source/final Discovery and Endorsement states; two derived human transition fields; four aligned machine source/final states; and one derived machine transition. The semantic states use C/W/U, while the transition fields are categorical paths such as C→C, C→W, W→C, and W→W.

The primary inferential field is `human_endorsement_transition_raw`, weighted by the frozen sampling-stratum populations. `human_discovery_to_final_endorsement_raw` is a secondary cross-axis diagnostic. The machine fields are used for sampling and human–machine agreement, not as ground truth, while the truncation fields are covariates or sensitivity descriptors. The 15 columns must therefore not be reported as fifteen separate error prevalences.

## 5.4 Reliability statistics

Agreement is reported as exact agreement and Cohen's κ. Bootstrap intervals for κ are based on resampling the evaluated rows. Hidden repeats estimate one annotator's internal consistency; they are not evidence of inter-rater agreement.

## 5.5 Stratum-weighted transition estimator

For transition category (t), the population count is estimated as

$$
\widehat{N}(t)=\sum_h N_h\frac{y_h(t)}{n_h},
$$

where (N_h) is the frozen full-pool size of machine stratum (h), (n_h) is its audited sample size, and (y_h(t)) is the number of human-audited items assigned to transition (t). Population proportions divide this estimate by the sum of the relevant (N_h). The point estimates are primary. Finite-population stratified confidence intervals are descriptive because selection within strata was greedily balanced across covariates rather than drawn by pure simple random sampling.

The prespecified primary treatment maps `U` to `W`, which is conservative for final correctness. Sensitivity analyses exclude U-bearing items or map `U` to `C`.

## 5.6 Budget and resource statistics

Budget comparisons use matched-item McNemar tests for the 1,000- versus 2,000-token conditions. Resource associations use fixed-effect stratified odds ratios, with high wall time or token use defined relative to the median within dataset × model variant × budget × system cells. These are observational associations and are not interpreted causally.

---

# 6. Benchmark, Fine-tuning, and Budget Results

## 6.1 End-to-end performance is dataset- and architecture-dependent

The lexical baseline does not support a universal statement that every MAS architecture is worse than SAS. On MuSiQue, the frozen SAS achieved final containment accuracy of 0.560 and 0.525 at the 1,000- and 2,000-token caps. Frozen Debate achieved 0.510 and 0.535, while Sequential achieved 0.335 and 0.340. Other MAS architectures were also below SAS in these cells. On 2Wiki, however, frozen Debate reached 0.935 and 0.930 compared with SAS at 0.860 and 0.845. The final-answer judge did not reproduce the full size of this lexical advantage, illustrating the sensitivity of absolute conclusions to the evaluator.

The correct interpretation is therefore conditional: decomposition is most damaging on the more difficult MuSiQue setting and for architectures with weak final synthesis, while Debate can remain competitive on 2Wiki. The dissertation's principal contribution is to explain these conditional outcomes rather than to average them into one universal ranking.

![Figure 2. Final accuracy by dataset, model variant, architecture, and token budget.](D:/thesis/dissertation/figures/fig_02_final_accuracy_by_condition.png)

**Figure data:** `D:/thesis/analysis/diagnostics/2wiki_frozen_token/metrics.csv`, `D:/thesis/analysis/diagnostics/2wiki_v3b_token/metrics.csv`, `D:/thesis/analysis/diagnostics/frozen_all_mas_token/metrics.csv`, and `D:/thesis/analysis/diagnostics/v3b_all_mas_token/metrics.csv`.

## 6.2 Fine-tuning did not consistently reverse the initial ordering

The `v3b` model is treated as an attempted intervention after the frozen-model comparison rather than as a separate model family. On MuSiQue at 1,000 tokens, SAS changed from 0.560 to 0.545, Debate from 0.510 to 0.505, and Sequential from 0.335 to 0.380. At 2,000 tokens, SAS changed from 0.525 to 0.530, Debate from 0.535 to 0.530, and Sequential remained at 0.340. The changes are mixed and do not show a consistent reversal of the SAS–MAS pattern. Because `v3b` was trained primarily with single-agent-style data, this result does not test whether architecture-conditioned training for planners, critics, or aggregators would succeed.

## 6.3 A larger token cap increased cost without improving aggregate semantic outcomes

Across matched items, increasing the nominal cap from 1,000 to 2,000 tokens changed machine-screened semantic Discovery from 0.8419 to 0.8284. There were 138 `W→C` and 192 `C→W` matched changes (McNemar (p=0.0035)). Semantic final correctness changed from 0.7408 to 0.7282, with 241 `W→C` and 291 `C→W` changes ((p=0.0335)). Mean observed wall time increased by 4.825 seconds.

This result does not imply that reasoning is harmful in general. It shows that doubling the cap did not repair the dominant errors in this fixed architecture and model setting. The cap also did not force every call to use twice as many tokens. Actual thinking-token consumption rose from 969 to 1,622 for Debate and from 644 to 884 for Sequential, while mean item wall time rose from 15.4 to 22.9 seconds for Debate and from 17.9 to 22.6 seconds for Sequential.

| System | Mean wall time, b1000 | Mean wall time, b2000 | Mean thinking tokens, b1000 | Mean thinking tokens, b2000 |
|---|---:|---:|---:|---:|
| Debate | 15.385 s | 22.922 s | 968.6 | 1,621.5 |
| Ensemble | 7.571 s | 10.883 s | 920.6 | 1,469.2 |
| Parallel Roles | 9.943 s | 14.789 s | 968.6 | 1,628.1 |
| Sequential | 17.890 s | 22.583 s | 644.3 | 884.4 |
| Subtask Parallel | 11.660 s | 15.398 s | 718.3 | 1,093.9 |

![Matched aggregate budget outcomes and observed resource use.](D:/thesis/dissertation/figures/fig_04_budget_outcome_resource_tradeoff.png)

**Figure data:** `D:/thesis/analysis/semantic_diagnostics/budget_pair_tests.csv` and `D:/thesis/analysis/semantic_diagnostics/budget_wallclock_overall.csv`.

The benchmark, fine-tuning, and budget results establish what happened, but they do not distinguish failure to discover from failure to preserve a correct answer. The following chapter therefore turns to the recorded traces.

---

# 7. Machine-Screened Failure Analysis

## 7.1 Automatic semantic screening identifies substantial discovery–finalisation gaps

The Mistral-labelled full-trace analysis suggests that several MAS architectures often generate answer-bearing material without preserving it to the final output. On frozen MuSiQue at 1,000 tokens, Debate had semantic final accuracy 0.720, candidate-oracle accuracy 0.845, and aggregation regret 0.125. Ensemble had final accuracy 0.660 and oracle accuracy 0.960, producing regret of 0.300. Parallel Roles had final accuracy 0.600 and oracle accuracy 0.915, with regret of 0.315. The corresponding semantic preservation rates were 0.774, 0.688, and 0.634.

These gaps were smaller on 2Wiki. Frozen Debate at 1,000 tokens had final accuracy 0.930, oracle accuracy 0.965, and regret 0.035. Dataset difficulty therefore changes both candidate quality and the cost of final selection.

These values are **screening estimates**. The targeted human audits show that machine transition labels are not sufficiently accurate to be described as ground truth. Their value is to identify where human validation should be concentrated.

![Figure 3. Semantic candidate oracle accuracy, final accuracy, and aggregation regret.](D:/thesis/dissertation/figures/fig_03_semantic_oracle_regret.png)

**Figure data:** `D:/thesis/analysis/semantic_diagnostics/semantic_metrics.csv`.

## 7.2 Resource and truncation associations are diagnostic rather than causal

In the Mistral-labelled full corpus, above-cell-median wall time was associated with lower semantic Discovery (adjusted OR 0.657, 95% CI [0.574, 0.753]) and higher drop after Discovery (OR 1.768, [1.529, 2.044]). Above-median thinking-token use showed the same direction: Discovery OR 0.529 [0.456, 0.613] and drop OR 2.679 [2.153, 3.334]. These patterns are compatible with harder items requiring more resources and producing more unstable traces; they do not show that additional computation causes failure.

Destination truncation had OR 1.268 [0.926, 1.736] for a `C→W` transition, with (p=0.139). The interval includes one, so the data do not establish an association between truncation and semantic loss. Moreover, exact human–Mistral transition agreement was lower for truncated outputs in a deliberately selected audit sample, making the machine-labelled truncation result especially sensitive to evaluator error.

![Adjusted resource and truncation associations with discovery and loss.](D:/thesis/dissertation/figures/fig_07_resource_associations.png)

**Figure data:** `D:/thesis/analysis/semantic_diagnostics/resource_associations.csv`.

The machine screen supplies breadth and identifies plausible failure boundaries, but it cannot provide the controlling prevalence estimates for difficult transitions. The following chapter therefore reports the blind human audit separately.

---

# 8. Human Audit and Transition Results

## 8.1 Human annotation was internally consistent, but Mistral disagreement remained material

All 20 hidden repeats received the same Discovery and Endorsement labels as their originals: 20/20 exact agreement and κ=1.000 on both axes. This demonstrates internal repeatability under the frozen codebook; it does not establish independent inter-rater reliability.

Across the 400 non-repeat stage rows, human–Mistral exact agreement was 330/400 for Discovery (82.5%, κ=0.632; bootstrap 95% CI [0.557, 0.705]) and 322/400 for Endorsement (80.5%, κ=0.617; [0.541, 0.691]). Discovery disagreements were asymmetric: 54 human-`W`/Mistral-`C` cases versus 16 human-`C`/Mistral-`W` cases, indicating that Mistral more often over-called discovery. Endorsement showed the opposite dominant direction: 51 human-`C`/Mistral-`W` cases versus 22 human-`W`/Mistral-`C` cases. Agreement was weakest for the Sequential last-worker Endorsement label, at 56/80 (70.0%).

| Evaluation | Axis | Exact agreement | Cohen's κ | Bootstrap 95% CI for κ |
|---|---|---:|---:|---:|
| Hidden-repeat intra-rater | Discovery | 20/20 (100.0%) | 1.000 | [1.000, 1.000] |
| Hidden-repeat intra-rater | Endorsement | 20/20 (100.0%) | 1.000 | [1.000, 1.000] |
| Human vs Mistral | Discovery | 330/400 (82.5%) | 0.632 | [0.557, 0.705] |
| Human vs Mistral | Endorsement | 322/400 (80.5%) | 0.617 | [0.541, 0.691] |

![Figure 5. Human–Mistral confusion matrices for Discovery and Endorsement.](D:/thesis/dissertation/figures/fig_05_human_mistral_confusion.png)

**Figure data:** `D:/thesis/analysis/final_transition_endorsement_audit/unblind/agreement_summary.csv` and `D:/thesis/analysis/final_transition_endorsement_audit/unblind/disagreement_breakdown.csv`.

## 8.2 The human audit localises a larger final-selection loss in Debate

The 160 audited items contain 80 Debate and 80 Sequential transitions. Before weighting, the human Debate transitions were 35 `C→C`, 19 `C→W`, 0 `W→C`, 25 `W→W`, and one U-bearing `U→W` case. Sequential contained 40 `C→C`, 4 `C→W`, 6 `W→C`, 29 `W→W`, and one `U→W` case.

After weighting by the frozen machine-stratum pool sizes and mapping `U→W`, the estimated harmful `C→W` rate was 5.45% for Debate (approximate 95% CI [3.01%, 7.89%]) and 0.59% for Sequential ([0.27%, 0.90%]). The Debate-minus-Sequential difference was 4.86 percentage points ([2.41, 7.32]). The estimated beneficial `W→C` rate was 0% for Debate and 5.82% for Sequential ([2.28%, 9.37%]).

The machine-defined Debate `W→C` stratum contained only one eligible population item. Human review classified this item as `C→C`, meaning that the apparent beneficial picker event did not survive unblinding. In contrast, six of the fifteen sampled Sequential machine `W→C` cases were confirmed as human `W→C` transitions.

Using source Discovery rather than source Endorsement, the weighted probability that answer-bearing content was present but the final output did not endorse the answer was 7.06% for Debate and 3.96% for Sequential. This broader measure captures both final selection loss and source outputs that contained the answer without yet committing to it.

| Architecture | Harmful C→W | Approximate 95% CI | Beneficial W→C | Approximate 95% CI | Discovery-to-final loss |
|---|---:|---:|---:|---:|---:|
| Debate | 5.45% | [3.01%, 7.89%] | 0.00% | [0.00%, 0.00%] | 7.06% |
| Sequential | 0.59% | [0.27%, 0.90%] | 5.82% | [2.28%, 9.37%] | 3.96% |

![Figure 6. Human-audited harmful and beneficial final-stage transition rates.](D:/thesis/dissertation/figures/fig_06_human_transition_rates.png)

**Figure data:** `D:/thesis/analysis/final_transition_endorsement_audit/unblind/weighted_transition_estimates.csv`.  
**Audit workbook:** `D:/thesis/outputs/final_transition_endorsement_audit/final_transition_unblind_analysis.xlsx`.

## 8.3 The primary transition result is robust to the treatment of uncertainty

Only three of the 420 stage annotations were `U`, all on the Endorsement axis and all caused by truncation inside an answer-bearing statement. The estimated harmful Debate rate was 5.45% when `U→W`, 5.51% when U-bearing items were excluded, and 6.58% when `U→C`. The corresponding Sequential rates were 0.59%, 0.60%, and 2.20%. Debate remained higher under every prespecified treatment.

## 8.4 Scope of the human comparison and the required SAS extension

The human transition audit supports a comparison of the final coordination boundaries in Debate and Sequential; it does not by itself establish why SAS outperforms a MAS in a particular benchmark condition. SAS remains part of the final-performance benchmark but has no equivalent multi-agent picker or aggregator. The cross-architecture process comparison should therefore apply the same machine-screening pipeline to SAS and compare pre-final Discovery with final Endorsement. Until that analysis is completed, the dissertation should not claim that SAS wins because it experiences a lower human-audited transition rate.

---

# 9. Discussion

## 9.1 Multi-agent failure is partly a preservation problem

The results distinguish failure to produce a correct candidate from failure to preserve one. Machine screening suggests large oracle-to-final gaps for Ensemble, Parallel Roles, and Debate on MuSiQue. The human audit provides stronger evidence for the final Debate boundary: a correct revised answer state is lost by the final picker more often than a correct last-worker state is lost by the Sequential aggregator. MAS evaluation should therefore report candidate availability and preservation in addition to final accuracy.

## 9.2 Failure is architecture-specific

The audited comparison does not imply that every MAS component is equally unreliable. Debate exposes two revised answers to a discrete final picker, creating a direct selection problem. Sequential exposes one last-worker state to its aggregator; in the audited population, harmful loss at this boundary was uncommon and beneficial recovery was measurable. Earlier machine screening also suggests that Sequential can fail earlier in the worker chain, but those counts remain less secure because automatic source-stage labels were unreliable in targeted transition strata.

The practical implication is that improvement should target the failing interface. Debate requires better preservation and selection of already-correct revised answers. Sequential may benefit more from worker-chain state tracking and error recovery than from changing the final aggregator alone.

## 9.3 More budget does not automatically repair coordination

The larger token cap increased actual tokens and latency but did not improve aggregate machine-screened Discovery or final correctness. This is consistent with an over-exploration or second-guessing mechanism: additional generations create more opportunities to revise a correct state as well as more opportunities to discover one. Because resource use is confounded with item difficulty and architecture behaviour, the current results support a descriptive claim—more budget did not rescue these systems—not a causal claim that extra computation is intrinsically harmful.

## 9.4 Fine-tuning does not support the narrow frozen-model explanation

The v3b results do not show a consistent removal of the MAS–SAS gap or of stage-level preservation loss. This weakens the narrow explanation that the observed failures occur only because the model was entirely untrained. However, v3b uses single-agent-style training data and cannot test whether architecture-conditioned MAS fine-tuning, preference optimisation for critics and aggregators, or outcome-based multi-agent training would succeed.

## 9.5 Judge validation changes the scientific conclusion

The general 200-stage calibration initially appeared strong enough to support full-trace rejudging. Performance fell sharply in the transition strata that mattered most to the causal narrative. The later dual-axis human audit showed different error directions for Discovery and Endorsement and only moderate κ. This demonstrates why an evaluator validated on ordinary final answers cannot be assumed valid for long, internally contradictory intermediate traces. Judge validation must match the intended label, stage position, and error stratum.

---

# 10. Limitations and Threats to Validity

First, the core experiments use one small open-weight model family. Frozen and v3b variants do not constitute cross-family replication. Claims should be limited to the evaluated Qwen3-4B settings until Llama/DeepSeek or Mistral-family experiments are added.

Second, each main benchmark cell contains 200 items and uses oracle evidence. This improves experimental control but limits generalisation to retrieval-augmented or full-context settings.

Third, the human audit was performed by one annotator. Hidden repeats demonstrate perfect internal consistency on 20 rows, but no independent inter-rater estimate is available.

Fourth, the human transition sample was stratified using machine labels and greedily balanced across covariates. Pool-size weighting corrects deliberate over-sampling at the stratum level, but the reported confidence intervals are approximate rather than design-exact.

Fifth, only Debate and Sequential final transitions received the full dual-axis human audit. Full-trace counts for Ensemble, Parallel Roles, and Subtask Parallel remain automatic screening estimates. Subtask outputs are partial findings and are not directly comparable with complete candidate answers.

Sixth, observed item latency is not GPU-seconds. Parallel batching and shared device execution prevent GPU consumption from being reconstructed by summing logical call durations.

Seventh, the semantic audit evaluates agreement with benchmark reference answers under a codebook. It is not an independent verification that every benchmark answer reflects real-world truth.

Finally, the stronger 72B judge improved over Mistral but failed the frozen acceptance threshold. Scaling the judge did not eliminate the need for human adjudication.

---

# 11. Conclusion

This dissertation reframes matched-budget SAS–MAS comparison as a problem of correctness flow. Multi-agent decomposition can expose a correct answer at an intermediate stage without ensuring that the final system preserves or selects it. In the human-audited final-transition population, Debate lost an endorsed correct source state at an estimated rate of 5.45%, compared with 0.59% for Sequential, while Sequential exhibited beneficial recovery that was absent from Debate. The directional result survived all prespecified treatments of uncertain labels.

The broader experiments show that a larger token cap increased latency and token use without improving aggregate machine-screened semantic outcomes. Fine-tuning with single-agent-style data did not consistently remove MAS failure. Together, these findings support a targeted conclusion: the value of additional agents depends not only on whether they generate useful information, but on whether the architecture can preserve and select that information under a fixed resource budget.

The methodological result is equally important. Automatic semantic judges were useful for screening and stratified sampling, but their errors were concentrated in exactly the transition strata required for failure-localisation claims. Human validation therefore changes the estimated transition rates and prevents misleading conclusions, including an apparent Debate beneficial transition that disappeared after unblinding.

---

# 12. Work not yet ready for the main claims

The following should remain explicit placeholders rather than being written as completed evidence:

1. Cross-family validation beyond Qwen3-4B.
2. Random or shuffled candidate-selection baselines.
3. A full independent second-annotator study.
4. Human-audited final transitions for Ensemble, Parallel Roles, and Subtask Parallel.
5. GPU-second accounting from scheduler/device telemetry.
6. Confirmatory causal claims relating truncation, wall time, or token use to correctness loss.
7. A complete bibliography and related-work synthesis.

---

# Figure and table production plan

| No. | Intended insertion | Target file | Data source | Status |
|---:|---|---|---|---|
| Fig. 1 | Research logic and evidence hierarchy | `D:/thesis/dissertation/figures/fig_01_research_logic.png` | Sections 3 and 5 | To generate |
| Fig. 2 | Final performance by experimental condition | `D:/thesis/dissertation/figures/fig_02_final_accuracy_by_condition.png` | `D:/thesis/analysis/diagnostics/*/metrics.csv` | To generate |
| Fig. 3 | Token-budget outcome/resource trade-off | `D:/thesis/dissertation/figures/fig_04_budget_outcome_resource_tradeoff.png` | `budget_pair_tests.csv`, `budget_wallclock_overall.csv` | To generate |
| Fig. 4 | Semantic oracle–final gap | `D:/thesis/dissertation/figures/fig_03_semantic_oracle_regret.png` | `D:/thesis/analysis/semantic_diagnostics/semantic_metrics.csv` | To generate |
| Fig. 5 | Resource association forest plot | `D:/thesis/dissertation/figures/fig_07_resource_associations.png` | `resource_associations.csv` | To generate |
| Fig. 6 | Human–Mistral confusion matrices | `D:/thesis/dissertation/figures/fig_05_human_mistral_confusion.png` | `agreement_summary.csv` | To generate |
| Fig. 7 | Human-audited transition rates | `D:/thesis/dissertation/figures/fig_06_human_transition_rates.png` | `weighted_transition_estimates.csv` | To generate |
| Table 1 | Experimental matrix and units | `D:/thesis/dissertation/tables/table_01_experimental_design.csv` | YAML configs and manifests | To generate |
| Table 2 | Evaluator reliability | `D:/thesis/dissertation/tables/table_02_evaluator_reliability.csv` | calibration and audit reports | To generate |
| Table 3 | Human transition estimates | `D:/thesis/dissertation/tables/table_03_human_transition_estimates.csv` | `weighted_transition_estimates.csv` | To generate |
| Table 4 | Sensitivity and limitations | `D:/thesis/dissertation/tables/table_04_sensitivity.csv` | final transition workbook | To generate |

## Principal reproducibility files

- Full semantic screening report: `D:/thesis/analysis/semantic_diagnostics/REPORT.md`
- Full semantic metrics: `D:/thesis/analysis/semantic_diagnostics/semantic_metrics.csv`
- Per-item semantic data: `D:/thesis/analysis/semantic_diagnostics/per_item_semantic.jsonl`
- Budget-paired tests: `D:/thesis/analysis/semantic_diagnostics/budget_pair_tests.csv`
- Resource associations: `D:/thesis/analysis/semantic_diagnostics/resource_associations.csv`
- Human unblind report: `D:/thesis/analysis/final_transition_endorsement_audit/UNBLIND_REPORT.md`
- Human stage-level data: `D:/thesis/analysis/final_transition_endorsement_audit/unblind/stage_level_unblinded_420.csv`
- Human item-level data: `D:/thesis/analysis/final_transition_endorsement_audit/unblind/item_level_unblinded_160.csv`
- Weighted human transitions: `D:/thesis/analysis/final_transition_endorsement_audit/unblind/weighted_transition_estimates.csv`
- Final audit workbook: `D:/thesis/outputs/final_transition_endorsement_audit/final_transition_unblind_analysis.xlsx`
- Judge sensitivity audit: `D:/thesis/analysis/semantic_transition_sensitivity/AUDIT_REPORT.md`
- Lexical robustness report: `D:/thesis/analysis/diagnostics/REPORT.md`
