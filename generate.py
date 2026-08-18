"""
Spike: 11x17" print-ready poster layout in ReportLab.

Exercises the risky parts of the astrology-poster spec end to end:
  1. 11x17 tabloid canvas (792 x 1224 pt), vector-only output
  2. "Ornate Inset Label Frame" boxes: thin double vector borders with
     concave arched end-caps (quarter-arc corner scoops)
  3. All-caps bold-serif headlines with +12% letter tracking
  4. Dynamic font-downscaling guards:
       - single-line customer name: never wraps, never touches the frame
       - 450-char paragraph: shrinks until it fits its fixed frame
  5. Vector glyph stamped in a pocket a fixed distance left of the title
     (both a native-drawn glyph and an SVG imported via svglib)
  6. 6pt light-grey legal footnote at the absolute bottom margin
  7. Transparent interiors everywhere - only strokes, no fills, so
     parchment shows through

Run:  python generate.py  ->  out/sample_poster.pdf
"""

import os

from reportlab.graphics import renderPDF
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from svglib.svglib import svg2rlg

PAGE_W, PAGE_H = 11 * inch, 17 * inch  # 792 x 1224 pt

# Placeholder "Regal Court" palette - client's real RGB values drop in here.
BORDER = HexColor("#9A7B2D")   # antique gold
TITLE_INK = HexColor("#2B1B4E")  # deep court purple
BODY_INK = HexColor("#1A1A1A")   # charcoal
GLYPH_INK = HexColor("#1A1A1A")  # spec: solid charcoal glyphs
FOOT_GREY = HexColor("#7F7F7F")  # spec: light grey footnote

SERIF_BOLD = "Times-Bold"    # stand-in; production registers the client's TTF
SERIF_BODY = "Times-Roman"

MARGIN = 0.75 * inch
TRACKING = 0.12  # +12% of font size, inside the spec's 10-15% window


# ---------------------------------------------------------------- frames ---

def ornate_frame(c, x, y, w, h, r=10, inner_gap=3):
    """Thin double border with concave quarter-arc corner scoops.

    Interior is left unfilled so the parchment texture shows through.
    """
    for inset, weight in ((0, 1.0), (inner_gap, 0.4)):
        xi, yi = x + inset, y + inset
        wi, hi = w - 2 * inset, h - 2 * inset
        ri = max(r - inset, 2)
        c.setStrokeColor(BORDER)
        c.setLineWidth(weight)
        # edges, stopping short of each corner
        c.line(xi + ri, yi, xi + wi - ri, yi)              # bottom
        c.line(xi + ri, yi + hi, xi + wi - ri, yi + hi)    # top
        c.line(xi, yi + ri, xi, yi + hi - ri)              # left
        c.line(xi + wi, yi + ri, xi + wi, yi + hi - ri)    # right
        # concave scoops: arcs centered ON each corner, bowing inward
        c.arc(xi - ri, yi - ri, xi + ri, yi + ri, 0, 90)                    # bottom-left
        c.arc(xi + wi - ri, yi - ri, xi + wi + ri, yi + ri, 90, 90)         # bottom-right
        c.arc(xi - ri, yi + hi - ri, xi + ri, yi + hi + ri, 270, 90)        # top-left
        c.arc(xi + wi - ri, yi + hi - ri, xi + wi + ri, yi + hi + ri, 180, 90)  # top-right


# ------------------------------------------------------------------ text ---

def tracked_width(text, font, size, tracking=TRACKING):
    """Width of a string including letter tracking.

    stringWidth() knows nothing about charSpace, so the tracking gaps
    (one per inter-character gap) must be added by hand.
    """
    return stringWidth(text, font, size) + max(len(text) - 1, 0) * size * tracking


def draw_tracked_center(c, text, cx, y, font, size, color, tracking=TRACKING):
    """Center a tracked, all-caps line on cx. Returns the width drawn."""
    text = text.upper()
    w = tracked_width(text, font, size, tracking)
    t = c.beginText()
    t.setTextOrigin(cx - w / 2, y)
    t.setFont(font, size)
    t.setFillColor(color)
    t.setCharSpace(size * tracking)
    t.textOut(text)
    # PDF charSpace (Tc) is persistent graphics state: it survives the end
    # of this text object and would silently track-out every Paragraph and
    # drawString that follows. Reset before closing the text object.
    t.setCharSpace(0)
    c.drawText(t)
    # trailing charSpace is emitted after the final glyph; harmless for
    # centering because we measured the same way we drew
    return w


