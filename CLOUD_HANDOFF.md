# Thesis cloud handoff

## Project

**Title:** Understanding Failure Modes in Multi-Agent LLM Reasoning Under Controlled Compute Budgets

This repository is the executable/source workspace for Youheng Xie's dissertation. The
cloud continuation should preserve the distinction between benchmark evidence,
machine-screening evidence, and human-audited evidence.

## Current dissertation structure

1. Introduction
2. Related Work
3. Research Questions and Analytical Framework
4. Experimental Design
5. Evaluation and Human Audit Methodology
6. Benchmark, Fine-Tuning, and Budget Results
7. Machine-Screened Failure Analysis
8. Human Audit and Transition Results
9. Discussion
10. Limitations
11. Conclusion

The current LaTeX entry point is `dissertation/latex/main.tex`. The current prose draft
is `dissertation/DISSERTATION_CURRENT_DRAFT.md`. The compiled submission candidate is
`output/pdf/DISSERTATION_FINAL_ENGLISH.pdf`.

## Evidence currently reported

- Benchmark breadth: one SAS and five MAS architectures across MuSiQue and
  2WikiMultiHopQA, frozen and v3b model variants, and 1,000/2,000-token budgets.
- Machine screen: 8,000 MAS item-configurations and 26,873 intermediate stage records.
- Human audit: 160 unique items, 400 non-repeat stage records, and 20 hidden repeats.
- Primary human outcomes: Discovery and Endorsement transitions at the final
  coordination boundary for Debate and Sequential.
- Population-weighted harmful C-to-W rate: Debate 5.45%, Sequential 0.59%.
- Population-weighted beneficial W-to-C rate: Debate 0.00%, Sequential 5.82%.

Machine labels are screening and sampling evidence, not ground truth for the primary
transition claims.

## Highest-priority unfinished revisions

1. Add a direct, operational SAS-versus-MAS definition and an architecture summary
   table early in the dissertation.
2. Add diagrams that apply SAS and the five MAS architectures to the same example
   question.
3. Add concrete target/prediction examples for exact match and token F1.
4. Include the frozen Mistral screening prompt and one complete screening-output
   example; formally define `evidence-valid accuracy`.
5. Expand the fine-tuning description with objective, data construction and training
   hyperparameters.
6. Convert per-architecture first-error counts into rates and add a consistent SAS
   versus each-MAS comparison where the stage definitions permit it.
7. Add a second independent base-model family only if time and compute permit; v3b is
   a fine-tuned Qwen3-4B variant and does not satisfy this generalisation check.

The detailed supervisor-feedback audit is in
`analysis/DISSERTATION_RESTRUCTURE_AND_REVISION_NOTES_2026-09-05.md` and the meeting
advice is in `analysis/MEETING_2026-08-28_DISSERTATION_ADVICE.md`.

## Cloud operating rules

- Do not treat unvalidated Mistral transition counts as human ground truth.
- Do not claim that SAS wins because it has a lower human-audited transition rate;
  SAS has not yet received an equivalent human process audit.
- Preserve the frozen audit strata and weights.
- Keep large meeting audio outside Git; transcripts are sufficient for cloud context.
- Before changing quantitative claims, trace them to the stored analysis outputs.
