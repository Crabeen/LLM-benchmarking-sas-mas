"""Merge a LoRA adapter into the base model for vLLM loading.

CPU merge (bf16 4B ~ 8 GB RAM) so it can run in the same GPU job right after
training without fighting vLLM/Trainer for device memory.

Usage:
  python -m src.merge_lora_v3 --adapter checkpoints/qwen3-4b-lora-v3b/final \
      --out checkpoints/qwen3-4b-sft-merged-v3b
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
    model = model.merge_and_unload()
    model.save_pretrained(args.out, safe_serialization=True)
    AutoTokenizer.from_pretrained(args.base).save_pretrained(args.out)
    print(f"[merge] merged model -> {args.out}")


if __name__ == "__main__":
    main()
