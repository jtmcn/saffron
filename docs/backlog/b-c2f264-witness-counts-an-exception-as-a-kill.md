---
id: b-c2f264
title: The witness gate counts a wrong version killed only by an exception as caught
status: open
tier: 2
filed: 2026-11-20
specs: []
prs: []
commits: []
cites: [§5.4.1]
related: [b-7f6ce2]
---

## Problem

Found by the Spec seat on #1281, in the spec loop's run 81.

Three `SA-0418` witnesses looked a task up in a dict before they asserted.
Fifteen wrong versions removed that task, and each died by `KeyError`. The
`witness` gate reads a failed test as a kill, whatever ended it. So every
wrong version counted as caught, though no assertion ever judged it.

The driver's `probe` already tells the two apart. Its outcome reads "killed
only by errors, not by an assertion" (`driver.py` `_ERROR_KILL`). The gate
has no such reading, so the cell's own REVIEW passed all fifteen.

## Done looks like

Suppose each failure a witness shows under a wrong version is an exception
other than `AssertionError`. That witness then reads as a survivor, or as an
outcome of its own that the critic sees. Core reads the exception name from the `tests` gate's failure text.
The pattern for that text is declared in `policy.yaml`, since it is
language knowledge (§2.1).

## Record

- 2026-11-20: filed from the spec loop's run 81. The review commit on #1281
  swapped each lookup for `.get` and `in`, and all fifteen then died by an
  assertion.
