"""Prezentacja HTML z tych samych danych, tokenów i wykresów co raport.

    uv run python -m prezentacja.build     # → build/prezentacja.html

Co się dzieje:
1. budujemy raport (dane → SVG → PDF) i mierzymy czas etapów — liczby
   trafiają na slajd,
2. wykresy SVG z pyDreamplet wstawiamy inline (animacje czytają ich klasy
   i atrybuty data-*),
3. fragmenty kodu wycinamy z prawdziwych plików repo, więc slajdy nie
   rozjadą się z kodem,
4. fonty są przycinane do potrzebnych znaków i osadzane — prezentacja
   nie potrzebuje internetu.
"""

from __future__ import annotations

import argparse
import base64
import html
import io
import itertools
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from raport import build as report
from raport.charts.stripes import coal_stripes
from raport.data import SOURCE_COLUMNS, build_report_data
from raport.theme import ROOT, THEME

HERE = Path(__file__).resolve().parent
ASSET_MIME = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
}
OUT = report.BUILD / "prezentacja.html"
SLIDE_CHARTS = report.BUILD / "charts_slides"
# Skala ekranu: 1 jednostka wykresu = S px na scenie 1920×1080.
# Wykresy dla slajdów to te same funkcje co w raporcie, tylko w innym kadrze —
# dzięki temu tekst 7,5 pt z raportu ma na ekranie ~20 px i jest czytelny
# z sali.
S = 2.6

# ------------------------------------------------------- fragmenty kodu z repo
# nazwa: (plik, regex linii początkowej, regex linii końcowej — włącznie,
#         czy pominąć linię początkową); pusty regex końca = do pustej linii
SNIPPETS: dict[str, tuple[str, str, str, bool]] = {
    "tokens": ("raport/theme.py", r"^class Ink:", r"accent: str =", False),
    "typst_chart": (
        "template/components.typ",
        r"^#let chart\($",
        r"^\]$",
        False,
    ),
    # pomocnik projektu: pod spodem dp.SVG w punktach i grupy warstw dp.G
    "canvas": (
        "raport/charts/base.py",
        r"def __post_init__",
        r"self\.svg\.append\(",
        False,
    ),
    # znacznik sekcji w raport.typ, sam fragment zaczyna się w następnej linii
    "typst_num": ("template/raport.typ", r"^// =+ 3\. MIKS", r"^\)$", True),
}
# slajd „Jeden wykres w pięciu krokach”: bloki „# krok N” z mix.py
SNIPPETS |= {
    f"mix{n}": ("raport/charts/mix.py", rf"# krok {n} ", "", False)
    for n in range(6)
}


def snippet(name: str) -> str:
    path, start, end, skip_start = SNIPPETS[name]
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    i = next(n for n, line in enumerate(lines) if re.search(start, line)) + int(
        skip_start
    )
    if end:
        j = next(n for n in range(i, len(lines)) if re.search(end, lines[n]))
    else:
        j = next(n for n in range(i, len(lines)) if not lines[n].strip()) - 1
    block = lines[i : j + 1]
    indent = min(len(x) - len(x.lstrip()) for x in block if x.strip())
    return "\n".join(x[indent:] for x in block)


# Klasy CSS dla tokenów Pygments (paleta w deck.css)
UNITS = {"pt", "mm", "cm", "in", "em", "fr", "%", "deg"}


def _css_class(ttype, value: str) -> str | None:  # noqa: ANN001
    from pygments.token import Comment, Keyword, Name, Number, Operator, String

    if ttype in Comment:
        return "c"
    if ttype in String:
        return "s"
    if ttype in Number:
        return "n"
    if ttype in Keyword.Reserved and value in UNITS:
        return "n"  # jednostki Typst (10.5pt, 100%) w kolorze liczby
    if ttype in Keyword or ttype in Operator.Word:
        return "k"
    if ttype in Name.Builtin or ttype in Name.Builtin.Pseudo:
        return "b"
    if ttype in Name.Tag:
        return "b"  # klucze w JSON
    if ttype in Name.Decorator:
        return "k"
    if ttype in Name.Function or ttype in Name.Class:
        return "f"
    if ttype in Name.Variable and value.startswith("#"):
        return "v"  # zmienna wstawiona w treść Typst: #YC
    return None


