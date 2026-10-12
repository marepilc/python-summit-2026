"""Miks energetyczny 100%.

Warstwy, etykiety bezpośrednie z rozwiązywaniem kolizji, adnotacje.
Funkcja `energy_mix` jest podzielona na bloki „krok N” — te same kroki
pokazuje prezentacja (slajd budowy wykresu wycina je z tego pliku).
"""

from __future__ import annotations

from pathlib import Path

import pydreamplet as dp
from pydreamplet.utils import place_labels_1d

from raport.charts.base import (
    Canvas,
    Margins,
    T,
    fmt,
    text,
    text_width,
    x_year_axis,
    y_axis,
)
from raport.theme import SOURCE_LABELS, SOURCE_ORDER

Bands = dict[str, tuple[list[float], list[float]]]


def energy_mix(
    years: list[int],
    share: dict[str, list[float]],
    out: Path,
    *,
    width: float,
    height: float,
    annotations: list[tuple[int, str]] | None = None,
) -> Path:
    size = T.type.label
    leader = 14
    names = {k: SOURCE_LABELS[k] for k in SOURCE_ORDER}
    values = {k: fmt(share[k][-1]) + "%" for k in SOURCE_ORDER}

    # krok 3 · najpierw mierzymy tekst — prawdziwe metryki fontu
    # (HarfBuzz); prawy margines wynika z najszerszej etykiety
    name_w = max(text_width(n, size) for n in names.values())
    value_w = max(text_width(v, size, weight=600) for v in values.values())
    right = leader + SWATCH + PAD + name_w + 6 + value_w + 2

    # krok 0 · scena w docelowym rozmiarze: 1 jednostka = 1 pt
    top = 26 if annotations else 6
    c = Canvas(width, height, Margins(top=top, right=right, left=26))
    sx = dp.LinearScale((years[0], years[-1]), (c.x0, c.x1))
    sy = dp.LinearScale((0, 100), (c.y1, c.y0))
    _axes(c, sx, sy, years)

    # krok 1 · warstwy: dolna i górna krawędź każdego źródła
    bands = _stack(share)
    area = dp.AreaGenerator(
        x0=lambda r, _: sx.map(r[0]),
        y0=lambda r, _: sy.map(r[1]),
        y1=lambda r, _: sy.map(r[2]),
    )
    for key, (lo, hi) in bands.items():
        rows = list(zip(years, lo, hi, strict=True))
        c.marks.append(
            dp.Path(
                area(rows),
                fill=T.source_color(key),
                class_name="layer",
                data_key=key,
            )
        )

    # krok 2 · szczelina w kolorze papieru zamiast obrysu
    line = dp.LineGenerator(
        x=lambda r, _: sx.map(r[0]),
        y=lambda r, _: sy.map(r[1]),
    )
    for _lo, hi in list(bands.values())[:-1]:
        points = list(zip(years, hi, strict=True))
        c.marks.append(
            dp.Path(
                line(points),
                fill="none",
                stroke=T.ink.paper,
                stroke_width=0.9,
                stroke_linejoin="round",
                class_name="gap",
            )
        )

    # krok 4 · kolizje: kotwica etykiety = środek warstwy w ostatnim
    # roku; place_labels_1d rozsuwa etykiety tylko tyle, ile trzeba
    anchors = [sy.map((lo[-1] + hi[-1]) / 2) for lo, hi in bands.values()]
    placed = place_labels_1d(
        anchors,
        [size * 1.45] * len(anchors),
        gap=1.5,
        bounds=(c.y0, c.y1 + 6),
    )
    for key, p in zip(SOURCE_ORDER, placed, strict=True):
        c.labels.append(_leader(c.x1, leader, p.anchor, p.position))
        # data-dy: o ile algorytm przesunął etykietę (slajdy to animują)
        dy = round(p.anchor - p.position, 2)
        label = dp.G(class_name="label", data_key=key, data_dy=dy)
        _label(label, key, values[key], c.x1 + leader, p.position, c.width)
        c.labels.append(label)

    # krok 5 · adnotacje przy danych: rok i opis zdarzenia; podpisy
    # mierzymy i przy kolizji przenosimy na drugą stronę linii
    notes = [(sx.map(year), year, note) for year, note in annotations or []]
    for (x, year, note), side in zip(notes, _note_sides(c, notes), strict=True):
        c.annotations.append(_annotation(c, x, year, note, side))

    return c.save(out)


# ------------------------------------------------------------------ pomocnicze
SWATCH, PAD = 7.0, 4.0


def _stack(share: dict[str, list[float]]) -> Bands:
    """Skumulowane krawędzie warstw: {źródło: (dolna, górna)}."""
    lower = [0.0] * len(share[SOURCE_ORDER[0]])
    bands: Bands = {}
    for key in SOURCE_ORDER:
        upper = [lo + v for lo, v in zip(lower, share[key], strict=True)]
        bands[key] = (lower, upper)
        lower = upper
    return bands


