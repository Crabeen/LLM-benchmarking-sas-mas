# v3b 多 MAS Benchmark

## 研究问题

本扩展固定数据、问题顺序、模型 checkpoint、judge 与 budget 协议，只改变
orchestration：

- `sas`
- `sequential`
- `subtask_parallel`
- `parallel_roles`
- `debate`
- `ensemble`

主比较是同一题上的 `Acc(MAS) - Acc(SAS)`。随后比较 frozen 与 v3b：

```text
DeltaGap =
  (MAS_v3b - SAS_v3b) - (MAS_frozen - SAS_frozen)
```

正值表示 v3b 令该 MAS 相对 SAS 上移；它不等于 MAS 或 SAS 自身一定提高。

## 与原论文对齐的部分

- Sequential：planner → 串行 workers → aggregator。
- Subtask-parallel：planner 生成近似独立任务，workers 用 vLLM batch 并行执行。
- Parallel-roles：Solver、Fact Extractor、Skeptic、Second Solver 四个固定角色。
- Debate：两个 debater 并行生成，再由两个 critic 交叉改进，最后 judge。
- Ensemble：候选并行生成，候选阶段温度 0.7，judge 温度 0。
- planner、aggregator/judge 的 `think_budget=0`；worker thinking tokens 的总上限为
  全局 token budget。

仓库沿用原项目的 oracle/full-context 扩展：相关段落被加入 worker 输入。Debate 的
critic 也显式收到问题与 context，否则独立 critic 调用无法知道它在批评哪道题。

## 一个必须显式报告的实现选择

论文只写 Ensemble 使用“multiple workers”，没有在正文或 prompt 附录给出候选数。
本实现将 `ensemble_size` 暴露为配置项，并在 frozen/v3b 主配置中固定为 4。论文中
可以写成：

> We use four ensemble candidates as an explicit implementation choice because
> the reference paper does not report the candidate count.

若做消融，可另测 2/4/8，但不能让 frozen 和 v3b 使用不同数量。

## 运行

先做两题 integration smoke test：

```bash
sbatch scripts/benchmark_all.sbatch configs/v3b_all_mas_smoke.yaml
```

确认六个 prediction/judged JSONL 都生成且无 `trace.error` 后，再跑正式实验。

先跑 token-budget 主实验：

```bash
sbatch scripts/benchmark_all.sbatch configs/frozen_all_mas_token.yaml
sbatch scripts/benchmark_all.sbatch configs/v3b_all_mas_token.yaml
```

再跑 wall-clock 扩展：

```bash
sbatch scripts/benchmark_all.sbatch configs/frozen_all_mas_wallclock.yaml
sbatch scripts/benchmark_all.sbatch configs/v3b_all_mas_wallclock.yaml
```

`run_experiment` 随模型运行的原始 judge 适合单次检查，但 frozen 与 v3b 会因此使用
不同 grader。正式跨 checkpoint 结论必须再用同一个 fixed judge 重判：

```bash
sbatch scripts/rejudge_all_mas.sbatch
```

若只重判 token 实验，可显式传目录：

```bash
sbatch scripts/rejudge_all_mas.sbatch \
  results/frozen_all_mas_token results/v3b_all_mas_token
```

若需要把预测与 judge 分开：

```bash
python -m src.run_experiment --config CONFIG --predict-only
python -m src.run_experiment --config CONFIG --judge-only
```

## 分析

单个 checkpoint 内比较：

```bash
python -m src.analyze results/v3b_all_mas_token
```

输出包括 accuracy、bootstrap CI、prompt/thinking token、逻辑调用数、实际模型
invocation 数、wall time、timeout、truncation、planner parse failure，以及每个
MAS 对 SAS 的 paired CI 和逐题 win/tie/loss。

跨 checkpoint：

```bash
python -m src.compare_runs \
  results/frozen_all_mas_token results/v3b_all_mas_token
```

使用 fixed judge 文件时：

```bash
export JUDGE_SUFFIX='*.rejudged.jsonl'
python -m src.analyze results/v3b_all_mas_token
python -m src.compare_runs \
  results/frozen_all_mas_token results/v3b_all_mas_token
```

## 判读边界

Token-budget 是论文对齐主结果。Wall-clock 下，parallel workers 在一个 vLLM batch
中执行；`n_calls` 是逻辑 agent 调用数，`n_model_invocations` 把同一 parallel
group 计为一次物理 batch。不要把 batch 中每个 worker 的共享 latency 相加；
端到端值使用 `wall_seconds`。

如果某架构 timeout 高，先调整 wall-clock level 或 answer reserve，再解释 accuracy。
Subtask-parallel 的 planner fallback 率也必须与 accuracy 一起报告，因为 MuSiQue
4-hop 的依赖链可能使“独立子任务”分解本身失败。
