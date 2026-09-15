---
id: 91
title: The 2026-09-09 mutation spike is evidence that lives nowhere `docs/evidence/` can see
status: done
tier: 3
closed: 2026-09-09
specs: []
prs: []
commits: [91f56c69, f76931df, f9f007c4]
cites: []
related: [87]
---

## Problem

**Tier 3 — real, not urgent.** Nothing fails; the risk is that a number
outlives the record that justified it.

Four mutations the adequacy lens named in pass 1 were applied at their fixture
heads and the suite run: `pr_body.py:391` at `f76931df` (1502 passed),
`batch.py:72` at `91f56c69` (1292 passed), and two at `f9f007c4` (1250 passed
each). All four stayed green, which is what makes them verified-real vacuities
rather than plausible ones, and they are the whole evidential basis for
`docs/superpowers/specs/2026-09-09-mutation-verified-capability-design.md`.

At the time this item was filed, that record existed only in a session ledger
under a scratch directory — a spec arguing from a measurement nobody can
re-read is the shape item 87 is about, one level out. Two of the four had
already been independently reproduced during review (`f76931df` and
`91f56c69`, both to the exact figure); the `f9f007c4` pair had been reproduced
by nobody.

The fix was small: land the four rows, their commands and outputs where any
exist, under `docs/evidence/`, reproducing the two nobody had re-run. Done, in
the "Done" line above — see `docs/evidence/2026-09-09-adequacy-probe-spike.md`
for the full per-row provenance, including which two remain transcribed from
the review reproduction rather than re-run for that file. It was a
**precondition of the plan** that spec leads to, not of the spec itself —
filed here because a precondition recorded only inside the document that
depends on it is a claim, not a record.

## Record

**Done, 2026-09-09** — `docs/evidence/2026-09-09-adequacy-probe-spike.md`. The
`f9f007c4` pair reproduces to the recorded `1250 passed` exactly; the
`f76931df`/`91f56c69` pair is transcribed from the review reproduction, not
re-run, and the file says so.
