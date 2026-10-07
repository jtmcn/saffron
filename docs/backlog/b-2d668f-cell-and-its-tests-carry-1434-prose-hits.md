---
id: b-2d668f
title: '`saffron/cell/`, `images/` and their tests carry 1,434 `prose` hits'
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07, b-ad1285, b-817ef7, b-80cad7, b-37de22, b-c962c7, b-30fed0, b-e8f092]
---

## Problem

15 files: `saffron/cell/**`, `images/**`, and the tests that drive a cell (`test_session.py`, `test_worktree.py`, `test_proxy.py`, `test_runtime.py`, `test_image.py`, `test_agent_runner.py`, `test_probe_cell.py`, `test_package_cell.py`, `test_review_cells.py`). `saffron/cell/session.py` holds 425 and `tests/test_session.py` holds 486.

`prose` is a ratchet, so these hits block nothing. They do fill every gate
result, which is item b-86fa07. Counts were measured on 2026-10-07 at
`508a018d`, with closed backlog records out of scope.

## Done looks like

`.saffron/gates/prose` reports no hit in any file named above. Each rewritten
sentence stays true, and review checks it against the code it describes
(item b-ad1285). A long docstring or comment block is cut before it is
rewritten, and its rationale moves to the commit message.

Many comments here cite a measurement from Appendices G to L. Reword such a comment, and keep the measurement it names.

## Record

**Filed 2026-10-07 by hand**, as one of seven items that split the repo's
`prose` hits by area. `DESIGN.md` and `CONTEXT.md` were cleared in a pull
request of their own. Their 24 remaining hits are named in b-c962c7 and b-e8f092.
