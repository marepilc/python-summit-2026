// Raport — treść. Każda liczba w tekście pochodzi z build/data.json:
// po odświeżeniu danych tekst aktualizuje się sam, nikt nie przepisuje liczb ręcznie.

#import "components.typ": *

#let d = json("/build/data.json")
#let k = d.kpi
#let Y0 = str(d.first_year)
#let Y1 = str(d.last_year)
#let YC = str(d.compare_year)
#let last(xs) = xs.at(xs.len() - 1)
#let wind-solar = last(d.twh.wiatr) + last(d.twh.slonce)
#let coal-drop-pp = k.coal_share_compare - k.coal_share_last
#let ic = d.years.position(y => y == d.compare_year)
#let wind-solar-compare = d.twh.wiatr.at(ic) + d.twh.slonce.at(ic)
#let src-name(key) = lower(theme.source_labels.at(key))
// przyrost produkcji od roku porównania, malejąco (TWh)
#let growth = (theme.source_order
  .map(key => (key: key, diff: last(d.twh.at(key)) - d.twh.at(key).at(ic)))
  .sorted(key: g => -g.diff))
#let top3 = (growth.slice(0, 3)
  .map(g => [#src-name(g.key) +#num(g.diff) TWh])
  .join(", "))
// pozostałe źródła poza węglem, od największego udziału
#let others = (theme.source_order.filter(key => key != "wegiel")
  .sorted(key: key => -last(d.share.at(key))))
#let rank-text(rank, n) = if rank == 1 [najwyższa wśród #n] else [#rank. miejsce wśród #n]

#show: report.with(title: "Węgiel traci grunt", subtitle: "Elektroenergetyka w Polsce " + Y0 + "–" + Y1)

// =================================================================== 1. OKŁADKA
#page(header: none, footer: none, margin: (x: lay.margin_x_mm * 1mm, top: 24mm, bottom: 18mm))[
  #kicker[Raport danych · Elektroenergetyka w Polsce]
  #v(14pt)
  #text(font: ty.serif, size: 54pt, weight: 600, tracking: -0.02em, fill: c("primary"),
    par(leading: 0.22em)[Węgiel\ traci grunt])
  #v(18pt)
  #block(width: 78%, text(size: 13pt, fill: c("secondary"))[
    Jak w ciągu #(d.last_year - d.first_year) lat zmieniło się źródło polskiego prądu, co zastępuje
    węgiel i gdzie jesteśmy na tle Unii Europejskiej.
  ])
  #v(1fr)
  #image("/build/charts/stripes.svg", width: 100%)
  #v(1fr)
  #grid(
    columns: (1fr, 1fr, 1fr),
    column-gutter: 18pt,
    figure-stat(num(k.coal_share_last, d: 0) + "%",
      [prądu z węgla w #Y1 r. (#num(k.coal_share_first, d: 0)% w #Y0 r.)]),
    figure-stat(num(k.intensity_last, d: 0),
      [gCO₂ na kWh — najwięcej w UE, #num(k.pl_vs_eu_intensity)× średnia unijna]),
    figure-stat("×" + num(k.solar_growth_since_2019, d: 0),
      [tyle razy wzrosła produkcja energii ze słońca od 2019 r.]),
  )
  #v(16pt)
  #line(length: 100%, stroke: 0.5pt + c("rule"))
  #v(2pt)
  #grid(columns: (1fr, auto),
    text(size: ty.tick * 1pt, fill: c("muted"))[Marek Pilczuk · Python Summit 2026],
    text(size: ty.tick * 1pt, fill: c("muted"))[Dane: Our World in Data (Ember, Energy Institute)],
  )
]

// =================================================================== 2. W SKRÓCIE
#section("W skrócie", [Udział węgla: #num(k.coal_share_first, d: 0)% w #Y0 r., #num(k.coal_share_last, d: 0)% w #Y1 r.],
  lead: [
    Reszta produkcji w #Y1 r.: #others.slice(0, 3).map(key => [#src-name(key) #num(last(d.share.at(key)))%]).join(", ")
    oraz inne źródła łącznie #num(others.slice(3).map(key => last(d.share.at(key))).sum())%.
  ])

