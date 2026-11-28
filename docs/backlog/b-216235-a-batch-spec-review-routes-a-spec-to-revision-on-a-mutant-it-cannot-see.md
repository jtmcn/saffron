---
id: b-216235
title: A batch's spec review routes a spec to revision on a mutant it cannot see
status: open
tier: 2
filed: 2026-11-21
specs: [SA-0446]
prs: []
commits: []
cites: [§5.4.1]
related: [80]
---

## Problem

Found in the spec loop's run 82, batch 101.

`SA-0419`'s spec review raised one concern. Its notes name two mutants on
`refs/saffron/mutants`, and the review's clone does not hold that ref. So
it could not confirm them and routed the spec to `revise`. The mutants
were there, at origin, with the text the notes name. A revision then
needed $63 against $56.78 left. So the batch ran no cell, and its $3.22
of review bought nothing.

The ref is kept out of a cell on purpose (item 80). The host can read it,
and the review cannot.

## Done looks like

The host checks each mutant the spec's criteria declare against the ref,
before the spec review. The review's prompt then says which ones the host
found. A concern that rests only on an unreadable ref is not a reason to
revise.

## Record

- 2026-11-21: filed from the spec loop's run 82. `SA-0419`'s second batch
  ran with room for a revision.
- 2026-11-22: batch 102 ran `SA-0419` at `--budget 100`. Its spec review
  routed `run` that time.
- 2026-11-23: two more weak wrong versions in the spec loop's run 84. `SA-0426`'s criterion 3 version widened `_DIGITS` and never made `identity` read `detail`. Finish 105's draft `SA-0428` declared two `migrate` versions its own witness could not reach, and REBUT left both blockers for the operator.