def highlight(code: str, lang: str, mark: str | None = None) -> str:
    """Podświetlanie składni przez Pygments (Python, Typst).

    `mark` — fragment do wyróżnienia (np. wywołanie, o którym mówimy);
    wyróżniane są wszystkie jego wystąpienia.
    """
    from pygments.lexers import JsonLexer, PythonLexer, TypstLexer
    from pygments.token import Name, Punctuation

    lexer = {"py": PythonLexer, "json": JsonLexer}.get(lang, TypstLexer)()
    tokens = list(lexer.get_tokens(code))
    if tokens and tokens[-1][1] == "\n" and not code.endswith("\n"):
        tokens = tokens[:-1]  # lexer dokleja końcowy znak nowej linii

    starts = (
        {m.start() for m in re.finditer(re.escape(mark), code)}
        if mark
        else set()
    )
    mark_end = -1
    out, pos, opened = [], 0, False
    for n, (ttype, value) in enumerate(tokens):
        cls = _css_class(ttype, value)
        # wywołanie (nazwa tuż przed nawiasem) — lexer Pythona tego nie oznacza
        nxt = tokens[n + 1] if n + 1 < len(tokens) else None
        if (
            cls is None
            and ttype in Name
            and nxt
            and nxt[0] in Punctuation
            and nxt[1].startswith("(")
        ):
            cls = "f"
        piece = html.escape(value)
        if cls:
            piece = f'<span class="{cls}">{piece}</span>'
        if not opened and pos in starts:
            out.append('<span class="h">')
            opened, mark_end = True, pos + len(mark or "")
        out.append(piece)
        pos += len(value)
        if opened and pos >= mark_end > 0:
            out.append("</span>")
            opened, mark_end = False, -1
    if opened:
        out.append("</span>")
    return "".join(out)


# --------------------------------------------------------------------- zasoby
def render_slide_charts(rd) -> None:  # noqa: ANN001
    """Warianty wykresów w kadrach slajdów (jednostki × S = piksele sceny)."""
    from raport.charts.europe import coal_dumbbell, intensity_ranking
    from raport.charts.mix import energy_mix
    from raport.charts.multiples import growth_multiples
    from raport.charts.waffle import mix_waffle
    from raport.theme import SOURCE_ORDER

    out = SLIDE_CHARTS
    notes = [(2004, "Wejście do UE"), (2023, "Węgiel < 60%")]
    coal_stripes(
        rd.years, rd.share["wegiel"], out / "stripes.svg", width=640, height=140
    )
    energy_mix(
        rd.years,
        rd.share,
        out / "mix.svg",
        width=300,
        height=236,
        annotations=notes,
    )
    energy_mix(
        rd.years,
        rd.share,
        out / "mix_small.svg",
        width=282,
        height=196,
        annotations=notes,
    )
    # ten sam wykres bez adnotacji — do wycinków na slajdzie z grzechami,
    # gdzie linie lat tylko by przeszkadzały; o 20 pt niższy (brak miejsca
    # na podpisy), więc obszar danych ma tę samą geometrię co mix_small
    energy_mix(
        rd.years,
        rd.share,
        out / "mix_plain.svg",
        width=282,
        height=176,
    )
    coal_dumbbell(
        rd.europe,
        rd.eu_avg,
        out / "dumbbell.svg",
        width=300,
        start_year=rd.compare_year,
        end_year=rd.last_year,
        row_h=11,
    )
    coal_dumbbell(
        rd.europe,
        rd.eu_avg,
        out / "dumbbell_wide.svg",
        width=360,
        start_year=rd.compare_year,
        end_year=rd.last_year,
        row_h=11,
    )
    intensity_ranking(
        rd.europe, rd.eu_avg, out / "ranking.svg", width=300, row_h=8
    )
    growth_multiples(
        rd.years,
        rd.twh,
        ["wiatr", "slonce", "gaz", "biomasa"],
        out / "multiples.svg",
        width=380,
        height=150,
    )
    mix_waffle(
        {k: rd.share[k][-1] for k in SOURCE_ORDER},
        out / "waffle.svg",
        width=215,
        height=118,
        year=rd.last_year,
    )


