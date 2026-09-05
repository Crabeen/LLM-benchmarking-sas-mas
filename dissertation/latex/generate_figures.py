from __future__ import annotations

import csv
import math
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

VIOLET = "#442359"
BLUE = "#23567A"
TEAL = "#2A7F7F"
GOLD = "#C18F2D"
RED = "#A64040"
GRAY = "#69727A"
LIGHT = "#F2EFF5"


def rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def set_stroke(c, color, width=1):
    c.setStrokeColor(color)
    c.setLineWidth(width)


def centered(c, text, x, y, font="Helvetica", size=9, color="#222222"):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x - stringWidth(text, font, size) / 2, y, text)


def finish(c):
    c.showPage()
    c.save()


def pipeline():
    path = OUT / "analysis_pipeline.pdf"
    w, h = 800, 292
    c = canvas.Canvas(str(path), pagesize=(w, h))
    box_data = [
        (18, 157, 139, 72, "Recorded traces", "9,600 item-configurations", LIGHT),
        (176, 157, 139, 72, "Lexical outcomes", "Exact match and F1", "#EDF3F7"),
        (334, 157, 139, 72, "Semantic screen", "26,873 MAS stages", "#E8F4F2"),
        (492, 157, 139, 72, "Blind human audit", "400 stages + 20 repeats", "#FBF2E1"),
        (650, 157, 132, 72, "Primary inference", "Weighted transitions", "#F8EAEA"),
    ]
    for x, y, bw, bh, title, subtitle, fill in box_data:
        c.setFillColor(fill)
        set_stroke(c, VIOLET, 1.3)
        c.roundRect(x, y, bw, bh, 7, fill=1, stroke=1)
        centered(c, title, x + bw / 2, y + 43, "Helvetica-Bold", 9.5, VIOLET)
        centered(c, subtitle, x + bw / 2, y + 22, "Helvetica", 7.3, "#333333")
    c.setFillColor(GRAY)
    set_stroke(c, GRAY, 1.5)
    for x in [158, 316, 474, 632]:
        c.line(x, 193, x + 14, 193)
        c.line(x + 14, 193, x + 9, 197)
        c.line(x + 14, 193, x + 9, 189)
    centered(c, "Discovery: is answer-equivalent evidence present?", 400, 91, "Helvetica-Bold", 10, BLUE)
    centered(c, "Endorsement: does the stage commit to that answer?", 400, 62, "Helvetica-Bold", 10, TEAL)
    centered(c, "Machine labels support screening; human labels support the primary transition estimates.", 400, 25, "Helvetica", 8.3, GRAY)
    finish(c)


