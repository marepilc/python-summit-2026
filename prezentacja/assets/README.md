# Grafiki do slajdów

## Slajd „Kto mówi”

| Plik | Źródło |
|---|---|
| `pydreamplet_logo.png`, `pydreamplet_*.svg` | [py.dreamplet.com](https://py.dreamplet.com) · repozytorium [marepilc/pydreamplet](https://github.com/marepilc/pydreamplet) (`docs/public`) |
| `pinkparquet_logo.svg` (z nagłówka strony), `pinkparquet_screenshot.jpg` | [pinkparquet.com](https://www.pinkparquet.com) · repozytorium [marepilc/pink-parquet](https://github.com/marepilc/pink-parquet) |

Oba projekty: licencja MIT, autor Marek Pilczuk.

## Slajd tytułowy i końcowy

`pys26_tytul.png`, `pys26_koniec.png` — grafiki z szablonu prezentacji Python Summit 2026 (organizator: Fundacja Academic Partners).

## Slajd końcowy — kod QR

`qr_repo.svg` — adres `https://github.com/marepilc/python-summit-2026`, wygenerowany biblioteką [segno](https://github.com/heuer/segno):

```bash
uv run --with segno python -c "import segno; segno.make('https://github.com/marepilc/python-summit-2026', error='m').save('prezentacja/assets/qr_repo.svg', kind='svg', scale=10, border=2, dark='#321207', light='#FFFFFF', xmldecl=False)"
```
