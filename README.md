# SAS vs MAS under Matched Budgets — Reproduction Scaffold

Small-scale reproduction of Tran & Kiela (arXiv:2604.02460), *Single-Agent
LLMs Outperform Multi-Agent Systems on Multi-Hop Reasoning Under Equal
Thinking Token Budgets*, with a wall-clock budget mode as the thesis
extension.

## Layout

```
src/
  budget.py            BudgetController: TokenBudget (paper) / WallClockBudget (thesis)
  engine.py            vLLM two-phase generation: capped <think> phase, then answer
  prompts.py           SAS / planner / worker / aggregator / judge prompts
  architectures/
    sas.py             one call, whole budget
    sequential.py      planner -> k workers (budget split) -> aggregator
  data.py              MuSiQue 4-hop loader (oracle / full / closed context)
  judge.py             LLM-as-judge + string-match sanity check
  run_experiment.py    (system x budget level) sweep, JSONL logging, judging
  analyze.py           accuracy + bootstrap CI, diagnostics, SAS-MAS gap
configs/
  pilot_token.yaml     paper-faithful token-budget pilot — run this first
  pilot_wallclock.yaml wall-clock pilot — same code, different budget block
scripts/pilot.sbatch   SLURM template
```

## Setup

```bash
python -m venv ~/venvs/sas-mas && source ~/venvs/sas-mas/bin/activate
pip install -r requirements.txt
```

If compute nodes lack internet, pre-download on the login node:

```bash
export HF_HOME=$SCRATCH/hf_cache
huggingface-cli download Qwen/Qwen3-8B
python -c "from datasets import load_dataset; load_dataset('dgslibisey/MuSiQue')"
```

## Run

```bash
sbatch scripts/pilot.sbatch configs/pilot_token.yaml      # step 1: validate vs paper
sbatch scripts/pilot.sbatch configs/pilot_wallclock.yaml  # step 2: thesis extension
# or interactively:
python -m src.run_experiment --config configs/pilot_token.yaml
python -m src.analyze results/pilot_token
```

## How budget enforcement works

Every model call is two-phase: the chat prompt is forced to end with an open
`<think>` tag, the thinking phase generates at most the allocated tokens
(stop token `</think>`, hard truncation on overflow), then `</think>` is
appended and the final answer is generated outside the thinking budget.
This matches the paper's open-model protocol: the budget is an **upper cap**,
not a forced spend — so always report *actual* thinking tokens used
(analyze.py does), not the nominal budget.

`WallClockBudget` swaps in transparently: it converts remaining seconds into
a token allocation via an EMA of observed decode throughput, reserves a few
seconds for the answer phase, and flags timeouts when the deadline passes
before a final answer exists.

## Before your formal (non-pilot) runs

1. **Prompts**: `src/prompts.py` bodies are written in the paper's spirit;
   replace them with the exact Appendix D / D.7 text (marked `TODO(appendix-d)`)
   for comparability.
2. **Context mode**: confirm which MuSiQue context setting the paper uses
   (oracle supporting paragraphs vs full 20-paragraph context vs closed-book)
   and set `data.context_mode` accordingly. `full` needs a larger
   `max_model_len`.
3. **Judge model**: the pilot reuses the same model as judge to save GPU
   memory. For formal runs, judge with a stronger model and spot-check ~30
   judgments by hand; the logged `string_match` column helps catch judge
   drift.
4. **Wall-clock hygiene**: questions run strictly one at a time (no
   cross-question batching), otherwise per-question latency is meaningless.
   Keep it that way for any run whose wall-clock numbers you will report,
   and note GPU model / driver / vLLM version in the thesis.
5. **Fine-tuning stage**: to evaluate a LoRA-SFT checkpoint, point
   `model.name` at your merged checkpoint (or add `enable_lora=True` +
   `LoRARequest` in `engine.py`). The 2x2 (frozen/tuned x SAS/MAS) is just
   four configs.

## Known sharp edges

- Small models emit malformed planner JSON; `sequential.py` falls back to
  regex extraction, then a generic 3-step plan, and logs `plan_parse_mode`
  so you can report the failure rate (analyze.py's `planfail` column).
- Some checkpoints emit `<think>` handling quirks (template already opens
  the tag, or model re-opens it in the answer phase). Inspect a few raw
  traces in the JSONL before trusting a run.
- Thinking often finishes well below the cap at large budgets — expected;
  the paper observes the same.