def semantic_oracle_final():
    data = rows(ROOT / "analysis" / "semantic_diagnostics" / "semantic_metrics.csv")
    systems = ["debate", "ensemble", "parallel_roles", "sequential"]
    names = {"debate": "Debate", "ensemble": "Ensemble", "parallel_roles": "Parallel Roles", "sequential": "Sequential"}
    w, h = 800, 330
    c = canvas.Canvas(str(OUT / "semantic_oracle_final.pdf"), pagesize=(w, h))
    centered(c, "Candidate availability versus final semantic accuracy", w / 2, h - 25, "Helvetica-Bold", 13, VIOLET)
    c.setFillColor(BLUE); c.rect(288, h - 47, 12, 8, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(420, h - 47, 12, 8, fill=1, stroke=0)
    c.setFillColor("#222222"); c.setFont("Helvetica", 8); c.drawString(305, h - 46, "Candidate oracle"); c.drawString(437, h - 46, "Final")
    plot_y, plot_h = 58, 212
    for panel, dataset in enumerate(["musique", "2wiki"]):
        x0 = 48 + panel * 390
        pw = 332
        subset = [r for r in data if r["model_variant"] == "frozen" and int(r["budget"]) == 1000 and r["dataset"] == dataset and r["system"] in systems]
        lookup = {r["system"]: r for r in subset}
        set_stroke(c, "#B5BBC0", 0.6)
        for tick in range(0, 101, 20):
            yy = plot_y + plot_h * tick / 100
            c.line(x0, yy, x0 + pw, yy)
            c.setFillColor(GRAY); c.setFont("Helvetica", 7); c.drawRightString(x0 - 5, yy - 2, str(tick))
        centered(c, "MuSiQue" if dataset == "musique" else "2WikiMultiHopQA", x0 + pw / 2, h - 68, "Helvetica-Bold", 10, "#222222")
        group_w = pw / 4
        bar_w = 22
        for idx, sys in enumerate(systems):
            r = lookup[sys]
            oracle = float(r["semantic_oracle_candidate_accuracy"])
            final = float(r["semantic_final_accuracy"])
            center = x0 + group_w * (idx + 0.5)
            for val, bx, color in [(oracle, center - bar_w - 2, BLUE), (final, center + 2, GOLD)]:
                bh = plot_h * val
                c.setFillColor(color); c.rect(bx, plot_y, bar_w, bh, fill=1, stroke=0)
                centered(c, f"{val:.2f}", bx + bar_w / 2, plot_y + bh + 5, "Helvetica", 6.5, "#333333")
            centered(c, names[sys], center, 38 if sys != "parallel_roles" else 31, "Helvetica", 7.2, "#333333")
    c.save()


def human_transitions():
    w, h = 620, 345
    c = canvas.Canvas(str(OUT / "human_transition_rates.pdf"), pagesize=(w, h))
    centered(c, "Population-weighted human transition rates", w / 2, h - 28, "Helvetica-Bold", 13, VIOLET)
    c.setFillColor(RED); c.rect(166, h - 52, 12, 8, fill=1, stroke=0)
    c.setFillColor(TEAL); c.rect(350, h - 52, 12, 8, fill=1, stroke=0)
    c.setFillColor("#222222"); c.setFont("Helvetica", 8); c.drawString(184, h - 51, "Harmful C-to-W"); c.drawString(368, h - 51, "Beneficial W-to-C")
    plot_x, plot_y, plot_w, plot_h = 70, 62, 500, 220
    max_y = 10.0
    set_stroke(c, "#B5BBC0", 0.6)
    for tick in range(0, 11, 2):
        yy = plot_y + plot_h * tick / max_y
        c.line(plot_x, yy, plot_x + plot_w, yy)
        c.setFillColor(GRAY); c.setFont("Helvetica", 7); c.drawRightString(plot_x - 6, yy - 2, str(tick))
    values = {
        "Debate": [(5.45, 3.01, 7.89, RED), (0.00, 0.00, 0.00, TEAL)],
        "Sequential": [(0.59, 0.27, 0.90, RED), (5.82, 2.28, 9.37, TEAL)],
    }
    centers = [210, 430]
    for center, (arch, vals) in zip(centers, values.items()):
        for offset, (val, low, high, color) in zip([-28, 28], vals):
            bx = center + offset - 19
            bh = plot_h * val / max_y
            c.setFillColor(color); c.rect(bx, plot_y, 38, bh, fill=1, stroke=0)
            ey1 = plot_y + plot_h * low / max_y
            ey2 = plot_y + plot_h * high / max_y
            set_stroke(c, "#333333", 1.1); c.line(center + offset, ey1, center + offset, ey2); c.line(center + offset - 5, ey1, center + offset + 5, ey1); c.line(center + offset - 5, ey2, center + offset + 5, ey2)
            centered(c, f"{val:.2f}%", center + offset, plot_y + bh + 8, "Helvetica", 8, "#222222")
        centered(c, arch, center, 40, "Helvetica-Bold", 9.5, "#222222")
    c.save()


def budget_tradeoff():
    data = rows(ROOT / "analysis" / "semantic_diagnostics" / "budget_pair_tests.csv")
    overall = {r["outcome"]: r for r in data if r["group"] == "all"}
    disc = overall["semantic_gold_discovered"]
    final = overall["semantic_final_correct"]
    w, h = 760, 330
    c = canvas.Canvas(str(OUT / "budget_tradeoff.pdf"), pagesize=(w, h))
    centered(c, "Matched budget outcomes and latency", w / 2, h - 27, "Helvetica-Bold", 13, VIOLET)
    c.setFillColor(BLUE); c.rect(160, h - 51, 12, 8, fill=1, stroke=0)
    c.setFillColor(GOLD); c.rect(290, h - 51, 12, 8, fill=1, stroke=0)
    c.setFillColor("#222222"); c.setFont("Helvetica", 8); c.drawString(178, h - 50, "1,000 tokens"); c.drawString(308, h - 50, "2,000 tokens")
    plot_y, plot_h = 62, 205
    x0, pw = 65, 390
    min_y, max_y = 65, 88
    set_stroke(c, "#B5BBC0", 0.6)
    for tick in [65, 70, 75, 80, 85]:
        yy = plot_y + plot_h * (tick - min_y) / (max_y - min_y)
        c.line(x0, yy, x0 + pw, yy)
        c.setFillColor(GRAY); c.setFont("Helvetica", 7); c.drawRightString(x0 - 5, yy - 2, str(tick))
    groups = [("Discovery", float(disc["rate_b1000"]) * 100, float(disc["rate_b2000"]) * 100), ("Final accuracy", float(final["rate_b1000"]) * 100, float(final["rate_b2000"]) * 100)]
    for center, (label, v1, v2) in zip([165, 350], groups):
        for val, off, color in [(v1, -25, BLUE), (v2, 5, GOLD)]:
            bh = plot_h * (val - min_y) / (max_y - min_y)
            c.setFillColor(color); c.rect(center + off, plot_y, 25, bh, fill=1, stroke=0)
            centered(c, f"{val:.2f}", center + off + 12.5, plot_y + bh + 6, "Helvetica", 7.2, "#222222")
        centered(c, label, center, 40, "Helvetica-Bold", 8.5, "#222222")
    rx, rw = 520, 165
    wall = float(final["mean_wall_change_seconds"])
    c.setFillColor(LIGHT); set_stroke(c, VIOLET, 1.1); c.roundRect(rx, 80, rw, 142, 8, fill=1, stroke=1)
    centered(c, "Mean paired wall-time", rx + rw / 2, 188, "Helvetica-Bold", 9, VIOLET)
    centered(c, "change per item", rx + rw / 2, 171, "Helvetica", 8.5, VIOLET)
    centered(c, f"+{wall:.2f} s", rx + rw / 2, 124, "Helvetica-Bold", 23, RED)
    centered(c, "2,000 minus 1,000 tokens", rx + rw / 2, 97, "Helvetica", 7.5, GRAY)
    c.save()


def resource_associations():
    data = rows(ROOT / "analysis" / "semantic_diagnostics" / "resource_associations.csv")
    labels = [
        "Higher wall time -> discovery",
        "Higher wall time -> post-discovery drop",
        "More thinking tokens -> discovery",
        "More thinking tokens -> post-discovery drop",
        "Destination truncation -> C-to-W",
    ]
    w, h = 760, 350
    c = canvas.Canvas(str(OUT / "resource_associations.pdf"), pagesize=(w, h))
    centered(c, "Resource exposure and semantic outcomes", w / 2, h - 28, "Helvetica-Bold", 13, VIOLET)
    x0, x1 = 300, 705
    xmin, xmax = 0.4, 4.0
    def sx(v):
        return x0 + (math.log(v) - math.log(xmin)) / (math.log(xmax) - math.log(xmin)) * (x1 - x0)
    set_stroke(c, "#B5BBC0", 0.6)
    for tick in [0.5, 1.0, 2.0, 4.0]:
        xx = sx(tick); c.line(xx, 55, xx, 298); centered(c, str(tick), xx, 38, "Helvetica", 7, GRAY)
    set_stroke(c, GRAY, 1.2); c.setDash(4, 3); c.line(sx(1.0), 55, sx(1.0), 298); c.setDash()
    colors = [BLUE, RED, BLUE, RED, GOLD]
    for idx, (r, label, color) in enumerate(zip(data, labels, colors)):
        y = 270 - idx * 46
        value, low, high = float(r["adjusted_or"]), float(r["ci_low"]), float(r["ci_high"])
        c.setFillColor("#222222"); c.setFont("Helvetica", 8.2); c.drawRightString(x0 - 14, y - 3, label)
        set_stroke(c, color, 2); c.line(sx(low), y, sx(high), y); c.line(sx(low), y - 4, sx(low), y + 4); c.line(sx(high), y - 4, sx(high), y + 4)
        c.setFillColor(color); c.circle(sx(value), y, 4, fill=1, stroke=0)
        c.setFillColor("#222222"); c.setFont("Helvetica", 7.3); c.drawString(min(sx(high) + 8, x1 - 25), y - 3, f"{value:.2f}")
    centered(c, "Adjusted odds ratio (log scale)", (x0 + x1) / 2, 16, "Helvetica", 8.5, "#222222")
    c.save()


if __name__ == "__main__":
    pipeline()
    semantic_oracle_final()
    human_transitions()
    budget_tradeoff()
    resource_associations()
