"""Merge a LoRA adapter into the base model and export full weights,
so vLLM can load it via a plain model path (config: model.name).

Usage:
    python -m src.merge_lora \
        --adapter /mnt/parscratch/users/$USER/checkpoints/qwen3-4b-lora-v1/final \
        --out /mnt/parscratch/users/$USER/checkpoints/qwen3-4b-sft-merged-v1
"""

from __future__ import annotations

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="Qwen/Qwen3-4B")
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    base = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="cpu")
    model = PeftModel.from_pretrained(base, args.adapter)
    merged = model.merge_and_unload()
    merged.save_pretrained(args.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
    print(f"merged model saved to {args.out}")


if __name__ == "__main__":
    main()
