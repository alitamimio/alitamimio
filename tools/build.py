#!/usr/bin/env python3
"""Emit the profile card as one tall SVG, in both themes.

One image rather than several stacked: GitHub puts whitespace between block
images, which would show as seams across a continuous background. And one
image rather than markdown because a README container cannot be styled, so a
background running the whole length has to be part of the content itself.

Every moving part is SMIL. GitHub serves README images through a proxy that
strips scripts, and an SVG rendered as <img> cannot pull a webfont either,
so the type is the system stack and nothing depends on JS.

Live figures come from tools/stats.json, refreshed nightly by the workflow,
and tools/langs.json, refreshed by hand with tools/langs.py. If either file
is missing the card still builds, without that block.

The card was rebuilt on 2026-09-11 from a reviewed preview; docs/PROFILE-PLAN.md
records what was decided and why. Copy is a senior engineer's register:
precise nouns, said once, no em dashes.
"""
import base64, json, pathlib

from logos import LINKEDIN, INTERFACE, SYSTEMS

W = 1000
PAD = 64
CONTENT = W - PAD * 2 - 40          # the width every section respects
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
    # Every neutral leans toward the accent, and the colour field is allowed
    # to show. The first light theme ran the field at 0.30 under a 0.30 white
    # veil, which erased it, and every neutral was a plain grey.
    ground="#f2f7f9", ink="#10161a", muted="#4d5c63", faint="#6d7e86",
    line="#b7ccd5", inset="#e4eff3", brand="#027c93", sweep="#00b7d9",
    live="#12866a", track="#cfe0e7",
    blobs=[("#00b7d9", .85), ("#039bb9", .6), ("#64d6f2", .95)],
    field=0.55, veil=0.10,
)

# AI stays first, because it is the title. UI/UX and FRONTEND follow because
# they are where the work is strongest; FULL STACK, the broadest claim, goes
# last. Each line names what the work actually is, from the repositories.
ROLES = [
    ("AI",         "Retrieval-grounded agents over enterprise document sets, served "
                   "through a streaming gateway"),
    ("UI/UX",      "Design systems, accessible component libraries, and every "
                   "state an interface can be in"),
    ("FRONTEND",   "Next.js architecture: routing, data fetching, command palettes, "
                   "responsive layouts"),
    ("FULL STACK", "API design, relational data modelling, caching, and production "
                   "observability"),
]

# The first FEATURED carry their landing page above the text, when one exists
# in assets/shots/<name>.jpg; the rest are text in the same grid. Rased and
# VOC360 may not be shown, so they stay last whatever lands in that folder.
#
# Nothing here sells Arabic or RTL as an achievement. Ali's note, 2026-09-11:
# shipping both languages is the bare minimum, and naming it as a credential
# reads as though it were hard.
WORK = [
    ("KHAYARAK", "Price-comparison platform for the Jordanian market: live shop data, price alerts, and a chat that answers from both.",
     "Next.js 16 · Tailwind v4 · TypeScript · Python gateway"),
    ("FORTILINK", "Fortinet integration console: interactive tool catalog, command palette, and an accessible dialog system.",
     "TypeScript · shadcn/ui · Radix · Framer Motion · Tailwind v4"),
    ("RASED", "Real-time traffic intelligence: live dashboards and model-monitored camera feeds.",
     "Node · Prometheus · PostgreSQL · Docker"),
    ("VOC360", "Fourteen-service platform that ingests public feedback, classifies it, and traces each issue to its root cause.",
     "FastAPI · PostgreSQL + pgvector · Redis · Docker"),
]
FEATURED = 2

# The request path, the platform it runs on, and what the client does with
# every token that comes back. Each row says something the others do not.
PIPE = [("UI", "Next.js"), ("GATEWAY", "FastAPI"), ("RETRIEVAL", "pgvector"), ("MODEL", "Ollama")]
PLATFORM = [("POSTGRESQL", "relational store"), ("REDIS", "cache"),
            ("DOCKER", "containers"), ("PROMETHEUS", "metrics")]
CLIENT = [("STREAM CLIENT", "SSE"), ("APPLICATION STATE", "per token"),
          ("COMPONENTS", "shadcn/ui on Radix"), ("RENDER", "React")]

