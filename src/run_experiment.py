"""Experiment runner.

Usage (from repo root):
    python -m src.run_experiment --config configs/pilot_token.yaml

Iterates over (system x budget_level) for every question, writes one JSONL
per (system, budget_level) into the output dir, then judges everything.

NOTE ON TIMING: to keep wall-clock measurements honest, questions are run
one at a time (no cross-question batching). For the token-budget pilot this
is fine at n<=30; if you later want throughput for large token-mode runs,
batch the SAS phase across questions — but never report wall-clock numbers
from batched runs.
"""

from __future__ import annotations

import argparse
import copy
import json
import time
from pathlib import Path

import yaml
from tqdm import tqdm

from .budget import make_budget
from .data import load_musique_4hop
from .engine import Engine
from .judge import judge, string_match
from .architectures.sas import run_sas
from .architectures.sequential import run_sequential

SYSTEMS = {"sas": run_sas, "sequential": run_sequential}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    cfg = yaml.safe_load(Path(args.config).read_text())

    out_dir = Path(cfg["output_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config_used.yaml").write_text(yaml.dump(cfg))

    engine = Engine(
        model=cfg["model"]["name"],
        tensor_parallel_size=cfg["model"].get("tensor_parallel_size", 1),
        max_model_len=cfg["model"].get("max_model_len", 16384),
        gpu_memory_utilization=cfg["model"].get("gpu_memory_utilization", 0.90),
        seed=cfg.get("seed", 0),
    )

    data = load_musique_4hop(
        split=cfg["data"].get("split", "validation"),
        n=cfg["data"]["n"],
        seed=cfg.get("seed", 0),
        context_mode=cfg["data"].get("context_mode", "oracle"),
    )
    print(f"Loaded {len(data)} MuSiQue 4-hop questions "
          f"(context_mode={cfg['data'].get('context_mode', 'oracle')})")

    budget_levels = cfg["budget"]["levels"]  # list of ints (tokens) or floats (seconds)
    temperature = cfg.get("temperature", 0.0)

    for system_name in cfg["systems"]:
        run_fn = SYSTEMS[system_name]
        for level in budget_levels:
            tag = f"{system_name}_b{level}"
            path = out_dir / f"{tag}.jsonl"
            print(f"\n=== {tag} -> {path} ===")
            with path.open("w") as f:
                for ex in tqdm(data, desc=tag):
                    level_cfg = copy.deepcopy(cfg)
                    key = ("thinking_tokens"
                           if cfg["budget"]["mode"] == "token" else "seconds")
                    level_cfg["budget"][key] = level
                    budget = make_budget(level_cfg)
                    t0 = time.monotonic()
                    try:
                        res = run_fn(engine, ex["question"], ex["context"],
                                     budget, temperature=temperature)
                    except Exception as e:  # log, don't kill a 12h job
                        res = {"prediction": "", "timeout": True,
                               "trace": {"error": repr(e)}, "budget": budget.summary()}
                    res.update(
                        id=ex["id"], question=ex["question"], gold=ex["gold"],
                        gold_aliases=ex["gold_aliases"], system=system_name,
                        budget_level=level, budget_mode=cfg["budget"]["mode"],
                        wall_seconds=round(time.monotonic() - t0, 3),
                        deadline_overrun=(cfg["budget"]["mode"] == "wallclock"
                                          and budget.overran()),
                    )
                    f.write(json.dumps(res, ensure_ascii=False) + "\n")

    # ---- judging pass ----
    print("\n=== judging ===")
    for path in sorted(out_dir.glob("*.jsonl")):
        if path.name.endswith(".judged.jsonl"):
            continue
        rows = [json.loads(l) for l in path.read_text().splitlines()]
        out_path = path.with_suffix(".judged.jsonl")
        with out_path.open("w") as f:
            for row in tqdm(rows, desc=f"judge {path.stem}"):
                correct, raw = judge(engine, row["question"],
                                     row["prediction"], row["gold"])
                row["judge_correct"] = correct
                row["judge_raw"] = raw
                row["string_match"] = string_match(
                    row["prediction"], row["gold_aliases"])
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"\nDone. Results in {out_dir}. Run: python -m src.analyze {out_dir}")


if __name__ == "__main__":
    main()
