"""Design tokens — jedno źródło prawdy dla wykresów (Python) i layoutu (Typst).

Zasada: każdy kolor, font i rozmiar występuje w projekcie dokładnie raz — tutaj.
`export_json()` zapisuje te same wartości do build/theme.json,
który czyta Typst.
Jednostka: 1 jednostka SVG == 1 pt w dokumencie (wykresy wstawiamy w skali 1:1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"


@dataclass(frozen=True)
class Ink:
    """Kolory tekstu i powierzchni (papier, nie ekran)."""

    paper: str = "#F7F5F0"  # ciepła biel — tło strony
    surface: str = "#FFFFFF"  # karty / kafle KPI
    primary: str = "#1B1F24"  # tekst główny
    secondary: str = "#55595F"  # opisy, podpisy osi
    muted: str = "#8A8D91"  # źródła, przypisy
    rule: str = "#DDD8CF"  # linie siatki, separatory (hairline)
    rule_strong: str = "#BDB6AA"
    accent: str = "#C8102E"  # Polska / wyróżnienie — używane oszczędnie


@dataclass(frozen=True)
class Sources:
    """Kolory źródeł energii — stała kolejność, kolor idzie za kategorią.

    Węgiel jest celowo szary (wyjątek od chroma floor): w tej historii
    kolor = czysta energia, szarość = węgiel. Identyfikację zapewniają
    etykiety bezpośrednie + legenda, nie sam kolor.
    """

    wegiel: str = "#5F5750"
    gaz: str = "#B5658A"
    inne: str = "#B9B2A8"
    biomasa: str = "#6E9B37"
    woda: str = "#4462B5"
    wiatr: str = "#1F9E8E"
    slonce: str = "#E8A317"


# kolejność warstw od dołu (stack) i w legendzie
SOURCE_ORDER: list[str] = [
    "wegiel",
    "gaz",
    "inne",
    "biomasa",
    "woda",
    "wiatr",
    "slonce",
]
SOURCE_LABELS: dict[str, str] = {
    "wegiel": "Węgiel",
    "gaz": "Gaz",
    "inne": "Ropa i inne",
    "biomasa": "Biomasa",
    "woda": "Woda",
    "wiatr": "Wiatr",
    "slonce": "Słońce",
}

# skala sekwencyjna (jedna barwa, jasny → ciemny) dla „pasków węglowych”
COAL_RAMP: tuple[str, str, str] = ("#EFEAE2", "#9C928A", "#26221F")


@dataclass(frozen=True)
class Type:
    sans: str = "Inter"
    serif: str = "Source Serif 4"
    mono: str = "IBM Plex Mono"
    # skala typograficzna (pt) — wykresy używają tylko tych wartości
    tick: float = 6.5
    label: float = 7.5
    body: float = 9.5
    lead: float = 12.0
    h2: float = 20.0
    h1: float = 34.0
    hero: float = 64.0


@dataclass(frozen=True)
class Layout:
    page_w_mm: float = 210
    page_h_mm: float = 297
    margin_x_mm: float = 18
    margin_top_mm: float = 20
    margin_bottom_mm: float = 22
    gutter_pt: float = 14

    @property
    def text_width_pt(self) -> float:
        return (self.page_w_mm - 2 * self.margin_x_mm) * 72 / 25.4


@dataclass(frozen=True)
class Theme:
    ink: Ink = field(default_factory=Ink)
    sources: Sources = field(default_factory=Sources)
    type: Type = field(default_factory=Type)
    layout: Layout = field(default_factory=Layout)

    def source_color(self, key: str) -> str:
        return getattr(self.sources, key)

    def export_json(self, path: Path) -> None:
        payload = {
            "ink": asdict(self.ink),
            "sources": asdict(self.sources),
            "source_order": SOURCE_ORDER,
            "source_labels": SOURCE_LABELS,
            "type": asdict(self.type),
            "layout": {
                **asdict(self.layout),
                "text_width_pt": self.layout.text_width_pt,
            },
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )


THEME = Theme()

FONT_FILES: dict[tuple[str, int], Path] = {
    ("Inter", 400): FONTS / "Inter-Regular.ttf",
    ("Inter", 500): FONTS / "Inter-Medium.ttf",
    ("Inter", 600): FONTS / "Inter-SemiBold.ttf",
    ("Inter", 700): FONTS / "Inter-Bold.ttf",
    ("Source Serif 4", 400): FONTS / "SourceSerif4-Regular.ttf",
    ("Source Serif 4", 600): FONTS / "SourceSerif4-SemiBold.ttf",
    ("Source Serif 4", 700): FONTS / "SourceSerif4-Bold.ttf",
}
