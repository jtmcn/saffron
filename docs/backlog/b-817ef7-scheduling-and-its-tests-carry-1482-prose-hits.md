---
id: b-817ef7
title: 'The scheduler, the batch and their tests carry 1,482 `prose` hits'
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07, b-ad1285, b-2d668f, b-80cad7, b-37de22, b-c962c7, b-30fed0, b-e8f092]
---

## Problem

9 files: `saffron/scheduler.py`, `batch.py`, `reconcile.py`, `preflight.py`, `follow_up.py`, and their tests. `tests/test_scheduler.py` alone holds 827. Of those, 626 are `docstring-length`.

`prose` is a ratchet, so these hits block nothing. They do fill every gate
result, which is item b-86fa07. Counts were measured on 2026-10-07 at
`508a018d`, with closed backlog records out of scope.

## Done looks like

`.saffron/gates/prose` reports no hit in any file named above. Each rewritten
sentence stays true, and review checks it against the code it describes
(item b-ad1285). A long docstring or comment block is cut before it is
rewritten, and its rationale moves to the commit message.

Most of the work is cutting long test docstrings. A test name and its assertions carry the claim, and the rest belongs in a commit message.

## Record

**Filed 2026-10-07 by hand**, as one of seven items that split the repo's
`prose` hits by area. `DESIGN.md` and `CONTEXT.md` were cleared in a pull
request of their own. Their 24 remaining hits are named in b-c962c7 and b-e8f092.
