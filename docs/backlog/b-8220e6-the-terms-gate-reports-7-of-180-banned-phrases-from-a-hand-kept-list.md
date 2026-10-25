---
id: b-8220e6
title: "The `terms` gate reports 7 of 180 avoided phrases from a hand-kept list, and no `_Avoid_` line says which kind each phrase is"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: [963]
commits: []
cites: [§5.4, §5.5]
related: [162, b-541e9a]
---

## Problem

ADR 11 splits each avoided phrase into banned or confusable. Nothing applies it
yet.

`AVOIDED` in `.saffron/gates/prose.py` names 7 phrases. `CONTEXT.md`'s `_Avoid_`
lines quote 194 distinct phrases at `2e1efa2b`, and 14 of them are another
term's headword. 49 of the other 180 have no hit in tracked Markdown outside
`CONTEXT.md`, `docs/evidence/` and `docs/appendices/`.

The lines also vary in form. "Regression test" is quoted inside an `_Avoid_`
paragraph that allows it. `_Avoid_ also` clauses sit mid-paragraph, and some
avoided phrases sit inside a definition. 21 phrases are avoided under more than
one entry.

## Done looks like

- Every `_Avoid_` line is triaged into `_Avoid_:` and `_Confusable_:` lines, in
  the grammar ADR 11 states. The 49 phrases with no hit go first.
- `terms` parses the `_Avoid_:` lines, and `AVOIDED` is deleted. The gate
  reports `error` on an empty list or a line holding anything but quotes.
- A test holds a banned phrase to one entry, and a phrase to one kind.
- `context.py`'s strip pattern names both markers, and the conventions lens
  keeps both lines.

`CONTEXT.md` is protected, so the triage is a host-side edit.

## Record

- 2026-10-24: filed with ADR 11 (#963).
