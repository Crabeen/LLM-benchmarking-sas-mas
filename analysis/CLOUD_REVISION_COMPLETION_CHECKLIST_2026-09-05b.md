# Supervisor Feedback — Second Revision Pass, 2026-09-05

Follows `CLOUD_REVISION_COMPLETION_CHECKLIST_2026-09-05.md`. This pass closed the
items that pass left open as editorial, and corrected one substantive metric
reporting problem found while checking them.

Build: `latexmk -pdf` clean, 86 pages, no undefined references or citations, no
multiply-defined labels, no overfull hboxes. Main-text count 17,070 words
(15,869 excluding tables and captions), up from 14,251.

## Substantive correction: the headline metric was mislabelled

Table 6.1 and the Chapter 6 prose report **normalised containment**, not
normalised exact match. This was verified by recomputing all 24 MuSiQue and 2Wiki
cells from `results/*/[system]_b[budget].jsonl` with the normalisation defined in
§5.1: every published figure reproduces exactly under containment and none under
exact match. Examples at frozen MuSiQue, 1,000 tokens:

| System | Published | Containment | Exact match | F1 |
|---|---|---|---|---|
| SAS | 0.560 | 0.560 | 0.290 | 0.371 |
| Debate | 0.510 | 0.510 | 0.030 | 0.075 |
| Sequential | 0.335 | 0.335 | 0.125 | 0.204 |

§5.1 previously stated that "EM and F1 are therefore the transparent final-output
benchmark measures; containment and LLM judgement are reported as sensitivity or
continuity measures," which contradicted Chapter 6. Changes made:

- §5.1 now defines normalised containment formally (eq. 5.3) alongside EM and F1,
  states that containment is the headline rule, gives the reason (reproduction
  protocol; several architectures answer in a sentence, which EM barely credits),
  and states the cost (containment credits a mentioned-then-rejected answer, so
  reported accuracies are upper bounds).
- Table 5.1 extended to four rows and a containment column, including a real
  Debate final output from the frozen 2Wiki run scoring containment 1, EM 0,
  F1 0.19.
- §6.1 opens by defining the metric and cross-referencing §5.1 and Table 5.1.
- New Table 6.2 gives containment, EM and F1 for all six systems on both datasets.
- §10.6 names the bias in both directions.

## Supervisor items closed in this pass

| Item | Change |
|---|---|
| Ch1: gloss Debate and Sequential before the research questions | §1.1 now describes both architectures' stages and names their source/final boundary |
| Ch1: Tran identified failures but did not explain them | §1.1 now states this explicitly and says what a final-answer metric cannot separate |
| Ch1: multi-hop vs multi-step | §1.1 forward-references the new labelled §2.3.1 |
| Ch2: state the MAS/SAS distinction | §2.2 restates the operational boundary and cross-references Ch1 |
| Ch2: more citations | 19 → 37 references; 18 added across all five sections (surveys, CAMEL, MetaGPT, ChatEval, ReConcile, MAD, Rethinking-the-Bounds, Cemri failure taxonomy, HotpotQA, Self-Ask, IRCoT, least-to-most, Decomposed Prompting, ToT, ReAct, Uesato, position bias, self-preference) |
| Ch2/Ch4: diagram of thinking steps on one question | Figure 2.1 redrawn: real steps for the stated question, SAS as one box against multi-box MAS, source/final boundary labelled per panel |
| Ch3: aggregation regret formula | Now numbered eq. 3.6, cross-referenced from §7.1 |
| Ch3: what is exact match matching against | §3.3 names the reference set and forward-references §5.1 |
| Ch4: move §4.4 earlier | Systems moved to §4.2, with a line tying it to Table 2.1 and Figure 2.1 |
| Ch5: why not annotate raw traces | New opening to §5.2: 26,873 stages is infeasible, and rare transitions make random sampling useless; the screen is a sampling instrument |
| Ch5: screening example on a real trace | Appendix B.3 replaced with a Debate revision that discovers "Athens" and then refuses to endorse it, with its six numbered statements and full JSON |
| Ch6: figure titles visible | Figure 7.1 panel headings moved above the plot area; y-axis relabelled to match the plotted proportions; axis labels added to Figures 6.1, 7.1, 8.1 |
| Ch6: arrowheads | `arrow()` barbs were swept forward (angle+pi±2.6) so every connector pointed backwards; now ±0.42. Affected Figures 2.1 and 3.1 |
| Ch6: hidden repeat reference | §8.1 now cross-references §5.4 and Ch4 |
| Ch6: SAS vs each of the five MAS | New §6.1.1 and Table 6.3: final-answer error rates and the per-architecture difference from SAS, both datasets, both budgets |

## Still open

| Item | Why |
|---|---|
| Second model family | Requires new inference. Documented in §4.3 and §10.1 |
| SAS process-level screen | Requires a new judge run over the 1,600 SAS traces. §6.1.1 now gives the final-answer comparison and points to §8.5 for why the process comparison is deferred |
| Second annotator | Requires new annotation |

## Verification notes

- The 18 added bibliography entries were written from memory of the literature
  and have **not** been checked against the published records. Verify authors,
  venues and years before submission.
- Previous versions of every edited file are in `dissertation/latex/.bak/`, and
  the previous figure script is `generate_figures.py.bak`.


## Third pass, same day: presentation changes

