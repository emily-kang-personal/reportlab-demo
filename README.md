# reportlab-demo

Spike: print-ready 11x17" (tabloid) poster layout generated entirely in Python
with ReportLab. Vector-only output intended for physical printing on parchment,
so all box interiors are transparent — strokes only, no fills.

![sample](out/sample_poster.pdf)

## What it exercises

- 11x17" canvas (792 x 1224 pt) with a placeholder natal chart wheel
- "Ornate inset label frames": thin double vector borders with concave
  quarter-arc corner scoops
- All-caps bold-serif headlines with +12% letter tracking (`setCharSpace`)
- Two dynamic font-downscaling guards:
  - single-line name: measured with `stringWidth` + tracking, shrunk until it
    cannot wrap or touch its frame
  - ~450-character paragraphs: shrunk via a `Paragraph.wrap()` measure loop
    until they provably fit their fixed frame
- Vector glyphs stamped in a pocket 15 pt left of each title — one drawn
  natively, one imported from SVG via `svglib` (stays vector in the PDF)
- 6 pt light-grey legal footnote pinned to the bottom margin

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install reportlab svglib
.venv/bin/python generate.py
open out/sample_poster.pdf
```

## The gotcha worth knowing

PDF character spacing (`Tc`) is persistent graphics state: setting
`setCharSpace` inside a text object silently leaks into every paragraph and
`drawString` that follows, tracking-out the entire rest of the page. Reset it
to 0 before closing the text object. `generate.py` documents this at the
call site — the first render of this spike hit it.
