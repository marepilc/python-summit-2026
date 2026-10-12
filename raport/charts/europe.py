"""Polska na tle UE: dumbbell (zmiana udziału węgla) + ranking emisyjności.

Technika wyróżnienia: wszystko szare, jeden kraj w kolorze akcentu.
Czytelnik nie musi szukać Polski — Polska znajduje jego.
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp
from pydreamplet.utils import calculate_ticks

from raport.charts.base import (
    Canvas,
    Margins,
    T,
    dot,
    fmt,
    text,
    text_width,
    vline,
)
from raport.data import CountryRow

NEUTRAL = "#B4ADA3"
NEUTRAL_SOFT = "#D9D3CA"


def coal_dumbbell(
    rows: list[CountryRow],
    eu_avg: dict[str, float],
    out: Path,
    *,
    width: float,
    start_year: int,
    end_year: int,
    min_start: float = 10.0,
    row_h: float = 22.0,
) -> Path:
    data = [r for r in rows if r.coal_start >= min_start]
    data.sort(key=lambda r: r.coal_end, reverse=True)
    eu = CountryRow(
        "EU",
        "Średnia UE-27",
        eu_avg["coal_start"],
        eu_avg["coal_end"],
        eu_avg["intensity_end"],
        eu_avg["renewables_end"],
    )
    entries: list[CountryRow | None] = [
        *data,
        None,
        eu,
    ]  # None = odstęp przed średnią

    label_w = (
        max(text_width(r.name_pl, T.type.label, 600) for r in data + [eu]) + 10
    )
    header = 22
    height = header + row_h * len(entries) + 14
    c = Canvas(
        width, height, Margins(top=header, right=34, bottom=14, left=label_w)
    )
    sx = dp.LinearScale((0, 100), (c.x0, c.x1))

    for t in (0, 25, 50, 75, 100):
        x = sx.map(t)
        c.grid.append(vline(x, c.y0 - 4, c.y1, stroke=T.ink.rule))
        c.labels.append(
            text(
                f"{t}%",
                x,
                c.y1 + 10,
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="middle",
            )
        )

    # legenda kształtów: pusta = rok początkowy, pełna = końcowy
    lx = c.x0
    c.labels.append(
        dot(lx + 3, 7, 3, T.ink.paper, ring=T.ink.secondary, ring_w=1.2)
    )
    c.labels.append(
        text(
            str(start_year),
            lx + 10,
            7,
            size=T.type.tick,
            fill=T.ink.secondary,
            middle=True,
        )
    )
    lx2 = lx + 16 + text_width(str(start_year), T.type.tick)
    c.labels.append(dot(lx2 + 3, 7, 3.2, T.ink.secondary, ring=None))
    c.labels.append(
        text(
            str(end_year),
            lx2 + 10,
            7,
            size=T.type.tick,
            fill=T.ink.secondary,
            middle=True,
        )
    )

    for i, r in enumerate(entries):
        if r is None:
            continue
        y = c.y0 + row_h * (i + 0.5)
        is_pl = r.country == "Poland"
        is_eu = r.country == "EU"
        color = T.ink.accent if is_pl else (T.ink.primary if is_eu else NEUTRAL)
        if is_pl:
            c.grid.append(
                dp.Rect(
                    x=0,
                    y=round(y - row_h / 2, 2),
                    width=width,
                    height=row_h,
                    fill=T.ink.accent,
                    opacity=0.08,
                )
            )
        x0, x1 = sx.map(r.coal_start), sx.map(r.coal_end)
        # data-dx: slajdy animują „przejazd” kropki z roku początkowego
        # do końcowego
        row = dp.G(
            class_name="row", data_dx=round(x0 - x1, 2), data_country=r.country
        )
        c.marks.append(row)
        row.append(
            dp.Line(
                x1=x0,
                y1=y,
                x2=x1,
                y2=y,
                stroke=color,
                stroke_width=2 if is_pl or is_eu else 1.4,
                stroke_linecap="round",
                opacity=1 if is_pl or is_eu else 0.8,
                class_name="stem",
            )
        )
        row.append(
            dot(x0, y, 3, T.ink.paper, ring=color, ring_w=1.2).set_class(
                "start"
            )
        )
        row.append(dot(x1, y, 3.4, color).set_class("end"))
        weight = 600 if is_pl or is_eu else 400
        ink = T.ink.primary if is_pl or is_eu else T.ink.secondary
        c.labels.append(
            text(
                r.name_pl,
                c.x0 - 10,
                y,
                size=T.type.label,
                weight=weight,
                fill=ink,
                anchor="end",
                middle=True,
            )
        )
        if is_pl or is_eu:  # wartości tylko tam, gdzie jest historia
            c.labels.append(
                text(
                    fmt(r.coal_start, 0) + "%",
                    x0 + 6,
                    y,
                    size=T.type.tick,
                    fill=T.ink.secondary,
                    middle=True,
                )
            )
            c.labels.append(
                text(
                    fmt(r.coal_end, 0) + "%",
                    x1 - 6,
                    y,
                    size=T.type.tick,
                    weight=600,
                    fill=T.ink.primary,
                    anchor="end",
                    middle=True,
                )
            )
    return c.save(out)


def intensity_ranking(
    rows: list[CountryRow],
    eu_avg: dict[str, float],
    out: Path,
    *,
    width: float,
    row_h: float = 16.0,
) -> Path:
    data = sorted(rows, key=lambda r: r.intensity_end, reverse=True)
    label_w = max(text_width(r.name_pl, T.type.tick, 600) for r in data) + 8
    header = 16
    height = header + row_h * len(data) + 14
    vmax = max(r.intensity_end for r in data)
    ticks = calculate_ticks(0, vmax, 4)
    c = Canvas(
        width, height, Margins(top=header, right=30, bottom=14, left=label_w)
    )
    sx = dp.LinearScale(
        (0, ticks[-1] if ticks[-1] >= vmax else vmax), (c.x0, c.x1)
    )
    bar = min(row_h * 0.62, 24)

    for t in ticks:
        x = sx.map(t)
        c.grid.append(vline(x, c.y0, c.y1, stroke=T.ink.rule))
        c.labels.append(
            text(
                fmt(t, 0),
                x,
                c.y1 + 10,
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="middle",
            )
        )

    for i, r in enumerate(data):
        y = c.y0 + row_h * i + (row_h - bar) / 2
        is_pl = r.country == "Poland"
        w = sx.map(r.intensity_end) - c.x0
        # 2 pt zaokrąglenie po stronie wartości, kwadratowo przy osi
        rad = min(2.0, bar / 2, w / 2)
        d = (
            f"M{c.x0:.2f},{y:.2f} h{w - rad:.2f} "
            f"a{rad},{rad} 0 0 1 {rad},{rad} v{bar - 2 * rad:.2f} "
            f"a{rad},{rad} 0 0 1 {-rad},{rad} h{-(w - rad):.2f} Z"
        )
        c.marks.append(
            dp.Path(
                d,
                fill=T.ink.accent if is_pl else NEUTRAL_SOFT,
                class_name="bar",
                data_i=i,
            )
        )
        yc = y + bar / 2
        c.labels.append(
            text(
                r.name_pl,
                c.x0 - 6,
                yc,
                size=T.type.tick,
                weight=600 if is_pl else 400,
                fill=T.ink.primary if is_pl else T.ink.secondary,
                anchor="end",
                middle=True,
            )
        )
        if is_pl or i == len(data) - 1:
            c.labels.append(
                text(
                    fmt(r.intensity_end, 0),
                    c.x0 + w + 4,
                    yc,
                    size=T.type.tick,
                    weight=600,
                    fill=T.ink.primary,
                    middle=True,
                )
            )

    # linia średniej UE — z podpisem, nie w legendzie
    xa = sx.map(eu_avg["intensity_end"])
    c.annotations.append(
        dp.Line(
            x1=xa,
            y1=c.y0 - 6,
            x2=xa,
            y2=c.y1,
            stroke=T.ink.primary,
            stroke_width=0.75,
        )
    )
    c.labels.append(
        text(
            f"Średnia UE: {fmt(eu_avg['intensity_end'], 0)}",
            xa + 4,
            c.y0 - 6,
            size=T.type.tick,
            weight=600,
            fill=T.ink.primary,
        )
    )
    c.labels.append(
        text(
            "gCO₂/kWh",
            c.x1 + 28,
            c.y1 + 10,
            size=T.type.tick,
            fill=T.ink.muted,
            anchor="end",
        )
    )
    return c.save(out)
