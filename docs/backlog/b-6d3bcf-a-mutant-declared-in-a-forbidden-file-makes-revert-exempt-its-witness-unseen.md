---
id: b-6d3bcf
title: A mutant declared in a forbidden file makes `revert` exempt its witness, and nothing tells the spec author
status: open
tier: 3
filed: 2026-09-27
closed:
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [84]
---

## Problem

Found in the spec loop's run 19, 2026-09-27, reviewing `SA-0178`'s spec.

`revert` exempts a witness whose mutant names a file outside the diff's source
(`saffron/gates/core/revert.py:193-205`, item 84). A cell never edits a
forbidden file, so a mutant declared there always exempts its witness.

`SA-0178`'s round-1 revision declared a mutant in a forbidden file. The
round-2 review found that `revert` then skipped the witness, and the delegate
removed the mutant by hand. Nothing at intake or in `driver.py check` names
the case.

## Done looks like

Intake or `driver.py check` names a mutant whose file matches `forbidden`, and
says `revert` will exempt its witness.

## Record

- 2026-09-27: filed from the spec loop's run 19.
