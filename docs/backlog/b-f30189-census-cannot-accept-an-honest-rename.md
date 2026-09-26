---
id: b-f30189
title: '`census` has no way to accept an honest rename, so tests keep names that state what they no longer test'
status: open
tier: 3
filed: 2026-09-23
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found in the spec loop's run 15, 2026-09-23.

`SA-0128` changed the ceilings a parametrised test drives from 300, 600 and
1000 to 1300, 3000 and 4200. Its node ids derive from the ceilings, so
attempt 1 failed `census` on three vanished ids. Repair pinned `ids=` to the
old names, so `main-a-bug-300` now drives 1300 (#483,
`tests/test_spec_loop_driver.py:170`). `SA-0126` changed a test's expected
state to `ORPHANED`, and its name still says `is_not_implemented` (#478). Both
seats flagged these, and both specs forbade renames because `census` would
fail.

## Done looks like

A spec can declare a rename, old id to new id, and `census` accepts exactly
the declared pairs. An undeclared disappearance still fails.

## Record

- 2026-09-23: filed from the spec loop's run 15 (#478, #483).
- 2026-09-25: recurred in run 17 (#519). `test_a_turn_prompt_constant_is_its_file`
  took its ids from each prompt's text, so `SA-0141`'s prompt edit failed
  `census` on four ids. Repair pinned the old text into the ids, and kept two
  cases the spec said to drop by inverting their assertion. A review commit
  made the ids the prompt names, so a prompt edit no longer renames a case.
  The spec told the cell to drop two parametrised cases, and neither the spec
  review nor the spec named `census`.
