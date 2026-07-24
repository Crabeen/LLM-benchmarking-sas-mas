"""v2a ablation: identical to train_lora.py except loss is computed on the
completion only (prompt tokens masked to -100).

Data: data/sft_train_v2a.jsonl with 'prompt' / 'completion' fields, split from
the exact v1 text so the ONLY changed variable is loss coverage.

SFTConfig kwargs are chosen by inspecting the installed TRL signature, so this
runs regardless of the max_seq_length -> max_length rename.
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
    ap.add_argument("--data", default="data/sft_train_v2a.jsonl")
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
        per_device_eval_batch_size=args.batch,
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
    kw["max_length" if "max_length" in sig else "max_seq_length"] = args.max_len
    if "completion_only_loss" in sig:
        kw["completion_only_loss"] = True
        print("[v2a] completion_only_loss=True set explicitly")
    else:
        print("[v2a] no completion_only_loss param; relying on TRL's default "
              "prompt-completion masking. VERIFY the label diagnostic below.")

    trainer = SFTTrainer(
        model=args.model, args=SFTConfig(**kw),
        train_dataset=ds["train"], eval_dataset=ds["test"],
        peft_config=peft_cfg,
    )

    # ---- masking diagnostic: MUST show a large masked fraction ----
    batch = next(iter(trainer.get_train_dataloader()))
    lab = batch["labels"]
    masked = (lab == -100).sum().item()
    total = lab.numel()
    pad = (batch["attention_mask"] == 0).sum().item()
    print(f"[v2a] labels==-100: {masked}/{total} ({masked/total:.1%}); "
          f"padding tokens: {pad} ({pad/total:.1%})")
    print(f"[v2a] masked beyond padding: {masked - pad} tokens "
          f"-> {'PROMPT MASKING ACTIVE' if masked - pad > 0.2 * total else 'WARNING: masking may NOT be active'}")

    trainer.train()
    trainer.save_model(args.out + "/final")
    print(f"adapter saved to {args.out}/final")


if __name__ == "__main__":
    main()
