// Design system raportu w Typst.
// Wszystkie wartości pochodzą z build/theme.json (generowanego z raport/theme.py),
// więc kolory i fonty w PDF są identyczne z tymi w wykresach SVG.

#let theme = json("/build/theme.json")
#let ink = theme.ink
#let ty = theme.type
#let lay = theme.layout
#let c(name) = rgb(ink.at(name))
#let src-color(key) = rgb(theme.sources.at(key))

// ------------------------------------------------------------------ liczby
// 50.398 → "50,4" ; ujemne z prawdziwym minusem
#let num(x, d: 1) = {
  let r = calc.round(float(x), digits: d)
  let s = if d == 0 { str(int(r)) } else {
    let s = str(r)
    if not s.contains(".") { s += "." }
    let frac = s.split(".").at(1).len()
    s + "0" * (d - frac)
  }
  s.replace(".", ",").replace("-", "−")
}

// ------------------------------------------------------------------ typografia
#let kicker(body) = text(
  font: ty.sans, size: ty.tick * 1pt + 0.5pt, weight: 600, tracking: 0.12em, fill: c("accent"), upper(body),
)

// Odstępy: nadtytuł → tytuł 9 pt, tytuł → lead 16 pt, lead → treść 24 pt.
// Tytuł ma ciaśniejszą interlinię niż tekst (duży stopień, krótkie wiersze).
#let section(kicker-text, title, lead: none) = {
  block(below: 9pt)[#kicker(kicker-text)]
  block(below: 0pt, text(font: ty.serif, size: ty.h2 * 1pt, weight: 600, fill: c("primary"),
    par(leading: 0.42em, title)))
  if lead != none {
    block(above: 16pt, below: 0pt, width: 88%,
      text(size: ty.lead * 1pt - 1pt, fill: c("secondary"), par(leading: 0.62em, lead)))
  }
  v(24pt)
}

// ------------------------------------------------------------------ wykres z ramą redakcyjną
// Tytuł = informacja z danych (nie opis osi i nie ocena), podtytuł = co dokładnie widać,
// stopka = źródło.
#let chart(
  file,
  title: none,
  subtitle: none,
  source: none,
  width: 100%,
) = block(width: width, breakable: false)[
  #if title != none {
    set text(size: 10.5pt, weight: 600, fill: c("primary"))
    block(below: 6pt, par(leading: 0.45em, title))
  }
  #if subtitle != none {
    set text(size: ty.label * 1pt, fill: c("secondary"))
    block(below: 12pt, par(leading: 0.5em, subtitle))
  }
  #image("/build/charts/" + file + ".svg", width: 100%)
  #if source != none {
    set text(size: ty.tick * 1pt, fill: c("muted"))
    v(8pt)
    [Źródło: #source]
  }
]

// ------------------------------------------------------------------ kafel KPI
#let kpi(label, value, unit: none, note: none, spark: none) = block(
  width: 100%,
  fill: c("surface"),
  stroke: 0.5pt + c("rule"),
  radius: 3pt,
  inset: (x: 12pt, top: 11pt, bottom: 10pt),
)[
  #text(size: ty.label * 1pt, fill: c("secondary"), label)
  #v(4pt)
  #grid(
    columns: (auto, 1fr),
    align: (left + bottom, right + bottom),
    column-gutter: 10pt,
    box[
      #text(size: 26pt, weight: 600, fill: c("primary"), tracking: -0.02em, value)
      #if unit != none { h(2pt); text(size: 9pt, weight: 500, fill: c("secondary"), unit) }
    ],
    if spark != none { image("/build/charts/" + spark + ".svg", width: 100pt) },
  )
  #if note != none {
    v(3pt)
    text(size: ty.tick * 1pt + 0.5pt, fill: c("muted"), note)
  }
]

// ------------------------------------------------------------------ wyróżnienie (callout)
#let callout(body) = block(
  width: 100%,
  inset: (left: 12pt, y: 4pt),
  stroke: (left: 2pt + c("accent")),
  text(size: 10.5pt, fill: c("primary"), font: ty.serif, style: "italic", body),
)

// ------------------------------------------------------------------ duża liczba (okładka)
#let figure-stat(value, label) = stack(
  spacing: 7pt,
  text(font: ty.sans, size: 30pt, weight: 600, tracking: -0.03em, fill: c("primary"), value),
  block(width: 100%, text(size: ty.label * 1pt, fill: c("secondary"), label)),
)

// ------------------------------------------------------------------ numerowana informacja
#let finding(n, title, body) = grid(
  columns: (22pt, 1fr),
  gutter: 0pt,
  text(font: ty.serif, size: 20pt, weight: 600, fill: c("accent"), str(n)),
  [
    #block(below: 6pt, text(weight: 600, fill: c("primary"), title))
    #text(fill: c("secondary"), body)
  ],
)

// ------------------------------------------------------------------ szablon dokumentu
#let report(title: "", subtitle: "", body) = {
  set document(title: title, author: "Marek Pilczuk")
  set text(font: ty.sans, size: ty.body * 1pt, fill: c("primary"), lang: "pl", region: "pl", number-type: "lining")
  set par(leading: 0.68em, spacing: 1.1em, justify: false)
  set page(
    paper: "a4",
    fill: c("paper"),
    margin: (x: lay.margin_x_mm * 1mm, top: lay.margin_top_mm * 1mm, bottom: lay.margin_bottom_mm * 1mm),
    header: context {
      let p = counter(page).get().first()
      if p > 1 {
        set text(size: ty.tick * 1pt, fill: c("muted"))
        grid(columns: (1fr, auto), title, subtitle)
        v(1pt)
        line(length: 100%, stroke: 0.5pt + c("rule"))
      }
    },
    footer: context {
      let p = counter(page).get().first()
      if p > 1 {
        set text(size: ty.tick * 1pt, fill: c("muted"))
        grid(columns: (1fr, auto),
          [Dane: Our World in Data],
          text(font: ty.mono, weight: 500, fill: c("primary"), if p < 10 { "0" + str(p) } else { str(p) }),
        )
      }
    },
  )
  show strong: set text(weight: 600)
  body
}
