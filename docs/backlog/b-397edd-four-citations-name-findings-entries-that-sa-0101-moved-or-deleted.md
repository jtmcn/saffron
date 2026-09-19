---
id: b-397edd
title: Four citations name `events.FINDINGS` entries that `SA-0101` moved or deleted
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: []
related: [43, 75]
---

## Problem

Found in the spec loop's run 8, 2026-09-18. `SA-0101`'s spec named them and
the cell's notes on #351 listed them.

`SA-0101` typed the task's outcome line and deleted `events.FINDINGS[0]`. The
`re-verify:` entry moved from index 1 to index 0 (`saffron/events.py:972` on
`origin/saffron/SA-0101`). Four comments outside that spec's `touches` still
cite the old indices:

- `saffron/phases/package.py:538`: `events.FINDINGS[1]`.
- `saffron/phases/package.py:542`: `events.FINDINGS[0]`'s outcome line, which
  no longer exists.
- `tests/test_package.py:1177`: `events.FINDINGS[1]`.
- `tests/test_package_cell.py:28`: `events.FINDINGS[1]`.

An index is a line number by another name. `events.py` itself cites by file and
symbol, never by line, and these four comments do not follow that rule.

## Done looks like

The four comments cite the `re-verify:` entry by its text or by `reverify`,
never by index. Done by hand once #351 merges, or by the next spec that touches
those files.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
