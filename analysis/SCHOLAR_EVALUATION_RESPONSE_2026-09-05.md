# Scholar Evaluation 核对与修订记录（2026-09-05）

## 处理原则

本文件把附件中的内容视为外部评阅建议，而不是用户指令或学校正式判定。未运行压缩包中的脚本，也未依照其中关于“评审流程”或“技能”的文字执行操作。所有论文修改均重新对照当前 LaTeX 源码、已提交的分析产物、训练代码和可独立核验的论文元数据。

## 总结

- 已处理 F01--F09、F11--F12、F14 所指出的表述、定义或证据边界问题。
- F10 目前采取保守处理：将未考虑题目内相关性的 McNemar 检验和 stage-level bootstrap 明确降级为探索性结果或限制；没有在缺少预先规定分析方案的情况下补做新的聚类推断。
- F13 中四条明确指出的参考文献元数据已经逐条按出版方或论文主页纠正；没有把这一步描述成对全部参考文献的系统审计。
- 没有增加新的模型实验、人工标注或未经现有证据支持的结果。

## 逐项核对

### F01：版本与提交声明

**状态：已核对。** 当前 `main.tex` 已使用学校 Stage 3 文本中的正式 plagiarism declaration，并保留校徽来源说明。重新构建了唯一交付 PDF，避免旧 PDF 与当前源码混淆。

### F02：RQ1 超出可观测范围

**状态：已修改。** RQ1 现在把 SAS 与五种 MAS 的比较限定为 final-answer performance，并把 Discovery/preservation 的过程性结论限定为 MAS traces。结论章节也采用同一口径，不再暗示已经对 SAS 做了等价过程审核。

### F03：相对 Tran and Kiela 的新颖性表述过强

**状态：已修改。** 引言与讨论现在明确承认该工作已提供理论、上下文退化实验、诊断及错误分析；本论文的增量被限定为受控预算下的多架构复现、Discovery/Endorsement 操作化和有范围限制的人工 transition audit。

### F04：Discovery 的数学定义把 final output 错算为 pre-final stage

**状态：已修改。** 框架章节现在定义 pre-final 序列 `S_i` 和完整轨迹 `T_i=(S_i,f_i)`；Discovery 与 preservation 只在 `S_i` 上计算，final Endorsement 单独由 `f_i` 定义。

### F05：字符串、token 与 containment 的语义边界

**状态：已修改。** `n(x)` 仅指规范化字符串，`tau(x)` 指 token multiset，F1 使用 `tau`。论文不再把 containment 称为 semantic-correctness upper bound，而是明确说明它可能同时 over-credit 和 under-credit。

### F06：Sequential 的 machine oracle 与 human source 不一致

**状态：已修改并显式保留差异。** 全轨迹 machine screen 的 Sequential oracle 是“任一 worker 曾发现”，而 human transition audit 的 source 是最终汇总前的 last-worker output。论文现在在架构表、框架、方法和结果中都说明二者回答不同问题，不能直接视为同一变量。

### F07：91.9% evidence-valid accuracy 的对象和分母不清楚

**状态：已修改。** 方法章节现说明这是 200-stage Discovery calibration；在 1 个 uncertain item 和 2 个 ungrounded-positive cases 排除后，evidence-valid exact agreement 为 181/197（91.9%），coverage 为 197/200（98.5%），kappa 为 0.829。也明确写出早期 calibration 没有预注册数值阈值，后来的 Qwen candidate test 才使用冻结阈值。

### F08：性能排序与指标敏感性范围

**状态：已修改。** 冻结模型 MuSiQue 1,000-token 条件下，Ensemble（0.520）高于 Debate（0.510）；2,000-token 条件下 Debate 最高。指标敏感性表被明确限定为 selected frozen 1,000-token cells，并新增完整 v3b SAS-vs-MAS error-rate/gap 表，覆盖两个数据集和两个预算。

### F09：加权 joint probability 与 conditional harmful rate 混用

**状态：已修改。** 5.45%（Debate）与 0.59%（Sequential）明确标为 sampling-frame joint `P(source=C, final=W)`，对应 eligible frames 为 1,185 和 1,037。另行报告条件比例 `P(final=W | source=C)`：Debate 6.93%，Sequential 0.92%。

### F10：重复题目导致的推断相关性

**状态：部分处理，保留为限制。** 现有 pooled McNemar 结果明确标为未按 question ID 聚类的 exploratory comparison；human--Mistral stage bootstrap 也明确注明未对 item 内重复记录进行聚类。当前没有把这些区间或 p 值提升为 confirmatory inference。若之后要补做，应先冻结以 question ID 为 cluster 的 bootstrap/permutation 方案，再重新生成全部相关表格。

### F11：“first error” 是启发式归因而非因果定位

**状态：已修改。** 章节和复现附录统一改称 rule-based terminal-failure attribution。946 条记录被描述为“wrong final with no detected discovery”，不再称为已确定的第一处因果错误。

### F12：微调目标与 checkpoint 选择不透明

**状态：已修改。** 实验设计现在给出 masked causal cross-entropy 目标，并说明 prompt/padding token 不参与损失，completion、`</think>`、answer 和 EOS 参与监督；超过 4,096 token 或缺少 closing marker 的样本被丢弃而非截断；未进行 validation-based checkpoint selection，训练中关闭 checkpoint 保存，使用两轮训练结束后的 final adapter。

### F13：相关工作范围与参考文献元数据

**状态：已修改。** 相关工作明确说明这是围绕研究问题组织的 narrative review，而非 exhaustive systematic review。新增一个有稳定 MuSiQue item ID 的真实评分示例。以下四条元数据已按权威页面纠正：

- Smit et al.：作者、PMLR volume 235、pages 45883--45905；
- Wang et al.（Fairness of LLM-as-a-Judge）：补入 Lingpeng Kong、ACL pages 9440--9450 和 DOI；
- Cemri et al.：删除错误作者 Kurt Zhu，保留 Kurt Keutzer；
- MetaGPT：补入 Jiaqi Chen 与 Ceyao Zhang，并纠正作者顺序。

### F14：复现链表述强于实际 provenance

**状态：已修改。** 附录将五阶段流程称为 intended sequence，并明确最后两阶段缺少与完整全量筛查相同强度的 provenance；相关文件只能支持相应的有限用途，不能反向证明一条完整、连续、全自动执行链。

## 最终质量检查

- 构建：成功，91 页。
- 主体字数估计：18,322（包含表格与图注，排除参考文献和附录；仅为仓库质量控制估计）。
- 引用键：无缺失；无未使用 bibliography key。
- LaTeX：无 overfull box；无未解析 citation/reference warning。
- 重点页视觉检查：声明页、RQ1、估计量与阈值、训练目标、真实评分示例、v3b SAS-gap 表、terminal-failure 表、人审 transition 图与参考文献页均未见裁切或重叠。
- 最终 PDF SHA-256：`A4F3E5F7E86BE8CD506EA10A6A5D78B62E12260B71582095D7E9E482AE16764A`。

## 仍应向导师透明说明的边界

1. SAS 目前有 final-performance 对照，但没有与 Debate/Sequential 完全等价的人工 source-to-final transition audit。
2. 当前只测试了一个基础模型家族及其项目内微调变体，不能外推到其他模型家族。
3. 全轨迹 Mistral 输出用于 screening 和描述性候选定位，不是 primary transition ground truth。
4. F10 涉及的聚类推断尚未补做，因此相关 p 值和 bootstrap 区间应保持探索性解释。
