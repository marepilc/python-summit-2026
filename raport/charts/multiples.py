"""Małe wielokrotności (small multiples).

Wspólna skala Y = uczciwe porównanie panelu z panelem.
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp
from pydreamplet.utils import calculate_ticks

from raport.charts.base import Canvas, Margins, T, dot, fmt, hline, text
from raport.theme import SOURCE_LABELS


def growth_multiples(
    years: list[int],
    twh: dict[str, list[float]],
    keys: list[str],
    out: Path,
    *,
    width: float,
    height: float,
    start_year: int = 2000,
) -> Path:
    i0 = years.index(start_year)
    ys = years[i0:]
    series = {k: twh[k][i0:] for k in keys}
    vmax = max(max(v) for v in series.values())
    ticks = calculate_ticks(0, vmax * 1.08, 3)

    c = Canvas(width, height, Margins(top=0, right=0, bottom=0, left=0))
    gap = 16.0
    axis_w = 18.0
    panel_w = (width - axis_w - gap * (len(keys) - 1)) / len(keys)
    title_h, foot_h = 16.0, 13.0
    py0, py1 = title_h + 6, height - foot_h
    sy = dp.LinearScale((0, max(ticks[-1], vmax * 1.12)), (py1, py0))

    # wspólna oś Y — tylko raz, po lewej
    for t in ticks:
        c.labels.append(
            text(
                fmt(t, 0),
                axis_w - 5,
                sy.map(t),
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="end",
                middle=True,
            )
        )
    c.labels.append(text("TWh", 0, py0 - 8, size=T.type.tick, fill=T.ink.muted))

    for n, key in enumerate(keys):
        px0 = axis_w + n * (panel_w + gap)
        px1 = px0 + panel_w - 14  # miejsce na kropkę końcową
        sx = dp.LinearScale((ys[0], ys[-1]), (px0, px1))
        color = T.source_color(key)
        values = series[key]

        for t in ticks:
            c.grid.append(
                hline(
                    px0,
                    px0 + panel_w,
                    sy.map(t),
                    stroke=T.ink.rule if t else T.ink.rule_strong,
                )
            )

        rows = list(zip(ys, values, strict=True))
        # sx=sx: wiążemy skalę bieżącego panelu (lambda w pętli)
        area = dp.AreaGenerator(
            x0=lambda r, _, sx=sx: sx.map(r[0]),
            y0=lambda r, _: sy.map(0),
            y1=lambda r, _: sy.map(r[1]),
        )
        line = dp.LineGenerator(
            x=lambda r, _, sx=sx: sx.map(r[0]),
            y=lambda r, _: sy.map(r[1]),
        )
        c.marks.append(
            dp.Path(
                area(rows),
                fill=color,
                fill_opacity=0.14,
                class_name="wash",
                data_panel=n,
            )
        )
        c.marks.append(
            dp.Path(
                line(rows),
                fill="none",
                stroke=color,
                stroke_width=1.6,
                stroke_linejoin="round",
                stroke_linecap="round",
                class_name="line",
                data_panel=n,
            )
        )
        ex, ey = sx.map(ys[-1]), sy.map(values[-1])
        c.marks.append(
            dot(ex, ey, 2.6, color).set_class("end").set_attr("data-panel", n)
        )

        # tytuł panelu: kreska-klucz w kolorze serii + nazwa w tokenie tekstu
        c.labels.append(
            dp.Rect(x=px0, y=4, width=10, height=3, rx=1.5, fill=color)
        )
        c.labels.append(
            text(
                SOURCE_LABELS[key],
                px0 + 14,
                5.5,
                size=T.type.label,
                weight=600,
                fill=T.ink.primary,
                middle=True,
            )
        )
        # wartość końcowa nad kropką
        c.labels.append(
            text(
                fmt(values[-1]),
                ex,
                ey - 6,
                size=T.type.label,
                weight=600,
                fill=T.ink.primary,
                anchor="middle",
            )
            .set_class("value")
            .set_attr("data-panel", n)
        )
        # oś X: tylko początek i koniec
        c.labels.append(
            text(
                str(ys[0]), px0, height - 3, size=T.type.tick, fill=T.ink.muted
            )
        )
        c.labels.append(
            text(
                str(ys[-1]),
                ex,
                height - 3,
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="middle",
            )
        )

    return c.save(out)
