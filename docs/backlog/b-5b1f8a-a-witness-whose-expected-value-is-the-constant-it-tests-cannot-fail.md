---
id: b-5b1f8a
title: A witness whose expected value is the constant it tests cannot fail, and no gate or lens flags it
status: partial
tier: 1
filed: 2026-09-29
closed:
specs: [SA-0195]
prs: [600]
commits: []
cites: [§5.4.1, §5.5]
related: [b-2750d5, b-78ccc7, b-7e69d0]
---

## Problem

Found in the spec loop's run 21, 2026-09-29, by both seats on #581
(`SA-0192`).

Criterion 2's witness compared `lens_prompt`'s output with
`review.NO_STANDING_INSTRUCTIONS` (`tests/test_review.py:585-587` at
`07e0ad21`). That is the constant under test. Any wording passes. Four wrong
wordings survived, one of them inserting "Read /work/CLAUDE.md".

The in-cell adequacy lens passed the witness. Review commit `d2ea4afe`
replaced the constant with a literal.

## Done looks like

- A `structure` rule flags a witness that asserts a module attribute against
  the output built from it. It ships with the `SA-0192` shape as its mutant.
- Or `witness` applies a wrong value to the constant and reads the witness
  still passing.
- The adequacy prompt names the shape.

## Record

- 2026-09-29: filed from the spec loop's run 21.
- 2026-09-29: `SA-0195` (#600) made the adequacy prompt name the shape. No gate refuses it yet.
