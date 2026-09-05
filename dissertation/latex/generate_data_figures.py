"""Regenerate the four data figures for the dissertation in a print-safe
black-and-white encoding.

Series are separated by hatch pattern, marker shape and line style rather than
by colour, so the figures carry the same information on a monochrome printer as
on screen. Nothing is recomputed here: every value is read from the committed
analysis CSVs, or, for the weighted human transition rates, from the frozen
unblind report.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

# Helpers from the scientific-visualization Agent Skill (K-Dense, MIT).
# Point SCIVIZ_SKILL at a checkout of
# github.com/K-Dense-AI/scientific-agent-skills, skills/scientific-visualization.
SKILL = Path(
    os.environ.get("SCIVIZ_SKILL", Path(__file__).resolve().parents[2] / "vendor"
                   / "scientific-visualization")
)
if not (SKILL / "scripts" / "style_presets.py").exists():
    raise SystemExit(
        f"scientific-visualization skill not found at {SKILL}. "
        "Set SCIVIZ_SKILL to its directory."
    )
sys.path.insert(0, str(SKILL / "scripts"))

import matplotlib as mpl
import matplotlib.pyplot as plt

from figure_export import export_figure
from style_presets import style_context

DATA = Path(__file__).resolve().parents[2] / "analysis"
# Overridable so the atomic exporter can write somewhere deletion is
# permitted; copy the finished PDFs into figures/ afterwards.
OUT = Path(os.environ.get("SCIVIZ_OUT",
                          Path(__file__).resolve().parent / "figures"))
OUT.mkdir(parents=True, exist_ok=True)

MM = 1 / 25.4
BLACK = "#000000"

# Two-series separation without colour: an open bar against a hatched bar.
FILL_A = dict(facecolor="white", edgecolor=BLACK, linewidth=0.7, hatch="")
FILL_B = dict(facecolor="white", edgecolor=BLACK, linewidth=0.7, hatch="/////")


def rows(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def bw_rc() -> dict:
    return {
        "hatch.linewidth": 0.6,
        "axes.edgecolor": BLACK,
        "axes.labelcolor": BLACK,
        "text.color": BLACK,
        "xtick.color": BLACK,
        "ytick.color": BLACK,
        "axes.grid": False,
        "legend.frameon": False,
        "legend.fontsize": 7,
        "font.size": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 7.5,
        "ytick.labelsize": 7.5,
        # Times New Roman itself is proprietary and not distributable here.
        # Liberation Serif is metrically compatible with it (identical advance
        # widths), so the rendered result matches Times New Roman line for line.
        "font.family": "serif",
        "font.serif": ["Liberation Serif", "TeX Gyre Termes", "Times New Roman",
                       "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
    }


def value_labels(ax, bars, fmt="{:.2f}", dy=0.6, size=6.5):
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            fmt.format(height),
            (bar.get_x() + bar.get_width() / 2, height),
            textcoords="offset points",
            xytext=(0, dy * 3),
            ha="center",
            va="bottom",
            fontsize=size,
        )


# ---------------------------------------------------------------- figure 6.1
def budget_tradeoff():
    data = rows(DATA / "semantic_diagnostics" / "budget_pair_tests.csv")
    overall = {r["outcome"]: r for r in data if r["group"] == "all"}
    disc = overall["semantic_gold_discovered"]
    final = overall["semantic_final_correct"]

    with style_context("default"), mpl.rc_context(bw_rc()):
        fig, (ax1, ax2) = plt.subplots(
            1, 2, figsize=(137 * MM, 68 * MM), layout="constrained",
            gridspec_kw={"width_ratios": [1.0, 1.0]},
        )

        # (a) paired outcome rates. A point encoding is used rather than bars so
        # that a non-zero axis is legitimate and the small paired differences
        # remain visible.
        series = [
            ("Discovery", float(disc["rate_b1000"]) * 100, float(disc["rate_b2000"]) * 100,
             "o", "-"),
            ("Final accuracy", float(final["rate_b1000"]) * 100, float(final["rate_b2000"]) * 100,
             "s", "--"),
        ]
        x = [0, 1]
        for label, v1, v2, marker, linestyle in series:
            ax1.plot(
                x, [v1, v2], linestyle=linestyle, color=BLACK, linewidth=1.0,
                marker=marker, markersize=4.5, markerfacecolor="white",
                markeredgecolor=BLACK, markeredgewidth=0.9, label=label, clip_on=False,
            )
            ax1.annotate(f"{v1:.2f}", (0, v1), textcoords="offset points",
                         xytext=(-6, 4), ha="right", fontsize=6.5)
            ax1.annotate(f"{v2:.2f}", (1, v2), textcoords="offset points",
                         xytext=(6, 4), ha="left", fontsize=6.5)
        ax1.set_xlim(-0.35, 1.35)
        ax1.set_xticks(x)
        ax1.set_xticklabels(["1,000", "2,000"])
        ax1.set_xlabel("Nominal thinking-token budget")
        ax1.set_ylabel("Paired rate (%)")
        ax1.set_ylim(70, 87)
        ax1.set_title("(a) Matched outcome rates", fontsize=8, loc="left")
        ax1.legend(loc="lower left", handlelength=2.6)

        # (b) the discordant pairs behind the McNemar tests. Counts, so the bars
        # start at zero.
        groups = ["Discovery", "Final accuracy"]
        improved = [int(disc["b1000_wrong_to_b2000_correct"]),
                    int(final["b1000_wrong_to_b2000_correct"])]
        worsened = [int(disc["b1000_correct_to_b2000_wrong"]),
                    int(final["b1000_correct_to_b2000_wrong"])]
        idx = [0, 1]
        width = 0.34
        b1 = ax2.bar([i - width / 2 for i in idx], improved, width,
                     label="Wrong $\\rightarrow$ correct", **FILL_A)
        b2 = ax2.bar([i + width / 2 for i in idx], worsened, width,
                     label="Correct $\\rightarrow$ wrong", **FILL_B)
        value_labels(ax2, b1, fmt="{:.0f}")
        value_labels(ax2, b2, fmt="{:.0f}")
        ax2.set_xticks(idx)
        ax2.set_xticklabels(groups)
        ax2.set_ylabel("Discordant item pairs")
        ax2.set_ylim(0, 340)
        ax2.set_title("(b) Items changing at 2,000 tokens", fontsize=8, loc="left")
        ax2.legend(loc="upper left", handlelength=1.8)

        report = export_figure(
            fig, OUT / "budget_tradeoff",
            formats=["pdf"], dpi=600, bbox_inches=None, overwrite=True,
            write_manifest=True,
            provenance={
                "raw_data": "analysis/semantic_diagnostics/budget_pair_tests.csv (group=all)",
                "transformations": ["rates scaled to percent; counts plotted as recorded"],
                "uncertainty": "exact McNemar p = 0.003465 (discovery), 0.033537 (final accuracy)",
                "notes": "panel (a) uses a non-zero point-encoded axis; panel (b) bars start at zero",
            },
        )
        plt.close(fig)
    return report


# ---------------------------------------------------------------- figure 7.1
def semantic_oracle_final():
    data = rows(DATA / "semantic_diagnostics" / "semantic_metrics.csv")
    systems = ["debate", "ensemble", "parallel_roles", "sequential"]
    names = {"debate": "Debate", "ensemble": "Ensemble",
             "parallel_roles": "Parallel\nRoles", "sequential": "Sequential"}

    with style_context("default"), mpl.rc_context(bw_rc()):
        fig, axes = plt.subplots(1, 2, figsize=(140 * MM, 78 * MM),
                                 layout="constrained", sharey=True)
        for ax, dataset, title in zip(
            axes, ["musique", "2wiki"], ["(a) MuSiQue", "(b) 2WikiMultiHopQA"]
        ):
            lookup = {
                r["system"]: r for r in data
                if r["model_variant"] == "frozen" and int(r["budget"]) == 1000
                and r["dataset"] == dataset and r["system"] in systems
            }
            idx = list(range(len(systems)))
            width = 0.36
            oracle = [float(lookup[s]["semantic_oracle_candidate_accuracy"]) for s in systems]
            final = [float(lookup[s]["semantic_final_accuracy"]) for s in systems]
            b1 = ax.bar([i - width / 2 for i in idx], oracle, width,
                        label="Candidate oracle", **FILL_A)
            b2 = ax.bar([i + width / 2 for i in idx], final, width,
                        label="Final", **FILL_B)
            value_labels(ax, b1, dy=0.4)
            value_labels(ax, b2, dy=0.4)
            ax.set_xticks(idx)
            ax.set_xticklabels([names[s] for s in systems])
            ax.set_ylim(0, 1.13)
            ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
            ax.set_title(title, fontsize=8, loc="left")
        axes[0].set_ylabel("Proportion of items")
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside lower center", ncol=2,
                   handlelength=1.8, frameon=False)

        report = export_figure(
            fig, OUT / "semantic_oracle_final",
            formats=["pdf"], dpi=600, bbox_inches=None, overwrite=True,
            write_manifest=True,
            provenance={
                "raw_data": "analysis/semantic_diagnostics/semantic_metrics.csv",
                "transformations": ["filtered to model_variant=frozen, budget=1000"],
                "uncertainty": "machine-screened point estimates; no interval reported",
                "notes": "Subtask Parallel omitted: its worker outputs are partial findings, "
                         "not full-answer candidates",
            },
        )
        plt.close(fig)
    return report


# ---------------------------------------------------------------- figure 7.2
def resource_associations():
    data = rows(DATA / "semantic_diagnostics" / "resource_associations.csv")
    labels = [
        "Discovery, under higher wall time",
        "Post-discovery drop, under higher wall time",
        "Discovery, under more thinking tokens",
        "Post-discovery drop, under more thinking tokens",
        "Harmful C$\\rightarrow$W, under destination truncation",
    ]
    markers = ["o", "s", "^", "D", "v"]
    faces = ["white", BLACK, "white", BLACK, "white"]

    with style_context("default"), mpl.rc_context(bw_rc()):
        fig, ax = plt.subplots(figsize=(134 * MM, 64 * MM), layout="constrained")
        for i, (record, label, marker, face) in enumerate(
            zip(data, labels, markers, faces)
        ):
            y = len(labels) - 1 - i
            value = float(record["adjusted_or"])
            low, high = float(record["ci_low"]), float(record["ci_high"])
            ax.plot([low, high], [y, y], color=BLACK, linewidth=0.9, solid_capstyle="butt")
            for bound in (low, high):
                ax.plot([bound, bound], [y - 0.13, y + 0.13], color=BLACK, linewidth=0.9)
            ax.plot(value, y, marker=marker, markersize=4.8, markerfacecolor=face,
                    markeredgecolor=BLACK, markeredgewidth=0.9, linestyle="none")
            ax.annotate(f"{value:.2f}", (high, y), textcoords="offset points",
                        xytext=(6, -2), fontsize=6.5)
        ax.axvline(1.0, color=BLACK, linewidth=0.8, linestyle=(0, (4, 3)))
        ax.set_xscale("log")
        ax.set_xlim(0.4, 5.2)
        ax.xaxis.set_major_locator(mpl.ticker.FixedLocator([0.5, 1.0, 2.0, 4.0]))
        ax.xaxis.set_major_formatter(mpl.ticker.FixedFormatter(["0.5", "1.0", "2.0", "4.0"]))
        ax.xaxis.set_minor_locator(mpl.ticker.NullLocator())
        ax.xaxis.set_minor_formatter(mpl.ticker.NullFormatter())
        ax.annotate("no association", (1.0, len(labels) - 0.45),
                    textcoords="offset points", xytext=(3, 0),
                    fontsize=6.3, va="top", ha="left")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(list(reversed(labels)))
        ax.set_ylim(-0.6, len(labels) - 0.4)
        ax.set_xlabel("Adjusted odds ratio (log scale)")
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="y", length=0)

        report = export_figure(
            fig, OUT / "resource_associations",
            formats=["pdf"], dpi=600, bbox_inches=None, overwrite=True,
            write_manifest=True,
            provenance={
                "raw_data": "analysis/semantic_diagnostics/resource_associations.csv",
                "transformations": ["none; adjusted_or, ci_low, ci_high plotted as recorded"],
                "uncertainty": "95% confidence intervals, fixed-effect stratification over "
                               "dataset+model_variant+budget+system",
                "notes": "observational associations, not causal effects",
            },
        )
        plt.close(fig)
    return report


# ---------------------------------------------------------------- figure 8.1
def human_transitions():
    # Weighted point estimates and approximate intervals as reported in the
    # dissertation text and analysis/final_transition_endorsement_audit/
    # UNBLIND_REPORT.md section 4 (primary U->W rule).
    values = {
        "Debate": {"harmful": (5.45, 3.01, 7.89), "beneficial": (0.00, 0.00, 0.00)},
        "Sequential": {"harmful": (0.59, 0.27, 0.90), "beneficial": (5.82, 2.28, 9.37)},
    }

    with style_context("default"), mpl.rc_context(bw_rc()):
        fig, ax = plt.subplots(figsize=(131 * MM, 68 * MM), layout="constrained")
        idx = [0, 1]
        width = 0.32
        architectures = list(values)
        harmful = [values[a]["harmful"] for a in architectures]
        beneficial = [values[a]["beneficial"] for a in architectures]

        def draw(offset, triples, fill, label):
            heights = [t[0] for t in triples]
            lower = [t[0] - t[1] for t in triples]
            upper = [t[2] - t[0] for t in triples]
            bars = ax.bar([i + offset for i in idx], heights, width, label=label, **fill)
            ax.errorbar(
                [i + offset for i in idx], heights, yerr=[lower, upper],
                fmt="none", ecolor=BLACK, elinewidth=0.9, capsize=2.6, capthick=0.9,
            )
            for bar, triple in zip(bars, triples):
                ax.annotate(
                    f"{triple[0]:.2f}%",
                    (bar.get_x() + bar.get_width() / 2, triple[2]),
                    textcoords="offset points", xytext=(0, 4),
                    ha="center", fontsize=6.8,
                )
            return bars

        draw(-width / 2, harmful, FILL_A, "Harmful C$\\rightarrow$W")
        draw(+width / 2, beneficial, FILL_B, "Beneficial W$\\rightarrow$C")
        ax.set_xticks(idx)
        ax.set_xticklabels(architectures)
        ax.set_ylabel("Population-weighted rate (%)")
        ax.set_ylim(0, 11)
        ax.legend(loc="upper left", handlelength=1.8)

        report = export_figure(
            fig, OUT / "human_transition_rates",
            formats=["pdf"], dpi=600, bbox_inches=None, overwrite=True,
            write_manifest=True,
            provenance={
                "raw_data": "analysis/final_transition_endorsement_audit/UNBLIND_REPORT.md "
                            "section 4 (weighted, primary U->W rule)",
                "transformations": ["finite-population stratum weighting; see eq. 3.7"],
                "uncertainty": "approximate 95% finite-population stratified intervals; "
                               "descriptive, not confirmatory",
                "notes": "Debate beneficial rate is 0.00% with a zero-width interval",
            },
        )
        plt.close(fig)
    return report


if __name__ == "__main__":
    for name, fn in [
        ("budget_tradeoff", budget_tradeoff),
        ("semantic_oracle_final", semantic_oracle_final),
        ("resource_associations", resource_associations),
        ("human_transition_rates", human_transitions),
    ]:
        report = fn()
        written = report.get("files") or report.get("outputs") or report
        print(f"{name}: {written}")
