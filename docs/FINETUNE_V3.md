# Finetune v3 — 重做设计（对齐监督目标与评估目标）

## 0. 诊断（本次重做的出发点）

之前所有 arm 的训练 completion 都是：

```
固定长度模板 trace
</think>
final answer
EOS
```

交叉熵在 `</think>` 所在位置直接奖励"在示范 trace 结束处停止思考"。v1/v2a 模板 trace 短（监督 completion ≈ 107 tok），v2b 加 evidence span 后更长（≈ 316 tok），推理时的自然 thinking 长度呈现同样顺序——SFT 学到的主要是"按训练 trace 长度结束推理"。这解释了：

- cap 1000 → 2000 几乎无效（fine-tuned 模型远在 cap 前主动停止，trunc = 0，预算不 binding）；
- completion-only masking（v2a）不解决问题：它只移除 prompt token loss，v1/v2a thinking 长度几乎相同（112 vs 112），v2a Sequential 仍低于 frozen；
- 整个监督目标与最终 accuracy 不一致——这是比"训了 prompt"更根本的病灶。

结合已确立的 v2b 证据（grounding 崩塌来自轨迹**内容**），当前有两个独立病灶：**轨迹内容**（v2b 已部分修复）与**停止位置监督**（未修复）。

## 1. 复用的程序结构（不动）

```
run_experiment.py → architectures/{sas,sequential}.py → budget.py → engine.py
judge.py（Appendix D.7 rubric）· analyze.py · grounding_metric.py · compare_runs.py
```

评估协议零改动：Appendix D prompt、budget-as-cap 语义、两阶段生成
（phase1 stop=["</think>"]，phase2 = prompt + thinking + "\n</think>\n\n"）、
LLM-as-judge、SAS/Sequential 共享同一份 merged 权重。

Finetune 链被替换为三个新文件（v1/v2 文件全部保留，保证旧 arm 可复现）：

```
src/build_sft_data_v3.py   rejection-sampled 自然轨迹（GPU / vLLM）
src/train_lora_v3.py       纯 transformers Trainer，label 策略显式可断言
src/merge_lora_v3.py       CPU merge，供 vLLM 加载
scripts/sft_v3.sbatch      gen → train → merge，按 arm 调度
```

## 2. Loss 规划（token 级覆盖表）

| arm | 轨迹来源 | 计入 loss | prompt | `</think>` | EOS | 检验的假设 |
|---|---|---|---|---|---|---|
| v1 | gold 分解模板 | 全序列 | 有 loss | 监督（~100 tok 处） | 监督 | baseline |
| v2a/v2aa | 模板 | completion | −100 | 监督 | 监督 | 信号稀释（已排除） |
| v2b | grounded 模板 | completion | −100 | 监督（~316 tok 处） | 监督 | 轨迹内容 |
| **v3a** | 模板（复用 v2a 数据） | completion | −100 | **−100** | 监督 | 停止监督的单独作用 |
| **v3b（主）** | rejection-sampled 自然轨迹 | completion | −100 | 监督（**自然位置**） | 监督 | 监督-目标对齐 |
| v3c（可选） | 同 v3b | completion | −100 | −100 | 监督 | 自然长度下停止监督的残余影响 |

设计原理：评估量是"预算上限内的最终 accuracy"，训练目标中不应强监督与其无关的决策。
`</think>` 的位置正是这样的决策——要么不监督（v3a/v3c 的 mask_stop：该 token 的
label 置 −100，移除"就在这里停"的梯度），要么让被监督的位置本身正确（v3b：停止点
是 frozen 模型自己的自然停止点）。EOS 属于答案阶段的结束，与 thinking 预算无关，
各 arm 均保留监督。

## 3. v3b 数据构造规则（rejection sampling）

frozen Qwen3-4B、论文 SAS prompt、oracle context、与 engine.py 逐字节一致的
chat 布局；每题采样 k=4（T=0.7, top_p=0.95），生成 cap 1536（远高于 frozen 自然
长度 ~690，且**被 cap 截断的候选一律丢弃**——绝不监督一个非自然的停止点）；
答案阶段 T=0 生成后按 gold+aliases 归一化子串校验（与 judge.py 的 string-match
fallback 同规则）；每题保留 sample 序最靠前的正确候选。产出记录 coverage、
think_tokens 分布（p10/50/90）、ctx 关键词率。

