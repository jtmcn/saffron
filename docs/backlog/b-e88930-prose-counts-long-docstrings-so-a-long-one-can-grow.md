---
id: b-e88930
title: The `prose` gate counts over-long docstrings per file, so a docstring already over the limit grows unnoticed
status: open
tier: 3
filed: 2026-09-25
specs: []
prs: []
commits: []
cites: [§5.4]
related: [b-440f17]
---

## Problem

Found in the review of #512 (`SA-0133`), 2026-09-24.

`_long_docstrings` yields one hit per docstring over `DOCSTRING_LIMIT` lines
(`.saffron/gates/prose.py:248-258`). The gate compares hit counts per file. A
docstring over the limit at base stays one hit at any length.

`_drive`'s docstring went from 15 to 19 lines in #512. The review cut it
back by hand.

## Done looks like

A docstring over the limit at base fails when it grows. A test grows one by
a line and reads a new hit.

## Record

- 2026-09-25: filed from the spec loop's run 16.
