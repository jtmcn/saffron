---
id: b-440f17
title: The `prose` and `terms` gates read no word rule in a Python comment or docstring, so three pull requests in one loop shipped what `CLAUDE.md` forbids
status: open
tier: 2
filed: 2026-09-21
specs: []
prs: []
commits: []
cites: []
related: [b-6a9707, b-08a36a]
---

## Problem

Found in the spec loop's run 11, 2026-09-20 and 2026-09-21.

`CLAUDE.md` forbids an em-dash, a semicolon, a contraction, perfect tense, a hedge
and a sentence over 25 words in a new comment. The `prose` gate enforces those
rules on Markdown only. For a `.py` path, `check` at
`.saffron/gates/prose.py:414-420` returns comment-block and docstring-length hits
alone, and it returns nothing for the `terms` gate.

Three pull requests in one loop shipped through that gap, and each was caught by
hand in review.

- #403 carried five em-dashes in new comments and docstrings.
- #404 carried five em-dashes, eleven semicolons, and a docstring sentence of 96
  words. Two comments also cited "(item 2)" meaning a spec's own list, where the
  file uses "(item N)" for backlog items.
- #406 carried two em-dashes and eight docstring sentences of up to 51 words.

Each review spent a pass on text a gate could catch. Item b-6a9707 is one
instance of the `terms` half of the same gap.

## Done looks like

The `prose` gate applies its word rules to the comments and docstrings of a `.py`
file, with the base subtraction it already does. The `terms` gate does the same.
A hunk that adds an em-dash to a new comment fails the gate.

## Record

- 2026-09-21: filed from the spec loop's run 11 (#403, #404, #406).
