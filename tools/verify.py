#!/usr/bin/env python3
"""The card's audit gate: prove it is sound, then shoot it mid-motion.

Three checks and a screenshot:

  1. Both themes parse as XML.
  2. The number of indefinitely-repeating animations stays under the ceiling a
     headless renderer can cope with (see build.py).
  3. No <text> runs past the card's right edge — the regression that a longer
     sentence in build.py's copy causes every time.

Then it shoots both themes with every `begin` shifted negative. A headless
screenshot driven by --virtual-time-budget stops advancing the clock on a
document this animated, so the card comes out frozen on its first frame and
looks broken. Shifting every begin back by the moment we want to see lands the
load frame on an already-running animation instead, which is the only way to
verify the motion without watching it in a real browser.

Usage:  python3 tools/verify.py [--at 6.0] [--out DIR]
"""
import argparse, pathlib, re, subprocess, sys, xml.etree.ElementTree as ET

W = 1000
CEILING = 35
MARGIN = 16
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
NS = "{http://www.w3.org/2000/svg}"
ANIM = re.compile(r'<(animate|animateTransform|animateMotion)\b[^>]*/>')
BEGIN = re.compile(r'begin="(-?[\d.]+)s"')

# Rough advance width per em: enough to catch a sentence running off the card,
# not enough to be trusted for layout.
ADVANCE = {"mono": 0.60, "sans": 0.55}


def shift(svg, at):
    """Rewrite every begin so the document's load frame is the frame at `at`.

    An animation's local time is (t - begin), so a begin of (begin - at) puts
    it at exactly `at` when the page loads. Animations with no begin default
    to zero and get one.
    """
    def one(m):
        tag = m.group(0)
        if BEGIN.search(tag):
            return BEGIN.sub(lambda b: f'begin="{round(float(b.group(1)) - at, 3)}s"', tag)
        return tag[:-2] + f' begin="-{at}s"/>'
    return ANIM.sub(one, svg)


def overflow(path):
    """Every text run's right edge, worst first."""
    root = ET.parse(path).getroot()
    worst = []
    for t in root.iter(NS + "text"):
        s = "".join(t.itertext())
        if not s or t.get("x") is None:
            continue
        size = float(t.get("font-size", 16))
        fam = "mono" if "mono" in (t.get("font-family") or "") else "sans"
        wide = len(s) * size * ADVANCE[fam] + len(s) * float(t.get("letter-spacing", 0))
        anchor = t.get("text-anchor")
        x = float(t.get("x"))
        right = x + wide if anchor is None else (x + wide / 2 if anchor == "middle" else x)
        worst.append((round(right), s[:46]))
    return sorted(worst, reverse=True)


ap = argparse.ArgumentParser()
ap.add_argument("--at", type=float, default=6.0, help="the second of the loop to shoot")
ap.add_argument("--out", default="/tmp", help="where the PNGs go")
a = ap.parse_args()

root = pathlib.Path(__file__).resolve().parent.parent
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)
bad = []

for theme in ("dark", "light"):
    svg_path = root / "assets" / f"card-{theme}.svg"
    svg = svg_path.read_text()

    try:
        height = ET.fromstring(svg).get("height")
    except ET.ParseError as e:
        bad.append(f"{theme}: not well-formed — {e}")
        continue

    loops = svg.count('repeatCount="indefinite"')
    if loops > CEILING:
        bad.append(f"{theme}: {loops} looping animations, ceiling is {CEILING}")

    over = [w for w in overflow(svg_path) if w[0] > W - MARGIN]
    for right, s in over:
        bad.append(f"{theme}: text reaches {right}px (limit {W - MARGIN}) — {s!r}")

    frame = out / f"card-{theme}-at{a.at}s.svg"
    frame.write_text(shift(svg, a.at))
    png = out / f"card-{theme}.png"
    shot = subprocess.run(
        [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-sandbox",
         f"--window-size={W},{height}", "--force-device-scale-factor=2",
         f"--screenshot={png}", frame.as_uri()],
        capture_output=True, text=True)
    ok = png.exists() and png.stat().st_size > 0
    if not ok:
        bad.append(f"{theme}: screenshot failed — {shot.stderr.strip()[:200]}")

    print(f"{theme:5}  {height}px tall  {loops} looping  "
          f"widest text {overflow(svg_path)[0][0]}px  ->  {png if ok else 'no shot'}")

if bad:
    print("\nFAIL")
    print("\n".join(f"  {b}" for b in bad))
    sys.exit(1)
print("\nOK")
