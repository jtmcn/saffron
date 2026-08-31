---
id: SA-0010
title: REBUT measures the fix nobody committed and hands it to no page
type: bug
priority: 2
touches:
  - saffron/phases/rebut.py
  - saffron/report/index.py
  - saffron/phases/package.py
  - tests/test_rebut.py
  - tests/test_report.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - docs/**
  - saffron/phases/review.py
  - saffron/cell/session.py
budget_usd: 8
max_attempts: 4
max_turns: 80
risk: elevated
---

## Context
`rebut_state` computes `claimed and not moved` at `rebut.py:331` and spends it on
a parenthetical in the `why` string: *"(a fix was claimed for some of them and no
commit was made)"*. That string reaches the ledger and stops there. `QueueLine.note`
carries packaging failures — conflicts, credential leaks, rebase failures — and
never the rebuttal's, so **no page has ever rendered this measurement**.

`SA-0008` landed §6's level 3 and left this beside it. §6 now says a confirmed
blocker answered with an uncommitted fix ranks *with* a sustained one and is not
counted *as* one, and nothing implements that sentence.

## Problem
The task is `READY_FOR_REVIEW` and the page ranks it on `sustained`, which counts
`confirmed ∧ argued` only. A blocker the critic confirmed, whose only answer was a
fix the implementer never committed, contributes **nothing** to that count.

The ordering survives this, and the spec is not asking you to change it: in the
mixed case an argued blocker carries the line into `_SUSTAINED` anyway, and when
*every* answer is an uncommitted fix `rebut_state` returns `REBUTTING`, which
`_STATE_RANK` already ranks. **What is wrong is the number, not the order** — the
page shows a count of live blockers that is lower than the number of live
blockers, on the one row it most wants you to read.

**The obvious version of this is wrong in the same way `SA-0008`'s was.** Folding
these into `sustained` would make one number mean two failures: an argument the
critic defeated, and a promise nobody kept. Those are not the same thing and §6 is
explicit that they get different words. `sustained_blockers` is correct and stays
correct — the new rule is a new function, exactly as it was last time.

## Acceptance criteria
- [ ] `rebut.py` exposes one function returning the count of confirmed blockers
      whose first-answer action is `fixed` **and** whose `RebutResult.moved` is
      `False`, paired on the shared 1-based blocker number
- [ ] It de-dupes a repeated `finding` **first-answer-wins**, the way
      `sustained_blockers` and `session.py:1062` both do — not last-wins, and not
      membership over every entry
- [ ] It returns `0` when `rebut_result` is `None`, when the rebuttal turn errored,
      when `moved` is `True`, and when a blocker was verdicted but never rebutted
- [ ] `QueueLine` carries the count and `_row` renders it in a cell whose wording
      is distinct from both `sustained` and `concerns`
- [ ] `sort_key` puts a non-zero count in the **existing** `_SUSTAINED` bucket —
      no new rank constant, no renumbering of `_ELEVATED` or `_ORDINARY` — and
      tiebreaks below `sustained` within it
- [ ] `package.py` supplies the count from `outcome.rebut_result`, and the test for
      it asserts **at `package.package`** by reading the value back out of
      `queue.json`, never by constructing a `QueueLine` and asserting on the value
      it was handed
- [ ] A test that a line with one unkept fix and `0` concerns sorts above a green
      `elevated` line, and below a line with one sustained blocker

## Out of scope
`sustained_blockers` is correct. Do not widen it, do not fold the two counts
together, and do not renumber the rank constants `SA-0008` just settled — §6 puts
this signal in level 3's bucket precisely so nothing has to move.

`saffron/cell/session.py` is forbidden for the third spec running, for the same
reason: it is a correct producer. `RebutResult` already carries `moved`,
`rebuttal` and `verdicts`, so the condition is derivable host-side from the object
you are handed. If you find yourself editing the producer, you have taken the
wrong turn.

`DESIGN.md` §6 is the specification being implemented and was amended before this
spec was written. If the code cannot match it, that is a finding to report.

## Notes for the agent
**`moved` is one bit for the whole rebuttal, not per blocker.** A task whose HEAD
moved cannot be attributed — you cannot tell which claimed fix the commit was for.
§6 names this and calls the count a floor: when `moved` is `True`, return `0`.
Do not invent a per-blocker attribution the phase cannot make. Mark the ceiling
with a `ponytail:` comment.

**The numbering is global, not per-lens** (`rebut.py:374`, `enumerate(blockers, 1)`).
A `Verdict` and a `Rebuttal` pair on one shared index across all lenses. Do not
compute per lens and sum. `sustained_blockers` directly above you is the shape to
copy.

**Only anchored blockers reach REBUT** (`review.py:231`, §5.5). An unanchored
blocker has no verdict and no rebuttal and must not be counted or crashed on.

**`QueueLine` is constructed by a test factory** (`tests/test_report.py:194`,
`QueueLine(**{**defaults, **overrides})`). A field without a default breaks every
test in that file at once. The dataclass ends with defaulted fields; the new one
goes after them, beside `sustained`.

**The trap this repository has now fallen into six times** (`docs/BACKLOG.md` item
18): a value computed, carried, and read by nobody, with a test that passes because
it hands the function the argument it then asserts on. This spec exists *because*
`rebut_state` measured something no page read. Do not fix that by adding a second
unread measurement. **The assertion that matters belongs at the caller.**

Commit after each coherent step. Uncommitted work dies with the cell.
