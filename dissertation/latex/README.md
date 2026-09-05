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

The current main-text count is approximately 12,100 words, excluding the
bibliography and appendices.

## Build

From this directory, run:

```powershell
tectonic main.tex --outdir D:\thesis\output\pdf
```

The charts can be regenerated from the committed analysis CSV files with:

```powershell
python generate_figures.py
```

The main evidence trail is documented in Appendix B and remains in the parent
repository under `analysis/`, `configs/`, and `results/`.
