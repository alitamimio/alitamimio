#!/usr/bin/env python3
"""Emit the profile card as one tall SVG, in both themes.

One image rather than several stacked: GitHub puts whitespace between block
images, which would show as seams across a continuous background. And one
image rather than markdown because a README container cannot be styled, so a
background running the whole length has to be part of the content itself.

Every moving part is SMIL. GitHub serves README images through a proxy that
strips scripts, and an SVG rendered as <img> cannot pull a webfont either,
so the type is the system stack and nothing depends on JS.

Live figures come from tools/stats.json, refreshed nightly by the workflow.
If that file is missing the card still builds, just without the year block.
"""
import json, pathlib

W = 1000
PAD = 64
FONT = "system-ui,-apple-system,'Segoe UI',Roboto,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

DARK = dict(
    ground="#121517", ink="#f1f3f4", muted="#9fa4a7", faint="#707579",
    line="#2a2e31", inset="#1a1e21", brand="#039bb9", sweep="#64d6f2",
    live="#20ac88", track="#22282b",
    blobs=[("#039bb9", .95), ("#027c93", .85), ("#00343f", .9)],
    field=0.72, veil=0.06,
)
LIGHT = dict(
    ground="#f9fafb", ink="#151819", muted="#585f64", faint="#7c848a",
    line="#ced3d9", inset="#eef1f4", brand="#027c93", sweep="#027c93",
    live="#12866a", track="#dfe4e9",
    blobs=[("#64d6f2", .9), ("#00b7d9", .7), ("#a8e7f6", .9)],
    field=0.30, veil=0.30,
)

# Ali's own ordering, 2026-09-10: "im an AI solutions engineer first, full
# stack, UI/UX guru and front end developer". Each role carries its own
# evidence rather than all of them sharing one flat tech list.
ROLES = [
    ("AI",         "LLM agents · streaming gateways · RAG · SSE · Ollama"),
    ("FULL STACK", "FastAPI · Node · PostgreSQL · Redis · Docker · Prometheus"),
    ("UI/UX",      "design systems · design tokens · accessibility · RTL · motion"),
    ("FRONTEND",   "Next.js · React · TypeScript · Tailwind · SVG"),
]

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

PIPE = [("UI", "Next.js"), ("GATEWAY", "FastAPI"), ("MODEL", "Ollama"), ("DATA", "Postgres")]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def txt(x, y, s, fill, size=16, weight=None, ls=None, family=None, anchor=None):
    a = f'x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
    if weight: a += f' font-weight="{weight}"'
    if ls:     a += f' letter-spacing="{ls}"'
    if family: a += f' font-family="{family}"'
    if anchor: a += f' text-anchor="{anchor}"'
    return f'  <text {a}>{esc(s)}</text>'


def section(y, label, c):
    """A quiet caps label with a hairline running out toward the right margin."""
    x2 = PAD + 10.5 * len(label) + 16
    return (txt(PAD, y, label, c["faint"], 11.5, 600, 2) + "\n" +
            f'  <rect x="{x2}" y="{y - 5}" width="{W - PAD - 40 - x2}" height="1" fill="{c["line"]}"/>')


def typed(uid, x, y, s, fill, size, begin, cycle):
    """A line that types itself, then holds for the rest of the cycle.

    calcMode="discrete" steps the clip one character at a time, which reads as
    a typewriter rather than a wipe. The values list is padded with the final
    width so the sentence sits still for most of the loop instead of
    retyping every couple of seconds.
    """
    n = len(s)
    cw = size * 0.6
    type_frac = 0.34
    steps = [round(i * cw, 1) for i in range(n + 1)]
    hold = max(1, int(len(steps) * (1 - type_frac) / type_frac))
    vals = ";".join(str(v) for v in steps + [steps[-1]] * hold)
    return (
        f'  <clipPath id="{uid}"><rect x="{x}" y="{y - size}" height="{size * 1.6}" width="0">'
        f'<animate attributeName="width" values="{vals}" dur="{cycle}s" begin="{begin}s" '
        f'calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>\n'
        f'  <text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fill}" '
        f'clip-path="url(#{uid})">{esc(s)}</text>'
    )


