# 2026-08-28 会议整理：Dissertation 建议

## 转写说明

- 音频：`D:/thesis/meet 2026-08-28 at 09h30m53s.wav`
- 时长：52 分 56 秒
- 本文件是从自动语音转写中提取的 **dissertation 相关建议整理稿**，不是逐字逐句的会议纪要。
- 时间戳对应原始音频，便于回听核对。
- 自动识别中的技术名词已按项目语境规范化，例如 Mistral、Qwen、SAS、MAS、MuSiQue 和 Tran paper。个别专名仍建议结合导师随后发送的书面批注确认。

---

## 1. 导师对当前论文的总体判断

导师的总体评价是积极的：分析 pipeline 和已经完成的工作量都不错，研究问题也合理，论文已经开始成形。当前主要问题不是没有工作，而是需要补最后一组关键对比，并把复杂的实验过程写得更清楚、更线性，让第二阅卷人能够快速理解。

对应时间：`00:01:44–00:02:24`

导师还表示，当前研究按清楚的逻辑重组并确认分析正确后，整体结构具备进一步整理成会议论文的潜力。问题在于这条研究演进逻辑目前没有充分体现在报告中。

对应时间：`00:31:03–00:34:44`

---

## 2. 最重要的新增结果：把同一失败分析 pipeline 应用于 SAS

### 2.1 导师真正希望回答的问题

当前已经知道，在相同或匹配的推理预算下，SAS 在不少条件中比多数 MAS 架构具有更高的最终准确率。论文进一步提出“为什么”。导师认为，回答这个问题不能只分析 MAS 内部在哪里失败，还需要让 SAS 经过同一套过程分析，以判断某类错误是否确实更常发生在 MAS 中。

导师给出的核心例子是：

> MAS 是否比 SAS 更容易先生成正确答案，随后又放弃、拒绝或没有选择该答案？

现有 pipeline 理论上能够计算这个现象，但目前缺少 SAS 与 MAS 的同口径结果，因此还不能完成这一机制比较。

对应时间：`00:02:20–00:03:34`

### 2.2 最低要求与可选增强

会议中的优先级非常明确：

1. **最低必须补充：**对 SAS 运行现有的 Mistral 自动分析 pipeline，得到能与 MAS 比较的过程指标。
2. **如果时间允许：**再对 SAS 做人工验证。
3. **并非最低要求：**不需要为了 SAS 重做与现有 MAS 同等规模的人类审计，前提是自动 pipeline 已经在现有工作中得到过人工验证，并且论文诚实说明 SAS 结果属于 machine-screened evidence。

对应时间：`00:04:46–00:05:40`

这意味着论文的证据层级可以写成：

- 最终 benchmark：SAS 与五种 MAS 的完整比较；
- 过程广度筛查：同一自动 pipeline 覆盖 SAS 和 MAS；
- 人工深度验证：主要验证 pipeline 和选定 MAS 边界；
- SAS 人工审计：属于时间允许时的增强，不应在尚未完成时写成已有证据。

### 2.3 推荐的 SAS 对比指标

根据导师问题和现有 Discovery/Endorsement 口径，至少应报告：

- pre-final trace 是否发现正确答案；
- final answer 是否认可/选择正确答案；
- 已发现正确答案但最终未选择的比例；
- 从错误或未发现状态恢复为正确 final answer 的比例；
- 上述指标在 SAS 和各 MAS 架构中的差异；
- 按 dataset、model variant 和 budget 分层，避免把“SAS 总是优于 MAS”写成普遍事实。

这里需要在方法章节明确：SAS 没有 picker/aggregator，因此跨架构对比应使用架构无关的 `pre-final Discovery → final Endorsement`；Debate/Sequential 的 `source Endorsement → final Endorsement` 可继续作为架构特定的协调边界分析。

---

## 3. 建议增加至少一个其他 LLM 的基本准确率对照

导师建议，如果尚未完成，可用至少一个额外 LLM 运行基本 benchmark accuracy checks，以证明观察到的 SAS/MAS 结果不是当前特定 Qwen 版本独有的现象。

导师没有要求为第二个模型重新进行昂贵的人类审计：

- 基本最终准确率对照即可显著增强说服力；
- human analysis 保持在当前主要 Qwen 模型上是合理的；
- 如果时间有限，优先级仍低于 SAS 过程对比。

对应时间：`00:04:15–00:05:24`

