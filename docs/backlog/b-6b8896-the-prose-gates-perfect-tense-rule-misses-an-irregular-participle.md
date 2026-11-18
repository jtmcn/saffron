---
id: b-6b8896
title: The `prose` gate's perfect-tense rule misses an irregular participle, so "has run" passes
status: open
tier: 3
filed: 2026-11-17
closed:
specs: []
prs: []
commits: []
cites: [§5.4]
related: [162]
---

## Problem

Found by batch 95's end review on `SA-0407` (#1250), in the spec loop's run
78.

`PERFECT` at `.saffron/gates/prose.py:97` matches "has been" and "has" or
"have" before a word ending in "-ed". An irregular participle passes it, so
"once the rebuttal turn has run" reached a new docstring with no hit. The
Spec seat on #1252 probed "has gone" too, and it passed.

The follow-up `SA-0412` (#1252) fixed the one docstring. Its witness,
`tests/test_session.py::test_the_host_survivor_cells_own_docstring_takes_no_perfect_tense`,
holds that docstring with a private copy of the rule. Four older lines in
`tests/test_session.py` say "has run" or "had run" and pass the gate.

## Done looks like

`PERFECT` matches "has", "have" or "had" before a common irregular
participle, measured against the corpus of new text first. The `SA-0412`
witness is deleted, since the gate then holds the rule.

## Record

- 2026-11-17: filed from the spec loop's run 78.
