# Perfekcyjne wizualizacje w Pythonie: raporty bez kompromisów

Materiały z wystąpienia na **Python Summit 2026** (Warszawa, 19–20 października 2026) · Marek Pilczuk

Case study: czterostronicowy raport PDF **„Węgiel traci grunt”** o produkcji prądu w Polsce w latach 1990–2025,
zbudowany w całości w Pythonie jednym poleceniem — od pliku z danymi do gotowego PDF-a.

| | |
|---|---|
| **Slajdy** | [`build/prezentacja.html`](build/prezentacja.html) — jeden plik, działa offline |
| **Raport** | [`build/raport.pdf`](build/raport.pdf) |
| **Jak powstał raport** | [`docs/jak-powstal-raport.md`](docs/jak-powstal-raport.md) — dane, proces, system wizualny, zasady |

```
dane (CSV) ──Polars──▶ ReportData ──pyDreamplet──▶ wykresy SVG (1 jednostka = 1 pt)
                           │                                  │
                           └──▶ data.json ──┐   theme.json ◀──┤◀── theme.py (wygląd)
                                            ▼                 │
                                         Typst ◀──────────────┘ ──▶ raport.pdf
```

## Prezentacja

Otwórz `build/prezentacja.html` w przeglądarce (Chrome, Edge, Firefox). Plik ma wszystko w środku — fonty, wykresy,
strony raportu — więc nie potrzebuje internetu ani serwera.

```bash
xdg-open build/prezentacja.html      # Linux
open build/prezentacja.html          # macOS
start build\prezentacja.html         # Windows
```

Albo w osobnym oknie bez paska przeglądarki (Chrome / Chromium / Edge):

```bash
chromium --app="file://$PWD/build/prezentacja.html"
```

| Klawisz | Działanie |
|---|---|
| → · spacja · klik | dalej (najpierw kolejne kroki slajdu) |
| ← | wstecz |
| F | pełny ekran |
| R | powtórz animację bieżącego slajdu |
| Home / End | pierwszy / ostatni slajd |

Adres `prezentacja.html#15.3` otwiera slajd 15 w kroku 3. Na slajdzie 21 można kliknąć kolorowe kółka —
zmienia się akcent w wykresie i w całej prezentacji.

Wykresy na slajdach to te same funkcje, które rysują wykresy do raportu, a fragmenty kodu są wycinane
z plików tego repozytorium przy każdym budowaniu.

## Wygenerowanie raportu

Potrzebny jest Python 3.12 lub nowszy. Najprościej z [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python -m raport.build            # dane → wykresy → PDF   → build/raport.pdf
uv run python -m raport.build --no-pdf   # tylko wykresy SVG (szybka iteracja)
```

Bez uv:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install polars pydreamplet typst pygments
python -m raport.build
```

Typst instaluje się jako pakiet Pythona, a fonty są w folderze `fonts/` — nic nie trzeba instalować w systemie.
Build wypisuje czas każdego etapu; cały raport powstaje w ułamku sekundy.

Spróbuj zmienić w [`raport/theme.py`](raport/theme.py) wartość `accent` (np. na `"#1F6FEB"`) i zbudować raport
jeszcze raz — zmienią się wykresy, układ i tekst naraz.

## Odbudowanie prezentacji

```bash
uv run python -m prezentacja.build     # → build/prezentacja.html (buduje też raport)
```

Treść slajdów jest w [`prezentacja/slides.html`](prezentacja/slides.html) (zwykły HTML ze znacznikami `{{...}}`,
które wypełnia `prezentacja/build.py`), wygląd w `deck.css`, nawigacja i animacje w `deck.js`.

## Struktura

| Ścieżka | Rola |
|---|---|
| `raport/theme.py` | wygląd: kolory, fonty, skala typograficzna, układ; eksport do `build/theme.json` |
| `raport/data.py` | Polars: dane OWID → `ReportData` (jedyne, co widzą wykresy i szablon) |
| `raport/charts/base.py` | płótno w punktach (`Canvas`), pomiar tekstu (HarfBuzz), osie, polski format liczb |
| `raport/charts/*.py` | wykresy: paski węglowe, miks 100%, small multiples, waffle, dumbbell UE, ranking, sparkline |
| `raport/build.py` | jedno polecenie od danych do PDF, z pomiarem czasu etapów |
| `template/components.typ` | komponenty Typst: `report`, `section`, `chart`, `kpi`, `callout`, `num` |
| `template/raport.typ` | treść raportu — wszystkie liczby z `build/data.json` |
| `prezentacja/` | slajdy HTML i ich build |
| `scripts/` | wykres „przed” (`00_przed.py`), grafiki do `docs/`, odświeżenie danych (`fetch_data.py`) |
| `data/owid_energy_eu.csv` | wycinek [owid/energy-data](https://github.com/owid/energy-data): UE-27, 1990–2025 |
| `fonts/` | Inter, Source Serif 4, IBM Plex Mono |

Biblioteka do wykresów: [pyDreamplet](https://py.dreamplet.com) ([GitHub](https://github.com/marepilc/pydreamplet)).

## Dane i licencje

- **Kod:** licencja [MIT](LICENSE).
- **Dane:** [Our World in Data](https://ourworldindata.org/energy) na podstawie Ember i Energy Institute, licencja
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Odświeżenie: `uv run python scripts/fetch_data.py`
  (wymaga internetu; wyniki mogą się wtedy różnić od tych na slajdach).
- **Fonty:** licencja SIL Open Font License, pliki licencji w `fonts/`.
- **Grafiki Python Summit 2026** na slajdzie tytułowym i końcowym należą do organizatora (Fundacja Academic Partners).
