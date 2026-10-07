---
id: b-30fed0
title: 'The harness, the ontology and the remaining Python carry 824 `prose` hits'
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07, b-ad1285, b-2d668f, b-817ef7, b-80cad7, b-37de22, b-c962c7, b-e8f092]
---

## Problem

33 files: `harness/**`, `ontology/**`, `saffron/repos/**`, `chain_walk.py`, `probe.py`, `replay.py`, `tests/ontology/**`, the spec loop's `driver.py`, and the tests of each. This is every Python file in scope that the other items in this set do not name.

`prose` is a ratchet, so these hits block nothing. They do fill every gate
result, which is item b-86fa07. Counts were measured on 2026-10-07 at
`508a018d`, with closed backlog records out of scope.

## Done looks like

`.saffron/gates/prose` reports no hit in any file named above. Each rewritten
sentence stays true, and review checks it against the code it describes
(item b-ad1285). A long docstring or comment block is cut before it is
rewritten, and its rationale moves to the commit message.

v1 deletes `saffron/replay.py`. Skip it if that lands first.

## Record

**Filed 2026-10-07 by hand**, as one of seven items that split the repo's
`prose` hits by area. `DESIGN.md` and `CONTEXT.md` were cleared in a pull
request of their own. Their 24 remaining hits are named in b-c962c7 and b-e8f092.
