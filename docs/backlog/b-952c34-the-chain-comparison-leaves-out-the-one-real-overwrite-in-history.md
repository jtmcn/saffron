---
id: b-952c34
title: Half the merged tasks never reach the chain comparison, and the one real overwrite in history is among them
status: partial
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
- 2026-11-09: b-60d804 closed. The projection no longer leaves a `test` or `docs` task out on its type, so `SA-0013` task 8 can reach the comparison.
- 2026-11-20: measured over the home ledger at main `4e58acd`. `saffron chains`
  compared 143 of 336 merged tasks, with 3 breaks (`SA-0245`, `SA-0277` and
  `SA-0415`). It left out 187 as unattributable, 5 as `spec_not_found` and 1
  as `spec_unusable`. Of those left out:
  - 151 date before their log's first span. `_all_tasks` dates a task by its
    run's `started_at`. A batch's later cells start long after the run does.
  - 20 logs hold no `Ceilings` event, and 17 tasks have no `events.jsonl`.
    `SA-0013` task 8 is one of the 17, so no log can attribute it.
  - 3 share a span with another task of the spec, and 2 spans lack a plan
    or diff line.
  Dating each task by its first attempt keeps 178 instead of 143. Newer
  tasks write that attempt about two seconds before the span's `Ceilings`
  event, and older ones after it. So neither date alone reaches both eras.
  The tally scripts were run by hand and are not in the tree.
