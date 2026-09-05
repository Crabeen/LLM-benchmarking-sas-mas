# 2026-08-28 会议整理：Presentation 建议

## 转写说明

- 音频：`D:/thesis/meet 2026-08-28 at 09h30m53s.wav`
- 时长：52 分 56 秒
- 本文件只整理与最终 presentation、现场形式和问答准备有关的内容。
- 时间戳对应原始音频，便于回听核对。

---

## 1. 时间要求

导师的明确建议是：

- presentation **绝对不要超过 10 分钟**；
- 准备时以 **约 8 分钟**为目标，因为现场通常会比排练略微超时；
- 这是一个很短的 presentation，不可能展示 dissertation 中的全部工作。

对应时间：`00:35:01–00:35:25`

实际准备建议：把正常语速的完整排练控制在 7:30–8:00，给换页、停顿和临场补充预留空间。

---

## 2. 核心目标不是讲完全部细节，而是让第二阅卷人理解整个项目

导师不建议只选一个结果讲得非常深。presentation 应给第二阅卷人一个完整但高度压缩的 overview，使其理解：

- 项目试图回答什么问题；
- 为什么这个问题值得研究；
- 做了哪些主要实验；
- 最重要的结果是什么；
- 证据有哪些限制；
- 接下来应该针对哪些地方提问。

presentation 的作用之一，是让第二阅卷人在随后阅读 final report 时更容易理解项目。

对应时间：`00:38:36–00:39:42`

---

## 3. 导师建议的故事线

### 3.1 一张背景/问题幻灯片

不需要逐一解释五种 MAS 的内部实现。可以只列出五种架构，然后在同一页表达：

1. Tran paper 发现，在相同 compute/inference budget 下，若干 MAS 不如 SAS；
2. 本项目的 initial results 也观察到相似现象；
3. 因此本项目最重要的问题不是再次证明最终准确率差异，而是：**Why does this happen?**

对应时间：`00:36:14–00:36:47`

### 3.2 清楚说出主要假设

导师建议把核心假设讲成一句容易理解的话：

> MAS may generate or expose a correct answer, but later revision or aggregation may reject it, switch away from it, or fail to select it more often than SAS.

中文可以理解为：MAS 的问题不一定只是“没有找到答案”，而可能是“已经找到，但后续协调又把它丢掉了”。

对应时间：`00:36:48–00:37:17`

### 3.3 说明如何检验假设

接下来用一页或一页半说明：

- 对 SAS 和 MAS 的推理轨迹标记正确答案何时出现；
- 计算答案从正确到错误、从错误到正确以及是否被最终保留；
- 用 LLM-as-a-judge pipeline 扩展到大规模 traces；
- 用人工标注子集检查自动 judge 是否可信。

对应时间：`00:37:18–00:37:48`

### 3.4 展示主要结果

结果页应优先展示能够回答主问题的数字：

- matched-budget SAS/MAS 的最终性能差异；
- SAS 与 MAS 的发现后丢失/最终保留差异；
- Debate/Sequential 中最有解释力的人工转移结果；
- human–Mistral agreement，用于说明为什么全量结果是 screening evidence、关键结果需要人审。

不要尝试把所有 architecture × dataset × model × budget 表格都塞进 presentation。完整数字可留作 backup slides，以便问答时调用。

### 3.5 最后一页只放高层结论和限制

导师明确建议用一张简洁的 conclusions and limitations slide 收尾。它应回答：

- 得出了什么；
- 哪些结果来自人工证据，哪些来自机器筛查；
- 不能把结论推广到哪里。

对应时间：`00:37:48–00:37:59`

---

## 4. 推荐的 8 分钟幻灯片结构

下面是根据导师建议整理的可执行版本，不是会议中的逐页硬性要求。

| 时间 | Slide | 需要表达的内容 |
|---:|---|---|
| 0:00–0:25 | 1. Title | 题目、姓名、导师；一句话研究目标。 |
| 0:25–1:15 | 2. Problem and prior result | matched budgets 下 SAS/MAS 的问题；列出五种 MAS；Tran paper 与 initial reproduction。 |
| 1:15–1:55 | 3. Main question and hypothesis | “Why?”；区分 failure to discover 与 failure to preserve/select。 |
| 1:55–2:45 | 4. Experimental scope | 两个 datasets、两个 model variants、SAS + 五种 MAS、两个 budgets；只给必要数字。 |
| 2:45–3:40 | 5. Failure-analysis method | 用一张简单图解释 Discovery、Endorsement、C→W/W→C，以及 machine screen → targeted human audit 的证据关系。 |
| 3:40–5:20 | 6. Main results | final performance + SAS/MAS process comparison；只突出最能回答主问题的图和数字。 |
| 5:20–6:35 | 7. Human audit | Debate/Sequential 关键转移、human–Mistral agreement，以及 machine evidence 的限制。 |
| 6:35–7:40 | 8. Conclusions and limitations | 三条结论、两条限制、设计含义。 |
| 7:40–8:00 | Closing | 回到主问题，用一句话结束并进入 questions。 |

如果 SAS process comparison 在制作 slides 时尚未完成，不应编造结论。可以先展示 final-performance gap，并把 SAS process result 留为明确的 remaining analysis；但导师将其视为最重要的最后一组结果，应优先在 presentation 前完成。

---

## 5. 哪些内容应该删减

导师明确表示，不需要在 8–10 分钟内详细解释五种 MAS 各自如何运行。建议：

