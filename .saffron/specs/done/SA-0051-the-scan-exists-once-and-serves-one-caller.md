---
id: SA-0051
title: the scan is resolved inside the command that prints it, so a second caller must copy it
type: refactor
priority: 1
depends_on:
  - SA-0050
touches:
  - saffron/cli.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/batch.py
  - saffron/watch.py
  - saffron/events.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
acceptance:
  - claim: >-
      Resolving a repo's queue is one function, separate from printing it. It
      does what the attended command does today and in the same order: the
      mirror, the pinned base, the reconcile, the slug, the export, and the
      scan over that export — never the working copy, which is what makes an
      unpushed spec a draft rather than tonight's work.
    witness: tests/test_cli.py::test_resolving_a_queue_is_one_function_over_the_pinned_base
  - claim: >-
      Whether the scan stamps an in-flight task is a required argument, given
      at the call site rather than defaulted. The two callers this exists for
      disagree about it, and a default would decide for whichever one forgets:
      one batch runs at a time, so a batch may treat an in-flight row as a
      corpse, and an operator looking at the queue mid-phase may not.
    witness: tests/test_cli.py::test_the_stamping_premise_is_a_required_argument
  - claim: >-
      Told to stamp, it stamps: a task left in an in-flight state is recorded
      orphaned and re-queues by the ordinary rule. Nothing calls it this way
      yet — the command that will is the next spec — so this witness drives
      the function directly, which is how the argument gets a test before it
      gets a caller.
    witness: tests/test_cli.py::test_told_to_stamp_it_orphans_an_in_flight_task_and_re_queues_it
  - claim: >-
      Told not to stamp, it leaves an in-flight task exactly as it found it.
      This is the existing behaviour of the attended command and the reason
      the argument exists rather than a constant.
    witness: tests/test_cli.py::test_told_not_to_stamp_it_leaves_an_in_flight_task_alone
  - claim: >-
      The attended command prints what it printed before — the candidates, the
      refusals, the reconcile summary, and the two lines that say a slug or a
      policy could not be read. Asserted against the current output rather
      than against the fact that output happened, because this is what an
      operator reads before trusting a night.
    witness: tests/test_cli.py::test_the_printed_queue_is_unchanged_by_the_extraction
  - claim: >-
      Looking at the queue still never stamps anything, driven through the
      command rather than the function. The existing guarantee, re-asserted at
      the level where it could regress: the extraction is what puts a stamping
      switch within reach of this path for the first time.
    witness: tests/test_cli.py::test_looking_at_the_queue_still_never_stamps_a_corpse
---

## Context

`saffron queue` resolves a repo's queue and prints it, in one function. The
resolving half is what a batch needs and the printing half is not, and the
resolving half reaches four helpers private to this module.

**This spec exists because the one that tried to do it all was refused.** The
first `SA-0051` asked for the extraction, the `saffron batch` command, its four
exit codes and the adapter that turns a candidate into a cell — three
mechanisms. The agent planned it honestly at 650 changed lines, and the plan
checkpoint refused it against the 600-line ceiling before an edit was made,
at $1.80. This half is the extraction alone.

## Problem

- **A second caller has to copy it.** The mirror, the pinned base, the
  reconcile, the slug, the export and the scan are one sequence inside a
  function whose other job is printing. Copied, the two drift, and a night
  stops matching what the operator was shown before trusting it.
- **The two callers disagree about one thing, and nothing expresses it.**
  §4.2.1 requires the batch scan to record an in-flight task as orphaned
  before filtering; this command's own docstring says it must never do that,
  because an operator can run it mid-phase. Today that difference is the
  absence of an argument, which is not a difference a second caller can see.

## Out of scope

**The command.** No new subcommand, no new flag. `SA-0054` adds
`saffron batch` and is the second caller this extraction is for.

**The adapter.** Turning a candidate into a cell needs this module's ceilings
and stacking resolvers, and it is `SA-0054`'s.

**Changing what the scan decides.** `saffron/scheduler.py` is `forbidden`.
Every refusal, the sort, and the filter stay exactly as they are; this moves
where the call is made from, not what it answers.

**Changing what the attended command prints.** A single character of different
output means the extraction went wrong.

## Notes for the agent

**Read `_queue`'s docstring before moving anything.** It states the guarantee
this spec must preserve in the words the repo uses for it — the scan is not a
batch scan, an operator can run it at will, mid-phase included. That sentence
is the whole reason the stamping argument is required rather than defaulted.

**Required, not defaulted, and not a keyword with a sensible value.** A
default here decides the premise for whichever caller forgets to think about
it, and the caller that forgets is the unattended one running at 03:00. Make
it impossible to call without saying which scan this is.

**Everything the resolve needs is already in this module.** The protected
paths, the retirement markers and the guarded `gh` runner are private helpers
here, and they stay private — this is not an invitation to move them anywhere
else. `saffron/scheduler.py` and `saffron/reconcile.py` are `forbidden`, so
the extraction is a rearrangement inside one file.

**Return what both callers need, not just what the printer needs.** The
printing path uses the candidates, the refusals, the reconcile summary, the
export directory and the two "could not read" lists. A batch also needs the
mirror, the pinned base and the repo id, and it is cheaper to return them now
than to have `SA-0054` re-derive them from a function that already had them.

**The third witness has no caller and that is deliberate.** `SA-0054` is the
first. Do not add one: this spec's `touches` covers `cli.py`, so a new
subcommand would pass `scope` and then fail the review that reads this
section — and `SA-0054` would arrive to find its own work half done in a
shape it did not choose.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. Nothing here needs a container: `tests/conftest.py` already
blocks the cell runtime and `gh` at the subprocess boundary, and the existing
queue tests inject `gh`.

`type: refactor` because that is what this is — the behaviour of the attended
command is unchanged by construction, and the sixth witness says so. It also
sets the ceiling this spec is sized against.
