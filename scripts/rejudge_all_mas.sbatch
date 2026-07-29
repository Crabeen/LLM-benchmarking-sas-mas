#!/bin/bash
#SBATCH --job-name=rejudge-all-mas
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out

set -eo pipefail
mkdir -p logs

module load GCC/12.3.0
export CC=$(which gcc)
export HF_HOME=/mnt/parscratch/users/$USER/hf_cache
export HF_HUB_OFFLINE=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python

DIRS=("$@")
if [ ${#DIRS[@]} -eq 0 ]; then
    DIRS=(
        results/frozen_all_mas_token
        results/v3b_all_mas_token
        results/frozen_all_mas_wallclock
        results/v3b_all_mas_wallclock
    )
fi

srun $PY -m src.rejudge \
    --judge_model Qwen/Qwen3-4B \
    --enforce_eager \
    --skip_existing \
    "${DIRS[@]}"

for DIR in "${DIRS[@]}"; do
    JUDGE_SUFFIX='*.rejudged.jsonl' $PY -m src.analyze "$DIR"
done

