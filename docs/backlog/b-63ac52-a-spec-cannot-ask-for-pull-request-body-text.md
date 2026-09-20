---
id: b-63ac52
title: A spec cannot ask for pull request body text, and nothing tells its author so
status: open
tier: 2
filed: 2026-09-18
specs: [SA-0099, SA-0111]
prs: []
commits: []
cites: [§5.7]
related: [153]
---

## Problem

Found in the spec loop's run 7, 2026-09-18, reviewing #338 (`SA-0099`).

`SA-0099`'s spec asks the pull request body to say two things. The column is
sourced from the baseline suite. And preflight parses a gate set and drops it.

PACKAGE renders the body from the ledger and the spec (§5.7,
`saffron/report/pr_body.py`). The cell writes none of it. Its one channel is
the implementer's notes, rendered under "Notes from the implementer" as
unadjudicated text and clipped at 4,000 characters (`saffron/report/pr_body.py:571`).
No gate reads the notes, and no witness can check them.

In #338 the notes named the gate-set drop. They did not say the column is
sourced from the baseline suite. Nothing flagged the gap, and the next spec
still has to guess.

## Done looks like

`docs/agents/` or the spec review's rubric says a spec cannot require body
text. A fact a later spec must know goes in the spec's own record, or in a
backlog item, instead. Optional: the spec review flags a spec that asks for
body text.

## Record

- 2026-09-18: filed from the spec loop's run 7 (stack #335 ← #338 ← #339 ←
  #342 ← #340). Surfaced by #338.
- 2026-09-19: a second sighting, in the spec loop's run 10 (#381). `SA-0111`'s
  Out of scope asked the body for three statements: why §4.2.1 allows a column
  nothing reads, what `SA-0099`'s precedent does and does not settle, and that
  `tests/test_ledger.py:802-826` is narrower than its name. None arrived. This
  time the implementer's notes assert the opposite. They say "I did read
  `DESIGN.md` §4.2.1 and `SA-0099` ... to justify the column in the PR body
  language", describing language the body does not contain. So the cell
  believes it complied, which hides the gap from the one channel that has it. The
  delegate wrote the three paragraphs into #381 by hand.
