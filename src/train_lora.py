"""LoRA-SFT on pre-built text data (see build_sft_data.py).

The data already contains fully formatted chat text (prelude + think + answer
+ eos), so we train plain completion-style on the 'text' field with no extra
templating. Loss is over the whole sequence for v1 simplicity; prompt-masked
loss is a possible refinement, note it in the thesis.

Usage:
    python -m src.train_lora --data data/sft_train.jsonl \
        --out /mnt/parscratch/users/$USER/checkpoints/qwen3-4b-lora-v1
"""

from __future__ import annotations

import argparse

from datasets import load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--data", default="data/sft_train.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--grad_accum", type=int, default=4)
    ap.add_argument("--max_len", type=int, default=4096)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    ds = load_dataset("json", data_files=args.data, split="train")
    ds = ds.train_test_split(test_size=0.02, seed=args.seed)

    peft_cfg = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    sft_cfg = SFTConfig(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="epoch",
        max_seq_length=args.max_len,
        dataset_text_field="text",
        packing=False,
        seed=args.seed,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=args.model,
        args=sft_cfg,
        train_dataset=ds["train"],
        eval_dataset=ds["test"],
        peft_config=peft_cfg,
    )
    trainer.train()
    trainer.save_model(args.out + "/final")
    print(f"adapter saved to {args.out}/final")


if __name__ == "__main__":
    main()
