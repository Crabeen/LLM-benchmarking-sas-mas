# v3b+：面向 MAS accuracy 的下一阶段 fine-tuning 设计

## 先区分两个问题

v3b 的现有证据支持把它当作新基线：natural-trace rejection-sampled SFT 基本保住
了 frozen SAS 行为，并使当前 Sequential 不再因为错误的短轨迹监督而额外退化。
现有结果不能证明 v3b 已经学会多代理协作，因为它的训练数据仍全部是 SAS 格式。

因此顺序应当是：

1. 用 `BENCHMARKING_V3B.md` 的六架构实验定位 MAS 的实际失败位置；
2. 再训练 v3b+；
3. 用完全相同的 frozen/v3b/v3b+ benchmark 判断改进来自哪里。

## 推荐主方法：architecture-conditioned rejection-sampled SFT

以 v3b checkpoint 为 rollout policy，只使用 MuSiQue train。对每题分别运行
Sequential、Subtask-parallel、Parallel-roles、Debate 和 Ensemble，多次采样完整
episode。每个 episode 保存：

```json
{
  "architecture": "debate",
  "question_id": "...",
  "calls": [
    {"role": "debater_a", "input": "...", "thinking": "...", "answer": "..."},
    {"role": "critic_a", "input": "...", "thinking": "...", "answer": "..."},
    {"role": "aggregator", "input": "...", "answer": "..."}
  ],
  "final_answer": "...",
  "final_correct": true,
  "thinking_tokens_total": 987
}
```

只保留最终正确、未被 thinking cap 截断、无空调用的 episode。训练样本必须带显式
条件，例如：

```text
<architecture=debate>
<role=critic>
```

loss 只覆盖对应 assistant completion；prompt、其他 agent 的历史文本与 padding 置
为 `-100`。模型推理时必须使用相同的 architecture/role 条件，避免训练—评估格式
错位。

### 防止 SAS 再次退化

把原 v3b 的正确 SAS 数据作为 replay。主实验预注册三个 mix：

- MAS:SAS = 25:75
- MAS:SAS = 50:50
- MAS:SAS = 75:25

模型选择不能只看 MAS 平均 accuracy；建议使用约束式规则：

```text
在 SAS accuracy 相对 v3b 不下降超过预注册容忍值的模型中，
选择 mean(MAS - SAS) 最大的 checkpoint。
```

容忍值应在跑实验前固定，不能看完 validation 结果再选。

## 第二阶段：只对 critic/aggregator 做 preference tuning

先从同一问题、同一架构的候选中构造 pair：

- chosen：使最终答案正确的 critic/aggregator output；
- rejected：使最终答案错误，或把原本正确候选改错的 output。

优先训练：

1. Debate critic；
2. Debate/Ensemble/Parallel-roles aggregator；
3. Sequential planner；
4. 普通 worker。

这是实验优先级，不是已验证排序。原因是假如正确答案曾出现在候选中，而最终 prediction
错误，故障可直接归到选择或修正阶段；这种 pair 比“最终答错，所以所有角色都不好”
提供更明确的监督。

可先用 DPO，避免立即引入在线 rollout 与多代理 credit assignment。DPO 后仍需报告
chosen/rejected 的来源比例，防止某个 architecture 在训练集中占比过大。

## 第三阶段：outcome-based RL（可选）

只有 RS-SFT/DPO 已稳定后再考虑 GRPO/MARL。团队 reward 可以写成：

\[
R = \mathbb{1}[\text{correct}]
  - \lambda_t \frac{\text{thinking tokens}}{B}
  - \lambda_o \mathbb{1}[\text{budget overrun}]
  - \lambda_e \mathbb{1}[\text{empty/malformed call}].
\]

accuracy 必须是主 reward。token 与格式项只能是正则项，否则模型可能通过少思考或输出
极短答案获得较高 reward。

## 架构变化可能带来的影响：待检验假设

| 架构 | 可能获得的能力 | 主要风险 | v3b+ 应训练的角色 |
|---|---|---|---|
| Sequential | 有序传递中间答案 | 早期错误传播、message bottleneck | planner、step worker、aggregator |
| Subtask-parallel | 并行覆盖不同证据 | MuSiQue hop 有依赖，任务未必独立 | independence-aware planner、reducer |
| Parallel-roles | 独立求解与事实/质疑互补 | 重复计算、输出高度相关 | 四角色条件化、aggregator |
| Debate | 显式纠错与候选修订 | critic 可能把正确答案改错 | critic、judge |
| Ensemble | 候选多样性 | SFT 造成 mode collapse，候选趋同 | 保持采样多样性、judge |

这些是预注册假设，不应在结果出来前写成结论。

## 必做诊断

除最终 accuracy 外，每种 architecture 至少报告：

- candidate oracle accuracy：任一候选正确的比例；
- aggregation loss：存在正确候选但最终答错的比例；
- correction gain/loss：critic 把错改对、把对改错的比例；
- planner parse failure；
- 候选答案的去重率；
- 每个 role 的 thinking tokens；
- paired win/tie/loss against SAS；
- frozen → v3b → v3b+ 的 paired DeltaGap。

其中 candidate oracle accuracy 与最终 accuracy 的差距决定下一轮应训练 solver 还是
aggregator：若 oracle 已高而最终低，优先改选择；若 oracle 本身低，继续训练
aggregator 不会创造缺失的正确候选。

## 泛化评估

MuSiQue 4-hop validation 是 in-domain 主结果。v3b+ 选择完成后，再做不继续训练的
out-of-domain 评估，例如 2WikiMultiHopQA oracle evidence。新数据集不能参与
checkpoint 选择，否则它不再是独立泛化测试。

相关方法背景：

- Tran & Kiela 的 matched-budget 架构定义：
  <https://arxiv.org/abs/2604.02460>
- Optima 的 generate/rank/filter/imitate 路线：
  <https://arxiv.org/abs/2410.08115>
- MALT 的角色化多代理训练：
  <https://arxiv.org/abs/2412.01928>

