#!/bin/bash
#SBATCH --job-name=sft-v2aa
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

PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python
CKPT=/mnt/parscratch/users/$USER/checkpoints

echo "=== provenance ==="
hostname; nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY -c "import torch, transformers, peft, trl; print('torch', torch.__version__, '| tf', transformers.__version__, '| peft', peft.__version__, '| trl', trl.__version__)"
echo "=================="

srun $PY -m src.train_lora_v2b --data data/sft_train_v2a_aligned.jsonl --out $CKPT/qwen3-4b-lora-v2a-aligned
$PY -m src.merge_lora --adapter $CKPT/qwen3-4b-lora-v2a-aligned/final --out $CKPT/qwen3-4b-sft-merged-v2a-aligned
echo "Done. Merged model: $CKPT/qwen3-4b-sft-merged-v2a"
