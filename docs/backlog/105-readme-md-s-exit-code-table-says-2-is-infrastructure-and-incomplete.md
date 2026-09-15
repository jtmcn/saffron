---
id: 105
title: '`README.md`''s exit-code table says `2` is infrastructure, and `INCOMPLETE` exits 2 too'
status: open
tier: 3
specs: []
prs: []
commits: []
by_hand: true
cites: []
related: []
---

## Problem

**Tier 3.** Found by `SA-0067`'s critic (PR #216), 2026-09-12. `README.md:142`
reads "`2` | infrastructure failed". Since `SA-0067`, `saffron batch` also exits
2 for an `INCOMPLETE` night, which `_batch`'s own docstring says must not be
described to the operator as the machine breaking. The README now sends a
reader to the place the `batch: INCOMPLETE` line was written to keep them out
of. `README.md` was outside the spec's `touches`.

## Done looks like

the row saying what `2` means for each command, by hand.
