---
id: b-b1a7d4
title: '`driver.py cite` takes a path, not an id, and flags correct citations'
status: partial
tier: 3
filed: 2026-09-29
specs: [SA-0152, SA-0167]
prs: []
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
