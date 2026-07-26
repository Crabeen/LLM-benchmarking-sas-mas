#!/bin/bash
#SBATCH --job-name=sft-v3
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out

# Usage:
#   sbatch scripts/sft_v3.sbatch v3a   # template data + stop-mask (cheap control)
#   sbatch scripts/sft_v3.sbatch v3b   # rejection-sampled natural traces (main)
#   sbatch scripts/sft_v3.sbatch v3c   # rejection data + stop-mask (optional)

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
$PY -c "import torch, transformers, peft; print('torch', torch.__version__, '| tf', transformers.__version__, '| peft', peft.__version__)"
echo "=================="

ARM=${1:-v3b}
V3DATA=data/sft_train_v3.jsonl

case "$ARM" in
  v3a)
    srun $PY -m src.train_lora_v3 --data data/sft_train_v2a.jsonl --mask_stop \
        --out $CKPT/qwen3-4b-lora-v3a
    $PY -m src.merge_lora_v3 --adapter $CKPT/qwen3-4b-lora-v3a/final \
        --out $CKPT/qwen3-4b-sft-merged-v3a
    ;;
  v3b)
    # HF_HUB_OFFLINE=1 for training, but data generation may need dataset download;
    # if the MuSiQue cache is already populated (v1 built sft_train.jsonl from it,
    # so it is), offline mode is fine here too.
    [ -f "$V3DATA" ] || srun $PY -m src.build_sft_data_v3 --out "$V3DATA" --k 4
    srun $PY -m src.train_lora_v3 --data "$V3DATA" \
        --out $CKPT/qwen3-4b-lora-v3b
    $PY -m src.merge_lora_v3 --adapter $CKPT/qwen3-4b-lora-v3b/final \
        --out $CKPT/qwen3-4b-sft-merged-v3b
    ;;
  v3c)
    [ -f "$V3DATA" ] || { echo "run v3b first to generate $V3DATA"; exit 1; }
    srun $PY -m src.train_lora_v3 --data "$V3DATA" --mask_stop \
        --out $CKPT/qwen3-4b-lora-v3c
    $PY -m src.merge_lora_v3 --adapter $CKPT/qwen3-4b-lora-v3c/final \
        --out $CKPT/qwen3-4b-sft-merged-v3c
    ;;
  *)
    echo "unknown arm: $ARM (expected v3a | v3b | v3c)"; exit 1
    ;;
esac
echo "Done. Merged model: $CKPT/qwen3-4b-sft-merged-$ARM"
