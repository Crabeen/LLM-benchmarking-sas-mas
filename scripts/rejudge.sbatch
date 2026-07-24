#!/bin/bash
#SBATCH --job-name=rejudge
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
set -eo pipefail
mkdir -p logs
module load GCC/12.3.0
export CC=$(which gcc)
export HF_HOME=/mnt/parscratch/users/$USER/hf_cache
export HF_HUB_OFFLINE=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python
srun $PY -m src.rejudge --judge_model Qwen/Qwen3-4B \
    results/pilot_token results/finetuned_token results/v2a_token \
    results/v2aa_token results/v2b_token \
    results/pilot_wallclock results/finetuned_wallclock
