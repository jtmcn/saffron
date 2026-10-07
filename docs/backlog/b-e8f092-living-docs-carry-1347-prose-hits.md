---
id: b-e8f092
title: 'The living Markdown outside `DESIGN.md` and `CONTEXT.md` carries 1,347 `prose` hits'
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07, b-ad1285, b-2d668f, b-817ef7, b-80cad7, b-37de22, b-c962c7, b-30fed0]
---

## Problem

73 files: open and partial backlog records (604), `docs/appendices/` (511), `.claude/` agents and skills (149), `CLAUDE.md` (52) and `README.md` (31).

`prose` is a ratchet, so these hits block nothing. They do fill every gate
result, which is item b-86fa07. Counts were measured on 2026-10-07 at
`508a018d`, with closed backlog records out of scope.

## Done looks like

`.saffron/gates/prose` reports no hit in any file named above. Each rewritten
sentence stays true, and review checks it against the code it describes
(item b-ad1285). A long docstring or comment block is cut before it is
rewritten, and its rationale moves to the commit message.

`docs/appendices/**` is protected, so a cell cannot edit it. A record's title renders into the index in `DESIGN.md`, and 11 of that file's hits sit there. Fix those in the record and run `uv run python -m ontology.render`. `CONTEXT.md`'s phase table marks a section no phase injects with a bare em-dash, 5 hits. `tests/test_citations.py` reads that cell, so the marker and the test change together.

## Record

**Filed 2026-10-07 by hand**, as one of seven items that split the repo's
`prose` hits by area. `DESIGN.md` and `CONTEXT.md` were cleared in a pull
request of their own. Their 24 remaining hits are named in b-c962c7 and b-e8f092.
