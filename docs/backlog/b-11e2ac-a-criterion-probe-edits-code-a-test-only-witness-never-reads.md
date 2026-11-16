---
id: b-11e2ac
title: A criterion probe of a test-only spec edits production code its witness never reads, and files the survivor as a blocker
status: done
closed: 2026-11-15
tier: 3
filed: 2026-11-15
specs: [SA-0400]
prs: [1228]
commits: []
cites: [§5.4.1, §5.5]
related: [b-7f6ce2, b-9ed36d]
---

## Problem

Found reviewing finish 89's follow-ups, #1218 and #1219, in the spec loop's
run 72.

Both specs touch one test file and nothing else. The host's criterion probes
edited files the claims cite only as background. For `SA-0397` these were
`.saffron/gates/prose.py:272` and `:423`. For `SA-0398` they were
`saffron/gates/suite.py`, `saffron/cell/worktree.py` and
`saffron/cell/session.py`. Each witness stayed green, which was right, and the
host filed six adequacy blockers. REBUT withdrew `SA-0398`'s four. `SA-0397`'s
two stayed as recorded disagreement. Both review seats on each pull request
judged all six to be mutants aimed at code the witness never reads.

## Done looks like

A criterion probe edits only files in its spec's `touches`, or in the
criterion's own `subject:`. Or a survivor in a file outside both is
reported as a note rather than a blocker.

## Record

- 2026-11-15: filed from the spec loop's run 72, #1218 and #1219.
- 2026-11-15: done in the spec loop's run 74. `SA-0400` (#1228) refuses a criterion probe outside `touches` and off its `subject`.
