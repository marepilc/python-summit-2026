"""Wspólny „szkielet” wykresów: płótno, pomiar tekstu, osie, format liczb.

Każdy wykres w raporcie powstaje z tych samych klocków, więc wygląda jak część
jednego systemu — a nie jak siedem obrazków z siedmiu różnych narzędzi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache, lru_cache
from pathlib import Path

import pydreamplet as dp
from pydreamplet.typography import TypographyMeasurer

from raport.theme import FONT_FILES, THEME

T = THEME
CAP = 0.727  # wysokość wersalików Inter (em) — do pionowego centrowania tekstu


# ------------------------------------------------------------ liczby po polsku
def fmt(value: float, digits: int = 1, *, sign: bool = False) -> str:
    """50.37 → '50,4'; 12345 → '12 345' (spacja niełamliwa wąska)."""
    text = f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")
    if sign and value > 0:
        text = "+" + text
    return text.replace("-", "−")


# ---------------------------------------------------------------- pomiar tekstu
@cache
def _measurer(family: str, weight: int) -> TypographyMeasurer:
    path = FONT_FILES[(family, weight)]
    return TypographyMeasurer(font_path=str(path))


@lru_cache(maxsize=4096)
def text_width(
    text: str, size: float, weight: int = 400, family: str = T.type.sans
) -> float:
    """Szerokość tekstu w pt — liczona z prawdziwych metryk fontu (HarfBuzz)."""
    width, _ = _measurer(family, weight).measure_text(text, font_size=size)
    return width


# ---------------------------------------------------------------- płótno
@dataclass
class Margins:
    top: float = 8
    right: float = 8
    bottom: float = 18
    left: float = 28


@dataclass
class Canvas:
    """SVG w jednostkach pt + obszar rysowania (plot) wewnątrz marginesów."""

    width: float
    height: float
    margins: Margins = field(default_factory=Margins)

    def __post_init__(self) -> None:
        self.svg = dp.SVG(self.width, self.height)
        # warstwy — kolejność rysowania jest częścią designu
        self.grid = dp.G(class_name="grid")
        self.marks = dp.G(class_name="marks")
        self.annotations = dp.G(class_name="annotations")
        self.labels = dp.G(class_name="labels")
        self.svg.append(self.grid, self.marks, self.annotations, self.labels)

    # obszar wykresu
    @property
    def x0(self) -> float:
        return self.margins.left

    @property
    def x1(self) -> float:
        return self.width - self.margins.right

    @property
    def y0(self) -> float:
        return self.margins.top

    @property
    def y1(self) -> float:
        return self.height - self.margins.bottom

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.svg.save(str(path))
        return path


# ---------------------------------------------------------------- prymitywy
def text(
    content: str,
    x: float,
    y: float,
    *,
    size: float = T.type.label,
    weight: int = 400,
    fill: str = T.ink.secondary,
    anchor: str = "start",
    family: str = T.type.sans,
    middle: bool = False,
) -> dp.Text:
    """Tekst w tokenach typografii.

    `middle=True` centruje w pionie po wysokości wersalików.
    """
    baseline = y + size * CAP / 2 if middle else y
    return dp.Text(
        content,
        x=round(x, 2),
        y=round(baseline, 2),
        font_family=family,
        font_size=size,
        font_weight=weight,
        fill=fill,
        text_anchor=anchor,
    )


def hline(
    x1: float,
    x2: float,
    y: float,
    *,
    stroke: str = T.ink.rule,
    width: float = 0.5,
) -> dp.Line:
    return dp.Line(x1=x1, y1=y, x2=x2, y2=y, stroke=stroke, stroke_width=width)


def vline(
    x: float,
    y1: float,
    y2: float,
    *,
    stroke: str = T.ink.rule,
    width: float = 0.5,
) -> dp.Line:
    return dp.Line(x1=x, y1=y1, x2=x, y2=y2, stroke=stroke, stroke_width=width)


def dot(
    x: float,
    y: float,
    r: float,
    fill: str,
    *,
    ring: str | None = T.ink.paper,
    ring_w: float = 1.5,
) -> dp.Circle:
    """Kropka z pierścieniem w kolorze tła — czytelna na liniach i w tłoku."""
    attrs = {"stroke": ring, "stroke_width": ring_w} if ring else {}
    return dp.Circle(pos=(round(x, 2), round(y, 2)), r=r, fill=fill, **attrs)


def y_axis(
    c: Canvas,
    scale: dp.LinearScale,
    ticks: list[float],
    *,
    suffix: str = "",
    digits: int = 0,
    grid: bool = True,
) -> None:
    """Oś Y bez linii osi: same etykiety + włoskowate linie siatki."""
    for t in ticks:
        y = scale.map(t)
        if grid:
            c.grid.append(hline(c.x0, c.x1, y, stroke=T.ink.rule))
        c.labels.append(
            text(
                fmt(t, digits) + suffix,
                c.x0 - 5,
                y,
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="end",
                middle=True,
            )
        )


def x_year_axis(
    c: Canvas, scale: dp.LinearScale, years: list[int], *, baseline: bool = True
) -> None:
    if baseline:
        c.grid.append(
            hline(c.x0, c.x1, c.y1, stroke=T.ink.rule_strong, width=0.75)
        )
    for year in years:
        x = scale.map(year)
        c.grid.append(
            vline(x, c.y1, c.y1 + 3, stroke=T.ink.rule_strong, width=0.75)
        )
        c.labels.append(
            text(
                str(year),
                x,
                c.y1 + 11,
                size=T.type.tick,
                fill=T.ink.muted,
                anchor="middle",
            )
        )


def ramp(stops: tuple[str, ...], t: float) -> str:
    """Interpolacja wielostopniowa.

    ColorScale z pyDreamplet obsługuje 2 kolory, więc łączymy odcinki.
    """
    t = min(max(t, 0.0), 1.0)
    n = len(stops) - 1
    i = min(int(t * n), n - 1)
    local = t * n - i
    return dp.ColorScale((0.0, 1.0), (stops[i], stops[i + 1])).map(local)
