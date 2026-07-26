#!/bin/bash
#SBATCH --job-name=rejudge-all
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out

set -eo pipefail
cd /users/acu25yx/sas-mas-repro

module load GCC/12.3.0
export CC=$(which gcc)
export TRITON_CC=$CC
export HF_HOME=/mnt/parscratch/users/$USER/hf_cache
export HF_HUB_OFFLINE=1

PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python

echo "=== provenance ==="
hostname
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY -c "import torch; print('CUDA:', torch.cuda.is_available(), torch.cuda.get_device_name(0))"
echo "=================="

srun $PY -m src.rejudge \
    --judge_model Qwen/Qwen3-4B \
    --enforce_eager \
    results/pilot_wallclock \
    results/finetuned_wallclock \
    results/v3a_token \
    results/v3b_token \
    results/v3a_wallclock \
    results/v3b_wallclock

echo "Rejudging complete."
