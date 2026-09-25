---
id: b-a7e5f3
title: The ledger cannot adopt a by-hand pull request for a task whose cell pushed nothing, so its children stay refused after it merges
status: open
tier: 1
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§4.2, §5.7]
related: [b-111c56, b-e471bd]
---

## Problem

Found in the spec loop's run 16, 2026-09-24, on `SA-0129`.

`SA-0129`'s only task row read `NOT_IMPLEMENTED`, since its cell pushed
nothing. The operator took it by hand as #502, and #502 merged. `saffron
queue` then refused its child: "depends_on SA-0129 is NOT_IMPLEMENTED, which
is not MERGED".

Item b-111c56 admits a child whose parent's recorded push reached the default
branch. `SA-0129` recorded no push, so that rule has nothing to read. The
workaround was to retire the spec to `done/` early, in #503.

`driver.py size` refused #502 as well: "SA-0129 is not reviewable, so it has
no stack to sit in" (`.claude/skills/run-saffron-spec-loop/driver.py:1628`).
`record` and `stack` know no by-hand pull request either.

## Done looks like

A by-hand pull request can be named as a task's, and its merge counts as the
parent's. A test covers a parent that ended `NOT_IMPLEMENTED` with no push,
whose by-hand pull request then merged, and its child is a candidate.

## Record

- 2026-09-25: filed from the spec loop's run 16.
