"""„Paski węglowe” — okładka. Inspiracja: warming stripes Eda Hawkinsa.

Jeden pasek = jeden rok, kolor = udział węgla w produkcji prądu.
Zero osi, zero siatki: to ma być obraz, który zostaje w głowie.
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp

from raport.charts.base import Canvas, Margins, T, fmt, ramp, text
from raport.theme import COAL_RAMP


def coal_stripes(
    years: list[int],
    coal_share: list[float],
    out: Path,
    *,
    width: float,
    height: float,
) -> Path:
    label_band = 16
    c = Canvas(
        width, height, Margins(top=0, right=0, bottom=label_band, left=0)
    )
    n = len(years)
    gap = (
        0.6  # wąska szczelina w kolorze papieru — paski czytają się jak „lata”
    )
    band = dp.BandScale(years, (c.x0, c.x1), padding=0, outer_padding=0)
    # skala względna (jak w warming stripes): pełen kontrast w zakresie,
    # który faktycznie wystąpił
    lo, hi = (min(coal_share) // 10) * 10 - 10, 100.0

    for year, share in zip(years, coal_share, strict=True):
        x = band.map(year)
        c.marks.append(
            dp.Rect(
                x=round(x, 2),
                y=c.y0,
                width=round(band.bandwidth - gap, 2),
                height=c.y1 - c.y0,
                fill=ramp(COAL_RAMP, (share - lo) / (hi - lo)),
                class_name="stripe",
                data_value=round(share, 1),
            )
        )

    # podpisy: pierwszy, ostatni rok + wartości skrajne nad paskiem
    def annotate(i: int, anchor: str) -> None:
        x = band.map(years[i]) + (
            0 if anchor == "start" else band.bandwidth - gap
        )
        c.labels.append(
            text(
                str(years[i]),
                x,
                c.y1 + 11,
                size=T.type.label,
                weight=600,
                fill=T.ink.primary,
                anchor=anchor,
            )
        )

    annotate(0, "start")
    annotate(n - 1, "end")
    mid = years.index(2004) if 2004 in years else n // 2
    c.labels.append(
        text(
            "Każdy pasek to jeden rok · im ciemniej, tym więcej węgla "
            f"(od {fmt(min(coal_share), 0)}% do {fmt(max(coal_share), 0)}%)",
            band.map(years[mid]) + band.bandwidth / 2,
            c.y1 + 11,
            size=T.type.tick,
            fill=T.ink.muted,
            anchor="middle",
        )
    )
    return c.save(out)
