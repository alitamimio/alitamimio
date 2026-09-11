#!/usr/bin/env python3
"""Sum language bytes across every repository Ali owns, and write tools/langs.json.

Run locally, by hand: it goes through the `gh` CLI and so through Ali's own
credentials. The Actions GITHUB_TOKEN can see this repository and nothing
else, and nearly all of the work lives in private ones, so a nightly refresh
would need a personal access token kept as a secret. The figures move slowly
enough that a committed file, refreshed when it matters, is the better trade.
The card prints the as-of date so a reader can see how fresh it is.

Repository names are not written out. Only the totals, and how many repos
they came from.

Usage:  python3 tools/langs.py
"""
import collections, datetime, json, pathlib, subprocess


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


repos = json.loads(gh("repo", "list", "--limit", "200", "--json", "nameWithOwner"))
total = collections.Counter()
for r in repos:
    total.update(json.loads(gh("api", f"repos/{r['nameWithOwner']}/languages")))

out = {
    "as_of": datetime.date.today().isoformat(),
    "repos": len(repos),
    "bytes": dict(total.most_common()),
}
pathlib.Path(__file__).resolve().parent.joinpath("langs.json").write_text(json.dumps(out, indent=2) + "\n")
grand = sum(total.values())
print(f"{len(repos)} repos, {grand:,} bytes, as of {out['as_of']}")
for k, v in total.most_common(5):
    print(f"  {k:12} {100 * v / grand:5.1f}%")