论文中应把这一扩展称为 robustness/generalisation check，而不是新的完整主实验。

---

## 4. 所有术语必须在首次使用前定义

导师反复强调，复杂实验最容易失分的地方是读者在遇到术语时尚不知道它的含义。解决方法不是只在后面集中定义一次，而是：

- 在第一次出现时给出一句简短定义；
- 在正式 methodology/framework 位置再给完整定义；
- 必要时重复简短定义，以保证章节可以线性阅读。

对应时间：`00:05:42–00:08:00`

### 4.1 Sequential、Debate 和“五种 MAS”之间的关系

导师指出，Introduction 和 research questions 很早就使用 Sequential 和 Debate，但当时尚未说明：

- 它们是五种 MAS 中的两种，还是五种架构的上位类别；
- 为什么人类分析只突出这两个架构；
- 其他三种架构在 broad results 中是否仍被分析。

修改建议：

- 首次出现时写明五种 MAS 的完整列表；
- 明确 “Debate and Sequential are two of the five evaluated MAS architectures”；
- broad benchmark/screening 结果尽量完整提及五种架构；
- 只有在进入 human-audited final-boundary analysis 时，才明确缩小到 Debate 和 Sequential，并解释其 source-to-final boundary 更清楚。

如果只有 Debate/Sequential 经过人审，不要让“all five results”被误读为五种架构都完成了同等程度的人类标注。

对应时间：`00:07:02–00:09:13`

### 4.2 Multi-hop 与 multi-step

导师最初认为论文在交替使用 multi-hop 和 multi-step。学生说明二者意图不同：

- multi-hop：问题本身的属性，需要连接多个事实或关系；
- multi-step：模型/架构采用多个推理步骤的求解过程。

导师接受二者可以不同，但要求论文明确区分，而不是期待读者自己推断。建议给一个 MuSiQue 问题实例，展示为什么它是 multi-hop，以及系统如何用 multi-step process 解答。

对应时间：`00:09:16–00:12:29`

### 4.3 SAS 与 MAS 的 working definition

导师认为领域本身并没有完全统一的 SAS/MAS 边界，尤其 Ensemble 很容易被描述成“一次 prompt 内生成多个候选再选择”的单智能体过程。因此论文必须给出本项目自己的 working definition，并说明：

- 什么条件使一个 architecture 被归为 MAS；
- 为什么五种架构满足该定义；
- 为什么 SAS 不满足；
- 面对一个新的 architecture 时，读者能否根据这条规则判断它属于 SAS 还是 MAS。

不需要非常数学化，但必须稳定、可操作。可以从独立模型调用/角色状态、信息可见性、跨调用中间结果交换、候选的独立生成和显式协调组件等方面定义。

对应时间：`00:12:34–00:16:01`

---

## 5. 更早、更直观地介绍五种架构

### 5.1 增加同一示例问题下的架构流程图

导师建议使用同一个 benchmark question 或一个简化示例，画并排流程图，说明 SAS、Sequential、Debate，以及必要时 Ensemble 等架构的 reasoning flow 有何不同。

图中可以使用很短的代表性输出，而不是粘贴完整模型 trace。例如：

- SAS：完整上下文 → 单一 reasoning state → final answer；
- Sequential：planner → worker 1 → accumulated state → worker 2 → aggregator；
- Debate：proposal A/B → cross-exposure → revision A/B → picker；
- Ensemble：independent candidates → aggregator。

这些例子只用于说明架构行为，不作为结果证据。

对应时间：`00:16:01–00:17:21`

### 5.2 将架构总览提前

当前详细架构说明到原 Section 4.4 才出现，但架构名在 Chapters/Sections 1–3 已多次使用。导师建议：

- 如果引用关系合适，将完整架构说明移到 Related Work/Framework 更早的位置；或
- 在前文加入一张五种架构总览表，并保留后文的实现细节。

这张表应成为统一的 “source of truth”，至少包含：架构名称、主要角色/组件、信息流、候选结构、最终决策组件和本文分析边界。

对应时间：`00:17:34–00:18:46`

---

## 6. 重画或删除当前 Figure 3.1

导师认为现有 Figure 3.1 容易让读者误解为：benchmark output 依次经过 lexical scoring → machine screening → human audit，最后只产生一个统一结果。

实际研究结构更接近三层并行/递进证据：