def inline_svg(name: str) -> str:
    svg = (SLIDE_CHARTS / f"{name}.svg").read_text(encoding="utf-8")
    vb = re.search(r'viewBox="([^"]+)"', svg).group(1).split()  # type: ignore[union-attr]
    w, h = float(vb[2]) * S, float(vb[3]) * S
    svg = re.sub(r'\s(width|height)="[^"]*px"', "", svg, count=2)
    attrs = f'role="img" aria-label="{name}" width="{w:.0f}" height="{h:.0f}"'
    return svg.replace("<svg ", f"<svg {attrs} ", 1)


def data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


FONT_FACES = [
    ("Inter", 400, "normal", "Inter-Regular.ttf"),
    ("Inter", 500, "normal", "Inter-Medium.ttf"),
    ("Inter", 600, "normal", "Inter-SemiBold.ttf"),
    ("Inter", 700, "normal", "Inter-Bold.ttf"),
    ("Inter", 400, "italic", "Inter-Italic.ttf"),
    ("Source Serif 4", 400, "normal", "SourceSerif4-Regular.ttf"),
    ("Source Serif 4", 600, "normal", "SourceSerif4-SemiBold.ttf"),
    ("Source Serif 4", 400, "italic", "SourceSerif4-Italic.ttf"),
    ("IBM Plex Mono", 400, "normal", "IBMPlexMono-Regular.ttf"),
    ("IBM Plex Mono", 500, "normal", "IBMPlexMono-Medium.ttf"),
]
UNICODES = ",".join(
    [
        "U+0020-007E",  # ASCII
        "U+00A0-017F",  # Latin-1 + Latin Extended-A (polskie znaki)
        "U+2000-206F",  # interpunkcja: – — „ ” …
        "U+2070-209F",  # indeksy górne i dolne: CO₂
        "U+2190-21FF",  # strzałki
        "U+2212,U+2264-2265,U+00D7",  # − ≤ ≥ ×
    ]
)


def font_css() -> str:
    """Fonty przycięte do łaciny i polskich znaków, osadzone w CSS.

    Dzięki temu prezentacja działa offline.
    """
    css = []
    opts = subset.Options()
    opts.layout_features = ["*"]
    opts.name_IDs = ["*"]
    # tabela „meta” (języki fontu) nie wpływa na glify; fontTools nie umie
    # jej przyciąć i ostrzega przy każdym foncie, więc od razu ją pomijamy
    opts.drop_tables += ["meta"]
    unicodes = subset.parse_unicodes(UNICODES)
    for family, weight, style, file in FONT_FACES:
        font = TTFont(THEME_FONTS / file)
        sub = subset.Subsetter(opts)
        sub.populate(unicodes=unicodes)
        sub.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        css.append(
            f'@font-face{{font-family:"{family}";font-weight:{weight};font-style:{style};font-display:block;'
            f'src:url(data:font/ttf;base64,{b64}) format("truetype")}}'
        )
    return "\n".join(css)


THEME_FONTS = ROOT / "fonts"


def render_pages(pdf_source: Path, ppi: int = 160) -> list[Path]:
    """Strony raportu jako PNG (slajd „Wynik”). Typst CLI albo pakiet typst."""
    out_dir = report.BUILD / "pages"
    out_dir.mkdir(exist_ok=True)
    exe = shutil.which("typst")
    if exe:
        subprocess.run(
            [
                exe,
                "compile",
                "--root",
                str(ROOT),
                "--font-path",
                str(THEME_FONTS),
                "--ignore-system-fonts",
                "--format",
                "png",
                "--ppi",
                str(ppi),
                str(pdf_source),
                str(out_dir / "page-{p}.png"),
            ],
            check=True,
        )
    else:
        import typst  # type: ignore[import-not-found]

        pages = typst.compile(
            str(pdf_source),
            root=str(ROOT),
            font_paths=[str(THEME_FONTS)],
            format="png",
            ppi=ppi,
        )
        for i, png in enumerate(
            pages if isinstance(pages, list) else [pages], start=1
        ):
            (out_dir / f"page-{i}.png").write_bytes(png)
    return sorted(
        out_dir.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1])
    )


