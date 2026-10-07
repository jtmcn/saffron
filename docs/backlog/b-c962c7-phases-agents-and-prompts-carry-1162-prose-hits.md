---
id: b-c962c7
title: 'The phases, the agents and the turn prompts carry 1,162 `prose` hits'
status: open
tier: 3
filed: 2026-10-07
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-86fa07, b-ad1285, b-2d668f, b-817ef7, b-80cad7, b-37de22, b-30fed0, b-e8f092]
---

## Problem

25 files: `saffron/phases/**`, `saffron/agents/**`, `task.py`, `end_review.py`, `spec_review.py`, `intake.py`, `finish.py`, and their tests. The prompts under `saffron/agents/prompts/` hold 205.

`prose` is a ratchet, so these hits block nothing. They do fill every gate
result, which is item b-86fa07. Counts were measured on 2026-10-07 at
`508a018d`, with closed backlog records out of scope.

## Done looks like

`.saffron/gates/prose` reports no hit in any file named above. Each rewritten
sentence stays true, and review checks it against the code it describes
(item b-ad1285). A long docstring or comment block is cut before it is
rewritten, and its rationale moves to the commit message.

A prompt is what a cell reads on every task, so rewording one changes behaviour. Clear the prompts in their own pull request, and judge it as a behaviour change. `DESIGN.md` §5.5 quotes the lens prompts verbatim and carries 8 hits in that quote. Change the quote with the prompts.

## Record

**Filed 2026-10-07 by hand**, as one of seven items that split the repo's
`prose` hits by area. `DESIGN.md` and `CONTEXT.md` were cleared in a pull
request of their own. Their 24 remaining hits are named in b-c962c7 and b-e8f092.
