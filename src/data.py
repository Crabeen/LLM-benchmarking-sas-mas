"""MuSiQue 4-hop loading.

Uses the HF mirror `dgslibisey/MuSiQue` (musique-ans). 4-hop items have ids
starting with "4hop". Context modes:

  oracle    - concatenate ONLY the supporting paragraphs (clean multi-hop
              reading setting; recommended for the pilot).
  full      - all 20 paragraphs (distractors included; much longer prompts,
              raise max_model_len accordingly).
  closed    - no paragraphs (closed-book world knowledge).

Check which setting Appendix of arXiv:2604.02460 uses for MuSiQue and align
your formal run to it; the pilot default here is `oracle`.
"""

from __future__ import annotations

import random

from datasets import load_dataset


def load_musique_4hop(
    split: str = "validation",
    n: int = 30,
    seed: int = 0,
    context_mode: str = "oracle",
) -> list[dict]:
    ds = load_dataset("dgslibisey/MuSiQue", split=split)
    items = [ex for ex in ds if str(ex["id"]).startswith("4hop")]
    rng = random.Random(seed)
    rng.shuffle(items)
    items = items[:n]

    out = []
    for ex in items:
        paras = ex["paragraphs"]
        if context_mode == "oracle":
            chosen = [p for p in paras if p.get("is_supporting")]
        elif context_mode == "full":
            chosen = paras
        elif context_mode == "closed":
            chosen = []
        else:
            raise ValueError(f"unknown context_mode: {context_mode}")
        context = "\n\n".join(
            f"[{p['title']}] {p['paragraph_text']}" for p in chosen
        ) or None
        golds = [ex["answer"]] + list(ex.get("answer_aliases") or [])
        out.append(
            {
                "id": ex["id"],
                "question": ex["question"],
                "context": context,
                "gold": ex["answer"],
                "gold_aliases": golds,
            }
        )
    return out
