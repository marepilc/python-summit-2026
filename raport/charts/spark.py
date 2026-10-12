"""Sparkline do kafli KPI.

Trend w kolorze wyciszonym, bieżący punkt w akcencie.
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp

from raport.charts.base import Canvas, Margins, T, dot


def sparkline(
    values: list[float | None],
    out: Path,
    *,
    width: float = 120,
    height: float = 30,
    color: str = T.ink.secondary,
    highlight: str = T.ink.accent,
) -> Path:
    pts = [(i, v) for i, v in enumerate(values) if v is not None]
    c = Canvas(width, height, Margins(top=4, right=5, bottom=4, left=2))
    lo = min(v for _, v in pts)
    hi = max(v for _, v in pts)
    sx = dp.LinearScale((0, len(values) - 1), (c.x0, c.x1))
    sy = dp.LinearScale((lo, hi), (c.y1, c.y0))

    line = dp.LineGenerator(
        x=lambda p, _: sx.map(p[0]), y=lambda p, _: sy.map(p[1])
    )
    area = dp.AreaGenerator(
        x0=lambda p, _: sx.map(p[0]),
        y0=lambda p, _: c.y1,
        y1=lambda p, _: sy.map(p[1]),
    )
    c.marks.append(dp.Path(area(pts), fill=color, fill_opacity=0.08))
    c.marks.append(
        dp.Path(
            line(pts),
            fill="none",
            stroke=color,
            stroke_width=1.2,
            stroke_linejoin="round",
            class_name="line",
            stroke_linecap="round",
        )
    )
    first, last = pts[0], pts[-1]
    c.marks.append(
        dot(sx.map(first[0]), sy.map(first[1]), 1.6, color, ring=None)
    )
    c.marks.append(
        dot(
            sx.map(last[0]),
            sy.map(last[1]),
            2.6,
            highlight,
            ring=T.ink.surface,
            ring_w=1.2,
        )
    )
    return c.save(out)
