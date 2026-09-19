---
id: b-952c34
title: Half the merged tasks never reach the chain comparison, and the one real overwrite in history is among them
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [170, b-946f03, b-60d804]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, running #366 (`SA-0108`) over a
copy of the real ledger.

The ledger holds 76 merged tasks. `saffron chains` compared 38 of them and
found 0 breaks. It left out the other 38: 35 as unattributable and 3 as
`spec_unusable`.

The one real overwrite in history is `SA-0013` task 8 (PR #51). Tasks 9 and
10 of the same spec later wrote over its `plan.json` in the batch tree, which
is keyed by spec. That task is one of the 3 left out as `spec_unusable`.
`SA-0013` is a `test` spec, and the projection refuses that type (item b-60d804).

Appendix T's instrument exists to find that shape, and it cannot see the one
instance history holds. Its "0 breaks" is a statement about the half it could
attribute. The command prints a line per reason, so the gap is visible, but
nothing asks why 35 tasks cannot be attributed.

## Done looks like

`SA-0013` task 8 reaches the comparison. The 35 unattributable tasks have a
measured cause, recorded in this item. Appendix T's decision rule is run again
over what is then kept, and the answer recorded in b-946f03. Item 170 then
decides whether the tasks still left out are migrated or abandoned.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353). The numbers are the Spec seat's run over a ledger copy.