# The strip at the top runs one exchange on a loop: the question typed, four
# tools lit in turn, the answer arriving, a hold, then every line fading
# together before it starts again. The card demonstrates the work instead of
# describing it. The answer names the architecture and ends on the interface.
ASK = "what do you actually own on a project?"
TRACE = ["ROUTE", "RETRIEVE", "STREAM", "RENDER"]
ANSWER = [
    "The interface, and everything it talks to. The design system and the",
    "screens, the API and the data underneath, and the model in between.",
]
STRIP_H = 150
CYCLE = 14
FADE_AT, FADE_DUR = 11.8, 1.2

MARK_COLOUR = False    # True paints the stack marks in their brand colours

# The links row, which cannot live on the card: GitHub serves that image
# through a proxy as an <img>, so nothing drawn inside it can be clicked. Each
# link is therefore its own small image, wrapped in an <a> out in the README.
LINKS = [
    ("linkedin", "LINKEDIN", "fill", LINKEDIN),
    ("email", "EMAIL", "stroke", "M2.5 5.5h19v13h-19zM2.5 6.5l9.5 7 9.5-7"),
    ("x", "X", "fill", "M18.9 1.2h3.7l-8 9.2 9.5 12.5h-7.4l-5.8-7.6-6.6 7.6H.6l8.6-9.8L0 1.2h7.6l5.2 6.9zm-1.3 19.5h2L6.5 3.2H4.3z"),
    ("build", "HOW IT'S BUILT", "stroke", "M9 7l-5 5 5 5M15 7l5 5-5 5"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def caps_w(s, size, ls=0):
    """Estimated width of a run of tracked uppercase type.

    There is no way to measure a font here, so every box that wraps type
    derives its width from this. 0.74em is calibrated against the STREAMING
    pill; verify.py checks the result.
    """
    return round(len(s) * size * 0.74 + len(s) * ls, 1)


def wrap(s, size, maxw, per=0.55):
    """Break a sentence to fit a column."""
    out, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and len(trial) * size * per > maxw:
            out.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


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


def keyed(frames, cycle, mode="linear"):
    """values/keyTimes for a list of (seconds, value), on the strip's clock."""
    frames = sorted(frames)
    kt = ";".join(str(round(s / cycle, 5)) for s, _ in frames)
    vs = ";".join(str(v) for _, v in frames)
    return (f'values="{vs}" keyTimes="{kt}" dur="{cycle}s" begin="0s" calcMode="{mode}" '
            f'repeatCount="indefinite"')


def type_in(uid, x, y, s, fill, size, start, dur, feather=22):
    """Reveal a line smoothly, left to right, on the strip's shared clock.

    A soft-edged mask slides across the text and each glyph fades in as the
    edge passes: continuous, not stepped. begin=0 with the phase in keyTimes,
    because a per-line begin let each line restart on its own schedule: the
    question was typing its next cycle while the answer still sat there from
    the last. At FADE_AT every line fades together.

    The gradient carries a static transform too, so a renderer that has not
    started the animation shows nothing rather than the first two letters.
    """
    w = round(len(s) * size * 0.6 + feather, 1)
    s0, s1 = round(start / CYCLE, 5), round((start + dur) / CYCLE, 5)
    f0, f1 = round(FADE_AT / CYCLE, 5), round((FADE_AT + FADE_DUR) / CYCLE, 5)
    return (
        f'  <linearGradient id="{uid}g" gradientUnits="userSpaceOnUse" x1="{x}" y1="0" '
        f'x2="{x + feather}" y2="0" spreadMethod="pad" gradientTransform="translate({-feather} 0)">'
        f'<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
        f'<animateTransform attributeName="gradientTransform" type="translate" '
        f'values="{-feather} 0;{-feather} 0;{w} 0;{w} 0" keyTimes="0;{s0};{s1};1" dur="{CYCLE}s" '
        f'begin="0s" calcMode="linear" repeatCount="indefinite"/></linearGradient>\n'
        f'  <mask id="{uid}m" maskUnits="userSpaceOnUse" x="{x - 4}" y="{y - size}" '
        f'width="{w + 8}" height="{size * 1.7}">'
        f'<rect x="{x - 4}" y="{y - size}" width="{w + 8}" height="{size * 1.7}" fill="url(#{uid}g)"/></mask>\n'
        f'  <text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fill}" '
        f'mask="url(#{uid}m)"><animate attributeName="opacity" values="1;1;0;0" '
        f'keyTimes="0;{f0};{f1};1" dur="{CYCLE}s" begin="0s" repeatCount="indefinite"/>'
        f'{esc(s)}</text>'
    )


def button(c, label, kind, d):
    """One link, as its own small image in the card's own materials."""
    h, m = 44, 20
    w = round(20 + m + 12 + caps_w(label, 12, 1.6) + 20)
    mark = (f'<path d="{d}" fill="{c["brand"]}"/>' if kind == "fill" else
            f'<path d="{d}" fill="none" stroke="{c["brand"]}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" font-family="{FONT}">\n'
            f'  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
            f'fill="{c["inset"]}" stroke="{c["line"]}"/>\n'
            f'  <svg x="20" y="{(h - m) / 2}" width="{m}" height="{m}" '
            f'viewBox="0 0 24 24">{mark}</svg>\n'
            f'{txt(20 + m + 12, h / 2 + 4.5, label, c["ink"], 12, 600, 1.6)}\n'
            f'</svg>\n')


def marks_row(o, y, group, c):
    """One run of brand marks, each named beneath it, arriving left to right
    once on load. The cell width is derived from the count, so a new mark
    re-spaces the row instead of pushing it past the margin."""
    tile, mark, lab = 44, 24, 8.5
    cell = CONTENT / len(group)
    row = 1.6
    for i, (label, brand_hex, d) in enumerate(group):
        mid = PAD + cell * i + cell / 2
        tx = round(mid - tile / 2, 1)
        # The base opacity is the FINAL state and the animation runs from t=0
        # with the stagger in keyTimes, so a renderer without SMIL still draws
        # the row and one with it never shows a snap.
        at = round((0.2 + i * 0.055) / row, 4)
        fade = (f'<animate attributeName="opacity" values="0;0;1;1" '
                f'keyTimes="0;{at};{round(at + 0.28 / row, 4)};1" dur="{row}s" begin="0s" '
                f'fill="freeze" calcMode="spline" '
                f'keySplines="0 0 1 1;0.16 1 0.3 1;0 0 1 1"/>')
        o.append(f'  <g opacity="1"><rect x="{tx}" y="{y}" width="{tile}" height="{tile}" '
                 f'rx="11" fill="{c["inset"]}" stroke="{c["line"]}"/>'
                 f'<svg x="{tx + (tile - mark) / 2}" y="{y + (tile - mark) / 2}" '
                 f'width="{mark}" height="{mark}" viewBox="0 0 24 24">'
                 f'<path d="{d}" fill="{brand_hex if MARK_COLOUR else c["ink"]}" '
                 f'fill-opacity="{1 if MARK_COLOUR else 0.82}"/></svg>{fade}</g>')
        o.append(f'  <g opacity="1">'
                 f'{txt(round(mid, 1), y + tile + 16, label.upper(), c["faint"], lab, 600, anchor="middle")}'
                 f'{fade}</g>')
    return y + tile + 30


def shot(o, x, y, w, h, path, c, uid):
    """A project image, embedded. The proxy blocks external references from
    an SVG served as <img>, so the bytes travel inside the card."""
    mime = "image/jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
    data = base64.b64encode(path.read_bytes()).decode()
    o.append(f'  <clipPath id="{uid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9"/></clipPath>')
    o.append(f'  <g><image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" '
             f'clip-path="url(#{uid})" href="data:{mime};base64,{data}"/>'
             f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="none" stroke="{c["line"]}"/></g>')


def strip(o, c):
    """The exchange at the top. Every animation shares one clock."""
    px, py, pw = PAD, 36, W - PAD * 2
    qy, cq, ay = py + 40, 13.5, py + 110
    cw = cq * 0.6

    o.append(f'  <rect x="{px}" y="{py}" width="{pw}" height="{STRIP_H}" rx="12" '
             f'fill="{c["inset"]}" stroke="{c["line"]}"/>')
    o.append(f'  <path d="M{px+22} {qy-9} l6 5 l-6 5" stroke="{c["brand"]}" stroke-width="1.8" '
             f'fill="none" stroke-linecap="round"/>')

    o.append(type_in("ask", px + 42, qy, ASK, c["muted"], cq, 0.6, 1.9))
    o.append(type_in("a1", px + 22, ay, ANSWER[0], c["ink"], cq, 4.4, 2.6))
    o.append(type_in("a2", px + 22, ay + 22, ANSWER[1], c["ink"], cq, 7.0, 2.4))

    # The caret glides with the question, blinks while the prompt waits, and
    # goes dark while the answer streams. A path rather than a rect: verify.py
    # reads a lone rect beside text as a chip whose type has escaped its box.
    full = round(len(ASK) * cw, 1)
    kx = [(0.0, "0 0"), (0.6, "0 0"), (2.5, f"{full} 0"), (CYCLE, f"{full} 0")]
    ko, t, on = [], 0.0, 1
    while t < 4.4 - 0.01:
        ko.append((round(t, 2), on)); on ^= 1; t += 0.35
    ko += [(4.4, 0), (CYCLE, 0)]
    o.append(f'  <path d="M{px+44} {qy-11} h7 v14 h-7 z" fill="{c["brand"]}" opacity="0">'
             f'<animateTransform attributeName="transform" type="translate" {keyed(kx, CYCLE)}/>'
             f'<animate attributeName="opacity" {keyed(ko, CYCLE, "discrete")}/></path>')

    # The tool trace: each pill lights in turn, decays, and settles when the
    # answer is done.
    tx = px + 22
    for i, label in enumerate(TRACE):
        tw = caps_w(label, 10, 1.4) + 24
        at = 2.9 + 0.5 * i
        kf = [(0.0, 0.18), (at - 0.2, 0.18), (at, 1.0), (at + 0.8, 0.5), (9.4, 0.5), (10.4, 0.18), (CYCLE, 0.18)]
        o.append(f'  <g><rect x="{tx}" y="{py+60}" width="{tw}" height="22" rx="6" fill="none" '
                 f'stroke="{c["brand"]}" stroke-width="1.2" stroke-opacity="0.18">'
                 f'<animate attributeName="stroke-opacity" {keyed(kf, CYCLE)}/></rect>'
                 f'<text x="{tx + tw/2}" y="{py+75}" text-anchor="middle" font-size="10" '
                 f'font-weight="600" letter-spacing="1.4" fill="{c["faint"]}">{label}</text></g>')
        if i < len(TRACE) - 1:
            o.append(f'  <path d="M{tx+tw+9} {py+67} l5 4 l-5 4" stroke="{c["faint"]}" '
                     f'stroke-width="1.4" fill="none"/>')
        tx += tw + 26

    # The status pill, lit only while tokens are arriving.
    sw = caps_w("STREAMING", 10, 1.4) + 48
    sx = px + pw - 22 - sw
    kd = [(0.0, 0.15), (4.2, 0.15), (5.2, 1.0), (6.6, 0.4), (8.0, 1.0), (9.5, 0.15), (CYCLE, 0.15)]
    o.append(f'  <g><rect x="{sx}" y="{py+26}" width="{sw}" height="22" rx="11" fill="none" '
             f'stroke="{c["line"]}"/>'
             f'<circle cx="{sx+18}" cy="{py+37}" r="3.5" fill="{c["brand"]}">'
             f'<animate attributeName="opacity" {keyed(kd, CYCLE)}/>'
             f'</circle><text x="{sx+30}" y="{py+41}" font-size="10" font-weight="600" '
             f'letter-spacing="1.4" fill="{c["faint"]}">STREAMING</text></g>')


def chips(o, y, items, c):
    """A row of four labelled chips in the pipeline's own materials."""
    w = (CONTENT - 3 * 22) / 4
    for i, (top, sub) in enumerate(items):
        bx = PAD + i * (w + 22)
        o.append(f'  <g><rect x="{bx}" y="{y}" width="{w}" height="40" rx="9" fill="none" '
                 f'stroke="{c["line"]}"/>'
                 f'<text x="{bx+w/2}" y="{y+17}" text-anchor="middle" font-size="10.5" '
                 f'font-weight="600" letter-spacing="1.4" fill="{c["ink"]}">{top}</text>'
                 f'<text x="{bx+w/2}" y="{y+31}" text-anchor="middle" font-size="10" '
                 f'fill="{c["faint"]}">{esc(sub)}</text></g>')
        if i < 3:
            o.append(f'  <path d="M{bx+w+7} {y+16} l5 4 l-5 4" stroke="{c["faint"]}" '
                     f'stroke-width="1.4" fill="none"/>')
    return y + 40


def build(c, stats, langs, shots):
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
    # Three periods, mutually prime, so the field never visibly loops back.
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
    strip(o, c)

    # ---- identity ---------------------------------------------------------
    y = 36 + STRIP_H + 82
    o.append(f'  <text x="{PAD}" y="{y}" font-size="56" font-weight="700" letter-spacing="7" '
             f'fill="url(#sweep)">ALI TAMIMI</text>')
    # Full width, fading to the right: the wordmark owns the whole line, so
    # the right side reads as composed rather than as a hole.
    o.append(f'  <rect x="{PAD+2}" y="{y+22}" width="{CONTENT}" height="2" rx="1" fill="url(#rule)"/>')
    o.append(txt(PAD + 2, y + 58, "AI Solutions Engineer", c["ink"], 21, 600))
    o.append(txt(PAD + 2, y + 86, "Full-stack engineer specialising in UI/UX and frontend architecture.",
                 c["ink"], 17))
    o.append(txt(PAD + 2, y + 110, "9XAI Fellow · Al Hussein Technical University", c["faint"], 13))

    # ---- what I do --------------------------------------------------------
    y += 156
    o.append(section(y, "WHAT I DO", c))
    y += 40
    for label, detail in ROLES:
        o.append(f'  <path d="M{PAD} {y-5} L{PAD+5} {y} L{PAD} {y+5} L{PAD-5} {y} Z" fill="{c["brand"]}"/>')
        o.append(txt(PAD + 18, y + 4, label, c["ink"], 11.5, 600, 1.6))
        o.append(txt(PAD + 136, y + 4, detail, c["ink"], 14.5))
        y += 34

    # ---- stack ------------------------------------------------------------
    y += 26
    o.append(section(y, "STACK", c))
    y += 34
    o.append(txt(PAD, y, "INTERFACE", c["brand"], 9.5, 700, 1.6))
    y = marks_row(o, y + 20, INTERFACE, c)
    o.append(txt(PAD, y + 14, "SYSTEMS", c["brand"], 9.5, 700, 1.6))
    y = marks_row(o, y + 34, SYSTEMS, c)

    # ---- selected work ----------------------------------------------------
    y += 22
    o.append(section(y, "SELECTED WORK", c))
    y += 36
    # Two columns the whole way down. The first two carry their landing page
    # above the words; the rest sit in the same grid without one, so the
    # section reads as one thing rather than a feature strip and a list.
    # Each row is as tall as its tallest card, so the next row starts level.
    # Every card's type is centred in its column, including the two without
    # an image, so both rows read as the same grid.
    colw = round((CONTENT - 40) / 2)
    imgh = round(colw / 1.6)          # the screenshots' own aspect, uncropped
    for r in range(0, len(WORK), 2):
        top, tallest = y, 0
        for col, (name, what, tech) in enumerate(WORK[r:r + 2]):
            cx = PAD + col * (colw + 40)
            cy = top
            pic = shots.get(name)
            if pic:
                shot(o, cx, cy, colw, imgh, pic, c, f"shot{r}{col}")
                cy += imgh + 18
            mid = round(cx + colw / 2, 1)
            # Centred in the column, under the image rather than flush with
            # its left edge. text-anchor="middle" centres the advance width,
            # and SVG letter-spacing adds a gap after the last glyph as well
            # as between them, so a tracked run lands ls/2 right of centre.
            # Only the name is tracked, so only the name is pulled back.
            o.append(txt(round(mid - 0.7, 1), cy + 12, name, c["brand"], 14, 700, 1.4,
                         anchor="middle"))
            ly = cy + 36
            for line in wrap(what, 14, colw):
                o.append(txt(mid, ly, line, c["ink"], 14, anchor="middle"))
                ly += 19
            o.append(txt(mid, ly + 4, tech, c["faint"], 12, anchor="middle"))
            tallest = max(tallest, ly + 4 - top)
        y = top + tallest + 44
    y += 10

    # ---- architecture -----------------------------------------------------
    o.append(section(y, "ARCHITECTURE", c))
    y += 52
    bw, gap, bh = 182, 40, 52
    cy = y + bh / 2
    xs = [PAD + i * (bw + gap) for i in range(4)]
    for i in range(3):
        o.append(f'  <path d="M{xs[i]+bw} {cy} H{xs[i+1]}" stroke="{c["line"]}" stroke-width="1.5"/>')
        o.append(f'  <path d="M{xs[i+1]-9} {cy-4} l5 4 l-5 4" stroke="{c["faint"]}" '
                 f'stroke-width="1.4" fill="none"/>')
    o.append(txt(PAD, y - 12, "the request", c["faint"], 11))
    # The request, as a beam with a tail. Drawn BEFORE the nodes, so their
    # opaque fill hides it: it shows in the gaps and passes behind each box.
    o.append(f'  <g><rect x="-30" y="-2" width="30" height="4" rx="2" fill="url(#beam)"/>'
             f'<circle r="4.5" fill="{c["sweep"]}"/>'
             f'<animateMotion dur="6s" repeatCount="indefinite" keyPoints="0;0;1;1" '
             f'keyTimes="0;0.06;0.62;1" calcMode="linear" '
             f'path="M{xs[0]+bw/2} {cy} H{xs[3]+bw/2}"/>'
             f'<animate attributeName="opacity" values="0;1;1;0;0" '
             f'keyTimes="0;0.07;0.6;0.64;1" dur="6s" repeatCount="indefinite"/></g>')
    for i, (top, sub) in enumerate(PIPE):
        # Each node brightens as the request reaches it, placed by keyTimes so
        # the glows stay locked to the beam.
        at = 0.06 + i * 0.18
        o.append(f'  <g><rect x="{xs[i]}" y="{y}" width="{bw}" height="{bh}" rx="10" '
                 f'fill="{c["inset"]}" stroke="{c["brand"]}" stroke-width="1.2" stroke-opacity="0.3">'
                 f'<animate attributeName="stroke-opacity" '
                 f'values="0.3;0.3;1;0.3;0.3" keyTimes="0;{round(at-0.05,3)};{at};'
                 f'{round(at+0.09,3)};1" dur="6s" repeatCount="indefinite"/></rect>'
                 f'<text x="{xs[i]+bw/2}" y="{y+21}" text-anchor="middle" font-size="11.5" '
                 f'font-weight="600" letter-spacing="1.6" fill="{c["ink"]}">{top}</text>'
                 f'<text x="{xs[i]+bw/2}" y="{y+39}" text-anchor="middle" font-size="11" '
                 f'fill="{c["faint"]}">{esc(sub)}</text></g>')
    # The response runs its own lane under the row, dashed, as separate tokens.
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
    o.append(txt((xs[0] + xs[3] + bw) / 2, ret + 17, "response tokens streamed back over SSE",
                 c["faint"], 11.5, anchor="middle"))
    y = ret + 50

    # Still rows: a second moving thing here competes with the beam.
    o.append(txt(PAD, y, "PLATFORM", c["brand"], 9.5, 700, 1.6))
    o.append(txt(PAD + 92, y, "the services every request runs on", c["faint"], 11))
    y = chips(o, y + 14, PLATFORM, c) + 30
    o.append(txt(PAD, y, "INTERFACE LAYER", c["brand"], 9.5, 700, 1.6))
    o.append(txt(PAD + 136, y, "what the client does with each token as it arrives", c["faint"], 11))
    y = chips(o, y + 14, CLIENT, c) + 46

    # ---- this year --------------------------------------------------------
    if stats:
        o.append(section(y, "THIS YEAR", c))
        y += 44
        figures = [(f'{stats["total"]:,}', "contributions"),
                   (str(stats.get("best_streak", stats["streak"])), "longest daily streak"),
                   (str(stats["active_days"]), "active days")]
        for i, (big, small) in enumerate(figures):
            x = PAD + i * 230
            o.append(txt(x, y, big, c["ink"], 27, 700))
            o.append(txt(x + 13 + 17 * len(big), y, small, c["muted"], 14))
        y += 34

        # The language bar. TypeScript is the largest share of everything
        # written, which is the frontend claim made as a fact rather than a
        # sentence. Drawn once, from the left; the base width is the final
        # one, so a renderer without SMIL still shows the whole bar.
        if langs:
            by = langs["bytes"]
            total = sum(by.values())
            top = sorted(by.items(), key=lambda kv: -kv[1])[:5]
            shown = sum(v for _, v in top)
            segs = top + ([("Other", total - shown)] if total - shown > 0 else [])
            tone = [c["sweep"], c["brand"], c["muted"], c["line"], c["line"], c["line"]]
            o.append(f'  <clipPath id="langbar"><rect x="{PAD}" y="{y}" width="{CONTENT}" height="10">'
                     f'<animate attributeName="width" values="0;{CONTENT}" dur="1.1s" begin="0s" '
                     f'fill="freeze" calcMode="spline" keySplines="0.16 1 0.3 1"/></rect></clipPath>')
            o.append('  <g clip-path="url(#langbar)">')
            bx = PAD
            for i, (name, v) in enumerate(segs):
                seg = CONTENT * v / total
                o.append(f'  <rect x="{round(bx,1)}" y="{y}" width="{round(max(seg-2,1),1)}" '
                         f'height="10" rx="5" fill="{tone[min(i,5)]}" '
                         f'opacity="{1 if i < 2 else 0.55}"/>')
                bx += seg
            o.append('  </g>')
            lx = PAD
            for i, (name, v) in enumerate(segs[:4]):
                pct = 100 * v / total
                o.append(f'  <circle cx="{lx+4}" cy="{y+28}" r="4" fill="{tone[min(i,5)]}" '
                         f'opacity="{1 if i < 2 else 0.55}"/>')
                o.append(txt(lx + 14, y + 32, f"{name} {pct:.0f}%",
                             c["ink"] if i < 2 else c["faint"], 12, 600 if i < 2 else None))
                lx += 26 + len(f"{name} {pct:.0f}%") * 7.1
            y += 50

    height = y + 26
    o.append('</svg>')

    return ("\n".join(o)
            .replace("{H}", str(height))
            .replace("{HB}", str(height - 1))
            .replace("{MID}", str(round(height * 0.45)))
            .replace("{LOW}", str(round(height * 0.88))) + "\n")


def main():
    root = pathlib.Path(__file__).resolve().parent
    stats_file, langs_file = root / "stats.json", root / "langs.json"
    stats = json.loads(stats_file.read_text()) if stats_file.exists() else None
    langs = json.loads(langs_file.read_text()) if langs_file.exists() else None
    assets = root.parent / "assets"
    assets.mkdir(exist_ok=True)
    # Project images, when Ali has dropped them in. Nothing placeholder is
    # drawn in their absence: the row simply renders as text.
    shots = {}
    for name, _, _ in WORK[:FEATURED]:
        for ext in (".png", ".jpg", ".jpeg"):
            p = assets / "shots" / f"{name.lower()}{ext}"
            if p.exists():
                shots[name] = p
                break

    for name, palette in (("dark", DARK), ("light", LIGHT)):
        out = assets / f"card-{name}.svg"
        svg = build(palette, stats, langs, shots)
        out.write_text(svg)
        # Past roughly 35 indefinitely-repeating animations a headless renderer
        # stops advancing the clock and the card screenshots frozen. Counting
        # it here keeps that ceiling visible.
        loops = svg.count('repeatCount="indefinite"')
        flag = "  <-- over the headless ceiling" if loops > 30 else ""
        print(f"assets/card-{name}.svg  ({out.stat().st_size:,} bytes, {loops} looping"
              f"{', ' + str(len(shots)) + ' images' if shots else ''}){flag}")

        for slug, label, kind, d in LINKS:
            btn = assets / f"link-{slug}-{name}.svg"
            btn.write_text(button(palette, label, kind, d))
            print(f"  {btn.name}  ({btn.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
