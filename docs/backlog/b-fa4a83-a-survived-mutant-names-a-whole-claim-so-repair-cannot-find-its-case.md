---
id: b-fa4a83
title: A survived mutant reaches REPAIR as a whole claim, so the repair turn cannot find the case it lacks
status: open
tier: 1
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-78a590]
---

## Problem

Found by the spec loop's run 53, in `SA-0330`'s cell.

The `witness` gate failed on both declared mutants in all three attempts.
Its failure names the witness and the claim, and withholds the edit by
design (`saffron/gates/core/witness.py:261-270`, §5.4.1). Both claims ran to
about a dozen sentences each.

The repair turns spent attempts 2 and 3 writing mutants of their own and
hardening against those. Neither found the case each declared mutant broke.
The cell ended `EXHAUSTED` at $41.67 of $40.

Each missing case took the delegate one test block to write:

- a no-`gh` case where an older waiting row and the newest row disagree.
- a multi-parent case with a parent retired at `base_sha`.

## Done looks like

A survived mutant tells REPAIR which part of its claim went untested, and
still withholds the edit. One shape is a sentence of the claim that the spec
names beside its mutant, which the message quotes.

## Record

- 2026-11-04: filed from the spec loop's run 53.
