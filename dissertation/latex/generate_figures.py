"""Schematic figures for the dissertation (Figures 2.1 and 3.1).

Set in Times (the base-14 PDF faces built into reportlab).

Drawn in black on white with square corners and no fills, so the diagrams read
identically on screen and on a monochrome printer. The four data figures are
produced separately by ``generate_data_figures.py``.
"""

from __future__ import annotations

import math
from pathlib import Path

from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLACK = "#000000"
WHITE = "#FFFFFF"


def set_stroke(c, width=0.8, color=BLACK):
    c.setStrokeColor(color)
    c.setLineWidth(width)


def box(c, x, y, w, h, width=0.8):
    """A square-cornered, unfilled rectangle."""
    c.setFillColor(WHITE)
    set_stroke(c, width)
    c.rect(x, y, w, h, fill=1, stroke=1)


def centered(c, text, x, y, font="Times-Roman", size=9, color=BLACK):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x - stringWidth(text, font, size) / 2, y, text)


def wrap(text, font, size, max_w, max_lines=3):
    lines, current = [], ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if not current or stringWidth(trial, font, size) <= max_w:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:max_lines]


def arrow(c, x1, y1, x2, y2, width=0.8):
    """Line with the head at (x2, y2); barbs swept back along the shaft."""
    set_stroke(c, width)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 5.0
    for offset in (0.42, -0.42):
        a = angle + math.pi + offset
        c.line(x2, y2, x2 + size * math.cos(a), y2 + size * math.sin(a))


def new_canvas(path, size):
    c = canvas.Canvas(str(path), pagesize=size)
    c.setFont("Times-Roman", 10)
    return c


def finish(c):
    c.showPage()
    c.save()


# Canvases are built at the exact width the document places them at
# (\textwidth is 422 pt), so nothing is scaled down and the type renders at the
# size it is set in.
TEXTWIDTH = 422.0


def left(c, text, x, y, font="Times-Roman", size=9, color=BLACK):
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text)


def rule(c, x1, y, x2, width=0.4):
    set_stroke(c, width)
    c.line(x1, y, x2, y)


def pipeline():
    w = 0.96 * TEXTWIDTH          # 405 pt, matching \includegraphics
    h = 306.0
    c = new_canvas(OUT / "analysis_pipeline.pdf", (w, h))

    centered(c, "Three evidence layers over one set of recorded runs",
             w / 2, h - 16, "Times-Bold", 10.5)

    margin = 8.0
    bw = 110.0
    gap = (w - 2 * margin - 3 * bw) / 2.0
    xs = [margin + i * (bw + gap) for i in range(3)]

    top_y, top_h = 224.0, 40.0
    mid_y, mid_h = 128.0, 56.0
    bot_y, bot_h = 46.0, 50.0

    box(c, w / 2 - 78, top_y, 156, top_h, width=1.3)
    centered(c, "Recorded benchmark runs", w / 2, top_y + 24, "Times-Bold", 8.5)
    centered(c, "9,600 item-configurations", w / 2, top_y + 11, "Times-Roman", 7.5)

    middle = [
        ("Deterministic final-output evaluation", "Normalised EM, F1, containment"),
        ("Full-trace Mistral screening", "8,000 runs; 26,873 stages"),
        ("Targeted blind human audit", "400 stages + 20 repeats"),
    ]
    bottom = [
        ("Benchmark results", "Direct outcome evidence"),
        ("Breadth and failure-location results", "Machine-screened evidence"),
        ("Primary transition estimates", "Human-audited evidence"),
    ]

    def filled(x, y, bh, title, sub):
        box(c, x, y, bw, bh)
        tl = wrap(title, "Times-Bold", 7.6, bw - 8, 3)
        sl = wrap(sub, "Times-Roman", 6.9, bw - 8, 2)
        block = len(tl) * 9.2 + len(sl) * 8.2
        ty = y + (bh + block) / 2 - 7.4
        for line in tl:
            centered(c, line, x + bw / 2, ty, "Times-Bold", 7.6)
            ty -= 9.2
        ty -= 1.5
        for line in sl:
            centered(c, line, x + bw / 2, ty, "Times-Roman", 6.9)
            ty -= 8.2

    for x, (title, sub) in zip(xs, middle):
        filled(x, mid_y, mid_h, title, sub)
    for x, (title, sub) in zip(xs, bottom):
        filled(x, bot_y, bot_h, title, sub)

    for x in xs:
        arrow(c, w / 2, top_y, x + bw / 2, mid_y + mid_h + 4, width=0.7)
        arrow(c, x + bw / 2, mid_y, x + bw / 2, bot_y + bot_h + 4, width=0.7)

    set_stroke(c, 0.8)
    c.setDash(3, 2)
    c.line(xs[1] + bw, mid_y + mid_h / 2, xs[2], mid_y + mid_h / 2)
    c.setDash()
    centered(c, "validates", (xs[1] + bw + xs[2]) / 2, mid_y + mid_h / 2 + 4,
             "Times-Italic", 6.3)

    centered(c, "Each layer is analysed on its own terms; the audit is not the last stage of a single chain.",
             w / 2, 18, "Times-Italic", 7.2)
    finish(c)


