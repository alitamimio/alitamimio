#!/usr/bin/env python3
"""Pin the card's layout, so a refactor cannot move it unseen.

verify.py proves the card is well-formed and inside its margins. It does not
notice when a section quietly shifts twelve pixels, or a label changes
weight, because both are still well-formed and still inside the margins.
This does: it builds the dark card with no live figures, so the result is
identical from one night to the next, and compares its hash to the one
recorded in tools/layout.sha256.

A mismatch means the layout changed. If that was the point, record it:

    python3 tools/snapshot.py --update

If it was not, something moved that should not have.
"""
import hashlib, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build  # noqa: E402

PIN = pathlib.Path(__file__).resolve().parent / "layout.sha256"


def digest():
    svg = build.build(build.DARK, None, None, {})
    return hashlib.sha256(svg.encode()).hexdigest()


if __name__ == "__main__":
    now = digest()
    if "--update" in sys.argv:
        PIN.write_text(now + "\n")
        print(f"layout pinned  {now[:12]}")
        sys.exit(0)
    if not PIN.exists():
        sys.exit("no layout pin yet; run  python3 tools/snapshot.py --update")
    was = PIN.read_text().strip()
    if was != now:
        sys.exit(f"layout changed: pinned {was[:12]}, built {now[:12]}. "
                 "Deliberate? python3 tools/snapshot.py --update")
    print(f"layout unchanged  {now[:12]}")