- 在主 slides 中只列名称和一行分类；
- 用一个简化图解释 SAS 与 MAS 为什么存在额外 coordination boundary；
- 不逐页讲完整 architecture implementation；
- 不展示大段 prompt、代码、完整模型输出或全部 15 字段；
- 不逐项讲所有 dataset/model/budget cells；
- 不花大量时间复述文献综述。

对应时间：`00:36:04–00:36:33`

需要详细内容时，放到 backup slides，供第二阅卷人提问时打开。

---

## 6. 问答比 presentation 本身更重要

现场 presentation 后，第二阅卷人可能会提问约 **5–10 分钟**。导师认为这是最重要的部分，因为这是第二阅卷人唯一能直接询问项目的机会。

presentation 应给出足够信息，让对方知道哪些地方需要追问；回答问题则是澄清报告中任何不清楚内容的机会。

对应时间：`00:38:24–00:39:42`

### 建议重点准备的问题

1. 你如何定义 SAS 和 MAS？为什么 Ensemble 算 MAS？
2. 五种 MAS 分别是什么？为什么 human audit 只重点分析 Debate 和 Sequential？
3. `item`、`configuration`、`stage` 和 `repeat` 分别是什么？
4. Discovery 和 Endorsement 有什么区别？能否举一个 Discovery=C、Endorsement=W 的例子？
5. 最终准确率如何计算？exact match、F1、LLM judge 与 human label 有什么差别？
6. 为什么 Mistral 可以用于 broad screening，却不能作为关键 transition 的 ground truth？
7. 为什么 raw audit counts 不能直接当作 population prevalence？
8. SAS 与 MAS 使用的 source boundary 是否真正可比？
9. 为什么增加 token budget 反而可能降低性能？这是因果结论吗？
10. 结果能否推广到其他模型、datasets 或 MAS implementations？
11. 15 个字段是否真的是 15 个二元错误类别？哪些是人工标签，哪些是派生或机器字段？
12. 如果继续研究，你会优先增加第二标注者、其他模型，还是更大规模 SAS audit？为什么？

每个问题准备 20–40 秒的直接答案，并准备一张 backup slide 支持复杂数字。

---

## 7. 推荐准备的 backup slides

这些页不进入正常 8 分钟流程，只在问答需要时打开：

- 五种 MAS 的完整架构比较表；
- 数据层级：question → item-configuration → trace → stage → repeat；
- 15 audit fields 的三组定义；
- 完整 SAS/MAS 结果表；
- Debate/Sequential raw counts 与 weighted estimates；
- Mistral calibration/confusion matrix；
- sampling strata 和 weighting 方法；
- budget、wall time、thinking tokens 和 truncation 结果；
- limitations 和 future work；
- 一个实际 trace 例子，展示正确答案先出现后被拒绝。

---

## 8. 现场形式

导师描述的预计安排是：

- 地点可能是较大的 computer lab；
- 学生会被分配一个位置，在桌面电脑或自己的 laptop 上展示；
- 现场可能只有第二阅卷人来到桌前听 presentation；
- presentation 结束后立即进入 5–10 分钟提问。

对应时间：`00:37:59–00:38:44`

因此应提前：

- 同时准备 PowerPoint/PDF 两种版本；
- 把文件放在本机和云端/USB；
- 确保图表在普通电脑屏幕上也能看清；
- 关闭通知，并准备离线展示；
- 不依赖现场网络、视频或需要长时间加载的动画。

---

## 9. 与导师预演

导师表示下一次会议在 presentation 前一天（Thursday），可以在会上共同过一遍 slides。学生应在此之前完成可完整演示的版本，而不是只带提纲。

对应时间：`00:40:16–00:40:55`

建议在会前发送：

- slides PDF；
- 一次完整排练的实际用时；
- 自己最担心的 3 个问题；
- 尚未完成但可能影响 slides 的 SAS result 状态。

---

## 10. Presentation 制作清单

### 内容

- [ ] 一页内建立 prior result、initial reproduction 和主问题 “why”。
- [ ] 用一句话讲清主假设：correct answer is generated but later lost/rejected/not selected。
- [ ] 清楚区分 machine screening 和 human audit。
- [ ] 在结果中加入 SAS 同口径过程比较。
- [ ] 最后一页只有高层结论和限制。

### 时间

- [ ] 正常排练不超过 8 分钟。
- [ ] 每页只承担一个主要信息。
- [ ] 对最重要结果停留更久，背景和系统列表快速带过。

### 可视化

- [ ] 主结果优先用 1–2 张易读图，不用密集表格。
- [ ] 字号、颜色、图例在 laptop 屏幕上清晰。
- [ ] 所有数字注明 raw、weighted、machine-screened 或 human-audited。
- [ ] 复杂架构和完整结果放入 backup slides。

### 问答

- [ ] 为 SAS/MAS 定义、metrics、judge reliability、sampling、limitations 准备短答案。
- [ ] 准备关键数字的 backup slides。
- [ ] 不确定时说明证据范围，不把相关性说成因果。

---

## 11. 一句话概括导师希望看到的 presentation

在约 8 分钟内讲清一条完整故事：**matched-budget MAS 往往没有稳定超过 SAS；本项目的关键问题是为什么；核心假设是 MAS 会在后续协调中丢失已经出现的正确答案；项目用大规模自动 trace screening 和小规模 human audit 检验这一点，并用 SAS 对照、明确的证据等级和局限性给出结论。**
