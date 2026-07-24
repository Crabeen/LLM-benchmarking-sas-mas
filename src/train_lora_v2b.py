"""v2b / v2a-aligned trainer: completion-only loss, LoRA, identical recipe.

The only thing that varies between arms is the --data file (grounded traces vs
answer-only traces on the same aligned id set), so both arms run through this
same script. Hard assertions replace warnings: an ineffective masking setup
fails fast instead of producing a misleading checkpoint.
"""

from __future__ import annotations

import argparse
import inspect

from datasets import load_dataset
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--data", default="data/sft_train_v2b.jsonl")
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

    kw = dict(
        output_dir=args.out,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        # no per_device_eval_batch_size: match v1/v2a defaults
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
        packing=False,
        seed=args.seed,
        report_to="none",
    )
    sig = set(inspect.signature(SFTConfig.__init__).parameters)
    if "completion_only_loss" not in sig:
        raise RuntimeError("Install a TRL version supporting completion_only_loss "
                           "(tested with trl==0.17.0).")
    kw["completion_only_loss"] = True
    if "max_length" in sig:
        kw["max_length"] = args.max_len
    elif "max_seq_length" in sig:
        kw["max_seq_length"] = args.max_len
    else:
        raise RuntimeError("TRL exposes neither max_length nor max_seq_length")

    trainer = SFTTrainer(
        model=args.model, args=SFTConfig(**kw),
        train_dataset=ds["train"], eval_dataset=ds["test"],
        peft_config=peft_cfg,
    )

    # ---- masking diagnostic via collator only; fail fast ----
    batch = trainer.data_collator([trainer.train_dataset[0]])
    lab, attn = batch["labels"], batch["attention_mask"].bool()
    masked_nonpad = ((lab == -100) & attn).sum().item()
    trained_nonpad = ((lab != -100) & attn).sum().item()
    unmasked_pad = ((lab != -100) & ~attn).sum().item()
    print(f"[train] data={args.data}")
    print(f"[train] masked non-padding={masked_nonpad}, "
          f"trained non-padding={trained_nonpad}, unmasked padding={unmasked_pad}")
    if masked_nonpad == 0:
        raise RuntimeError("Prompt masking is NOT active")
    if trained_nonpad == 0:
        raise RuntimeError("No completion tokens contribute to loss")
    if unmasked_pad != 0:
        raise RuntimeError("Padding tokens unexpectedly contribute to loss")

    trainer.train()
    trainer.save_model(args.out + "/final")
    print(f"adapter saved to {args.out}/final")


if __name__ == "__main__":
    main()
