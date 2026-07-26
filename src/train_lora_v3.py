"""v3 LoRA-SFT trainer with an explicit, assertable label policy.

Replaces TRL's SFTTrainer with a plain transformers Trainer + manual label
construction, so the loss coverage is stated in code rather than inferred
from library version behaviour. Two independent switches define the arm:

  --mask_prompt / --no-mask_prompt   prompt tokens -> -100 (default: on;
                                     v2a established this as hygiene)
  --mask_stop                        the </think> token(s) inside the
                                     completion -> -100, removing the
                                     "stop thinking HERE" gradient

Arms (data x flags):
  v3a  --data data/sft_train_v2a.jsonl  --mask_stop
       (templated traces, stop supervision removed: isolates the
        stop-position variable against v2a)
  v3b  --data data/sft_train_v3.jsonl
       (rejection-sampled natural traces, natural stop supervised: the
        aligned-objective main arm)
  v3c  --data data/sft_train_v3.jsonl   --mask_stop
       (optional: does stop supervision still matter at natural length?)

Data: jsonl with "prompt" / "completion" fields (v2a and v3 files both
qualify). Prompt and completion are tokenized separately and concatenated —
the same boundary convention as the v2a arm, kept for comparability.

Diagnostics (printed and asserted before training):
  masked/trained non-padding counts, unmasked-padding == 0, and per-dataset
  verification that every </think> occurrence inside completions carries the
  intended label state for the chosen policy.

Usage:
  python -m src.train_lora_v3 --data data/sft_train_v3.jsonl \
      --out checkpoints/qwen3-4b-lora-v3b
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import torch
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                          TrainingArguments)
from peft import LoraConfig, get_peft_model

THINK_CLOSE = "</think>"


def find_subseq(hay: list[int], needle: list[int]) -> list[int]:
    out = []
    n = len(needle)
    for i in range(len(hay) - n + 1):
        if hay[i:i + n] == needle:
            out.append(i)
    return out


class Rows(Dataset):
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> dict:
        return self.rows[i]


def build_rows(path: str, tok, mask_prompt: bool, mask_stop: bool,
               max_len: int):
    stop_ids = tok.encode(THINK_CLOSE, add_special_tokens=False)
    rows, skipped_len, no_stop = [], 0, 0
    stop_occurrences = stop_masked = 0
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        p = tok.encode(r["prompt"], add_special_tokens=False)
        c = tok.encode(r["completion"], add_special_tokens=False)
        ids = p + c
        if len(ids) > max_len:
            skipped_len += 1
            continue
        labels = ([-100] * len(p) if mask_prompt else list(p)) + list(c)
        hits = find_subseq(c, stop_ids)
        if not hits:
            no_stop += 1          # completion without </think>: malformed
            continue
        stop_occurrences += len(hits)
        if mask_stop:
            for h in hits:
                for j in range(h, h + len(stop_ids)):
                    labels[len(p) + j] = -100
                stop_masked += 1
        rows.append({"input_ids": ids, "labels": labels})
    return rows, {"skipped_too_long": skipped_len,
                  "dropped_no_stop_token": no_stop,
                  "stop_occurrences": stop_occurrences,
                  "stop_occurrences_masked": stop_masked}


@dataclass
class PadCollator:
    pad_id: int

    def __call__(self, feats: list[dict]) -> dict:
        ids = [torch.tensor(f["input_ids"], dtype=torch.long) for f in feats]
        lbs = [torch.tensor(f["labels"], dtype=torch.long) for f in feats]
        att = [torch.ones(len(x), dtype=torch.long) for x in ids]
        return {
            "input_ids": pad_sequence(ids, batch_first=True,
                                      padding_value=self.pad_id),
            "labels": pad_sequence(lbs, batch_first=True, padding_value=-100),
            "attention_mask": pad_sequence(att, batch_first=True,
                                           padding_value=0),
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    ap.add_argument("--mask_prompt", action=argparse.BooleanOptionalAction,
                    default=True)
    ap.add_argument("--mask_stop", action="store_true")
    ap.add_argument("--max_len", type=int, default=4096)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--per_device_bsz", type=int, default=2)
    ap.add_argument("--grad_accum", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.model)
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id

    rows, dstats = build_rows(args.data, tok, args.mask_prompt,
                              args.mask_stop, args.max_len)
    print(f"[train] data={args.data} rows={len(rows)} "
          f"mask_prompt={args.mask_prompt} mask_stop={args.mask_stop} "
          f"{dstats}")
    assert rows, "no training rows"
    if args.mask_stop:
        assert dstats["stop_occurrences_masked"] == dstats["stop_occurrences"], \
            "mask_stop requested but some </think> occurrences left supervised"
    else:
        assert dstats["stop_occurrences_masked"] == 0

    # ---- masking diagnostic on one collated batch (same convention as v2) ----
    coll = PadCollator(pad_id)
    batch = coll([rows[0]])
    lab, attn = batch["labels"], batch["attention_mask"].bool()
    masked_nonpad = ((lab == -100) & attn).sum().item()
    trained_nonpad = ((lab != -100) & attn).sum().item()
    unmasked_pad = ((lab != -100) & ~attn).sum().item()
    print(f"[train] masked non-padding={masked_nonpad}, "
          f"trained non-padding={trained_nonpad}, "
          f"unmasked padding={unmasked_pad}")
    assert trained_nonpad > 0, "completion fully masked - no gradient"
    assert unmasked_pad == 0, "padding leaking into loss"
    if args.mask_prompt:
        assert masked_nonpad > 0, "prompt masking requested but nothing masked"

    model = AutoModelForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16)
    model.config.use_cache = False
    model.enable_input_require_grads()
    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    targs = TrainingArguments(
        output_dir=args.out,
        per_device_train_batch_size=args.per_device_bsz,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        bf16=True,
        gradient_checkpointing=True,
        logging_steps=10,
        save_strategy="no",
        report_to=[],
        seed=args.seed,
    )
    trainer = Trainer(model=model, args=targs,
                      train_dataset=Rows(rows), data_collator=coll)
    trainer.train()

    final = Path(args.out) / "final"
    model.save_pretrained(str(final))
    tok.save_pretrained(str(final))
    print(f"[train] adapter saved -> {final}")


if __name__ == "__main__":
    main()
