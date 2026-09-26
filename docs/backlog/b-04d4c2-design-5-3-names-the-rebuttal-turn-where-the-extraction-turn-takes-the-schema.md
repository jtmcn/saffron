---
id: b-04d4c2
title: '§5.3 says the rebuttal turn takes the schema, where the rebuttal extraction turn does'
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.3]
related: [b-4e0868]
---

## Problem

Found by the Standards seat on #519, the spec loop's run 17.

`DESIGN.md` §5.3 says "REBUT's rebuttal turn and its verdict sessions use
it". `SA-0141` sends `output_format` on the rebuttal extraction turn
(`saffron/phases/rebut.py`, `_REBUTTALS_FORMAT`). Its criterion 3 requires
that the rebuttal turn itself is sent none. So §5.3 names the wrong turn.

`DESIGN.md` is protected, and `SA-0141` forbade it. The operator edits it
by hand.

## Done looks like

§5.3 names the rebuttal extraction turn.

## Record

- 2026-09-25: filed from the Standards seat on #519 (run 17).