1. benchmark accuracy 本身产生并报告结果；
2. machine screening 对 trace 进行广度分析并产生结果；
3. human audit 检查机器标签并支撑关键转移结论。

Human audit 不是把 machine output 再加工成唯一 final output；它同时承担验证和独立证据作用。导师认为最简单的修复是删除误导性流程图，也可以重画为三个 evidence layers，并清楚标出它们各自的输出和相互比较关系。

对应时间：`00:19:04–00:21:10`

此外，学生也提到多张图的可见性和可视化仍需改进。最终检查应包括字体、图例、颜色、坐标和打印可读性。

---

## 7. 不要使用含义不清的 “evidence-valid accuracy”

论文中约 91% 的 “evidence-valid accuracy” 让导师误以为，这是在衡量模型答案是否有外部证据支持。学生实际想表达的是 Mistral 与人工标签之间的准确率/一致率。

建议：

- 删除或重命名 “evidence-valid accuracy”；
- 如果指总体相符程度，写 `human–Mistral exact agreement`；
- 如果指以 human label 为 reference 的二元准确率，明确写 `Mistral accuracy against human labels`；
- 同时报告 denominator、coverage、Cohen's kappa、false-positive/false-negative direction；
- 清楚解释人工验证为何影响 Mistral 是否能推广到全量 trace screening。

对应时间：`00:21:15–00:23:46`

---

## 8. 必须详细解释“答案正确率”如何计算

导师指出，语言模型和 benchmark 的输出都是字符串，“正确”并不是天然明确的。论文必须展示从 gold answers 到 model outputs 的评分过程。

### 8.1 需要补充的内容

- 两个 benchmark 的 gold answer/aliases 长什么样；
- 模型输出通常是短语、句子还是段落；
- normalization 具体包括什么：大小写、标点、冠词、空格、aliases 等；
- 哪些输出会被 exact match/F1 判为正确；
- 给至少一个正确匹配、一个合法改写和一个错误匹配的例子；
- 说明为什么简单 substring containment 可能把“提到正确答案但随后拒绝它”的输出误判为正确；
- 尽量遵循 benchmark 或相关工作的标准评分流程，并说明任何偏离。

对应时间：`00:24:00–00:27:47`

### 8.2 区分 accuracy metrics 与其他 trace metrics

导师建议明确列出哪些指标真正回答“最终输出是否正确”，哪些指标分析 reasoning trace 或资源使用。对于 accuracy metrics：

- 逐项定义 lexical exact match、token F1、LLM-as-a-judge 和 human judgement；
- 给出 F1 等公式；
- 写明每种指标的输入、输出、阈值和 abstention/uncertain 处理；
- 说明 Tran paper 或其他相关工作使用哪一种指标；
- 如果 previous work 使用 LLM-as-a-judge，应把它作为可比基线，同时解释为什么本文还补充 hard-coded lexical metrics 和 human audit；
- 比较各种方法的优缺点，而不是让“gold-standard accuracy”在章节间无说明地改变。

对应时间：`00:28:04–00:30:37`

### 8.3 解释证据标准为何随研究阶段变化

学生提到：早期 fine-tuning/benchmark 实验主要使用 LLM judge，后期为了研究失败机制才引入 human ground truth。导师认为这并非问题，只要论文诚实呈现研究进展，不必假装所有实验和指标从一开始就一次性设计完成。

建议明确写出：

- 早期目标是复现/比较最终性能，因此采用与 previous work 可比的自动指标；
- 后期目标转向精确定位稀有状态转移，因而自动 judge 的可靠性不够，需要 targeted human audit；
- human labels supersede machine labels only for相应的关键 transition claims，而不是替代所有 benchmark 指标。

对应时间：`00:30:24–00:31:42`

---

## 9. 按研究实际演进重组论文

导师建议用一条清楚的因果问题链组织报告：

1. **Reproduce the initial outcome:** 在 matched compute budgets 下比较 SAS 与 MAS，复现/检验 Tran paper 的现象；
2. **Attempt improvement:** 做 fine-tuning，检查能否改善 MAS；结果没有观察到预期提升；
3. **Budget analysis:** 增加 MAS budget 后性能不升反降；
4. **Ask why:** 进入 trace-level failure analysis；
5. **Scale the diagnosis:** 用 Mistral judge 对全量或大规模 traces 筛查；
6. **Validate the diagnosis:** 用 human audit 检查自动 judge，并以人工标签支撑关键转移；
7. **Compare with SAS:** 判断相关错误是否确实更常发生在 MAS。

