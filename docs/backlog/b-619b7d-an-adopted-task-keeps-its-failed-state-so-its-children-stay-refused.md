---
id: b-619b7d
title: "`saffron adopt` keeps a task `EXHAUSTED`, refuses `MERGE_FAILED`, and nothing moves a fixed task back to waiting, so its children stay refused"
status: partial
tier: 2
filed: 2026-10-19
specs: [SA-0313]
prs: [961]
commits: []
cites: [§4.2.1]
related: [b-dc5212, b-6b06e1]
---

## Problem

Found in the spec loop's run 44.

`adopt` takes `EXHAUSTED`, `NOT_IMPLEMENTED` and `READY_FOR_REVIEW`
(`saffron/cli.py:2322`). It names the pull request and leaves the state.
`SA-0279` ended `EXHAUSTED`, was finished by hand as #912 and adopted. Its
task stayed `EXHAUSTED`. The loop's `driver.py size` and `driver.py stack`
then refused it, so the delegate measured and linked it by hand. Its three
children, `SA-0290`, `SA-0291` and `SA-0295`, cannot run until #912 merges.

`SA-0277` ended `MERGE_FAILED` in the first batch, on a literal key header in
a test. The delegate fixed the patch by hand as #904. `adopt` and `package`
both refuse `MERGE_FAILED`, so the nine tasks below it stayed refused. The
operator chose a re-run, and #904 closed.

## Done looks like

A task finished by hand reaches a state its children and the driver read as
a reviewable parent. One route takes a fixed `MERGE_FAILED` task there, such
as `regate` then `adopt`. A test drives each route and starts a child on it.

## Record

- 2026-10-19: filed from the spec loop's run 44.
- 2026-10-23: recurred twice in the spec loop's run 46. `SA-0298` stayed `EXHAUSTED` after `saffron adopt`, so the driver could not stack or size it. The adopted `SA-0302` recorded no pushed sha, so batch 44 refused its child `SA-0303` (b-066901).
- 2026-10-24: recurred in the spec loop's run 47. `SA-0312` was adopted as #957 and
  kept `EXHAUSTED`. So `saffron finish 51` reviewed `SA-0314` against `SA-0311` and
  charged `SA-0312`'s diff to it. `driver.py size` measured from the same wrong
  parent. `SA-0313` carries the fix and waits on #957.
- 2026-10-25: done in #961 (`SA-0313`), from the spec loop's run 48. `saffron adopt` records
  the adopted head as a `task_push` fact and moves the task to `READY_FOR_REVIEW` on a
  green re-gate.
- 2026-11-09: partial from the spec loop's run 56. `saffron adopt SA-0353 1099` printed `regate: task 396 ran a recorded spec text, not a file at base_sha` and kept the task `EXHAUSTED`. The batch had rewritten the spec's moved citations, so the text it ran is in no file. `driver.py record` still prints the task `EXHAUSTED`.
- 2026-11-10: a new block in the spec loop's run 60. `saffron adopt
  SA-0364 1136` named the pull request, but its re-gate declined: "task 407
  ran a recorded spec text, not a file at base_sha" (`saffron/regate.py`). A
  stack batch records a revised text for each layer its review revised. So
  no route moves such a `MERGE_FAILED` task to `READY_FOR_REVIEW`.
- 2026-11-11: the route held where no spec text was recorded. In the spec
  loop's run 61, `saffron adopt SA-0368 1145` re-gated the head green and set
  `READY_FOR_REVIEW`. Batch 79 recorded no revised text for that layer. But
  `saffron finish 79` then refused: "batch 79 holds no layer". An adopted
  task is not a stack layer, so its end review never runs.