def fit_line_size(text, font, max_width, start_size, min_size=6.0,
                  tracking=TRACKING, step=0.5):
    """Downscale until a single line fits max_width. The 'name guard'."""
    size = start_size
    while size > min_size and tracked_width(text.upper(), font, size, tracking) > max_width:
        size -= step
    return size


def draw_fitted_paragraph(c, text, x, y_top, w, h, start_size=10.5,
                          min_size=6.0, step=0.25):
    """Shrink a paragraph until wrap() proves it fits the fixed frame.

    Returns the font size used. Platypus' KeepInFrame(mode='shrink') does
    this too, but the explicit loop is auditable and reports the size.
    """
    size = start_size
    while size >= min_size:
        style = ParagraphStyle(
            "body", fontName=SERIF_BODY, fontSize=size,
            leading=size * 1.3, textColor=BODY_INK, alignment=TA_JUSTIFY,
        )
        para = Paragraph(text, style)
        _, needed_h = para.wrap(w, h)
        if needed_h <= h:
            para.drawOn(c, x, y_top - needed_h)
            return size
        size -= step
    raise ValueError("paragraph cannot fit frame even at minimum size")


# ---------------------------------------------------------------- glyphs ---

def draw_hourglass(c, cx, cy, s):
    """Solid vector hourglass, drawn natively (no SVG dependency)."""
    c.setFillColor(GLYPH_INK)
    c.setStrokeColor(GLYPH_INK)
    c.setLineWidth(0.8)
    half = s / 2
    p = c.beginPath()
    p.moveTo(cx - half, cy + half)
    p.lineTo(cx + half, cy + half)
    p.lineTo(cx - half, cy - half)
    p.lineTo(cx + half, cy - half)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.line(cx - half * 1.2, cy + half, cx + half * 1.2, cy + half)
    c.line(cx - half * 1.2, cy - half, cx + half * 1.2, cy - half)


SCROLL_SVG = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
  <path fill="#1A1A1A" d="M6 3c-1.7 0-3 1.3-3 3s1.3 3 3 3h1v10c0 1.7 1.3 3 3
    3h8c1.7 0 3-1.3 3-3v-1h-2v1c0 .6-.4 1-1 1h-8c-.6 0-1-.4-1-1V9h10V6
    c0-1.7-1.3-3-3-3H6zm0 2h7.2c-.1.3-.2.6-.2 1v1H6c-.6 0-1-.4-1-1s.4-1 1-1z"/>
