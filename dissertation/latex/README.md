# Dissertation LaTeX project

This directory contains the formal English dissertation derived from
`DISSERTATION_CURRENT_DRAFT.md` and formatted from the supplied COM dissertation
template.

## Before submission

Edit the four metadata commands near the top of `main.tex`:

- `\studentname`
- `\supervisorname`
- `\degreeprogramme`
- `\submissiondate`

The current main-text count is approximately 18,300 words including tables and
figure captions, excluding the bibliography and appendices. This is a repository
quality-control estimate rather than an institutional word-count ruling.

The bibliography uses `unsrtnat`, so reference numbers follow the order of first
citation in the text rather than alphabetical order. Abbreviations and notation are
in Appendix A, not the front matter.

## Build

From this directory, run:

```powershell
tectonic main.tex --outdir D:\thesis\output\pdf
```

or, with a TeX Live installation:

```powershell
latexmk -pdf main.tex
```

The figures can be regenerated from the committed analysis CSV files with:

```powershell
python generate_figures.py        # the two schematics (Figures 2.1, 3.1)
$env:SCIVIZ_SKILL = "<path to the scientific-visualization skill>"
python generate_data_figures.py   # the four data figures
```

All figures are black on white, set in Times, with series separated by hatch
pattern, marker shape and line style rather than by colour.

The main evidence trail is documented in Appendix B and remains in the parent
repository under `analysis/`, `configs/`, and `results/`.
