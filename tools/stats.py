#!/usr/bin/env python3
"""Fetch the contribution figures the card shows, and write tools/stats.json.

Source is the public contributions calendar, the same one rendered on the
profile page, rather than the GraphQL API. Three reasons:

  1. No secret. The GraphQL route needs `viewer`, which means a personal
     access token, because the Actions GITHUB_TOKEN is not the user. Worse,
     it would not fail loudly: it would quietly return the bot's own empty
     contribution history.
  2. It agrees with the graph. The card sits inches from the contribution
     graph on the profile, and the two disagreeing by 13 is worse than
     either being off. Whatever the calendar shows is what a visitor sees.
  3. Private work is included, because Ali has "include private
     contributions on my profile" switched on. Without that setting this
     account reads as empty: 607 of his 620 contributions are private.

Aggregates only. Repository names are deliberately not collected, since
printing a private repo name on a public profile would leak it.

If anything here fails the file is left untouched and the card keeps
yesterday's numbers.
"""
import json, pathlib, re, ssl, sys, urllib.request

try:
    import certifi
    TLS = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Actions runners carry a system CA bundle; a python.org build on macOS
    # does not, which is why certifi is preferred when it is present.
    TLS = ssl.create_default_context()

USER = "alitamimio"
URL = f"https://github.com/users/{USER}/contributions"

req = urllib.request.Request(URL, headers={
    "User-Agent": "alitamimio-profile-card",
    "Accept": "text/html",
    "X-Requested-With": "XMLHttpRequest",
})
with urllib.request.urlopen(req, timeout=30, context=TLS) as r:
    html = r.read().decode("utf-8", "replace")

# Each day is a <td> carrying its date and id; the exact count lives in a
# sibling <tool-tip> that points back at that id. data-level is only a 0-4
# bucket, so the tooltip is the one place the real number appears.
cells = {cid: date for date, cid in re.findall(
    r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="(contribution-day-component-[\d-]+)"', html)}
tips = dict(re.findall(
    r'for="(contribution-day-component-[\d-]+)"[^>]*>\s*(No|[\d,]+) contributions? on', html))

if not cells:
    sys.exit("could not parse the contributions calendar; markup may have changed")
if not tips:
    # The day cells parsed but not one count did. Without this the card would
    # rebuild with every figure at zero and look, for all the world, correct.
    sys.exit("found the calendar but not a single count; the tooltip markup may have changed")

days = sorted((date, 0 if tips.get(cid, "No") == "No" else int(tips[cid].replace(",", "")))
              for cid, date in cells.items())

# The streak runs back from the most recent day with activity, so a build
# that happens before the day's first commit does not report it as broken.
streak = 0
for _, n in reversed(days):
    if n > 0:
        streak += 1
    elif streak:
        break

# The card shows the longest streak of the year rather than the current one.
# A current streak on a public card only ever has bad news to deliver: the
# first week off, it reads "1 day streak". The longest only goes up.
best = run = 0
for _, n in days:
    run = run + 1 if n > 0 else 0
    best = max(best, run)

stats = {
    "total": sum(n for _, n in days),
    "streak": streak,
    "best_streak": best,
    "active_days": sum(1 for _, n in days if n > 0),
    "recent": [n for _, n in days[-21:]],
    "through": days[-1][0],
}

if stats["total"] == 0:
    sys.exit("parsed a year with zero contributions, which is not this account; refusing to write it")

out = pathlib.Path(__file__).resolve().parent / "stats.json"
out.write_text(json.dumps(stats, indent=2) + "\n")
print(json.dumps(stats))
