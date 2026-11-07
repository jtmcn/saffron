---
id: b-e88930
title: The `prose` gate counts over-long docstrings per file, so a docstring already over the limit grows unnoticed
status: done
tier: 3
filed: 2026-09-25
closed: 2026-11-07
specs: []
prs: [616]
commits: []
cites: [§5.4]
related: [b-440f17, b-ec607a, b-8acb05]
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
- 2026-11-07: closed in grooming. `9ef9e7b2` (#616, for b-ec607a) made `_long_docstrings` yield one hit per line past `DOCSTRING_LIMIT`, keyed by name and line (`.saffron/gates/prose.py:310-324`). A growth adds only the lines past its base. `tests/test_prose_gate.py::test_a_long_docstring_that_grows_is_new_and_one_edited_in_place_is_not` and its neighbour grow a docstring and read the new hits. b-8acb05 tracks the rename hole that keying leaves.
