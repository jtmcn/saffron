---
id: b-0281e4
title: The projection parses two printed lines with regexes, and Q4's path is spelled in two files
status: open
tier: 3
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: [§4.1]
related: [43, 170, b-946f03]
---

## Problem

Found in the spec loop's run 8, 2026-09-19, reviewing #355 (`SA-0107`) and
#366 (`SA-0108`).

The projection reads what a task recorded at extraction by parsing the prose
of two event details, not a typed field:

- `_DIFF_EXPORTED` (`saffron/projection.py:62` on `origin/saffron/SA-0108`)
  parses `exported N bytes to …`, written as free text at
  `saffron/cell/session.py:768`.
- `_PLAN_ACCEPTED` (`saffron/projection.py:61`) parses `accepted, sha256 …`,
  written at `saffron/cell/session.py:1593`.

A reworded detail line breaks the projection, and no test ties the writer to the
reader. `session.py` was forbidden to both specs, so neither could add a field.
The diff's record is also a length only, so a diff overwritten by one of the
same length goes undetected (`SA-0108`'s notes).

Q4's path is spelled twice: `Q4_QUERY` at `saffron/chain_walk.py:19` and
again at `tests/test_projection.py:220`.

## Done looks like

The plan hash and the diff's size and hash reach the event log as fields of a
typed event, and the projection reads those fields. The detail strings stay
prose. Q4's path has one spelling that the test imports.

## Record

- 2026-09-19: filed from the spec loop's run 8 (stack #351 ← #360 ← #355 ←
  #366 ← #353).
