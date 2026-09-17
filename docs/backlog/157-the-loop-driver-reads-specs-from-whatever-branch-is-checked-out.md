---
id: 157
title: The spec loop's driver reads specs from whatever branch is checked out, and tells the operator to revert an edit that was never made
status: open
tier: 2
filed: 2026-09-17
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [137]
---

## Problem

**Tier 2.** By hand: `.claude/skills/run-saffron-spec-loop/driver.py` is not
something a cell can land. Found in the spec loop's run 5, 2026-09-17.

Step 2c checks each reviewed branch out in the main checkout. A stacked chain's
bottom branch is cut from `main` before the loop's spec fixes merge, so its
`.saffron/specs/` holds the old text. With `saffron/SA-0095` checked out,
`driver.py status` reported:

```
stale — `snapshot --force` before the next cell:
  SA-0094: the spec changed after the snapshot
  SA-0094: editing it with its pull request open leaves it held out of the order,
  and #305 with it. Revert the edit to the `spec_sha` its task ran at, …
```

Nothing had been edited. From `main` the same command reported nothing stale.
The advice is the harmful part: reverting to the checkout's text would have
undone #304 and #306, and actually held both specs out of the order (item 137).

## Done looks like

`status`, `next` and `snapshot` read spec files from the default branch's tip
(`git show origin/<default>:<path>`), or refuse to run with a spec-loop branch
checked out, saying which.

## Record

**Filed 2026-09-17** from the spec loop's run 5 (stack #308).
