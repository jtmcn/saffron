---
id: b-6377cf
title: Baseline subtraction hides a `preserves` witness whose mutant survives at base, so a cell that never strengthens it passes `witness`
status: open
tier: 2
filed: 2026-09-23
specs: [SA-0139]
prs: []
commits: []
cites: [§5.4, §5.5.1]
related: [b-19b255]
---

## Problem

Found in the spec loop's run 15, 2026-09-22, on `SA-0127` (#476).

`SA-0127` declared mutants on two summary f-strings whose existing witnesses
checked substrings only. At base both mutants survived, so the cell's baseline
reported `witness=fail`. The spec asked the cell to add exact-summary
assertions. Baseline subtraction then spares that failure: a cell that never
adds the assertions still reports no new `witness` failure. This cell did add
them. The delegate had to confirm it by hand, and the Spec seat re-ran both
mutants at head and at base to show it.

## Done looks like

A mutant that survives at base is not subtracted. `witness` fails at head
unless the mutant is killed there. A test pins that with a `preserves`
criterion whose witness is left unstrengthened.

## Record

- 2026-09-23: filed from the spec loop's run 15 (#476).
