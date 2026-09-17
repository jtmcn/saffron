---
id: 153
title: The spec author's conventions cover one of the six checks the spec review runs, and the largest defect class has no rule at all
status: done
tier: 2
filed: 2026-09-16
closed: 2026-09-16
by_hand: true
specs: []
prs: [290]
commits: []
cites: []
related: [123, 145, 152]
---

## Problem

**Tier 2.** By hand: `docs/agents/issue-tracker.md` is the file, and
`.claude/agents/spec-reviewer.md` is where the two rules already exist in their
proven form. Both are outside what a cell can land.

`.claude/agents/spec-reviewer.md` runs six checks. `docs/agents/issue-tracker.md`,
which is what an author writes a spec from, covers **one** of them — check 3,
witness and mutant discipline, at length and hard-won. Checks 1, 2, 4, 5 and 6
have no counterpart in the authoring conventions: criteria against invariants,
scope reaching every caller, ceilings against `history`, size against the
ceiling, and claims about current code.

There is also no template. A spec is written by copying a recent one.

Measured on #290, three specs written 2026-09-16 and reviewed before any cell
ran. Classified by the reviewer's own six checks, the defects were:

- **Check 6, claims about current code — five**, the largest class and one of
  the two blockers. A pre-clean block described as identical in two functions
  when it differs by a network removal; one call site named where there are
  two; a test cited that does not exist; `§5.4` cited for a rule that lives at
  `§4.1`; a code comment quoted as saying something it does not say.
- **Check 3, witness discipline — two**, and the other blocker. Both the same
  shape: a witness that passes on a plausible wrong implementation.
- **Checks 1 and 2 — one each.**
- **Outside the six — four**, including a prescribed removal that would have
  deleted an operator's unrelated network.

The check-6 cluster is a sequencing failure, not a knowledge one. The author
read the code first, wrote three specs from memory of it, and verified no
sentence at the time of writing; the blocker among them was copied from item
140's own record, which was wrong, and propagated without being re-read against
the file. The reviewer is held to *"Every finding carries evidence you read: a
file:line at `base` and the quoted text"*. The author is held to nothing
equivalent.

The check-3 pair is **not** a documentation gap, and the record should say so:
`issue-tracker.md`'s witness bullets are extensive and were read — their rules
were quoted into all three specs' notes for the *agent's* future witnesses, and
never applied to the author's own criteria. What is missing is one technique the
reviewer has and the author does not: check 3 tells the reviewer to *"name a
plausible wrong implementation its witness would pass"*. Nothing tells the
author to construct that adversary. Both blockers die there.

## Done looks like

Two rules added to `docs/agents/issue-tracker.md`'s conventions, each lifted
from the reviewer's rubric because that is where it has already been proven:

1. **Every sentence in a spec that says what the code does now carries a
   `file:line` the author read while writing that sentence** — not earlier, and
   not from a backlog record's own words. This is check 6 moved upstream, and it
   costs ordering rather than effort.
2. **For each criterion, name the plausible wrong implementation its witness
   would pass, before declaring the witness.** If one exists, the witness is not
   yet a witness. This is check 3's technique, which the author's half of the
   same discipline never states.

Not a template: checks 4 and 5 were the two the author got right unprompted by
running `driver.py history`, and a skeleton would mostly duplicate the model
specs people already copy from. The gap is a verification discipline.

Two things this deliberately does not do. It does not weaken the spec review,
which worked: two blockers caught in about four minutes per spec, against $8–22
and an hour for the cell each would have cost. Moving two checks upstream is
redundancy, not replacement, and the thin author rubric is partly deliberate —
the review was built on 2026-09-14 to be the backstop
(`docs/superpowers/specs/2026-09-14-spec-reviewer-design.md`). And it adds no
citation gate: `tests/test_citations.py` already scans `.saffron/specs/` and
resolved the `§5.4` citation above without complaint, correctly, because §5.4
exists. A gate catches a dangling citation, never a misattributed one, so that
defect is review-or-nothing and nothing closes it.

## Record

**Filed 2026-09-16** from writing #290's three specs and reading their reviews.
Item **152** is the mechanically checkable part of the same measurement.

**2026-09-16, done, by hand.** Both rules are in `docs/agents/issue-tracker.md`'s
conventions, in the order an author meets them: name the wrong implementation
before declaring a witness (check 3's technique), and give every sentence about
current code a `file:line` read while writing it (check 6). The witness
bullets also point to item 152's test as the mechanical half. No template and no
new gate, for the reasons "Done looks like" gives.
