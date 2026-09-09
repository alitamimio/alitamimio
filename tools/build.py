#!/usr/bin/env python3
"""Emit the profile card as one tall SVG, in both themes.

One image rather than several stacked ones: GitHub puts whitespace between
block images, which would show as seams across a continuous background. And
one image rather than markdown because a README container cannot be styled,
so a background that runs the whole length has to be part of the content.

Animation is SMIL. GitHub serves README images through a proxy that strips
scripts, and an SVG rendered as <img> cannot load a webfont either, so the
type is the system stack and every moving part is declarative.
"""
import pathlib

W, H = 1000, 1040
FONT = "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"

DARK = dict(
    ground="#121517", ink="#f1f3f4", muted="#9fa4a7", faint="#707579",
    line="#2a2e31", rule="#3f4548", brand="#039bb9", sweep="#64d6f2",
    live="#20ac88", blobs=[("#039bb9", .95), ("#027c93", .8), ("#00343f", .9)],
    field=0.72, veil=0.06,
)
LIGHT = dict(
    ground="#f9fafb", ink="#151819", muted="#585f64", faint="#7c848a",
    line="#ced3d9", rule="#dde2e7", brand="#027c93", sweep="#027c93",
    live="#12866a", blobs=[("#64d6f2", .9), ("#00b7d9", .7), ("#a8e7f6", .9)],
    field=0.30, veil=0.30,
)

WORK = [
    ("KHAYARAK",
     "Price comparison for the Jordanian market. Arabic and English, full RTL.",
     "Next.js 16 · Tailwind v4 · TypeScript · Python gateway · streaming answers"),
    ("VOC360",
     "Fourteen services for public-sector feedback: intake, classification, root cause, BI.",
     "FastAPI · PostgreSQL + pgvector · Redis · Docker"),
    ("RASED",
     "Traffic intelligence on live data. Dashboards and computer-vision supervision.",
     "Node · Prometheus · PostgreSQL · Docker"),
    ("FORTILINK",
     "Fortinet integration plugin.",
     "TypeScript"),
]

