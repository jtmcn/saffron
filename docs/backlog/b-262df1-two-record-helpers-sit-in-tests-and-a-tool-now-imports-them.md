---
id: b-262df1
title: Two record helpers sit under tests/ because only tests ran them, and a tool now imports them
status: open
filed: 2026-09-20
specs: []
prs: []
commits: []
cites: []
related: [b-7d3810, b-990bd9]
---

## Problem

Filed 2026-09-20 while writing `SA-0116`.

`tests/records/check.py` holds one pure function per record integrity rule.
Its module docstring says why they live there: "Test support, moved from
`records/`: only these tests ran it."

`SA-0116` gives two of them a second caller. Its command prints the four edits
a spec's commit owes. It reads `first_cited_item` at
`tests/records/check.py:362` for the origin item a spec's `## Context` cites,
and `check_priority` at `:441` for the records `PRIORITY.md` does not place.
So the stated reason for the move stops being true the day that command lands.

The direction is backwards. `records/` is the dev-only package for this
repository's project documents, and nothing under it imports from `tests/`.
A tool under `.claude/skills/` reaching into `tests/` for a rule inverts that.
The import resolves only because both run under `uv run` from the repository
root.

Copying the two functions into the driver was rejected when `SA-0116` was
written. Two definitions of one rule drift, and the copy would not be the one
`make check` applies, which is the defect [[b-990bd9]] names one file over.

## Done looks like

`first_cited_item` and `check_priority` live in `records/`, with whatever they
depend on. `tests/records/check.py` imports them rather than defining them, and
so does the driver's bookkeeping command. No rule has two definitions, and
`make check` applies the same function the command printed from.

## Record

- 2026-09-20: filed with `SA-0116`, by operator decision. The spec imports from
  `tests/records/check.py` as drafted rather than moving the helpers. The move
  would take that spec's estimate past the margin its contract asks for. This
  record is the debt, and it closes when the move happens.
