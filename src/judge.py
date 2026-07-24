"""LLM-as-judge, paper Appendix D.7: fixed rubric, run right after prediction,
same model, and the decision is parsed from
{Explanation: ..., Decision: TRUE or FALSE}.
String-match fallback is logged alongside for sanity-checking.
"""

from __future__ import annotations

import re
import string

from .engine import Engine
from . import prompts


def _normalize(s: str) -> str:
    s = s.lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    return " ".join(s.split())


def string_match(prediction: str, gold_aliases: list[str]) -> bool:
    p = _normalize(prediction)
    return any(_normalize(g) in p for g in gold_aliases if g.strip())


def judge(
    engine: Engine, question: str, prediction: str, gold: str
) -> tuple[bool, str]:
    """Returns (correct, raw_judge_output)."""
    if not prediction.strip():
        return False, ""
    msgs = [
        {"role": "system", "content": prompts.JUDGE_SYSTEM},
        {"role": "user", "content": prompts.judge_user(question, prediction, gold)},
    ]
    r = engine.generate(msgs, think_budget=0, answer_max_tokens=256,
                        temperature=0.0)
    raw = r.answer
    m = re.search(r"Decision\s*[:=]\s*[\"']?\s*(TRUE|FALSE)", raw, re.I)
    if m:
        return m.group(1).upper() == "TRUE", raw
    # lenient fallback on malformed judge output
    return bool(re.search(r"\bTRUE\b", raw, re.I)) and not re.search(
        r"\bFALSE\b", raw, re.I
    ), raw
