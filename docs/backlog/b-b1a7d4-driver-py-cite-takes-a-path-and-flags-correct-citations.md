---
id: b-b1a7d4
title: '`driver.py cite` takes a path, not an id, and flags correct citations'
status: done
tier: 3
filed: 2026-09-29
closed: 2026-11-08
by_hand: true
specs: [SA-0152, SA-0167]
prs: [956, 1064]
commits: []
cites: []
related: []
---

## Problem

Found in the spec loop's run 22, 2026-09-29. Four chain writers reported it.

`driver.py cite SA-0152` fails with "no such spec". `cmd_cite` reads its
argument as a path (`.claude/skills/run-saffron-spec-loop/driver.py:2287`).

It also flags correct citations. On `SA-0152` it flagged 10 of 37, and on
`SA-0167` 9 of 46. It compares the cited range against other backticked text
beside the anchor.

## Done looks like

`cite` accepts a spec id. It compares the cited range against the cited
symbol alone.

## Record

- 2026-09-29: filed from the spec loop's run 22.
- 2026-10-02: `SA-0167` retired as #638. `driver.py cite` still takes a path, and its quoted-text warnings still flag correct citations (18 on `SA-0167`).
- 2026-10-03: `SA-0152` retired as #650. `cite` is unchanged.
- 2026-11-07: marked by hand in grooming. The work is in the spec loop's driver under
  `.claude/`, and `SA-0279` refuses any spec that touches that path.
- 2026-11-07: groomed. Its second half landed under b-2da959. `cite` now calls core's checker in `saffron/spec_citations.py`, which judges a range by the construct its clause names (`SA-0314`, #956). Left: `cite` still takes a path and not a spec id. Its count of false warnings predates that checker and needs a new measurement.
- 2026-11-08: done by hand. `cite` takes a spec id, queued or retired. Each spec read at its last edit draws no warning: `SA-0152` checks 40 citations at `a003daed` and `SA-0167` checks 64 at `71d824c9`.
