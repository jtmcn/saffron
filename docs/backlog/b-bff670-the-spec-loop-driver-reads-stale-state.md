---
id: b-bff670
title: The spec loop's driver reads stale state, so `status` shows merged PRs as reviewable and `check` judges a branch's spec on main's ceilings
status: open
tier: 2
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§8]
related: [b-e8027b, b-a4df62]
---

## Problem

Found in the spec loop's run 16, 2026-09-23.

`status` (`.claude/skills/run-saffron-spec-loop/driver.py:1469`) read the last
loop's snapshot and never asked GitHub. It showed five merged pull requests as
`READY_FOR_REVIEW`.

`history` and `check` (`driver.py:2020`, `:1978`) read the spec from the
checkout. The delegate edited `SA-0140`'s ceilings on a branch (#498). Both
commands judged it on the old ceilings, and the reviewer recomputed by hand.

`snapshot --force` released `SA-0140`'s hold while #498 was still open. That
is item b-e8027b, and it is recorded there.

## Done looks like

- `status` reconciles each pull request's state before it prints.
- `history` and `check` accept a ref and read the spec there.
- A test drives each against a fixture where the snapshot or the checkout is
  stale.

## Record

- 2026-09-25: filed from the spec loop's run 16.
- 2026-09-26: recurred in the spec loop's run 18. After run 17 merged,
  `status` said to run `snapshot --force`. That exited 1 with no candidates.
  The right command was `snapshot --new`, and neither output named it.