STACK = [
    ("FRONT", "Next.js · React · TypeScript · Tailwind · SVG motion · a11y · RTL"),
    ("BACK",  "Python · FastAPI · Node · PostgreSQL · Redis · pgvector"),
    ("INFRA", "Docker · Compose · Prometheus · Tailscale · GitHub Actions"),
    ("AI",    "LLM gateways · SSE streaming · RAG · Ollama"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fill, size=16, weight=None, ls=None, opacity=None):
    a = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
    if weight:  a += f' font-weight="{weight}"'
    if ls:      a += f' letter-spacing="{ls}"'
    if opacity: a += f' opacity="{opacity}"'
    return f'  <text {a}>{esc(s)}</text>'


def section(y, label, c):
    """A quiet caps label with a hairline running out to the right margin."""
    return (txt(64, y, label, c["faint"], 11.5, 600, 2) +
            f'\n  <rect x="{64 + 11 * len(label)}" y="{y - 5}" '
            f'width="{W - 64 - (64 + 11 * len(label)) - 40}" height="1" fill="{c["line"]}"/>')


def build(c):
    o = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}" fill="none" font-family="{FONT}">')
    o.append('  <defs>')
    o.append(f'    <clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    o.append('    <filter id="soft" x="-60%" y="-60%" width="220%" height="220%">'
             '<feGaussianBlur stdDeviation="110"/></filter>')
    o.append('    <linearGradient id="sweep" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="360" y2="0">')
    for off, col in ((0, c["ink"]), (0.40, c["ink"]), (0.50, c["sweep"]),
                     (0.60, c["ink"]), (1, c["ink"])):
        o.append(f'      <stop offset="{off}" stop-color="{col}"/>')
    o.append('      <animateTransform attributeName="gradientTransform" type="translate" '
             f'from="-420 0" to="{W + 120} 0" dur="5s" repeatCount="indefinite"/>')
    o.append('    </linearGradient>')
    o.append(f'    <linearGradient id="rule" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{c["brand"]}" stop-opacity="0.9"/>'
             f'<stop offset="1" stop-color="{c["brand"]}" stop-opacity="0"/></linearGradient>')
    o.append('  </defs>')

    # Ground and field
    o.append('  <g clip-path="url(#card)">')
    o.append(f'    <rect width="{W}" height="{H}" fill="{c["ground"]}"/>')
    o.append(f'    <g filter="url(#soft)" opacity="{c["field"]}">')
    drift = [("0 0; -55 60; 35 -30; 0 0", "27s"), ("0 0; 45 -70; -50 30; 0 0", "34s"),
             ("0 0; 70 -40; -25 -60; 0 0", "41s")]
    spots = [(830, 120, 190), (940, 640, 165), (720, 1000, 150)]
    for (cx, cy, r), (fill, op), (vals, dur) in zip(spots, c["blobs"], drift):
        o.append(f'      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" opacity="{op}">'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'values="{vals}" dur="{dur}" repeatCount="indefinite"/></circle>')
    o.append('    </g>')
    o.append(f'    <rect width="{W}" height="{H}" fill="{c["ground"]}" opacity="{c["veil"]}"/>')
    o.append('  </g>')
    o.append(f'  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="18" fill="none" stroke="{c["line"]}"/>')

    # Identity
    o.append(f'  <text x="64" y="122" font-size="56" font-weight="700" letter-spacing="7" '
             f'fill="url(#sweep)">ALI TAMIMI</text>')
    o.append(f'  <rect x="66" y="144" width="300" height="2" rx="1" fill="url(#rule)"/>')
    o.append(txt(66, 182, "Frontend and full-stack engineer.", c["ink"], 17))
    o.append(txt(66, 210, "Most of what I build is bilingual, Arabic and English, "
                          "and ships to people who are not developers.", c["muted"], 15))

    # Live location
    o.append(f'  <g transform="translate(872 52)">'
             f'<circle cx="0" cy="-4" r="4" fill="{c["live"]}">'
             f'<animate attributeName="opacity" values="1;0.35;1" dur="2.8s" repeatCount="indefinite"/>'
             f'</circle>'
             f'<text x="14" y="0" font-size="11.5" letter-spacing="1.6" font-weight="600" '
             f'fill="{c["muted"]}">AMMAN, JO</text></g>')

    # Work
    o.append(section(272, "WORK", c))
    y = 316
    for name, what, tech in WORK:
        o.append(txt(64, y, name, c["brand"], 15, 700, 1.4))
        o.append(txt(64, y + 24, what, c["ink"], 15.5))
        o.append(txt(64, y + 46, tech, c["faint"], 13.5))
        y += 86

    # The gate
    o.append(section(y + 4, "THE GATE", c))
    o.append(txt(64, y + 44, "Every commit runs it: 90 colour pairs checked for WCAG contrast,",
                 c["ink"], 15.5))
    o.append(txt(64, y + 68, "207 files checked against the design rules, then types and lint.",
                 c["ink"], 15.5))

    # Stack
    sy = y + 124
    o.append(section(sy, "STACK", c))
    ry = sy + 40
    for label, value in STACK:
        o.append(f'  <path d="M64 {ry-5} L69 {ry} L64 {ry+5} L59 {ry} Z" fill="{c["brand"]}"/>')
        o.append(txt(82, ry + 4, label, c["faint"], 11.5, 600, 1.6))
        o.append(txt(170, ry + 4, value, c["ink"], 14.5))
        ry += 32

    o.append(txt(64, H - 40, "Amman, Jordan · most of my work is in private and organisation repos",
                 c["faint"], 12.5))
    o.append('</svg>')
    return "\n".join(o) + "\n"


here = pathlib.Path(__file__).resolve().parent.parent / "assets"
here.mkdir(exist_ok=True)
for name, palette in (("dark", DARK), ("light", LIGHT)):
    (here / f"card-{name}.svg").write_text(build(palette))
    print(f"assets/card-{name}.svg")
