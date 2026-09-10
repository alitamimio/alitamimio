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

from logos import STACK

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

# The strip at the top runs one exchange on a loop: the question typed a
# letter at a time, three tools lighting in turn, then the answer arriving in
# tokens. The card demonstrates the work instead of describing it, which is
# also why the two rhythms differ — see reveal().
ASK = "what do you actually build?"
TRACE = ["ROUTE", "RETRIEVE", "STREAM"]
ANSWER = [
    "Agents that stream, end to end: a FastAPI gateway, SSE to the browser, RAG on Postgres —",
    "and the interface that makes all of it legible.",
]
STRIP_H = 150
CYCLE = 14      # one exchange, start to finish, then a long hold before the loop

MARK_COLOUR = False    # True paints the stack marks in their brand colours


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


def reveal(uid, x, y, s, fill, size, begin, dur, cycle, by="char"):
    """Reveal a line by stepping a clip, then hold it for the rest of the cycle.

    Two rhythms, and the difference is the whole point of the strip: by="char"
    is a person at a keyboard, by="word" is a model emitting tokens. People
    type letters; models do not.

    calcMode="discrete" holds each width until the next keyTime, so it steps
    rather than wipes. The schedule lives in keyTimes, which keeps the values
    list to one entry per step — the earlier version padded it out with a few
    hundred copies of the final width just to fill the wait.
    """
    cw = size * 0.6
    if by == "char":
        widths = [round(i * cw, 1) for i in range(len(s) + 1)]
    else:
        widths, run = [0.0], 0
        for word in s.split(" "):
            run = min(run + len(word) + 1, len(s))
            widths.append(round(run * cw, 1))
    n = max(1, len(widths) - 1)
    frac = dur / cycle
    keys = ";".join(str(round(i * frac / n, 5)) for i in range(n + 1)) + ";1"
    vals = ";".join(str(v) for v in widths + [widths[-1]])
    return (
        f'  <clipPath id="{uid}"><rect x="{x}" y="{y - size}" height="{size * 1.7}" width="0">'
        f'<animate attributeName="width" values="{vals}" keyTimes="{keys}" '
        f'dur="{cycle}s" begin="{begin}s" calcMode="discrete" '
        f'repeatCount="indefinite"/></rect></clipPath>\n'
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
    o.append(f'    <linearGradient id="beam" x1="0" y1="0" x2="1" y2="0">'
             f'<stop offset="0" stop-color="{c["sweep"]}" stop-opacity="0"/>'
             f'<stop offset="1" stop-color="{c["sweep"]}" stop-opacity="0.85"/></linearGradient>')
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

    # ---- the answer strip -------------------------------------------------
    # Every element here shares CYCLE and repeats indefinitely, so their
    # relative phases hold forever: each one carries its own begin, and its
    # keyTimes are read from that begin, not from the page load.
    px, py, pw = PAD, 36, W - PAD * 2
    qy, cq, ay = py + 40, 13.5, py + 110
    o.append(f'  <rect x="{px}" y="{py}" width="{pw}" height="{STRIP_H}" rx="12" '
             f'fill="{c["inset"]}" stroke="{c["line"]}"/>')

    # The question: a prompt mark, then somebody typing.
    o.append(f'  <path d="M{px+22} {qy-9} l6 5 l-6 5" stroke="{c["brand"]}" stroke-width="1.8" '
             f'fill="none" stroke-linecap="round"/>')
    o.append(reveal("ask", px + 42, qy, ASK, c["muted"], cq, 0.6, 1.9, CYCLE))
    # The caret rides the text on the same discrete steps, then goes dark at
    # the moment the question is sent rather than blinking through the answer.
    cw = cq * 0.6
    o.append(f'  <rect x="{px+42}" y="{qy-11}" width="7" height="14" fill="{c["brand"]}">'
             f'<animate attributeName="x" calcMode="discrete" '
             f'values="{";".join(str(round(px + 44 + i*cw, 1)) for i in range(len(ASK) + 1))};'
             f'{round(px + 44 + len(ASK)*cw, 1)}" '
             f'keyTimes="{";".join(str(round(i * (1.9/CYCLE) / len(ASK), 5)) for i in range(len(ASK) + 1))};1" '
             f'dur="{CYCLE}s" begin="0.6s" repeatCount="indefinite"/>'
             f'<animate attributeName="opacity" values="1;0;1;0;1;0;0" '
             f'keyTimes="0;0.025;0.05;0.075;0.1;0.136;1" dur="{CYCLE}s" begin="0.6s" '
             f'repeatCount="indefinite"/></rect>')

    # The tool trace: three pills lighting in turn, then dimming under the
    # answer they produced. One animation each, placed by keyTimes, so they
    # cannot drift out of step with the stream.
    tx = px + 22
    for i, label in enumerate(TRACE):
        at = round(0.207 + i * 0.036, 3)
        tw = 22 + round(7.0 * len(label))
        o.append(f'  <g><rect x="{tx}" y="{py+60}" width="{tw}" height="22" rx="6" fill="none" '
                 f'stroke="{c["brand"]}" stroke-width="1.2" stroke-opacity="0.18">'
                 f'<animate attributeName="stroke-opacity" values="0.18;0.18;1;0.5;0.18;0.18" '
                 f'keyTimes="0;{round(at-0.02,3)};{at};{round(at+0.06,3)};0.96;1" '
                 f'dur="{CYCLE}s" repeatCount="indefinite"/></rect>'
                 f'<text x="{tx + tw/2}" y="{py+75}" text-anchor="middle" font-size="10" '
                 f'font-weight="600" letter-spacing="1.4" fill="{c["faint"]}">{label}</text></g>')
        if i < len(TRACE) - 1:
            o.append(f'  <path d="M{tx+tw+9} {py+67} l5 4 l-5 4" stroke="{c["faint"]}" '
                     f'stroke-width="1.4" fill="none"/>')
        tx += tw + 26

    # The status pill, lit only while tokens are actually arriving.
    sw = 103
    sx = px + pw - 22 - sw
    o.append(f'  <g><rect x="{sx}" y="{py+26}" width="{sw}" height="22" rx="11" fill="none" '
             f'stroke="{c["line"]}"/>'
             f'<circle cx="{sx+18}" cy="{py+37}" r="3.5" fill="{c["brand"]}">'
             f'<animate attributeName="opacity" values="0.15;0.15;1;0.4;1;0.15;0.15" '
             f'keyTimes="0;0.3;0.36;0.44;0.52;0.6;1" dur="{CYCLE}s" repeatCount="indefinite"/>'
             f'</circle><text x="{sx+30}" y="{py+41}" font-size="10" font-weight="600" '
             f'letter-spacing="1.4" fill="{c["faint"]}">STREAMING</text></g>')

    # The answer, in tokens rather than characters.
    o.append(reveal("a1", px + 22, ay, ANSWER[0], c["ink"], cq, 4.4, 2.6, CYCLE, by="word"))
    o.append(reveal("a2", px + 22, ay + 22, ANSWER[1], c["ink"], cq, 7.0, 1.4, CYCLE, by="word"))

    # ---- identity ---------------------------------------------------------
    y = py + STRIP_H + 82
    o.append(f'  <text x="{PAD}" y="{y}" font-size="56" font-weight="700" letter-spacing="7" '
             f'fill="url(#sweep)">ALI TAMIMI</text>')
    o.append(f'  <rect x="{PAD+2}" y="{y+22}" width="300" height="2" rx="1" fill="url(#rule)"/>')
    o.append(txt(PAD + 2, y + 60, "AI Solutions Engineer", c["ink"], 21, 600))
    o.append(txt(PAD + 2, y + 88, "Full-stack developer. UI/UX. Frontend.", c["muted"], 15.5))

    o.append(f'  <g transform="translate(872 {y - 56})">'
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

    # ---- stack ------------------------------------------------------------
    # The tech named in WHAT I DO, as marks. Tinted to one ink by default:
    # twelve brands at full saturation is twelve palettes arguing, and two of
    # them (Next.js, Ollama) are black, so they vanish on this ground anyway.
    y += 26
    o.append(section(y, "STACK", c))
    y += 34
    # The row spans exactly as far as the section hairline above it, whatever
    # the count: the gap is derived, so a thirteenth mark re-spaces the row
    # instead of pushing it past the margin.
    tile, mark = 52, 26
    gap = round((W - PAD - 40 - PAD - len(STACK) * tile) / (len(STACK) - 1), 2)
    row = 1.6
    for i, (label, brand_hex, d) in enumerate(STACK):
        tx = PAD + i * (tile + gap)
        # Marks arrive left to right on load, once — fill="freeze" rather than
        # repeatCount="indefinite", so the row costs nothing against the
        # headless animation ceiling.
        #
        # The base opacity is the FINAL state and the animation runs from t=0,
        # with the stagger carried in keyTimes rather than in begin. Both
        # halves of that matter: a begin in the future leaves a window where
        # the base value shows and then snaps away, and a base of 0 means a
        # renderer that never runs SMIL draws nothing at all.
        at = round((0.2 + i * 0.055) / row, 4)
        o.append(f'  <g opacity="1"><rect x="{tx}" y="{y}" width="{tile}" height="{tile}" '
                 f'rx="12" fill="{c["inset"]}" stroke="{c["line"]}"/>'
                 f'<svg x="{tx + (tile - mark) / 2}" y="{y + (tile - mark) / 2}" '
                 f'width="{mark}" height="{mark}" viewBox="0 0 24 24">'
                 f'<path d="{d}" fill="{brand_hex if MARK_COLOUR else c["ink"]}" '
                 f'fill-opacity="{1 if MARK_COLOUR else 0.82}"/></svg>'
                 f'<animate attributeName="opacity" values="0;0;1;1" '
                 f'keyTimes="0;{at};{round(at + 0.28 / row, 4)};1" dur="{row}s" begin="0s" '
                 f'fill="freeze" calcMode="spline" '
                 f'keySplines="0 0 1 1;0.16 1 0.3 1;0 0 1 1"/></g>')
    y += tile + 4

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
        # Each node brightens as the request reaches it. One 6s animation per
        # node with the spike placed by keyTimes, so the glows stay locked to
        # the beam instead of drifting out of phase over time. The spacing
        # tracks the beam's own window, which now ends at 0.62 to leave the
        # rest of the cycle to the response.
        at = 0.06 + i * 0.18
        o.append(f'  <g><rect x="{xs[i]}" y="{y}" width="{bw}" height="{bh}" rx="10" '
                 f'fill="{c["inset"]}" stroke="{c["brand"]}" stroke-width="1.2" stroke-opacity="0.3">'
                 f'<animate attributeName="stroke-opacity" '
                 f'values="0.3;0.3;1;0.3;0.3" keyTimes="0;{round(at-0.05,3)};{at};'
                 f'{round(at+0.09,3)};1" dur="6s" repeatCount="indefinite"/></rect>'
                 f'<text x="{xs[i]+bw/2}" y="{y+22}" text-anchor="middle" font-size="11.5" '
                 f'font-weight="600" letter-spacing="1.6" fill="{c["ink"]}">{top}</text>'
                 f'<text x="{xs[i]+bw/2}" y="{y+40}" text-anchor="middle" font-size="12" '
                 f'fill="{c["faint"]}">{sub}</text></g>')
    # The request, as a beam with a tail rather than a dot: it reads as
    # something travelling in a direction, which a circle does not.
    o.append(f'  <g><rect x="-30" y="-2" width="30" height="4" rx="2" fill="url(#beam)"/>'
             f'<circle r="4.5" fill="{c["sweep"]}"/>'
             f'<animateMotion dur="6s" repeatCount="indefinite" keyPoints="0;0;1;1" '
             f'keyTimes="0;0.06;0.62;1" calcMode="linear" '
             f'path="M{xs[0]+bw/2} {cy} H{xs[3]+bw/2}"/>'
             f'<animate attributeName="opacity" values="0;1;1;0;0" '
             f'keyTimes="0;0.07;0.6;0.64;1" dur="6s" repeatCount="indefinite"/></g>')

    # And the answer coming back, which is the half the old version left out.
    # The response does not retrace the request; it runs its own lane under
    # the row, dashed, and arrives as separate tokens rather than one object.
    ret = round(y + bh + 24)
    lane = (f'M{xs[3]+bw/2} {y+bh} V{ret} H{xs[0]+bw/2} V{y+bh}')
    o.append(f'  <path d="{lane}" stroke="{c["line"]}" stroke-width="1.5" fill="none" '
             f'stroke-dasharray="3 5"/>')
    for i in range(3):
        at, end = round(0.6 + i * 0.05, 3), round(0.88 + i * 0.05, 3)
        o.append(f'  <rect x="-4" y="-1.5" width="8" height="3" rx="1.5" fill="{c["sweep"]}" '
                 f'opacity="0">'
                 f'<animateMotion dur="6s" repeatCount="indefinite" path="{lane}" '
                 f'keyPoints="0;0;1;1" keyTimes="0;{at};{end};1" calcMode="linear"/>'
                 f'<animate attributeName="opacity" values="0;0;0.95;0.95;0;0" '
                 f'keyTimes="0;{at};{round(at+0.02,3)};{round(end-0.02,3)};{end};1" '
                 f'dur="6s" repeatCount="indefinite"/></rect>')
    o.append(txt((xs[0] + xs[3] + bw) / 2, ret + 17, "tokens streaming back over SSE",
                 c["faint"], 11.5, anchor="middle"))
    y += bh + 74   # the caption under the lane needs the same air as a section break

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
    svg = build(palette, stats)
    out.write_text(svg)
    # Past roughly 35 indefinitely-repeating animations a headless renderer
    # driven by --virtual-time-budget stops advancing the clock, and the card
    # screenshots frozen. Counting it here keeps that ceiling visible instead
    # of turning into an afternoon spent hunting a bug that is not there.
    loops = svg.count('repeatCount="indefinite"')
    flag = "  <-- over the headless ceiling" if loops > 30 else ""
    print(f"assets/card-{name}.svg  ({out.stat().st_size:,} bytes, {loops} looping){flag}")
