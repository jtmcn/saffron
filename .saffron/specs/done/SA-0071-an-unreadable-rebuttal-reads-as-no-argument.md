---
id: SA-0071
title: a rebuttal turn that recorded nothing renders in the pull request as an implementer who declined to argue
type: bug
priority: 2
depends_on: []
touches:
  - saffron/report/pr_body.py
  - tests/test_report.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 60
risk: standard
acceptance:
  - claim: >-
      When `RebutResult.rebuttal.error` is set, every blocker's implementer cell
      in the Disagreements table says, in fixed words, that no rebuttal was
      recorded and points at `rebuttal.json`. It does not show `—`, and it never
      shows the error's own text. And only then: a turn that was read, whether
      it answered some blockers or returned an empty list, still renders `—` for
      each blocker it did not answer. Today every case is the same dash, and
      beside a critic verdict of "confirmed: the implementer offered no
      argument" the dash reads as agreeing with it.
    witness: tests/test_report.py::test_a_rebuttal_turn_that_recorded_nothing_is_not_rendered_as_no_answer
  - claim: >-
      The row says whether that turn moved HEAD. `rebuttal.json` already
      records it, but the body is what gets read. A turn that recorded no
      rebuttal and moved HEAD may have fixed the blocker, so the reader needs to
      know to look at the diff before believing the verdict.
    witness: tests/test_report.py::test_a_rebuttal_turn_that_recorded_nothing_says_whether_it_moved_head
  - claim: >-
      Each row still carries its own blocker's rebuttal and verdict.
    witness: tests/test_report.py::test_disagreement_rows_attribute_the_right_rebuttal_to_the_right_blocker
    preserves: true
  - claim: >-
      A duplicated finding still shows its first answer.
    witness: tests/test_report.py::test_the_disagreements_table_shows_the_first_answer_to_a_duplicated_finding
    preserves: true
---

## Context

`docs/BACKLOG.md` item **42**, measured 2026-09-01 on `SA-0040` (PR #93):

```
REBUT: 0 rebuttal(s), HEAD moved, not the schema: Illegal trailing comma
       before end of object: line 6 column 1116 (char 1186)
```

The turn cost $2.59, edited the branch, and conceded one of two blockers. The
critic correctly marked that one `withdrawn`. The trailing comma destroyed the
turn's *arguments*. On the other blocker the critic then wrote `confirmed: The
implementer offered no argument and made no visible change`, and that was false:
there was an argument, and nothing survived to say so.

`RebuttalTurn.error`'s own docstring promises the distinction: it is set when no
rebuttal was recorded, "never the same value as 'argued nothing'". It is set in
two cases, output that was not the schema and a turn that failed outright, and
both mean the same thing for the table: nothing the implementer said reached the
record. `rebuttal.json` keeps the distinction, carrying both the error and
`head_moved`. The pull request body breaks it. `_disagreements` builds its
answers from `first_answers(rebut_result.rebuttal)`, which is empty for an
errored turn, so every blocker renders `—` exactly as if the implementer had
nothing to say.

## Problem

The operator inherits a pull request body asserting a confirmed disagreement
that nobody actually had. The body is what gets read, and "HEAD already says
what it did" is true only for a reader who re-reads the diff against every
finding.

## Out of scope

**Re-prompting a malformed rebuttal.** Whether one is worth a second turn is a
separate question from whether the record should imply an answer that was never
read. `saffron/phases/**` is forbidden for that reason.

**The ledger and the queue's counts.** They cannot tell an errored turn from
an unanswered blocker either: the ledger writes no rebuttal for both, and
`sustained_blockers` counts both as zero. Only `rebuttal.json` tells them
apart. That is a separate item, filed on backlog item 42, and not this spec's.

**The critic's verdict text.** The lens wrote what it saw. This spec makes the
row beside it honest, not the verdict.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** The branch that tells the cases apart does not exist yet.

**Every new witness must fail with `pr_body.py` reverted, not merely be missing
at base.** The `revert` gate re-runs each new witness against the reverted
source and blocks any that still pass. Both new criteria assert words base
never renders, so an honest test fails reverted. Import new names inside tests,
not at module scope. A module-scope import of a name you add makes the reverted
run a collection error, which `revert` reads as `skip`.

**Key on `error`, not on an empty list.** `RebuttalTurn(rebuttals=[])` with no
error is a turn that was read and chose to answer nothing, and it must keep its
dashes. Checking "no rebuttals" instead of `error` marks it as recording nothing.

**One body per turn, so the first criterion's test renders several.** A body
renders one `RebutResult`, and one turn either errored or was read. Render at
least three in the same test: an errored turn, a read turn that answered
blocker 1 and not blocker 2, and a read turn that returned an empty list. Give
the errored turn a hostile error string, such as `SA-0040`'s trailing-comma
message with a `|` and an `@name` in it, and assert that none of it reaches the
body. The error can quote model output, and the body is a channel to GitHub.

**A turn that recorded nothing and did not move HEAD never reaches a packaged
body today.** With no argument and no commit, REBUT stops at `REBUTTING`, and
only `READY_FOR_REVIEW` is packaged. Render that case anyway, since the renderer
should not assume its caller, but do not claim in a docstring that it happens.
