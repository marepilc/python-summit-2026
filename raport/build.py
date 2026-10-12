"""Cały raport jednym poleceniem:  uv run python -m raport.build

Polars (dane) → pyDreamplet (SVG) → Typst (PDF). Żadnych kroków ręcznych.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from raport.charts.europe import coal_dumbbell, intensity_ranking
from raport.charts.mix import energy_mix
from raport.charts.multiples import growth_multiples
from raport.charts.spark import sparkline
from raport.charts.stripes import coal_stripes
from raport.charts.waffle import mix_waffle
from raport.data import ReportData, build_report_data
from raport.theme import ROOT, SOURCE_ORDER, THEME

DATA = ROOT / "data" / "owid_energy_eu.csv"
BUILD = ROOT / "build"
CHARTS = BUILD / "charts"
TYPST_MAIN = ROOT / "template" / "raport.typ"


def render_charts(rd: ReportData) -> list[Path]:
    W = (
        THEME.layout.text_width_pt
    )  # szerokość kolumny tekstu w pt → wykres w skali 1:1
    half = (W - THEME.layout.gutter_pt) / 2
    out: list[Path] = []

    out.append(
        coal_stripes(
            rd.years,
            rd.share["wegiel"],
            CHARTS / "stripes.svg",
            width=W,
            height=250,
        )
    )
    out.append(
        energy_mix(
            rd.years,
            rd.share,
            CHARTS / "mix.svg",
            width=W,
            height=300,
            annotations=[
                (2004, "Wejście do UE"),
                (2023, "Węgiel po raz pierwszy < 60%"),
            ],
        )
    )
    out.append(
        growth_multiples(
            rd.years,
            rd.twh,
            ["wiatr", "slonce", "gaz", "biomasa"],
            CHARTS / "multiples.svg",
            width=W,
            height=120,
        )
    )
    out.append(
        mix_waffle(
            {k: rd.share[k][-1] for k in SOURCE_ORDER},
            CHARTS / "waffle.svg",
            width=half,
            height=round(half * 0.55),
            year=rd.last_year,
        )
    )
    out.append(
        coal_dumbbell(
            rd.europe,
            rd.eu_avg,
            CHARTS / "dumbbell.svg",
            width=half,
            start_year=rd.compare_year,
            end_year=rd.last_year,
        )
    )
    out.append(
        intensity_ranking(
            rd.europe, rd.eu_avg, CHARTS / "ranking.svg", width=half
        )
    )

    i2000 = rd.years.index(2000)
    oze = [
        sum(rd.share[k][i] for k in ("biomasa", "woda", "wiatr", "slonce"))
        for i in range(len(rd.years))
    ]
    out.append(
        sparkline(
            rd.share["wegiel"], CHARTS / "spark_coal.svg", width=100, height=34
        )
    )
    out.append(sparkline(oze, CHARTS / "spark_oze.svg", width=100, height=34))
    out.append(
        sparkline(
            rd.intensity, CHARTS / "spark_intensity.svg", width=100, height=34
        )
    )
    out.append(
        sparkline(
            rd.twh["slonce"][i2000:],
            CHARTS / "spark_solar.svg",
            width=100,
            height=34,
        )
    )
    return out


def compile_pdf(output: Path) -> None:
    """Typst przez pakiet Pythona (`typst`), a gdy go brak — przez CLI."""
    font_paths = [str(ROOT / "fonts")]
    try:
        import typst  # type: ignore[import-not-found]

        if not hasattr(typst, "compile"):
            raise ImportError
        typst.compile(
            str(TYPST_MAIN),
            output=str(output),
            root=str(ROOT),
            font_paths=font_paths,
        )
        return
    except ImportError:
        pass
    exe = shutil.which("typst")
    if exe is None:
        sys.exit(
            "Brak Typst: `uv add typst` albo zainstaluj CLI (https://typst.app/open-source/)."
        )
    subprocess.run(
        [
            exe,
            "compile",
            "--root",
            str(ROOT),
            "--font-path",
            font_paths[0],
            "--ignore-system-fonts",
            str(TYPST_MAIN),
            str(output),
        ],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Buduje raport PDF")
    parser.add_argument(
        "--no-pdf",
        action="store_true",
        help="tylko dane i wykresy (szybka iteracja)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=BUILD / "raport.pdf"
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    BUILD.mkdir(exist_ok=True)
    rd = build_report_data(DATA)
    rd.to_json(BUILD / "data.json")
    THEME.export_json(BUILD / "theme.json")
    meta = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "data_file": DATA.name,
        "data_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest()[:12],
        "python": sys.version.split()[0],
    }
    (BUILD / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    t1 = time.perf_counter()
    charts = render_charts(rd)
    t2 = time.perf_counter()
    years = f"{rd.first_year}–{rd.last_year}"
    print(f"dane      {1000 * (t1 - t0):6.0f} ms   ({years})")
    print(f"wykresy   {1000 * (t2 - t1):6.0f} ms   ({len(charts)} × SVG)")
    if not args.no_pdf:
        compile_pdf(args.output)
        ms = 1000 * (time.perf_counter() - t2)
        print(f"PDF       {ms:6.0f} ms   → {args.output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
