---
id: b-b33854
title: "Three texts still say the gate never parses a witness id and the spec declared every mutant, and constant mutants make both false"
status: open
tier: 3
filed: 2026-10-19
by_hand: true
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-5b1f8a]
---

## Problem

Found by both seats and the in-cell critic on #908, in the spec loop's run 44.

`SA-0280` (#908) derives constant mutants from patterns a repo declares.
`witness` now applies the repo's `witness_name` pattern to a criterion's
witness id. Three texts still describe the gate before that change.

- `Criterion`'s docstring says the gate never parses the witness id
  (`saffron/intake.py:116-117`).
- `CONTEXT.md:427` says a survivor at base is not subtracted because "The
  spec declared that mutant".
- `DESIGN.md:1051` says the same, "The spec declared its mutant".

A constant mutant is derived, not declared. `saffron/intake.py`, `CONTEXT.md`
and `DESIGN.md` were each forbidden to the spec. The last two are protected,
so they change by hand.

## Done looks like

Each text covers a constant mutant beside a declared one.

## Record

- 2026-10-19: filed from the spec loop's run 44.
