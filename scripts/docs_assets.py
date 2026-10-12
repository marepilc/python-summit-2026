"""Grafiki do dokumentacji (docs/img).

Też z pyDreamplet i z tych samych tokenów.

uv run python -m scripts.docs_assets
"""

from pathlib import Path

import pydreamplet as dp

from raport.charts.base import T, text
from raport.theme import SOURCE_LABELS, SOURCE_ORDER

OUT = Path(__file__).resolve().parent.parent / "docs" / "img"


def palette(path: Path) -> None:
    keys = [*SOURCE_ORDER, "accent"]
    w, gap, sw_h = 92, 10, 56
    svg = dp.SVG(len(keys) * (w + gap) - gap, sw_h + 44)
    svg.append(dp.Rect(x=0, y=0, width=svg.w, height=svg.h, fill=T.ink.paper))
    for i, key in enumerate(keys):
        x = i * (w + gap)
        color = T.ink.accent if key == "accent" else T.source_color(key)
        name = "Akcent" if key == "accent" else SOURCE_LABELS[key]
        svg.append(dp.Rect(x=x, y=0, width=w, height=sw_h, rx=4, fill=color))
        svg.append(
            text(name, x, sw_h + 16, size=11, weight=600, fill=T.ink.primary)
        )
        svg.append(
            text(
                color,
                x,
                sw_h + 32,
                size=10,
                fill=T.ink.muted,
                family=T.type.mono,
            )
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    svg.save(str(path))


if __name__ == "__main__":
    palette(OUT / "paleta.svg")
    print(f"→ {OUT / 'paleta.svg'}")