</svg>"""


def draw_svg_glyph(c, svg_path, x, y, target):
    """Import an SVG with svglib and stamp it as vectors at (x, y)."""
    drawing = svg2rlg(svg_path)
    scale = target / max(drawing.width, drawing.height)
    drawing.scale(scale, scale)
    drawing.width *= scale
    drawing.height *= scale
    renderPDF.draw(drawing, c, x, y)


# ------------------------------------------------------------ chart wheel ---

def chart_wheel(c, cx, cy, r):
    """Placeholder natal wheel: rings, 12 houses, tick marks."""
    c.setStrokeColor(BORDER)
    c.setLineWidth(1.0)
    c.circle(cx, cy, r)
    c.setLineWidth(0.4)
    c.circle(cx, cy, r * 0.82)
    c.circle(cx, cy, r * 0.35)
    import math
    for i in range(12):
        a = math.radians(i * 30)
        c.setLineWidth(0.4)
        c.line(cx + r * 0.35 * math.cos(a), cy + r * 0.35 * math.sin(a),
               cx + r * math.cos(a), cy + r * math.sin(a))
    for i in range(72):
        a = math.radians(i * 5)
        c.setLineWidth(0.3)
        c.line(cx + r * 0.96 * math.cos(a), cy + r * 0.96 * math.sin(a),
               cx + r * math.cos(a), cy + r * math.sin(a))


# ------------------------------------------------------------------ main ---

def main():
    os.makedirs("out", exist_ok=True)
    svg_file = os.path.join("out", "scroll.svg")
    with open(svg_file, "w") as f:
        f.write(SCROLL_SVG)

    c = canvas.Canvas(os.path.join("out", "sample_poster.pdf"),
                      pagesize=(PAGE_W, PAGE_H))
    c.setTitle("Signature Star Mapping - layout spike")

    # deliberately hostile inputs for the two guard rules
    long_name = "Alexandrina-Konstantina Papadopoulos-Wintergarden III"
    body_450 = (
        "Born beneath a sky arranged in rare symmetry, this chart shows the "
        "Sun standing in its own dignity while the Moon answers from the "
        "opposite horizon, a balance that marks a life of deliberate purpose. "
        "Mercury rises close to the Ascendant, lending precise speech and an "
        "instinct for timing. Saturn's steady trine to the Midheaven builds "
        "ambition brick by brick, and Venus in the fifth house promises that "
        "what is built will also be loved and shared."
    )
    assert 430 <= len(body_450) <= 460, len(body_450)

    # --- header ------------------------------------------------------------
    title_size = fit_line_size("Signature Star Mapping", SERIF_BOLD,
                               PAGE_W - 2 * MARGIN, 34)
    draw_tracked_center(c, "Signature Star Mapping", PAGE_W / 2,
                        PAGE_H - MARGIN - 30, SERIF_BOLD, title_size, TITLE_INK)

    # name line with the no-wrap guard (starts at 24pt, shrinks as needed)
    name_size = fit_line_size(long_name, SERIF_BOLD, PAGE_W - 2 * MARGIN - 40, 24)
    draw_tracked_center(c, long_name, PAGE_W / 2, PAGE_H - MARGIN - 62,
                        SERIF_BOLD, name_size, BODY_INK)

    # --- top section: chart wheel -----------------------------------------
    wheel_r = 3.1 * inch
    wheel_cy = PAGE_H - MARGIN - 95 - wheel_r
    chart_wheel(c, PAGE_W / 2, wheel_cy, wheel_r)

    # --- lower section: 5 stacked ornate boxes -----------------------------
    boxes_top = wheel_cy - wheel_r - 30
    footer_h = 24
    gap = 12
    box_h = (boxes_top - MARGIN - footer_h - 4 * gap) / 5
    box_w = PAGE_W - 2 * MARGIN
    box_titles = ["Solar Identity", "Lunar Nature", "Rising Sign",
                  "Houses of Fortune", "The Year Ahead"]

    used_sizes = []
    for i, box_title in enumerate(box_titles):
        bx = MARGIN
        by = boxes_top - box_h - i * (box_h + gap)
        ornate_frame(c, bx, by, box_w, box_h)

        # centered tracked title, glyph pocket 15pt to its left (spec: "15px")
        t_size = 13
        t_y = by + box_h - 26
        t_w = draw_tracked_center(c, box_title, PAGE_W / 2, t_y,
                                  SERIF_BOLD, t_size, TITLE_INK)
        glyph_s = 12
        glyph_x = PAGE_W / 2 - t_w / 2 - 15 - glyph_s
        if i % 2 == 0:
            draw_hourglass(c, glyph_x + glyph_s / 2, t_y + 4, glyph_s)
        else:
            draw_svg_glyph(c, svg_file, glyph_x, t_y - 2, glyph_s)

        # 450-char paragraph, auto-shrunk into the remaining box interior
        pad = 16
        size = draw_fitted_paragraph(
            c, body_450, bx + pad, t_y - 10,
            box_w - 2 * pad, box_h - 26 - 10 - pad * 0.5)
        used_sizes.append(size)

    # --- legal footnote -----------------------------------------------------
    disclaimer = ("For entertainment purposes only. Astrological readings are "
                  "not a substitute for professional, financial, medical, or "
                  "legal advice. All interpretations are provided as-is. "
                  "(c) 2026 - all rights reserved.")
    c.setFont(SERIF_BODY, 6)
    c.setFillColor(FOOT_GREY)
    c.drawString(MARGIN, MARGIN * 0.5, disclaimer)

    c.showPage()
    c.save()
    print(f"title size: {title_size}pt, name size: {name_size}pt "
          f"(guard engaged: {name_size < 24})")
    print(f"paragraph sizes per box: {used_sizes}")
    print("wrote out/sample_poster.pdf")


if __name__ == "__main__":
    main()
