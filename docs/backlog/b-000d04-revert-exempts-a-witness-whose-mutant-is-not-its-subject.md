---
id: b-000d04
title: "`revert` reads a mutant's file as its claim's subject, so a mutant pointed elsewhere exempts a witness of code the diff changed"
status: open
tier: 1
filed: 2026-10-13
specs: [SA-0291]
prs: []
commits: []
cites: [§5.4, §5.4.1]
related: [84, b-02d328]
---

## Problem

Found in the second spec chain run of 2026-10-12, on `SA-0286`'s second
review.

`revert` sets aside a witness whose `mutant.file` lies outside the diff's
source (`saffron/gates/core/revert.py:195-216`). Item 84 built that rule, and
it is right for item 84's case. `SA-0064`'s new test checked a predicate in a
file the spec forbade. Reverting the diff's source could not make it fail, so
"theater" was the wrong verdict.

The rule reads `mutant.file` as the subject the claim is about. A spec can
break that reading. `SA-0286`'s witnesses read two prompts the diff changed.
Its mutants pointed one `LENSES` entry in `saffron/phases/review.py`, a file
the spec forbade, at another prompt. `revert` dropped both witnesses, and only
the `witness` gate checked them. That gate was advisory at `standard` before
`SA-0288`.

The mutant is the weaker check. A witness that asserted only the five base
bullets still killed `SA-0286`'s first mutant, yet passed with the prompts
reverted. `revert` exists to catch that witness.

`docs/agents/issue-tracker.md:137-141` invites the shape. It tells a writer to
list a mutant's file under `forbidden`, and says nothing of what that costs.
`SA-0191`, `SA-0195` and `SA-0247` merged with mutants in `review.py` while
their witnesses read changed files.

## Done looks like

- A criterion can declare `subject:`, a path, when its mutant's file is not
  the code its claim is about. Intake refuses `subject:` on a criterion with
  no mutant.
- `revert` sets a witness aside only when its mutant's file and its declared
  subject both lie outside the diff's source. A declared subject can only
  remove an exemption, never add one.
- A test drives a witness whose mutant sits in an untouched file and whose
  declared subject the diff changed, and asserts `revert` judges it.
- `issue-tracker.md` says when to declare `subject:`. `driver.py check` names
  a criterion whose mutant file lies outside `touches` with no `subject:`.
  Both land by hand.

## Record

- 2026-10-13: filed by the operator's delegate. The operator chose the
  declared field over running exempt witnesses or a rule alone.
- 2026-10-13: specced as `SA-0291`, the declared field and the narrowed
  rule. `issue-tracker.md` and `DESIGN.md` §5.4 changed by hand in the
  spec's own commit. The glossary entry is b-cd1566, and the `driver.py
  check` warning lands by hand after the cell.
