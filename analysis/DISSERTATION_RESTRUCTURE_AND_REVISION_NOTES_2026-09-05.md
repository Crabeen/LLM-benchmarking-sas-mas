# Dissertation 重构与修改意见（依据 2026-08-28 导师会议）

## 1. 本次重构目标

导师认为当前实验量、分析 pipeline 和研究问题基本成立，主要问题是论文没有把研究推进过程呈现为一条容易跟随的论证链。原稿把 final benchmark、machine screening、budget、human audit 和 transition results 放在同一个 Results chapter 中，导致读者需要在不同证据等级之间来回切换。

本次顺序调整采用以下主线：

> matched-budget benchmark → fine-tuning attempt → budget intervention → why does failure occur? → machine-screened trace analysis → human validation and transition inference → discussion

重构原则：

- 优先移动和拆分已有内容，不改变已经冻结的数字；
- 将最终性能、机器筛查和人工审计分成不同结果章节；
- 每章只承担一个主要证据任务；
- 未完成的 SAS process comparison 和 cross-family experiment 不写成已完成结果；
- 所有核心术语必须在首次使用时简要定义，在方法章节再完整定义。

---

## 2. 原顺序与新顺序

### 原顺序

1. Introduction
2. Related Work
3. Research Questions and Analytical Framework
4. Experimental Design
5. Evaluation and Human Audit Methodology
6. Results
7. Discussion
8. Limitations and Threats to Validity
9. Conclusion

原 Chapter 6 同时包含：

- final-answer benchmark；
- semantic discovery/oracle coverage；
- machine-screened failure localisation；
- human audit reliability；
- human transition estimates；
- budget effects；
- resource/truncation associations。

### 新顺序

1. Introduction
2. Related Work
3. Research Questions and Analytical Framework
4. Experimental Design
5. Evaluation and Human Audit Methodology
6. **Benchmark, Fine-tuning, and Budget Results**
7. **Machine-Screened Failure Analysis**
8. **Human Audit and Transition Results**
9. Discussion
10. Limitations and Threats to Validity
11. Conclusion

这一顺序先建立“发生了什么”，再回答“为什么”，最后说明最可信的人审证据如何修正机器筛查结果。

---

## 3. 章节移动映射

| 原位置 | 新位置 | 修改理由 |
|---|---|---|
| 6.1 Final-answer benchmark | Chapter 6 开头 | 首先建立 SAS/MAS 的 outcome pattern 和 dataset dependence。 |
| 原 6.1 中 frozen/v3b 比较 | Chapter 6 的 fine-tuning subsection | 将 fine-tuning 明确写成尝试改善初始结果的 intervention。 |
| 6.5 Budget effects | Chapter 6 后半 | 在进入机制分析前说明增加预算未解决 outcome gap。 |
| 6.2 Semantic discovery/oracle/regret | Chapter 7 开头 | 从 final outcome 自然转入“为什么失败”的 machine-screened explanation。 |
| 6.3 Machine-screened failure localisation | Chapter 7 中部 | 与 semantic screening 同属广度证据，不与 human ground truth 混写。 |
| 6.7 Resource and truncation associations | Chapter 7 末尾 | 这些关联依赖 machine labels，且属于诊断性而非因果性结果。 |
| 6.4 Human audit reliability | Chapter 8 开头 | 在给出人工 transition rates 前先证明 annotation completeness/repeatability，并量化 judge disagreement。 |
| 6.5 Human transition estimates | Chapter 8 主体 | 将论文最强的人工证据单独成章。 |
| 6.6 Uncertainty sensitivity | Chapter 8 末尾 | 紧接 primary human result，说明结论是否依赖 U 的处理。 |
| 6.8 Answers to RQs | 删除重复段落，由 Conclusion 统一回答 | 避免 Results 和 Conclusion 重复回答研究问题。 |

---

## 4. 新章节的论证职责

### Chapter 6 — Benchmark, Fine-tuning, and Budget Results

只回答三件事：

1. SAS 与五种 MAS 在最终答案上的表现如何；
2. frozen 与 `v3b` 的比较是否改变总体排序；
3. 从 1,000 增加到 2,000 thinking tokens 是否改善结果，以及付出了多少 latency/token cost。

