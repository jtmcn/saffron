---
id: b-92c92a
title: "A blocker the critic still holds after REBUT reaches `READY_FOR_REVIEW`, and only the pull request body says so"
status: open
tier: 3
filed: 2026-10-27
specs: []
prs: []
commits: []
cites: [§5.6]
related: []
---

## Problem

Found in the spec loop's run 49.

`SA-0322`'s adequacy lens held a blocker after REBUT, recorded as a disagreement
for the operator to adjudicate. The cell still reached `READY_FOR_REVIEW` as
#978. Both review seats then showed the mutant equivalent on the path it named,
and the delegate withdrew it. Nothing outside the body marks the pull request as
holding an open blocker.

## Done looks like

A pull request with a held blocker carries a mark `driver.py record` and
`saffron queue` both print.

## Record

- 2026-10-27: filed from the spec loop's run 49.
