"""Slajd „PRZED”: ten sam wykres miksu, ale tak, jak wygląda „domyślnie”.

    uv run --group demo python scripts/00_przed.py   → build/przed.png

Celowo bez poprawek: domyślne kolory, legenda w rogu, tytuł-opis.
Zapis w 300 dpi (ten sam układ co 800×450 px przy 100 dpi): slajd z grzechami
powiększa fragmenty, a „zły” wykres ma być zły projektowo, nie przez piksele.
Pokaż go obok build/charts/mix.svg — różnica robi połowę wstępu.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
df = (
    pl.read_csv(ROOT / "data" / "owid_energy_eu.csv")
    .filter(pl.col("country") == "Poland")
    .sort("year")
)
cols = [
    "coal_electricity",
    "gas_electricity",
    "oil_electricity",
    "biofuel_electricity",
    "hydro_electricity",
    "wind_electricity",
    "solar_electricity",
]
df = df.select("year", *[pl.col(c).fill_null(0) for c in cols]).drop_nulls()

fig, ax = plt.subplots(figsize=(8, 4.5), dpi=100)
# po polsku, ale nadal „domyślnie”: tytuł powtarza to, co jest na osiach
labels = ["węgiel", "gaz", "ropa", "biopaliwa", "woda", "wiatr", "słońce"]
ax.stackplot(df["year"], *[df[c] for c in cols], labels=labels)
years = f"{df['year'].min()}–{df['year'].max()}"
ax.set_title(f"Produkcja energii elektrycznej w latach {years}")
ax.set_xlabel("rok")
ax.set_ylabel("TWh")
ax.legend(loc="upper left", fontsize=7)
ax.grid(True)
(ROOT / "build").mkdir(exist_ok=True)
fig.savefig(ROOT / "build" / "przed.png", dpi=300)
print("→ build/przed.png")