# ------------------------------------------------- slajd „Dane jako kontrakt”
RAW_COLUMNS = [
    "country",
    "year",
    "coal_electricity",
    "gas_electricity",
    "wind_electricity",
    "solar_electricity",
]


def raw_record(csv: Path, year: int) -> str:
    """Jeden wiersz surowego CSV (Polska, ostatni rok) jako lista pól."""
    import polars as pl

    df = pl.read_csv(csv)
    row = df.filter(pl.col("country") == "Poland", pl.col("year") == year).row(
        0, named=True
    )
    rows = "".join(
        f"<div><dt>{html.escape(k)}</dt><dd>{html.escape(str(row[k]))}</dd></div>"
        for k in RAW_COLUMNS
    )
    more = len(df.columns) - len(RAW_COLUMNS)
    return (
        f'<dl class="record">{rows}</dl>'
        f'<p class="record-more">… i {more} kolumn więcej</p>'
    )


def contract_preview(data_json: Path) -> str:
    """Fragment build/data.json — tego, co czyta Typst (wartości skrócone)."""
    d = json.loads(data_json.read_text(encoding="utf-8"))

    def ends(xs: list[float]) -> str:
        return f"[{xs[0]:.1f}, …, {xs[-1]:.1f}]"

    pl = next(r for r in d["europe"] if r["country"] == "Poland")
    coal = d["kpi"]["coal_share_last"]
    code = "\n".join(
        [
            "{",
            f'  "years": [{d["years"][0]}, …, {d["years"][-1]}],',
            f'  "share": {{"wegiel": {ends(d["share"]["wegiel"])}, …}},',
            f'  "europe": [{{"name_pl": "{pl["name_pl"]}", …}}, …],',
            f'  "kpi": {{"coal_share_last": {coal:.1f}, …}},',
            "  …",
            "}",
        ]
    )
    return highlight(code, "json")


# ------------------------------------------------ slajd „6 grzechów”: wycinki
# Panele „przed” i „po” to powiększone fragmenty tych samych dwóch wykresów
# co na slajdzie 2. Źródło jest osadzone raz (<defs>), wycinki to <use>
# z innym viewBox — bez kopiowania PNG i SVG sześć razy.
def crop_defs(png: str, charts: list[str]) -> str:
    def inner(chart: str) -> str:
        svg = (SLIDE_CHARTS / f"{chart}.svg").read_text(encoding="utf-8")
        return re.sub(r"^<svg[^>]*>|</svg>\s*$", "", svg.strip())

    groups = "".join(f'<g id="crop-{c}">{inner(c)}</g>' for c in charts)
    return (
        '<svg width="0" height="0" style="position:absolute" '
        'aria-hidden="true">'
        f'<defs><image id="crop-{Path(png).stem}" width="800" height="450" '
        f'href="{data_uri(report.BUILD / png, "image/png")}"/>'
        f"{groups}</defs></svg>"
    )


_crop_ids = itertools.count(1)


def crop(arg: str) -> str:
    """`zrodlo|x y w h` → SVG pokazujący tylko ten prostokąt źródła.

    clipPath odcina resztę źródła, która inaczej byłaby widoczna, gdy
    proporcje panelu różnią się od proporcji wycinka.
    """
    src, _, box = arg.partition("|")
    x, y, w, h = box.split()
    cid = f"crop-clip-{next(_crop_ids)}"
    return (
        f'<svg class="crop" viewBox="{box}" '
        'preserveAspectRatio="xMidYMid meet">'
        f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" '
        f'height="{h}"/></clipPath>'
        f'<use href="#crop-{Path(src).stem}" clip-path="url(#{cid})"/></svg>'
    )


