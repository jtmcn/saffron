---
id: b-262df1
title: Record helpers sit under tests/ because only tests ran them, and a tool now imports three of them
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

`SA-0116` gives three of them a second caller. Its command prints three of the
four edits a spec's commit owes, and it imports `spec_files` at
`tests/records/check.py:283`, `first_cited_item` at `:362` and
`_context_section` at `:371`: the spec id to file map, the origin item a
spec's `## Context` cites, and the section that citation is read out of.
`check_priority` at `:441` was a fourth until that spec's second review cut
its `PRIORITY.md` block on size. It becomes one again when the rest of
[[b-7d3810]] lands. So the stated reason for the move stops being true the
day that command lands.

The direction is backwards. `records/` is the dev-only package for this
repository's project documents, and nothing under it imports from `tests/`.
A tool under `.claude/skills/` reaching into `tests/` for a rule inverts that.
The import resolves only because both run under `uv run` from the repository
root.

Copying the two functions into the driver was rejected when `SA-0116` was
written. Two definitions of one rule drift, and the copy would not be the one
`make check` applies, which is the defect [[b-990bd9]] names one file over.

## Done looks like

`spec_files`, `first_cited_item`, `_context_section` and `check_priority` live
in `records/`, with whatever they depend on. `tests/records/check.py` imports
them rather than defining them, and so does the driver's bookkeeping command.
No rule has two definitions, and `make check` applies the same function the
command printed from.

## Record

- 2026-09-20: filed with `SA-0116`, by operator decision. The spec imports from
  `tests/records/check.py` as drafted rather than moving the helpers. The move
  would take that spec's estimate past the margin its contract asks for. This
  record is the debt, and it closes when the move happens.
- 2026-09-20: counted the cross-import from `SA-0116`'s second review. It is
  three names, not one, and this record named one of the three.