def _axes(
    c: Canvas, sx: dp.LinearScale, sy: dp.LinearScale, years: list[int]
) -> None:
    # siatka NAD warstwami, półprzezroczysta: czytelna, ale nie konkuruje
    # z danymi
    for t in (25, 50, 75):
        c.annotations.append(
            dp.Line(
                x1=c.x0,
                y1=sy.map(t),
                x2=c.x1,
                y2=sy.map(t),
                stroke=T.ink.paper,
                stroke_width=0.5,
                opacity=0.55,
            )
        )
    y_axis(c, sy, [0, 25, 50, 75, 100], suffix="%", grid=False)
    decade_ticks = [y for y in years if y % 5 == 0]
    x_year_axis(c, sx, decade_ticks, baseline=False)


def _leader(x1: float, leader: float, anchor: float, pos: float) -> dp.Polyline:
    """Łącznik od krawędzi wykresu do etykiety; łamany, gdy ją przesunięto."""
    lx = x1 + leader
    pts = (
        [x1 + 1.5, anchor, x1 + leader * 0.45, anchor, lx - 2, pos]
        if abs(pos - anchor) > 0.5
        else [x1 + 1.5, anchor, lx - 2, pos]
    )
    return dp.Polyline(
        [round(v, 2) for v in pts],
        fill="none",
        stroke=T.ink.rule_strong,
        stroke_width=0.5,
        class_name="leader",
    )


def _label(
    g: dp.G, key: str, value: str, lx: float, y: float, right: float
) -> None:
    """Próbka koloru, nazwa źródła i wartość wyrównana do prawej."""
    g.append(
        dp.Rect(
            x=lx,
            y=round(y - SWATCH / 2, 2),
            width=SWATCH,
            height=SWATCH,
            rx=1.5,
            fill=T.source_color(key),
        )
    )
    g.append(
        text(
            SOURCE_LABELS[key],
            lx + SWATCH + PAD,
            y,
            size=T.type.label,
            fill=T.ink.secondary,
            middle=True,
        )
    )
    g.append(
        text(
            value,
            right - 2,
            y,
            size=T.type.label,
            weight=600,
            fill=T.ink.primary,
            anchor="end",
            middle=True,
        )
    )


NOTE_GAP = 6.0
Side = tuple[str, float]  # (text-anchor, odsunięcie od linii)


def _note_sides(c: Canvas, notes: list[tuple[float, int, str]]) -> list[Side]:
    """Strona podpisu każdej adnotacji.

    Domyślnie podpis stoi po stronie środka wykresu. Gdy dwa podpisy
    zachodzą na siebie (szerokości z metryk fontu), lewy przechodzi na
    lewą stronę swojej linii, a jeśli tam się nie mieści — prawy na prawą.
    """
    sides: list[Side] = [
        ("end", -4) if x > (c.x0 + c.x1) / 2 else ("start", 4)
        for x, _, _ in notes
    ]
    widths = [
        max(
            text_width(note, T.type.tick),
            text_width(str(year), T.type.tick, weight=600),
        )
        for _, year, note in notes
    ]

    def span(i: int) -> tuple[float, float]:
        anchor, dx = sides[i]
        x = notes[i][0] + dx
        return (x, x + widths[i]) if anchor == "start" else (x - widths[i], x)

    for i in range(len(notes) - 1):
        if span(i)[1] + NOTE_GAP <= span(i + 1)[0]:
            continue
        if notes[i][0] - 4 - widths[i] >= 0:
            sides[i] = ("end", -4)
        elif notes[i + 1][0] + 4 + widths[i + 1] <= c.width:
            sides[i + 1] = ("start", 4)
    return sides


def _annotation(c: Canvas, x: float, year: int, note: str, side: Side) -> dp.G:
    """Włoskowata linia przez wykres + podpis nad obszarem danych."""
    a = dp.G(class_name="annot", data_year=year)
    a.append(
        dp.Line(
            x1=x,
            y1=c.y0 - 6,
            x2=x,
            y2=c.y1,
            stroke=T.ink.primary,
            stroke_width=0.6,
            opacity=0.8,
        )
    )
    a.append(dp.Circle(pos=(x, c.y0 - 6), r=1.6, fill=T.ink.primary))
    anchor, dx = side
    a.append(
        text(
            note,
            x + dx,
            c.y0 - 12,
            size=T.type.tick,
            fill=T.ink.secondary,
            anchor=anchor,
        )
    )
    a.append(
        text(
            str(year),
            x + dx,
            c.y0 - 4,
            size=T.type.tick,
            weight=600,
            fill=T.ink.primary,
            anchor=anchor,
        )
    )
    return a