## 4. 执行步骤

```bash
# 0) 同步文件到 ~/sas-mas-repro（src/ scripts/ 对应目录）
# 1) 廉价对照先行（复用 v2a 数据，~12 min）
sbatch scripts/sft_v3.sbatch v3a
# 2) 主 arm（生成 ~1–2 h + 训练 ~20 min + merge）
sbatch scripts/sft_v3.sbatch v3b
# 3) 评估：复制现有 finetuned config，仅改 model.name
for a in v3a v3b; do
  sed "s|checkpoints/qwen3-4b-sft-merged-v1|checkpoints/qwen3-4b-sft-merged-$a|; \
       s|results/finetuned_token|results/${a}_token|" \
      configs/finetuned_token.yaml > configs/${a}_token.yaml
  sbatch scripts/pilot.sbatch configs/${a}_token.yaml
done
# wall-clock 同理复制 finetuned_wallclock.yaml
# 4) 诊断链
python -m src.analyze results/v3a_token results/v3b_token
python -m src.grounding_metric results/pilot_token results/finetuned_token \
    results/v2a_token results/v2b_token results/v3a_token results/v3b_token
python -m src.compare_runs results/pilot_token results/v3b_token
# 5) （可选，若 v3b 成立且想收尾停止监督问题）sbatch scripts/sft_v3.sbatch v3c
```

## 5. 预注册预测与判读标准（跑前登记）

- **v3a**：think_tok 相对 v2a 的 112 有回升但内容仍是模板腔，ctx-ref 仍低，
  acc 变化有限。若如此 → 证明两个病灶（内容 + 停止监督）都必须修，
  单独去掉停止监督不充分。若 think_tok 大幅回升且 acc 明显改善 →
  停止监督是主导病灶，叙事相应调整。
- **v3b 成功标准**（全部满足才算"对齐修复"成立）：
  1. think_tok 回到 frozen 量级（数百，非 ~100）；
  2. b1000 处 trunc 率重新非零 → 预算重新 binding，2×2×2 中 fine-tuned 行的
     "matched budget" 前提恢复；
  3. ctx-ref / valid-cite 显著回升；
  4. SAS acc ≥ frozen 0.600（至少不再是 −0.075 的退步）。
  然后才有资格重新读 ΔGap。
- 判读顺序：先看 4 条诊断，再看 gap——若诊断不达标，gap 数字不解读。

## 6. 忠于 Tran & Kiela 的约束清单

- SFT 数据仅 SAS 格式（与此前一致），SAS/MAS 共享权重的不对称照旧记录；
- 训练文本布局与 engine.py 推理布局逐字节一致（prelude + `<think>\n` + trace +
  `\n</think>\n\n` + answer + eos）；
- 评估侧 prompt/budget/judge 与 frozen 复现完全一致，v3 与 frozen、v1、v2
  的所有数字直接可比；
- 数据生成的 cap（1536）只是采样工程参数，不进入任何评估语义；截断候选丢弃
  保证"cap 从未作为停止点被示范"。

## 7. 已知局限（写进论文）

1. **Selection bias**：rejection sampling 丢弃 frozen 在 k 次内解不出的题，
   保留集偏简单（STaR 类方法的标准问题）。报告 coverage；k 越大偏差越小。
2. **自蒸馏性质**：v3b 轨迹来自 frozen 模型本身，注入的是格式/程序的巩固而非
   新知识；acc 大幅超越 frozen 不应预期，"不退步 + 行为保持"即达标。
3. **过滤器噪声**：归一化子串校验比 judge 宽松，可能放进少量碰巧含 gold 的
   错误推理轨迹；可抽 30 条人工核查过滤精度。
4. **监督 token 量跨 arm 不匹配**（v3b 自然轨迹远长于模板）——与 v2b 的
   长度混杂同类，limitations 里并列说明。
