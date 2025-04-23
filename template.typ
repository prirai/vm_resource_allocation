#let project(title: "", authors: (), subtitle: none, body) = {
  set document(author: authors, title: title)
  set page(numbering: "1", number-align: end)
  set page(margin: 6em)
  set text(font: "Libertinus Serif", lang: "en", size: 12pt)
  show math.equation: set text(weight: 400)

  show link: underline
  show cite: set text(fill: blue)
  show link: set text(fill: blue)
  show figure.caption: emph
  set par(spacing: 1.2em)

  set par(leading: 0.75em)

  align(center)[
    #block(text(weight: 700, 1.75em, title))
  ]

  // Add subtitle if provided
  if subtitle != none {
    align(center)[
      #block(text(weight: 400, 1.25em, subtitle))
    ]
  }

  pad(
    top: 0.5em,
    bottom: 0.5em,
    x: 0em,
    grid(
      columns: (0.5fr,) * calc.min(4, authors.len()),
      gutter: 5em,
      ..authors.map(author => align(center, strong(author))),
    ),
  )

  set par(justify: true)

  body
}

#let fancy-table = table.with(
  align: center,
  stroke: 0.7pt,
  inset: 5pt,
  fill: (_, row) => if row == 0 { rgb("#e5e5e5") } else { none },
)