这个结构解释了为什么每一步实验会自然引出下一步，也更像一篇可发表论文的论证顺序。

对应时间：`00:31:03–00:34:10`

### 9.1 可以偏离课程推荐模板

导师明确表示，不必为了遵循通用 dissertation template 而牺牲项目自身的逻辑。可以把 Results 拆成多个章节，例如：

- Benchmark and Fine-tuning Results；
- Budget and Resource Results；
- Failure-Trace Screening Results；
- Human Audit and SAS Comparison。

大部分工作是移动和重组已有文字，不一定要新增大量篇幅。

对应时间：`00:34:11–00:34:44`

---

## 10. 写作层面的统一要求

导师强调 scientific writing 中不要为了文风变化而频繁换同义词。术语重复虽然显得“无聊”，但会更严谨、更容易解释。

全文应统一检查：

- `multi-hop` 与 `multi-step` 是否各自只有一个固定含义；
- `SAS`、`single-agent system` 是否一致；
- `MAS architecture` 是否始终指同一个分类范围；
- `item`、`configuration`、`trace`、`stage`、`repeat` 的层级；
- `accuracy`、`agreement`、`Discovery`、`Endorsement` 是否被混用；
- 每个研究结果究竟来自 lexical benchmark、machine screen 还是 human audit。

对应时间：`00:09:16–00:10:30`

---

## 11. 行政和提交事项

这些不是论文章节内容，但会议中给出了明确行动项：

### Ethics form

- 即使项目只由学生本人生成/标注数据、是否严格需要伦理审批并不完全明确，导师仍建议为稳妥起见填写表格；
- 提交后会直接发给导师审批；
- 提交完成后通知导师，他可以尽快批准。

对应时间：`00:00:41–00:01:44`

### 提交前反馈与 deadline

- 学生计划约 9 月 7–10 日把完整稿再次发给导师；
- 导师表示届时只能提供少量反馈，但可以在最终提交前再看一次；
- 会议中导师日历显示 deadline 是 9 月 16 日，可能为 15:00；
- 必须以 Blackboard 的正式时间为准并自行再次确认。

对应时间：`00:43:28–00:44:28`

导师还表示会在会议后发送更详细的书面 comments；收到后应与本清单合并，而不是只按本次自动转写修改。

对应时间：`00:01:44–00:02:03`、`00:52:18–00:52:24`

---

## 12. 建议执行顺序

### P0：本周先做

- [ ] 对 SAS 运行与 MAS 相同的 Mistral failure-analysis pipeline。
- [ ] 产出 SAS/MAS 同口径的 Discovery→final Endorsement 结果。
- [ ] 为 presentation 准备可以使用的最简 SAS 对比数字。
- [ ] 填写并提交 ethics form，随后通知导师。

### P1：重组论文

- [ ] 按“复现 → fine-tuning → budget → why → machine screen → human audit → SAS comparison”重组论证。
- [ ] 在前文加入五种 MAS 的总览表或流程图。
- [ ] 重画或删除误导性的 Figure 3.1。
- [ ] 将 Results 拆成更容易跟随的多个章节/大节。

### P2：方法与术语

- [ ] 首次出现时定义 Sequential、Debate、SAS、MAS、Discovery 和 Endorsement。
- [ ] 写出 SAS/MAS working definition。
- [ ] 区分 multi-hop problem 与 multi-step process，并加入示例。
- [ ] 将 “evidence-valid accuracy” 改成准确的一致率/准确率术语。
- [ ] 完整说明 lexical EM、F1、LLM judge 和 human audit 的计算与证据角色。

### P3：时间允许时增强

- [ ] 为 SAS 自动分析抽样做人工复核。
- [ ] 用至少一个额外 LLM 做基本 final-accuracy robustness check。
- [ ] 全面改善图表可读性。

---

## 13. 一句话概括导师希望看到的 dissertation

这篇论文应当呈现一条清楚的证据链：**首先确认在受控预算下 SAS 与 MAS 的性能差异，然后测试 fine-tuning 和额外预算能否解决它，接着通过 trace analysis 判断 MAS 是否更容易发现后又丢失正确答案，最后用 SAS 对照和 human audit 验证这一解释，而不是仅仅罗列多个互相分离的实验。**