# --------------------------------------------------------------------- szablon
def fmt_pl(value: float, digits: int) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def fill(template: str, ctx: dict) -> str:
    def repl(m: re.Match) -> str:
        kind, _, arg = m.group(1).partition(":")
        if kind == "chart":
            return inline_svg(arg)
        if kind == "code":
            name, _, rest = arg.partition("|")
            lang, _, mark = rest.partition("|")
            return highlight(snippet(name), lang or "py", mark or None)
        if kind == "num":  # {{num:kpi_key|cyfry}}
            key, _, digits = arg.partition("|")
            return fmt_pl(float(ctx["kpi"][key]), int(digits or 0))
        if kind == "raw":
            return str(ctx["kpi"][arg])
        if kind == "img":
            return data_uri(report.BUILD / arg, "image/png")
        if kind == "asset":  # grafiki z prezentacja/assets (loga, zrzuty)
            return data_uri(HERE / "assets" / arg, ASSET_MIME[Path(arg).suffix])
        if kind == "var":
            return html.escape(str(ctx[arg]))
        if kind == "crop":  # {{crop:przed.png|x y w h}}
            return crop(arg)
        if kind == "cropdefs":  # {{cropdefs:przed.png|mix_small,mix_plain}}
            png, _, charts = arg.partition("|")
            return crop_defs(png, charts.split(","))
        if kind == "block":  # gotowy HTML policzony z danych
            return ctx["blocks"][arg]
        raise KeyError(m.group(0))

    template = re.sub(
        r"<!--(?!PAGES).*?-->", "", template, flags=re.S
    )  # komentarze autora nie trafiają do HTML
    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", repl, template)


HELP = '<div class="help">→ / spacja: dalej · ← wstecz · F pełny ekran</div>'


def main() -> None:
    parser = argparse.ArgumentParser(description="Buduje prezentację HTML")
    parser.add_argument("-o", "--output", type=Path, default=OUT)
    args = parser.parse_args()

    t0 = time.perf_counter()
    report.BUILD.mkdir(exist_ok=True)
    rd = build_report_data(report.DATA)
    rd.to_json(report.BUILD / "data.json")
    THEME.export_json(report.BUILD / "theme.json")
    t1 = time.perf_counter()
    report.render_charts(rd)
    # wariant okładkowy pasków: szerszy kadr pod slajd 16:9
    render_slide_charts(rd)
    t2 = time.perf_counter()
    report.compile_pdf(report.BUILD / "raport.pdf")
    t3 = time.perf_counter()
    pages = render_pages(report.TYPST_MAIN)

    ink = THEME.ink
    tokens = ";".join(
        f"--{k.replace('_', '-')}:{v}" for k, v in vars(ink).items()
    )
    ctx = {
        "kpi": rd.kpi,
        "t_data": f"{(t1 - t0) * 1000:.0f}",
        "t_charts": f"{(t2 - t1) * 1000:.0f}",
        "t_pdf": f"{(t3 - t2) * 1000:.0f}",
        "t_total": fmt_pl(t3 - t0, 1),
        "first_year": rd.first_year,
        "last_year": rd.last_year,
        "compare_year": rd.compare_year,
        "accent": ink.accent,
        "data_file": report.DATA.name,
        "coal_drop_pp": fmt_pl(
            rd.kpi["coal_share_compare"] - rd.kpi["coal_share_last"], 0
        ),
        "n_owid_cols": sum(len(c) for c in SOURCE_COLUMNS.values()),
        "n_sources": len(SOURCE_COLUMNS),
        "blocks": {
            "raw": raw_record(report.DATA, rd.last_year),
            "contract": contract_preview(report.BUILD / "data.json"),
        },
    }
    template = (HERE / "slides.html").read_text(encoding="utf-8")
    template = template.replace("<!--HELP-->", HELP)
    body = fill(template, ctx)
    pages_html = "".join(
        f'<img src="{data_uri(p, "image/png")}" alt="Strona {i} raportu">'
        for i, p in enumerate(pages, start=1)
    )
    body = body.replace("<!--PAGES-->", pages_html)

    doc = f"""<!doctype html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport"
      content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Perfekcyjne wizualizacje w Pythonie</title>
<style>
{font_css()}
:root{{{tokens}}}
{(HERE / "deck.css").read_text(encoding="utf-8")}
</style>
</head>
<body>
{body}
<script>
{(HERE / "deck.js").read_text(encoding="utf-8")}
</script>
</body>
</html>
"""
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    n_slides = body.count('class="slide')
    size_kb = round(len(doc.encode()) / 1024)
    print(f"prezentacja → {out}  ({n_slides} slajdów, {size_kb} KB)")


if __name__ == "__main__":
    main()
