"""Wykres gofrowy (waffle).

100 kratek = 100% produkcji prądu w ostatnim roku.
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp

from raport.charts.base import Canvas, Margins, T, fmt, text
from raport.theme import SOURCE_LABELS, SOURCE_ORDER


def largest_remainder(
    values: dict[str, float], total: int = 100
) -> dict[str, int]:
    """Zaokrąglenie, które ZAWSZE sumuje się do 100.

    Metoda największych reszt.
    """
    s = sum(values.values())
    raw = {k: v / s * total for k, v in values.items()}
    cells = {k: int(v) for k, v in raw.items()}
    missing = total - sum(cells.values())
    for k in sorted(raw, key=lambda k: raw[k] - cells[k], reverse=True)[
        :missing
    ]:
        cells[k] += 1
    return cells


def mix_waffle(
    share_last: dict[str, float],
    out: Path,
    *,
    width: float,
    height: float,
    year: int,
) -> Path:
    c = Canvas(width, height, Margins(top=0, right=0, bottom=0, left=0))
    cells = largest_remainder(share_last)
    cols, rows = 10, 10
    side = min(height, width * 0.55)
    gap = 2.0
    cell = (side - gap * (cols - 1)) / cols

    # wypełniamy kolumnami od dołu — węgiel „osiada” na dnie, jak w miksie
    # warstwowym
    order = [k for k in SOURCE_ORDER for _ in range(cells[k])]
    for i, key in enumerate(order):
        col, row = divmod(i, rows)
        x = col * (cell + gap)
        y = side - (row + 1) * cell - row * gap
        c.marks.append(
            dp.Rect(
                x=round(x, 2),
                y=round(y, 2),
                width=round(cell, 2),
                height=round(cell, 2),
                rx=1.6,
                fill=T.source_color(key),
                class_name="cell",
                data_i=i,
                data_key=key,
            )
        )

    # legenda-tabela: kolor + nazwa + wartość
    # (identyfikacja nigdy samym kolorem)
    lx = side + 18
    keys = [k for k in reversed(SOURCE_ORDER) if share_last[k] > 0]
    step = side / len(keys)
    for i, key in enumerate(keys):
        y = step * (i + 0.5)
        c.labels.append(
            dp.Rect(
                x=lx,
                y=round(y - 3.5, 2),
                width=7,
                height=7,
                rx=1.5,
                fill=T.source_color(key),
            )
        )
        c.labels.append(
            text(
                SOURCE_LABELS[key],
                lx + 12,
                y,
                size=T.type.label,
                fill=T.ink.secondary,
                middle=True,
            )
        )
        c.labels.append(
            text(
                fmt(share_last[key]) + "%",
                width - 2,
                y,
                size=T.type.label,
                weight=600,
                fill=T.ink.primary,
                anchor="end",
                middle=True,
            )
        )
    return c.save(out)
