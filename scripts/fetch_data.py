"""Odświeża data/owid_energy_eu.csv z repozytorium owid/energy-data.

    uv run python scripts/fetch_data.py

Na konferencji NIE uruchamiaj tego na żywo — w repo jest gotowy plik
(demo offline).
"""

from pathlib import Path

import polars as pl

URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
OUT = Path(__file__).resolve().parent.parent / "data" / "owid_energy_eu.csv"

EU = [
    "Austria",
    "Belgium",
    "Bulgaria",
    "Croatia",
    "Cyprus",
    "Czechia",
    "Denmark",
    "Estonia",
    "Finland",
    "France",
    "Germany",
    "Greece",
    "Hungary",
    "Ireland",
    "Italy",
    "Latvia",
    "Lithuania",
    "Luxembourg",
    "Malta",
    "Netherlands",
    "Poland",
    "Portugal",
    "Romania",
    "Slovakia",
    "Slovenia",
    "Spain",
    "Sweden",
    "European Union (27)",
]
COLUMNS = [
    "country",
    "iso_code",
    "year",
    "electricity_generation",
    "coal_electricity",
    "gas_electricity",
    "oil_electricity",
    "nuclear_electricity",
    "biofuel_electricity",
    "hydro_electricity",
    "wind_electricity",
    "solar_electricity",
    "other_renewable_exc_biofuel_electricity",
    "coal_share_elec",
    "renewables_share_elec",
    "carbon_intensity_elec",
    "greenhouse_gas_emissions",
]

if __name__ == "__main__":
    df = (
        pl.read_csv(URL, infer_schema_length=10_000)
        .filter(pl.col("country").is_in(EU), pl.col("year") >= 1990)
        .select(COLUMNS)
    )
    df.write_csv(OUT)
    print(f"{df.height} wierszy → {OUT}")
