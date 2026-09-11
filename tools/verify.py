#!/usr/bin/env python3
"""The card's audit gate: prove it is sound, then shoot it mid-motion.

Five checks and a screenshot:

  1. Both themes parse as XML, and so does every link button.
  2. The number of indefinitely-repeating animations stays under the ceiling a
     headless renderer can cope with (see build.py).
  3. No <text> runs past the card's right edge — the regression that a longer
     sentence in build.py's copy causes every time.
  4. No <text> escapes the box drawn around it. Ali caught the STREAMING pill
     doing exactly that, five pixels of it, so the check exists now.
  5. The layout hash matches tools/layout.sha256 (see tools/snapshot.py), so a
     refactor cannot move a section unseen.

Then it shoots both themes with every `begin` shifted negative. A headless
screenshot driven by --virtual-time-budget stops advancing the clock on a
document this animated, so the card comes out frozen on its first frame and
looks broken. Shifting every begin back by the moment we want to see lands the
load frame on an already-running animation instead, which is the only way to
verify the motion without watching it in a real browser.

Usage:  python3 tools/verify.py [--at 6.0] [--out DIR]
"""
import argparse, os, pathlib, re, shutil, subprocess, sys, xml.etree.ElementTree as ET

W = 1000
CEILING = 35
MARGIN = 16


def chrome():
    """The browser that shoots the card.

    Was a hardcoded macOS path, which meant the gate could only run on Ali's
    machine and the nightly job rebuilt and pushed the card with no check at
    all. The Actions runner has google-chrome on PATH; CHROME overrides.
    """
    for cand in (os.environ.get("CHROME"),
                 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                 shutil.which("google-chrome"), shutil.which("google-chrome-stable"),
                 shutil.which("chromium-browser"), shutil.which("chromium")):
        if cand and pathlib.Path(cand).exists():
            return cand
    sys.exit("no Chrome or Chromium found; set CHROME=/path/to/binary")


CHROME = chrome()
NS = "{http://www.w3.org/2000/svg}"
ANIM = re.compile(r'<(animate|animateTransform|animateMotion)\b[^>]*/>')
BEGIN = re.compile(r'begin="(-?[\d.]+)s"')
TRANSLATE = re.compile(r"translate\(\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*\)")

# Rough advance width per em: enough to catch a sentence running off the card,
# not enough to be trusted for layout.
ADVANCE = {"mono": 0.60, "sans": 0.55, "caps": 0.74}


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


def extent(t):
    """A text run as (string, left, right) in user units, or None with no x.

    Uppercase runs get a wider per-em figure. Tracked caps are the thing that
    actually overflows, and averaging them in with lowercase prose is how the
    STREAMING pill came out five pixels too narrow.
    """
    s = "".join(t.itertext())
    if not s or t.get("x") is None:
        return None
    size = float(t.get("font-size", 16))
    if "mono" in (t.get("font-family") or ""):
        per = ADVANCE["mono"]
    else:
        per = ADVANCE["caps"] if s == s.upper() else ADVANCE["sans"]
    wide = len(s) * size * per + len(s) * float(t.get("letter-spacing", 0))
    x, anchor = float(t.get("x")), t.get("text-anchor")
    left = x if anchor is None else (x - wide / 2 if anchor == "middle" else x - wide)
    return s, left, left + wide


def walk(el, dx=0.0):
    """Every element, with the horizontal offset of its translated ancestors.

    Without this the gate reads raw x attributes, so anything inside a
    translated group looks like it sits at zero — which is precisely where
    AMMAN, JO lives, the label that was hanging 37px past the margin while
    this check reported nothing.
    """
    m = TRANSLATE.search(el.get("transform") or "")
    if m:
        dx += float(m.group(1))
    yield el, dx
    for kid in el:
        yield from walk(kid, dx)


def overflow(path):
    """Every text run's right edge, worst first."""
    worst = []
    for el, dx in walk(ET.parse(path).getroot()):
        if el.tag == NS + "text":
            e = extent(el)
            if e:
                worst.append((round(e[2] + dx), e[0][:46]))
    return sorted(worst, reverse=True)


def escapes(path):
    """Type that runs outside the box drawn around it.

    Any group holding exactly one rect and some text is a chip: the status
    pill, a tool in the trace, a pipeline node, a link button. The rect is the
    box and the text has to sit inside it with a little air. This is the check
    that would have caught the STREAMING pill before it shipped.
    """
    out = []
    root_el = ET.parse(path).getroot()
    # The root counts as a container too: a link button is a rect, a mark and
    # a label sitting directly in its own <svg>, with no group around them.
    for g, dx in walk(root_el):
        if g is not root_el and g.tag != NS + "g":
            continue
        rects, texts = g.findall(NS + "rect"), g.findall(NS + "text")
        if len(rects) != 1 or not texts or rects[0].get("width") is None:
            continue
        bx = float(rects[0].get("x", 0)) + dx
        bw = float(rects[0].get("width"))
        for t in texts:
            e = extent(t)
            if not e:
                continue
            left, right = e[1] + dx, e[2] + dx
            if left < bx + 3 or right > bx + bw - 3:
                out.append(f"{e[0]!r} spans {round(left)}..{round(right)} in a box "
                           f"of {round(bx)}..{round(bx + bw)}")
    return out


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

    for esc in escapes(svg_path):
        bad.append(f"{theme}: {esc}")

    # The link buttons are cards too, small ones, and their labels set their
    # width — so they get the same containment check and the same parse.
    for btn in sorted((root / "assets").glob(f"link-*-{theme}.svg")):
        try:
            ET.parse(btn)
        except ET.ParseError as e:
            bad.append(f"{btn.name}: not well-formed — {e}")
            continue
        for esc in escapes(btn):
            bad.append(f"{btn.name}: {esc}")

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

# 5. The layout has not moved. tools/snapshot.py builds the card without its
#    live figures and compares the hash to the pinned one; a refactor that
#    shifts a section passes every check above and fails this one.
snap = subprocess.run([sys.executable, str(root / "tools" / "snapshot.py")],
                      capture_output=True, text=True)
print(snap.stdout.strip() or snap.stderr.strip())
if snap.returncode:
    bad.append(snap.stderr.strip() or snap.stdout.strip())

if bad:
    print("\nFAIL")
    print("\n".join(f"  {b}" for b in bad))
    sys.exit(1)
print("\nOK")
