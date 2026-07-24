#!/bin/bash
#SBATCH --job-name=sas-mas
#SBATCH --partition=gpu
#SBATCH --qos=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=82G
#SBATCH --time=06:00:00
#SBATCH --output=logs/%x_%j.out

set -eo pipefail
mkdir -p logs

module load GCC/12.3.0
export CC=$(which gcc)
export HF_HOME=/mnt/parscratch/users/$USER/hf_cache
export HF_HUB_OFFLINE=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

# absolute path to the conda env's python — no activation needed
PY=/mnt/parscratch/users/$USER/conda/envs/sas-mas/bin/python

echo "=== provenance ==="
hostname
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
$PY -c "import sys, vllm, torch; print(sys.executable); print('vllm', vllm.__version__, '| torch', torch.__version__)"
gcc --version | head -1
echo "=================="

CONFIG=${1:-configs/pilot_token.yaml}
srun $PY -m src.run_experiment --config "$CONFIG"
$PY -m src.analyze "$($PY -c "import yaml;print(yaml.safe_load(open('$CONFIG'))['output_dir'])")"
