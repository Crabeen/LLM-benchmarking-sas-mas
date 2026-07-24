# Making analyze.py / compare_runs.py read the unified judgements

Both scripts glob `*.judged.jsonl`. To analyse the unified grading without
duplicating them, add a suffix switch driven by an environment variable.

## analyze.py

Replace:

    for path in sorted(out_dir.glob("*.judged.jsonl")):

with:

    import os
    SUF = os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl")
    ...
    for path in sorted(out_dir.glob(SUF)):

## compare_runs.py

Replace, inside `load()`:

    for p in sorted(Path(dir_path).glob("*.judged.jsonl")):

with:

    import os
    for p in sorted(Path(dir_path).glob(os.environ.get("JUDGE_SUFFIX", "*.judged.jsonl"))):

## grounding_metric.py

Replace:

    p = Path(d) / "sas_b1000.judged.jsonl"

with:

    import os
    p = Path(d) / os.environ.get("SAS_FILE", "sas_b1000.judged.jsonl")

## Usage

    # per-arm judging (original)
    python -m src.analyze results/pilot_token

    # unified judging
    JUDGE_SUFFIX='*.rejudged.jsonl' python -m src.analyze results/pilot_token
    JUDGE_SUFFIX='*.rejudged.jsonl' python -m src.compare_runs \
        results/pilot_token results/finetuned_token
    SAS_FILE=sas_b1000.rejudged.jsonl python -m src.grounding_metric results/v2b_token
