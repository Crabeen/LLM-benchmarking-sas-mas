#!/bin/bash
#SBATCH --job-name=mas-benchmark
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=yxie59@sheffield.ac.uk

set -eo pipefail
mkdir -p logs

module load GCC/12.3.0
export CC=$(which gcc)
export HF_HOME=/mnt/parscratch/users/$USER/hf_cache
export HF_HUB_OFFLINE=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python
CONFIG=${1:?usage: sbatch scripts/benchmark_all.sbatch CONFIG.yaml}

echo "=== provenance ==="
hostname
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY -c "import sys, vllm, torch; print(sys.executable); print('vllm', vllm.__version__, '| torch', torch.__version__)"
gcc --version | head -1
echo "=================="

srun $PY -m src.run_experiment --config "$CONFIG"
OUT_DIR=$($PY -c "import yaml; print(yaml.safe_load(open('$CONFIG'))['output_dir'])")
$PY -m src.analyze "$OUT_DIR"