章节末尾应明确指出：final scores 和 budget results 只能证明 outcome，不能区分 failure to discover 与 failure to preserve，因此下一章进入 trace analysis。

### Chapter 7 — Machine-Screened Failure Analysis

只承担广度诊断：

- semantic Discovery；
- candidate-oracle accuracy；
- final semantic accuracy；
- aggregation regret；
- first-error localisation；
- Debate/Sequential 的机器转移筛查；
- wall time、thinking tokens、truncation 与语义结果的诊断性关联。

每个表或图必须标记 `machine-screened`，不得称为 human-validated prevalence。

章节末尾应说明机器筛查揭示了候选机制，但 targeted cases 上的 judge reliability 不足，因此需要 Chapter 8 的人审。

### Chapter 8 — Human Audit and Transition Results

先报告 audit integrity，再报告 substantive results：

1. 160 audited item-configurations、400 non-repeat stage records、20 hidden repeats；
2. Discovery/Endorsement 的 human–Mistral agreement；
3. 15 item-level audit fields 的三组描述表；
4. Debate 与 Sequential 的 raw transition composition；
5. stratum-weighted harmful/beneficial rates；
6. Discovery→final-Endorsement secondary diagnostic；
7. U-as-W、exclude-U、U-as-C sensitivity。

如果 SAS process analysis 在提交前完成，应在本章新增独立小节，并明确其证据等级：

- 自动 SAS pipeline 结果属于 machine-screened comparison；
- 如另有 SAS human validation，再报告 human-audited results；
- 在没有同构 picker/aggregator 的情况下，SAS 应使用 pre-final Discovery → final Endorsement，而不是虚构 aggregation boundary。

---

## 5. 必须同步完成的表达修改

### 5.1 首次使用前定义架构

Introduction 首次出现时应写明：

> The five evaluated MAS architectures are Sequential, Subtask Parallel, Parallel Roles, Debate, and Ensemble. Debate and Sequential are two members of this set and are examined in greater human-audited depth because they expose interpretable final coordination boundaries.

Related Work 或 Framework 前部加入五种架构总览表，至少包括：

- component roles；
- information flow；
- candidate/source state；
- final decision component；
- human-audit scope。

### 5.2 明确 multi-hop 与 multi-step

- `multi-hop`：问题需要连接多个事实/关系，是 task property；
- `multi-step`：系统通过多个连续计算步骤求解，是 process property。

建议用一个 MuSiQue question 给出两者差异，避免交替用作同义词。

### 5.3 给出 SAS/MAS working definition

定义必须能解释 Ensemble 为什么属于本文的 MAS。建议口径：

> In this dissertation, an MAS is a computational graph containing multiple separately invoked role instances that maintain distinct local generation states and whose outputs are exchanged, selected, or aggregated by an explicit coordination procedure. The SAS baseline uses one solver invocation and one continuous local state, even when its single trajectory contains multiple reasoning steps.

这是本项目的 operational definition，不需要声称是整个领域唯一正确的定义。

### 5.4 统一数据单位

全文固定使用：

- `benchmark question`：`dataset + original_id`；
- `experimental condition`：dataset × model × system × budget；
- `item-configuration`：某个 question 在一个 condition 下的一次 run；
- `trace`：一次 run 的完整可观察输出；
- `stage record`：trace 中一个有明确 role/position 的输出；
- `repeat`：同一 stage 的 blinded duplicate，仅用于 intra-rater consistency。

将 “160 unique items” 改成：

> 160 distinct audited item-configurations drawn from 160 distinct benchmark question identifiers.

### 5.5 重命名 judge reliability 术语

删除含糊的 `evidence-valid accuracy`。根据实际统计量分别写：

- `human–Mistral exact agreement`；
- `Mistral accuracy against human labels`；
- `Cohen's kappa`；
- `coverage`；
- false-positive/false-negative direction。

### 5.6 解释最终答案评分

Evaluation chapter 需要补齐：

- gold answer 和 aliases 示例；
- model output 示例；
- exact match normalization；
- token precision、recall、F1 公式；
- 为什么 substring containment 会误判“先提及后拒绝”；
- previous work 使用的 judge/metric；
- lexical、LLM judge、human labels 的优缺点和证据角色。

---