def architecture_example():
    w = 0.98 * TEXTWIDTH          # 414 pt, matching \includegraphics
    margin = 8.0
    inner = w - 2 * margin

    rows = [
        ("SAS", "one invocation, one continuous state",
         [("solver", "read both passages, date each film, compare, answer")],
         "source: pre-final reasoning     final: the prediction"),
        ("Sequential", "planner, ordered workers, aggregator",
         [("planner", "split into two date lookups"),
          ("worker 1", "date of Little Buddha"),
          ("worker 2", "date of the second film"),
          ("aggregator", "compare and answer")],
         "audited boundary: last worker     final: aggregator"),
        ("Subtask Parallel", "planner, independent workers, aggregator",
         [("planner", "split into two date lookups"),
          ("workers in parallel", "each date found without the other"),
          ("aggregator", "compare and answer")],
         "source: partial findings     final: aggregator"),
        ("Parallel Roles", "one input, several analytical views",
         [("solver, extractor, verifier, skeptic", "the same passages read four ways, in parallel"),
          ("aggregator", "select the supported view")],
         "source: candidate oracle     final: aggregator"),
        ("Debate", "propose, revise, pick",
         [("proposers A and B", "two independent answers"),
          ("cross-revision", "each sees the other, then revises"),
          ("picker", "choose one revised answer")],
         "audited boundary: revised-candidate oracle     final: picker"),
        ("Ensemble", "sample, then aggregate",
         [("four samples at T = 0.7", "four independent answers"),
          ("aggregator", "choose among the candidates")],
         "source: candidate oracle     final: aggregator"),
    ]

    row_h = 60.0
    banner_h = 32.0
    top_pad = 22.0
    h = top_pad + banner_h + 10.0 + len(rows) * row_h + 8.0
    c = new_canvas(OUT / "architecture_example.pdf", (w, h))

    centered(c, "The same question, step by step, in six architectures",
             w / 2, h - 15, "Times-Bold", 10.5)

    banner_y = h - top_pad - banner_h
    box(c, margin, banner_y, inner, banner_h, width=1.0)
    centered(c, "Which film was released earlier, Little Buddha or Course for Collision?",
             w / 2, banner_y + 18, "Times-Bold", 8.4)
    centered(c, "The passages needed to answer are supplied to every system as oracle context.",
             w / 2, banner_y + 7, "Times-Roman", 7.0)

    rows_top = banner_y - 10.0
    for i, (name, descriptor, nodes, boundary) in enumerate(rows):
        y = rows_top - (i + 1) * row_h
        if i:
            rule(c, margin, y + row_h - 2, w - margin, 0.35)

        # Name and descriptor share one baseline, which removes a whole line of
        # vertical space per row.
        left(c, name, margin, y + 48, "Times-Bold", 8.8)
        name_w = stringWidth(name, "Times-Bold", 8.8)
        left(c, "—  " + descriptor, margin + name_w + 5, y + 48, "Times-Italic", 7.2)

        n = len(nodes)
        gap = 12.0
        node_w = (inner - (n - 1) * gap) / n
        node_y, node_h = y + 11, 32.0
        for idx, (role, step) in enumerate(nodes):
            nx = margin + idx * (node_w + gap)
            box(c, nx, node_y, node_w, node_h, width=0.7)
            rl = wrap(role, "Times-Bold", 7.0, node_w - 8, 2)
            sl = wrap(step, "Times-Roman", 6.8, node_w - 8, 2)
            block = len(rl) * 8.4 + len(sl) * 7.8
            ty = node_y + (node_h + block) / 2 - 6.8
            for line in rl:
                centered(c, line, nx + node_w / 2, ty, "Times-Bold", 7.0)
                ty -= 8.4
            for line in sl:
                centered(c, line, nx + node_w / 2, ty, "Times-Roman", 6.8)
                ty -= 7.8
        for idx in range(n - 1):
            x1 = margin + idx * (node_w + gap) + node_w
            arrow(c, x1 + 1, node_y + node_h / 2, x1 + gap - 2, node_y + node_h / 2, width=0.7)

        left(c, boundary, margin, y + 2, "Times-Italic", 6.6)

    finish(c)


if __name__ == "__main__":
    pipeline()
    architecture_example()
    print("wrote analysis_pipeline.pdf and architecture_example.pdf")