def build(c, stats):
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{{H}}" '
         f'viewBox="0 0 {W} {{H}}" fill="none" font-family="{FONT}">']

    # ---- defs -------------------------------------------------------------
    o.append('  <defs>')
    o.append(f'    <clipPath id="card"><rect width="{W}" height="{{H}}" rx="18"/></clipPath>')
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

    # ---- ground and field -------------------------------------------------
    o.append('  <g clip-path="url(#card)">')
    o.append(f'    <rect width="{W}" height="{{H}}" fill="{c["ground"]}"/>')
    o.append(f'    <g filter="url(#soft)" opacity="{c["field"]}">')
    # Sped up at Ali's call, 2026-09-10. The three periods stay mutually prime
    # so the field never visibly loops back to the same arrangement.
    drift = [("0 0; -70 80; 45 -40; 0 0", "11s"),
             ("0 0; 60 -90; -65 40; 0 0", "13s"),
             ("0 0; 90 -55; -35 -75; 0 0", "17s")]
    spots = [(830, 150, 200), (940, "{MID}", 175), (720, "{LOW}", 160)]
    for (cx, cy, r), (fill, op), (vals, dur) in zip(spots, c["blobs"], drift):
        o.append(f'      <circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" opacity="{op}">'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'values="{vals}" dur="{dur}" repeatCount="indefinite"/></circle>')
    o.append('    </g>')
    o.append(f'    <rect width="{W}" height="{{H}}" fill="{c["ground"]}" opacity="{c["veil"]}"/>')
    o.append('  </g>')
    o.append(f'  <rect x="0.5" y="0.5" width="{W-1}" height="{{HB}}" rx="18" fill="none" stroke="{c["line"]}"/>')

    # ---- terminal strip ---------------------------------------------------
    o.append(f'  <rect x="{PAD}" y="36" width="{W - PAD*2}" height="96" rx="10" '
             f'fill="{c["inset"]}" stroke="{c["line"]}"/>')
    for i, dot in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        o.append(f'  <circle cx="{PAD + 22 + i*16}" cy="60" r="4.5" fill="{dot}" opacity="0.75"/>')
    o.append(typed("t1", PAD + 22, 84, "$ whoami", c["faint"], 13, 0.4, 13))
    o.append(typed("t2", PAD + 22, 108,
                   "ai solutions engineer · full stack · ui/ux · frontend",
                   c["ink"], 13, 1.9, 13))
    o.append(f'  <rect x="{PAD + 22 + 13*0.6*52 + 3}" y="97" width="7" height="14" fill="{c["brand"]}">'
             f'<animate attributeName="opacity" values="0;0;1;0;1;0" dur="13s" '
             f'keyTimes="0;0.15;0.42;0.56;0.70;1" repeatCount="indefinite"/></rect>')

    # ---- identity ---------------------------------------------------------
    y = 214
    o.append(f'  <text x="{PAD}" y="{y}" font-size="56" font-weight="700" letter-spacing="7" '
             f'fill="url(#sweep)">ALI TAMIMI</text>')
    o.append(f'  <rect x="{PAD+2}" y="{y+22}" width="300" height="2" rx="1" fill="url(#rule)"/>')
    o.append(txt(PAD + 2, y + 60, "AI Solutions Engineer", c["ink"], 21, 600))
    o.append(txt(PAD + 2, y + 88, "Full-stack developer. UI/UX. Frontend.", c["muted"], 15.5))

    o.append(f'  <g transform="translate(872 158)">'
             f'<circle cx="0" cy="-4" r="4" fill="{c["live"]}">'
             f'<animate attributeName="opacity" values="1;0.35;1" dur="2.8s" repeatCount="indefinite"/>'
             f'</circle><text x="14" y="0" font-size="11.5" letter-spacing="1.6" font-weight="600" '
             f'fill="{c["muted"]}">AMMAN, JO</text></g>')

    # ---- what I do --------------------------------------------------------
    y += 150
    o.append(section(y, "WHAT I DO", c))
    y += 40
    for label, detail in ROLES:
        o.append(f'  <path d="M{PAD} {y-5} L{PAD+5} {y} L{PAD} {y+5} L{PAD-5} {y} Z" fill="{c["brand"]}"/>')
        o.append(txt(PAD + 18, y + 4, label, c["faint"], 11.5, 600, 1.6))
        o.append(txt(PAD + 136, y + 4, detail, c["ink"], 14.5))
        y += 34

    # ---- work -------------------------------------------------------------
    y += 30
    o.append(section(y, "WORK", c))
    y += 44
    for name, what, tech in WORK:
        o.append(txt(PAD, y, name, c["brand"], 15, 700, 1.4))
        o.append(txt(PAD, y + 24, what, c["ink"], 15.5))
        o.append(txt(PAD, y + 46, tech, c["faint"], 13.5))
        y += 86

    # ---- how it fits ------------------------------------------------------
    y += 6
    o.append(section(y, "HOW IT FITS", c))
    y += 52
    bw, gap, bh = 168, 48, 52
    cy = y + bh / 2
    xs = [PAD + i * (bw + gap) for i in range(4)]
    for i in range(3):
        o.append(f'  <path d="M{xs[i]+bw} {cy} H{xs[i+1]}" stroke="{c["line"]}" stroke-width="1.5"/>')
        o.append(f'  <path d="M{xs[i+1]-9} {cy-4} l5 4 l-5 4" stroke="{c["faint"]}" '
                 f'stroke-width="1.4" fill="none"/>')
    for i, (top, sub) in enumerate(PIPE):
        # Each node brightens as the pulse reaches it. One 6s animation per
        # node with the spike placed by keyTimes, so the glows stay locked to
        # the pulse instead of drifting out of phase over time.
        at = 0.06 + i * 0.28
        o.append(f'  <g><rect x="{xs[i]}" y="{y}" width="{bw}" height="{bh}" rx="10" '
                 f'fill="{c["inset"]}" stroke="{c["brand"]}" stroke-width="1.2" stroke-opacity="0.3">'
                 f'<animate attributeName="stroke-opacity" '
                 f'values="0.3;0.3;1;0.3;0.3" keyTimes="0;{round(at-0.05,3)};{at};'
                 f'{round(at+0.09,3)};1" dur="6s" repeatCount="indefinite"/></rect>'
                 f'<text x="{xs[i]+bw/2}" y="{y+22}" text-anchor="middle" font-size="11.5" '
                 f'font-weight="600" letter-spacing="1.6" fill="{c["ink"]}">{top}</text>'
                 f'<text x="{xs[i]+bw/2}" y="{y+40}" text-anchor="middle" font-size="12" '
                 f'fill="{c["faint"]}">{sub}</text></g>')
    o.append(f'  <circle r="4.5" fill="{c["sweep"]}">'
             f'<animateMotion dur="6s" repeatCount="indefinite" keyPoints="0;0;1;1" '
             f'keyTimes="0;0.06;0.90;1" calcMode="linear" '
             f'path="M{xs[0]+bw/2} {cy} H{xs[3]+bw/2}"/>'
             f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.07;0.89;1" '
             f'dur="6s" repeatCount="indefinite"/></circle>')
    y += bh + 30

    # ---- this year --------------------------------------------------------
    if stats:
        o.append(section(y, "THIS YEAR", c))
        y += 44
        figures = [(f'{stats["total"]:,}', "contributions"),
                   (str(stats["streak"]), "day streak"),
                   (str(stats["active_days"]), "days shipped")]
        for i, (big, small) in enumerate(figures):
            x = PAD + i * 200
            o.append(txt(x, y, big, c["ink"], 27, 700))
            o.append(txt(x + 13 + 17 * len(big), y, small, c["muted"], 14))
        # No public/private split any more: the calendar reports one total and
        # does not break it down, and inventing the split would be worse than
        # losing it. The sentence is true without a number.
        o.append(txt(PAD, y + 26,
                     'Nearly all of it in private and organisation repos, '
                     'which is why this account looks quiet.', c["faint"], 13))

        # Sparkline. Bars grow from a baseline once on load: an SVG rect grows
        # downward, so each bar is drawn upward from its own origin and the
        # group is scaled, which keeps the baseline still.
        y += 62
        rec = stats["recent"]
        peak = max(rec) or 1
        bwid, bgap, hmax = 24, 17, 52
        for i, n in enumerate(rec):
            bx = PAD + i * (bwid + bgap)
            h = max(2, round(hmax * n / peak))
            fill = c["brand"] if n else c["track"]
            o.append(f'  <g transform="translate({bx} {y + hmax})">'
                     f'<rect y="{-h}" width="{bwid}" height="{h}" rx="2.5" fill="{fill}">'
                     f'</rect>'
                     f'<animateTransform attributeName="transform" type="scale" additive="sum" '
                     f'values="1 0;1 1" keyTimes="0;1" dur="0.5s" begin="{round(0.3 + i*0.045, 3)}s" '
                     f'calcMode="spline" keySplines="0.16 1 0.3 1" fill="freeze"/></g>')
        o.append(txt(PAD, y + hmax + 20, f'last {len(rec)} days, through {stats["through"]}',
                     c["faint"], 12))
        y += hmax + 34

    # ---- footer -----------------------------------------------------------
    y += 34
    o.append(txt(PAD, y, "Amman, Jordan", c["faint"], 12.5))
    height = y + 34
    o.append('</svg>')

    return ("\n".join(o)
            .replace("{H}", str(height))
            .replace("{HB}", str(height - 1))
            .replace("{MID}", str(round(height * 0.45)))
            .replace("{LOW}", str(round(height * 0.88))) + "\n")


root = pathlib.Path(__file__).resolve().parent
stats_file = root / "stats.json"
stats = json.loads(stats_file.read_text()) if stats_file.exists() else None
assets = root.parent / "assets"
assets.mkdir(exist_ok=True)
for name, palette in (("dark", DARK), ("light", LIGHT)):
    out = assets / f"card-{name}.svg"
    out.write_text(build(palette, stats))
    print(f"assets/card-{name}.svg  ({out.stat().st_size:,} bytes)")
