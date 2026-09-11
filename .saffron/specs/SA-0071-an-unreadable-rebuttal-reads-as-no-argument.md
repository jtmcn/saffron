---
id: SA-0071
title: a rebuttal that could not be read renders in the pull request as an implementer who declined to argue
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
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: standard
acceptance:
  - claim: >-
      When the rebuttal turn recorded no rebuttal, every blocker's implementer
      cell in the Disagreements table says the rebuttal was unreadable, in fixed
      words, not `—`. And only then: a blocker that a turn which was read simply
      did not answer still renders `—`. Today the two are the same dash, and
      beside a critic verdict of "confirmed: the implementer offered no
      argument" the dash reads as agreeing with it.
    witness: tests/test_report.py::test_an_unreadable_rebuttal_is_not_rendered_as_no_answer
  - claim: >-
      The row says whether that turn moved HEAD. `rebuttal.json` already
      records it, but the body is what gets read. An unreadable rebuttal from a
      turn that moved HEAD may have fixed the blocker, so the reader needs to
      know to look at the diff before believing the verdict.
    witness: tests/test_report.py::test_an_unreadable_rebuttal_says_whether_the_turn_moved_head
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

`RebuttalTurn.error`'s own docstring promises the distinction: set when no
rebuttal was recorded, "never the same value as 'argued nothing'". The record
keeps that promise. `rebuttal.json` carries the error and `head_moved`, and
`sustained_blockers` already counts an errored turn as zero. The pull request
body breaks it. `_disagreements` builds its answers from
`first_answers(rebut_result.rebuttal)`, which is empty for an errored turn, so
every blocker renders `—` exactly as if the implementer had nothing to say.

## Problem

The operator inherits a pull request body asserting a confirmed disagreement
that nobody actually had. The body is what gets read, and "HEAD already says
what it did" is true only for a reader who re-reads the diff against every
finding.

## Out of scope

**Re-prompting a malformed rebuttal.** Whether one is worth a second turn is a
separate question from whether the record should imply an answer that was never
read. `saffron/phases/**` is forbidden for that reason.

**The record.** `rebuttal.json`, the ledger and the queue's counts already tell
an errored turn from an empty one. Only the body is wrong.

**The critic's verdict text.** The lens wrote what it saw. This spec makes the
row beside it honest, not the verdict.

## Notes for the agent

**This spec creates new code, so its new criteria carry witnesses and no
mutants.** The branch that tells the two cases apart does not exist yet.

**Fixed words, never the error text.** `RebuttalTurn.error` can quote model
output, since a validation error echoes the input it rejected. The body is a
channel to GitHub. The full error already lives in `rebuttal.json`, so the body
needs only enough to send the reader there. Assert in the first criterion's test
that the error string does not appear in the body.

**The "only then" half is the one that can regress quietly.** The easy
implementation keys on "no rebuttal for this finding" and marks every
unanswered blocker unreadable, including on a turn that was read. The first
criterion's test has to cover both cases in the same body, or that mistake
passes.
