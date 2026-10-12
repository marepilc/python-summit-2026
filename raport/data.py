"""Warstwa danych (Polars).

CSV → czyste struktury dla wykresów i tekstu raportu.

Kontrakt: wykresy NIE dotykają DataFrame'ów. Dostają `ReportData` — zwykłe listy
i słowniki. Dzięki temu warstwę danych da się podmienić (np. na API PSE/GUS)
bez ruszania ani jednej linii kodu wizualizacji.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

from raport.theme import SOURCE_ORDER

# Agregacja kolumn OWID do 7 kategorii używanych w raporcie
SOURCE_COLUMNS: dict[str, list[str]] = {
    "wegiel": ["coal_electricity"],
    "gaz": ["gas_electricity"],
    "inne": [
        "oil_electricity",
        "nuclear_electricity",
        "other_renewable_exc_biofuel_electricity",
    ],
    "biomasa": ["biofuel_electricity"],
    "woda": ["hydro_electricity"],
    "wiatr": ["wind_electricity"],
    "slonce": ["solar_electricity"],
}
RENEWABLES = ["biomasa", "woda", "wiatr", "slonce"]
RENEWABLE_PCT = [f"{k}_pct" for k in RENEWABLES]

EU27_PL: dict[str, str] = {
    "Austria": "Austria",
    "Belgium": "Belgia",
    "Bulgaria": "Bułgaria",
    "Croatia": "Chorwacja",
    "Cyprus": "Cypr",
    "Czechia": "Czechy",
    "Denmark": "Dania",
    "Estonia": "Estonia",
    "Finland": "Finlandia",
    "France": "Francja",
    "Germany": "Niemcy",
    "Greece": "Grecja",
    "Hungary": "Węgry",
    "Ireland": "Irlandia",
    "Italy": "Włochy",
    "Latvia": "Łotwa",
    "Lithuania": "Litwa",
    "Luxembourg": "Luksemburg",
    "Malta": "Malta",
    "Netherlands": "Holandia",
    "Poland": "Polska",
    "Portugal": "Portugalia",
    "Romania": "Rumunia",
    "Slovakia": "Słowacja",
    "Slovenia": "Słowenia",
    "Spain": "Hiszpania",
    "Sweden": "Szwecja",
}
EU_AGGREGATE = "European Union (27)"
FIRST_YEAR = 1990
COMPARE_YEAR = 2015


@dataclass
class CountryRow:
    country: str
    name_pl: str
    coal_start: float
    coal_end: float
    intensity_end: float
    renewables_end: float


@dataclass
class ReportData:
    first_year: int
    last_year: int
    compare_year: int
    years: list[int]
    share: dict[str, list[float]]  # % udziału w produkcji energii elektrycznej
    twh: dict[str, list[float]]  # produkcja w TWh
    total_twh: list[float]
    intensity: list[float | None]  # gCO2/kWh
    europe: list[CountryRow]
    eu_avg: dict[str, float]
    kpi: dict[str, float]

    def to_json(self, path: Path) -> None:
        path.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=1),
            encoding="utf-8",
        )


def load(path: Path) -> pl.DataFrame:
    return pl.read_csv(path).filter(pl.col("year") >= FIRST_YEAR)


def poland_mix(df: pl.DataFrame) -> pl.DataFrame:
    """Jeden wiersz = rok; kolumny TWh i % dla każdej kategorii źródeł."""
    sources = [
        pl.sum_horizontal(pl.col(cols).fill_null(0.0)).alias(key)
        for key, cols in SOURCE_COLUMNS.items()
    ]
    shares = [
        (pl.col(k) / pl.col("total") * 100).alias(f"{k}_pct")
        for k in SOURCE_ORDER
    ]
    is_poland = pl.col("country") == "Poland"
    has_data = pl.col("coal_electricity").is_not_null()

    return (
        df.filter(is_poland, has_data)
        .select("year", *sources, intensity=pl.col("carbon_intensity_elec"))
        .with_columns(total=pl.sum_horizontal(SOURCE_ORDER))
        .with_columns(shares)
        .with_columns(oze_pct=pl.sum_horizontal(RENEWABLE_PCT))
        .sort("year")
    )


def europe_table(df: pl.DataFrame, last_year: int) -> pl.DataFrame:
    def snapshot(year: int, suffix: str) -> pl.DataFrame:
        return df.filter(pl.col("year") == year).select(
            "country",
            pl.col("coal_share_elec").alias(f"coal_{suffix}"),
            pl.col("carbon_intensity_elec").alias(f"intensity_{suffix}"),
            pl.col("renewables_share_elec").alias(f"renewables_{suffix}"),
        )

    return (
        snapshot(last_year, "end")
        .join(snapshot(COMPARE_YEAR, "start"), on="country", how="inner")
        .with_columns(
            pl.col("country")
            .replace_strict(EU27_PL, default=None, return_dtype=pl.String)
            .alias("name_pl")
        )
        .drop_nulls(["coal_start", "coal_end", "intensity_end"])
    )


def build_report_data(csv_path: Path) -> ReportData:
    df = load(csv_path)
    mix = poland_mix(df)
    last_year = int(mix["year"].max())  # type: ignore[arg-type]

    eu_all = europe_table(df, last_year)
    countries = eu_all.filter(pl.col("name_pl").is_not_null()).sort(
        "intensity_end", descending=True
    )
    eu_avg_row = eu_all.filter(pl.col("country") == EU_AGGREGATE).row(
        0, named=True
    )

    first = mix.row(0, named=True)
    last = mix.row(-1, named=True)
    compare = mix.filter(pl.col("year") == COMPARE_YEAR).row(0, named=True)
    solar_2019 = mix.filter(pl.col("year") == 2019)["slonce"].item()
    pl_rank = countries["country"].to_list().index("Poland") + 1

    kpi = {
        "coal_share_first": first["wegiel_pct"],
        "coal_share_last": last["wegiel_pct"],
        "coal_share_compare": compare["wegiel_pct"],
        "oze_share_compare": compare["oze_pct"],
        "oze_share_last": last["oze_pct"],
        "intensity_first": first["intensity"],
        "intensity_last": last["intensity"],
        "solar_twh_last": last["slonce"],
        "solar_growth_since_2019": last["slonce"] / solar_2019,
        "wind_twh_last": last["wiatr"],
        "coal_twh_first": first["wegiel"],
        "coal_twh_last": last["wegiel"],
        "total_twh_last": last["total"],
        "pl_intensity_rank": pl_rank,
        "eu_count": countries.height,
        "pl_vs_eu_intensity": last["intensity"] / eu_avg_row["intensity_end"],
    }

    return ReportData(
        first_year=int(first["year"]),
        last_year=last_year,
        compare_year=COMPARE_YEAR,
        years=mix["year"].to_list(),
        share={k: mix[f"{k}_pct"].to_list() for k in SOURCE_ORDER},
        twh={k: mix[k].to_list() for k in SOURCE_ORDER},
        total_twh=mix["total"].to_list(),
        intensity=mix["intensity"].to_list(),
        europe=[
            CountryRow(
                country=r["country"],
                name_pl=r["name_pl"],
                coal_start=r["coal_start"],
                coal_end=r["coal_end"],
                intensity_end=r["intensity_end"],
                renewables_end=r["renewables_end"],
            )
            for r in countries.iter_rows(named=True)
        ],
        eu_avg={
            "coal_start": eu_avg_row["coal_start"],
            "coal_end": eu_avg_row["coal_end"],
            "intensity_end": eu_avg_row["intensity_end"],
            "renewables_end": eu_avg_row["renewables_end"],
        },
        kpi=kpi,
    )
