---
id: b-865399
title: Step 1b judges a criterion's fixture arrangement by reading, when the helper it will be judged by can be run against it
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: []
related: [123, 124, b-2750d5, b-281f0a]
---

## Problem

Found in the spec loop's run 10, 2026-09-19, on `SA-0112`.

Step 1b's check 3 is witness and mutant discipline, and the reviewer answers it
by reading, because its Bash is limited to git and `driver.py history`. A
criterion can pin a *selection*, meaning which rows a command judges. Reading
one took three rounds, and found a different hole each time:

- round 1: every same-type row in the fixture the spec named is identical in
  `touches` and `criteria`. The closeness sort is a tie, so a `check` skipping
  it passes.
- round 2, on the delegate's fix: the arrangement contradicted the paragraph
  above it, and "placed first" survived the date sort only by an unstated
  property of `_cell`'s defaults.
- round 3, on that fix: the other-type row carries the target's own shape and
  sits after the twelve. The cut drops it either way, so the type filter goes
  unwatched.

Round 4 was not dispatched. The fourteen rows were built against
`_history_lines` at `origin/main` and the selection printed, which took about
two minutes and answered all three arms at once. The correct selection prints
the twelve low-peak rows. A `check` skipping the sort, the cut or the type
filter each keeps a row that blocks. The cell then delivered exactly that
arrangement and the Spec seat's probes killed all three wrong implementations
separately.

Run 9 recorded the same shape for a gate question (a `dead`-gate blocker
overturned by running the gate over a mutated worktree). This is the same move
against a witness-adequacy question, and it is the cheaper half of `b-2750d5`:
that item mutates the *implementation* inside the cell, where this runs the
*fixture* before one starts.

## Done looks like

The skill's step 1b measures a criterion that pins a selection, an ordering or
a cut. It runs the helper that performs it, before the spec's cell starts. The
measurement then ends the round in place of a further review.
Optional: the driver grows the command, so the arrangement is built and printed
rather than hand-scripted each time.

## Record

- 2026-09-19: filed from the spec loop's run 10 (`SA-0112`, #382). Three
  reviews at roughly six minutes each preceded a two-minute measurement that
  settled what they were circling.