| Request | Change |
|---|---|
| Citation order | `\bibliographystyle{plainnat}` -> `unsrtnat` in `main.tex`. Reference numbers now follow order of first citation in the text instead of alphabetical order by author. `[1]` is now AutoGen, the first work cited in §1.1. `natbib` options are unchanged (`numbers,sort&compress`), so multiple keys in one `\citep` are still sorted and range-compressed. |
| Survey of prior work in the introduction | New §1.2 *Prior work in brief*, about 430 words in five paragraphs: single-model reasoning; multi-agent systems and the contested debate evidence; the two results that motivate the project (Tran, Cemri); the evaluation literature (multi-hop QA, process supervision, LLM-as-judge); then the gap statement. It cites 22 of the 37 references, so the citation order established by `unsrtnat` now follows the narrative from the first page. §1.2-§1.5 renumbered to §1.3-§1.6. |
| Abbreviations in the appendix | New `appendices/abbreviations.tex`, included as **Appendix A** (the codebook, screening materials and reproducibility appendices shift to B, C and D; all cross-references use labels, so nothing broke). Two `longtable` sections: A.1 Abbreviations, 18 entries expanded from the 7 that were in the front matter, each cross-referenced to where the term is defined; A.2 Notation and label values, 13 entries covering C/W/U, the transition arrows, D(s)/E(s), T_i, n(x), G, kappa, W_h and v3b. The front-matter `\chapter*{Abbreviations}` block was removed rather than duplicated. |

Incidental: the Appendix D provenance paragraph was reflowed into a list so the long
`\path` identifiers no longer overrun the text block.

Pre-edit copies of `main.tex` and `01_introduction.tex` from this pass are in
`dissertation/latex/.bak2/`.

## Fourth pass: figures redrawn for monochrome print

All six figures rebuilt so they carry their information without colour. Series
are separated by hatch pattern, marker shape and line style; every box is square
-cornered and unfilled; all text is Times.

| Figure | Change |
|---|---|
| 2.1 Architectures | Square corners, no fill, black rules only. Times via reportlab's base-14 faces |
| 3.1 Evidence layers | Same; the source box keeps a heavier rule so the shared origin still reads first |
| 6.1 Budget | Rebuilt in Matplotlib. Panel (a) is now a point encoding, which makes the non-zero axis legitimate rather than a truncated bar chart. Panel (b) replaces the decorative "+4.83 s" callout with the discordant pair counts behind the McNemar tests (138/192 and 241/291), which is real data from `budget_pair_tests.csv`; wall time moved to the caption |
| 7.1 Oracle vs final | Open bars against hatched bars, value labels above each |
| 7.2 Resource associations | Forest plot with a distinct marker per row, dashed reference line at OR = 1 |
| 8.1 Human transitions | Open vs hatched bars, black error bars, labels above the whiskers |

Tooling: the `scientific-visualization` Agent Skill (K-Dense, MIT). Its plugin
install shipped only `SKILL.md`, so the helpers were taken from the public
repository instead. Before use, the bundled scripts were checked against the
claim in `SKILL.md` that they are deterministic and network-free: no
`requests`/`urllib`/`socket`/`subprocess`/`eval`/`exec` appears in any of them,
and `os` is used only for type hints and atomic writes.

`figure_export.py` writes each figure with a `*.export.json` manifest recording
the source CSV, the transformations applied, and how uncertainty is defined.
`image_metadata.py` confirmed each PDF holds its exact physical page size
(e.g. 140.0 x 78.0 mm for Figure 7.1) with all fonts embedded.

Fonts: Times New Roman is proprietary and cannot be embedded here. The charts use
Liberation Serif, which is metrically compatible with it, and the schematics use
the base-14 Times faces built into PDF. Both render as Times.

Two notes for future runs:

- `figure_export.py` writes atomically and so must delete a temporary file; that
  is not permitted on the mounted folder. Set `SCIVIZ_OUT` to a scratch directory
  and copy the results into `figures/` afterwards, which is what the build now does.
- The four charts are generated by `dissertation/latex/generate_data_figures.py`
  (set `SCIVIZ_SKILL` to a checkout of the skill); the two schematics by
  `dissertation/latex/generate_figures.py`. The previous colour version of the
  latter is kept at `generate_figures.py.color.bak`.

### Correction found while redrawing: the two schematics were rendering at half size

`\textwidth` is 422 pt. `architecture_example.pdf` was built on an 860 pt canvas
and placed at `0.98\textwidth` (414 pt), so it was scaled to **48%**: type set at
6.9 pt printed at about 3.3 pt. `analysis_pipeline.pdf` had the same fault at 49%.
The four data figures were unaffected — they were built to their exact placed
width in millimetres, which `image_metadata.py` confirms (e.g. 140.0 x 78.0 mm
for Figure 7.1, placed at `0.94\textwidth` = 140.1 mm).

Both schematics are now built on canvases equal to their placed width
(414 pt and 405 pt), so nothing is scaled and the type prints at the size it is
set in.

Figure 2.1 was also restructured. The old 2x3 grid of panels left most of each
panel empty, because a panel sized for a four-step chain also had to hold a
one-step one. It is now one architecture per row, full width, with the name and
descriptor sharing a baseline and the source/final boundary on a single line
beneath. Reading down the left edge now shows the structural contrast directly:
one box for SAS against four for Sequential. Height fell from 604 pt of mostly
blank canvas to 432 pt that is nearly all content.

Float-only pages are now top-aligned (`\@fptop` set to 0 pt in `main.tex`), so a
full-page figure no longer floats in the middle of an otherwise empty page.