## 6. 图表顺序和 Figure 3.1

原 Figure 3.1 将 lexical scoring、machine screening 和 human audit 画成单一路径，容易让读者误以为前一层结果只是后一层的中间输入。

建议重画为三个 evidence layers：

```text
Recorded benchmark runs
├── deterministic final-output evaluation → benchmark results
├── full-trace Mistral screening → breadth/failure-location results
└── targeted blind human audit ↔ validation of selected machine labels
                                  → primary human transition estimates
```

其中 human audit 既检查 machine labels，也产生独立的 primary evidence；它不是 machine screening 的简单后处理步骤。

重排后图表出现顺序建议为：

1. research design/data hierarchy；
2. final benchmark performance；
3. matched budget outcome/resource trade-off；
4. semantic oracle–final gap；
5. machine-screened failure locations/resource associations；
6. human–Mistral agreement；
7. human-audited weighted transitions。

---

## 7. 15 个字段在新结构中的位置

15 个字段应只在 Chapter 5 定义，在 Chapter 8 报告：

- 4 truncation descriptors；
- 4 human semantic states；
- 2 human derived transitions；
- 4 Mistral semantic states；
- 1 machine derived transition。

必须写成 `15 named item-level audit fields of mixed type`，不能写成 `15 independent binary error labels`。

Chapter 8 建议使用三张表：

1. trace integrity/truncation metadata；
2. human states and transitions；
3. machine fields and human–machine validation。

同时保留 raw audit composition 与 population-weighted estimates 的区别。

---

## 8. 不应因重排而扩大结论

重构只改善论证顺序，不会自动弥补证据缺口。以下内容在完成前必须继续作为 limitation/future work：

- SAS 的同口径 process-level machine analysis；
- SAS 的独立 human validation（可选增强）；
- Qwen3-4B 之外的 cross-family robustness check；
- 第二名独立人工标注者；
- Ensemble、Parallel Roles、Subtask Parallel 的完整人审；
- truncation、wall time 或 token use 的因果结论。

尤其不能因为将 “why” 单独成章，就把 machine-screened patterns 改写成已经由人工确认的机制。

---

## 9. 已实施的文件级调整

- `dissertation/latex/main.tex`
  - 原单一 Results chapter 已拆成三个连续结果章节。
- `dissertation/latex/chapters/06_results.tex`
  - 保留为旧版组合结果文件，退出 `main.tex` 的正式编译顺序，便于核对移动前内容。
- `dissertation/latex/chapters/06_benchmark_budget_results.tex`
  - final benchmark、fine-tuning interpretation、budget results。
- `dissertation/latex/chapters/07_machine_screening_results.tex`
  - semantic breadth screen、failure localisation、resource/truncation diagnostics。
- `dissertation/latex/chapters/08_human_audit_results.tex`
  - audit reliability、human transitions、uncertainty sensitivity。
- `dissertation/latex/chapters/01_introduction.tex`
  - 更新 dissertation structure 段落和新章节交叉引用。
- `dissertation/DISSERTATION_CURRENT_DRAFT.md`
  - 同步采用新的 Chapter 6–11 顺序。

---

## 10. 后续修改优先级

### P0：结构完成后立即做

- [ ] 对 SAS 运行同一 Mistral process pipeline，并加入 Chapter 7/8 的正确证据位置。
- [ ] 在 Chapter 8 增加全部 15 fields 的三组定量表。
- [ ] 修复 `final_truncated` 的缺失值被转换为 false 的问题。

### P1：提高可读性

- [ ] 在 Chapter 2/3 提前加入五种 MAS 总览表和同一示例问题下的架构图。
- [ ] 重画 Figure 3.1 为 evidence-layer diagram。
- [ ] 全文统一 item/configuration/stage/repeat 和 Discovery/Endorsement。
- [ ] 补充 benchmark scoring 示例与公式。

### P2：提交前验证

- [ ] 重新编译 PDF，检查 chapter numbering、目录、图表编号和所有 `\Cref`。
- [ ] 检查每个数字是否标明 evidence level：deterministic、machine-screened 或 human-audited。
- [ ] 检查 Discussion/Conclusion 是否只使用前文已经报告的结果。
- [ ] 根据导师书面 comments 再做一次逐项对照。
