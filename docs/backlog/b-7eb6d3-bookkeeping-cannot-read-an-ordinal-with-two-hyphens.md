---
id: b-7eb6d3
title: "`bookkeeping` cannot read an ordinal with two hyphens, so it drafts `<Nth>`"
status: open
tier: 3
filed: 2026-10-05
specs: [SA-0200]
prs: []
commits: []
cites: []
related: [b-7d3810]
---

## Problem

Found in the spec loop's run 28.

The queue smoke test's docstring opens with "a hundred-and-twentieth time".
`driver.py`'s `_ORDINAL_PHRASE` (`.claude/skills/run-saffron-spec-loop/driver.py:2790`)
allows one hyphen in the ordinal. It cannot match two, so `bookkeeping`
finds no ordinal and drafts `<Nth>`. Every ordinal from a hundred-and-first
on carries two hyphens. The delegate writes each one by hand.

## Done looks like

`bookkeeping` steps "a hundred-and-twentieth time" to "a
hundred-and-twenty-first time". A test pins a two-hyphen ordinal.

## Record

- 2026-10-05: filed from the spec loop's run 28.
