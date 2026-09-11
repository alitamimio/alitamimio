# Profile plan

Locked 2026-09-11, from the approved preview (v7 of the card rewrite).

**Positioning.** AI Solutions Engineer is the title. UI/UX and frontend carry
the evidence. Copy is a senior engineer's register: precise nouns, stated once,
no em dashes, no folksy phrasing, nothing bilingual presented as a feat.

**Rhythm.** Working branch `profile/rewrite`. Each phase: build, run
`python3 tools/verify.py` (the fixed audit for this repo: both themes, the link
buttons, the animation ceiling, overflow and containment, a mid-motion
screenshot), check for regressions, push. One sweep across every phase at the
end. One PR to `main`, opened only when Ali says so, merged with a merge
commit, never squashed. Fast-forward the branch after the merge.

---

## The card, as decided

| Block | What ships |
|-------|------------|
| Strip | `what do you build, end to end?` typed letter by letter through a soft-edged mask; `ROUTE → RETRIEVE → STREAM → RENDER`; the answer streams the same way and ends on the interface. Every line on one shared clock. The exchange holds, every line fades together at 11.8s, and it reloads. 14s cycle |
| Identity | `ALI TAMIMI`, a full-width rule fading right, `AI Solutions Engineer`, `Full-stack engineer specialising in UI/UX and frontend architecture.`, `9XAI Fellow · Al Hussein Technical University`. No location pill, no mark |
| WHAT I DO | AI → UI/UX → FRONTEND → FULL STACK, four filled diamonds, every label in ink, copy rewritten from the repos |
| STACK | `INTERFACE`: TypeScript, React, Next.js, Tailwind, shadcn/ui, Radix, Framer Motion, Vite. `SYSTEMS`: Python, FastAPI, Ollama, PostgreSQL, Redis, Docker, Prometheus, Node.js. Both labels in the brand. Figma is out until a repo evidences it |
| SELECTED WORK | Khayarak and FortiLink featured with an image beside the text; Rased and VOC360 as text only (neither may be shown). One line: client and private repositories, walkthroughs on request |
| ARCHITECTURE | The request path `UI → GATEWAY → RETRIEVAL → MODEL` with the beam and the return lane; a `PLATFORM` row (PostgreSQL, Redis, Docker, Prometheus); an `INTERFACE LAYER` row (stream client, application state, components, render), still |
| THIS YEAR | contributions, longest daily streak, active days; the language bar from every repo, drawn in once on load, with its as-of date. No sparkline |
| Footer | None. Contact lives in the links row under the card |
| Light theme | Every neutral leans toward the accent; the colour field shows |
| Links row | LinkedIn, Email, X, How it's built |

Cut along the way, and why: the credentials strip (duplicated the UI/UX row),
the sparkline (duplicated the graph beside it), role lines (unverifiable), the
footer (Ali's call), the Arabic wordmark and the AT monogram (Ali's call), the
travelling dot on the interface layer (looked wrong), scroll-off and the three
alternative terminal endings (Ali's call: v5's fade stays).

---

## Two constraints

**Animation ceiling.** `verify.py` fails above 35 indefinitely repeating
animations; the card ships at 29. The Arabic stream needs roughly three.

**Height.** 1000 × 1924. Every addition from here is paid for by a cut.

---

## Phase 0 — Port

The approved card moves from the preview into the repository.

| Item | Note |
|------|------|
| `tools/build.py` | The preview build, with the preview-only switches removed |
| `tools/logos.py` | Four new marks; Ollama's real hex; the two groups |
| Thumbnails | Optional: `assets/shots/khayarak.png` and `assets/shots/fortilink.png` are embedded when present, and the row renders as text when they are not. Nothing placeholder goes live |
| `tools/stats.py` | Adds the longest streak, from the same public calendar, no secret |
| `tools/langs.py` | Run locally with `gh`; writes `tools/langs.json`, committed. The Actions token cannot read the private repositories where the work lives, and the figures move slowly enough that a hand refresh is the right trade |
| README | Alt text for the new card; the X button; three lines of indexable text |
| Docs | This file |

## Phase 1 — Free wins

| Item | Owner |
|------|-------|
| Bio that names frontend and UI/UX, three drafts in `docs/ACCOUNT-SETTINGS.md` | Ali pastes |
| Sidebar: Company reads the literal string `none`; Website empty; LinkedIn missing from social accounts; Available for hire off | Ali |
| Pin this repository | Ali |
| `verify.py` finds Chrome on Linux; `card.yml` runs the gate before it commits. Until this lands the nightly job pushes an unverified card | Claude |

## Phase 2 — Evidence

| Item | Note |
|------|------|
| Screenshots of Khayarak and FortiLink into `assets/shots/`, rebuild | **Blocked on Ali** |
| Mobile card selected by `<picture media="(max-width: 600px)">` | Verify GitHub honours the width query before committing to it |

## Phase 3 — Arabic stream

Streams the answer in Arabic after the English. It changes the strip Ali just
approved, so it gets a preview and a yes before it lands. ~3 loops.

## Phase 4 — Tooling

| Item |
|------|
| Stale stats visible on the card when `stats.py` fails silently |
| Guard `card.yml` and `snake.yml` against racing |
| Snapshot test on `build.py`, so a refactor cannot move the layout unseen |

## Phase 5 — Sweep and PR

The gate over everything together; then the PR, when Ali says.

## Phase 6 — Portfolio site

Its own plan. Next.js + Tailwind + shadcn on Vercel, the card's design language,
21st.dev for the bento grid and hero, a live RTL toggle, one written case study,
sanitised public case-study repositories for the pins.