#grid(
  columns: (1fr, 1fr),
  gutter: lay.gutter_pt * 1pt,
  kpi([Udział węgla w produkcji prądu], num(k.coal_share_last), unit: "%", spark: "spark_coal",
    note: [#Y0: #num(k.coal_share_first)% · #YC: #num(k.coal_share_compare)%]),
  kpi([Udział OZE (wiatr, słońce, biomasa, woda)], num(k.oze_share_last), unit: "%", spark: "spark_oze",
    note: [#YC: #num(k.oze_share_compare)%]),
  kpi([Emisyjność produkcji prądu], num(k.intensity_last, d: 0), unit: "gCO₂/kWh", spark: "spark_intensity",
    note: [#Y0: #num(k.intensity_first, d: 0) · średnia UE: #num(d.eu_avg.intensity_end, d: 0)]),
  kpi([Produkcja energii ze słońca], num(k.solar_twh_last), unit: "TWh", spark: "spark_solar",
    note: [od 2000 r. · 2019 → #Y1: ×#num(k.solar_growth_since_2019, d: 0)]),
)

#v(22pt)
#grid(
  columns: (1fr, 1fr),
  column-gutter: 26pt,
  chart("waffle",
    title: [Struktura produkcji prądu, #Y1],
    subtitle: [100 kratek = #num(k.total_twh_last, d: 0) TWh],
    source: [Our World in Data]),
  [
    #text(size: 10.5pt, weight: 600)[Najważniejsze liczby]
    #v(10pt)
    #finding(1, [Węgiel: #num(k.coal_share_last)% produkcji],
      [#num(k.coal_twh_last, d: 0) TWh z węgla wobec #num(k.total_twh_last - k.coal_twh_last, d: 0) TWh ze wszystkich pozostałych źródeł razem.])
    #v(10pt)
    #finding(2, [Wiatr i słońce: #num(wind-solar, d: 0) TWh],
      [#num((last(d.share.wiatr) + last(d.share.slonce)), d: 0)% produkcji; w #YC r. — #num(wind-solar-compare, d: 0) TWh.])
    #v(10pt)
    #finding(3, [Emisyjność: #rank-text(int(k.pl_intensity_rank), int(k.eu_count)) krajów UE],
      [#num(k.intensity_last, d: 0) gCO₂/kWh — #num(k.pl_vs_eu_intensity)× średnia unijna (#num(d.eu_avg.intensity_end, d: 0) gCO₂/kWh).])
  ],
)

#v(1fr)
#let gas-bio = last(d.twh.gaz) + last(d.twh.biomasa)
#callout[Od #YC r. produkcja z wiatru i słońca wzrosła z #num(wind-solar-compare, d: 0) do #num(wind-solar, d: 0) TWh
  #if wind-solar > gas-bio [— to więcej niż cała produkcja z gazu i biomasy razem.] else [.]]
#v(8pt)

#pagebreak()

// =================================================================== 3. MIKS
#section(
  "Miks energetyczny",
  [Od #YC r. udział węgla spadł
   o #num(coal-drop-pp, d: 0) pkt proc.],
  lead: [
    Dla porównania: w latach #Y0–#YC spadł
    o #num(k.coal_share_first - k.coal_share_compare, d: 0) pkt proc.
    Największy przyrost produkcji
    od #YC r.: #top3.
  ],
)

#chart("mix",
  title: [Udział źródeł w produkcji energii elektrycznej],
  subtitle: [% rocznej produkcji, Polska #Y0–#Y1],
  source: [Our World in Data na podstawie Ember i Energy Institute. „Ropa i inne” obejmuje ropę i pozostałe OZE.])

#v(20pt)
#chart("multiples",
  title: [Wiatr i słońce: z niemal zera do #num(wind-solar, d: 0) TWh],
  subtitle: [Produkcja energii elektrycznej, TWh, 2000–#Y1. Wspólna skala dla wszystkich paneli.],
  source: [Our World in Data])

#v(16pt)
#callout[W #Y1 r. z węgla wyprodukowano #num(k.coal_twh_last, d: 0) TWh, wobec #num(k.coal_twh_first, d: 0) TWh
  w #Y0 r. Łączna produkcja energii elektrycznej wzrosła w tym czasie z #num(d.total_twh.at(0), d: 0)
  do #num(k.total_twh_last, d: 0) TWh.]

#pagebreak()

// =================================================================== 4. EUROPA
#let coal-rows = d.europe.filter(r => r.coal_start >= 10)
#let coal-down = coal-rows.filter(r => r.coal_end < r.coal_start).len()
#let coal-top = d.europe.sorted(key: r => -r.coal_end).first().name_pl
#section("Polska na tle Unii", [Udział węgla w UE #(YC)–#(Y1): spadek w #coal-down z #(coal-rows.len()) krajów],
  lead: [
    Dotyczy krajów, w których w #YC r. węgiel dawał co najmniej 10% prądu. W Polsce udział węgla
    spadł z #num(k.coal_share_compare, d: 0)% do #num(k.coal_share_last, d: 0)%. Najwyższy udział w #Y1 r.: #coal-top.
  ])

#grid(
  columns: (1fr, 1fr),
  gutter: lay.gutter_pt * 1pt,
  chart("dumbbell",
    title: [Udział węgla w produkcji prądu],
    subtitle: [Kraje UE z udziałem ≥ 10% w #YC r.],
    source: [Our World in Data]),
  chart("ranking",
    title: [Emisyjność produkcji prądu, #Y1],
    subtitle: [gCO₂ na kWh, wszystkie kraje UE-27],
    source: [Our World in Data]),
)

#v(1fr)
#callout[Emisyjność polskiego prądu spadła od #Y0 r. o #num((1 - k.intensity_last / k.intensity_first) * 100, d: 0)% —
  do #num(k.intensity_last, d: 0) gCO₂/kWh. To #rank-text(int(k.pl_intensity_rank), int(k.eu_count)) krajów Unii.]

#v(14pt)
#line(length: 100%, stroke: 0.5pt + c("rule"))
#v(4pt)
#text(size: ty.tick * 1pt, fill: c("muted"))[
  *Dane:* Our World in Data (owid/energy-data) na podstawie Ember i Energy Institute, licencja CC BY 4.0.
  Udziały liczone z produkcji w TWh. *OZE* — biomasa, woda, wiatr, słońce. *Emisyjność* — gCO₂ (ekw.) na kWh.
]
