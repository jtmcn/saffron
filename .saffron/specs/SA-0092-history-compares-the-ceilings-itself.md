---
id: SA-0092
title: check 4 asks a spec review to judge ceilings against history rows by eye, and it read them wrong in both directions
type: bug
priority: 3
touches:
  - .claude/skills/run-saffron-spec-loop/driver.py
  - tests/test_spec_loop_driver.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/**
  - .claude/agents/**
  - .claude/skills/run-saffron-spec-loop/SKILL.md
budget_usd: 12
max_attempts: 3
max_turns: 80
risk: standard
acceptance:
  - claim: >-
      `history` ends with a `ceilings:` line of its own, comparing the target
      spec's `max_turns` with the highest `peak` among the rows it printed, and
      its `budget_usd` with the highest plan plus implement plus repair total
      among them. The line says which row each number came from and whether the
      ceiling is above or below it, by how much. Today `history` prints the
      target's ceilings in its header and the rows below it, and nothing
      compares the two.
    witness: tests/test_spec_loop_driver.py::test_history_compares_the_targets_ceilings_with_the_rows_it_printed
  - claim: >-
      A row whose attempt ended `error_max_turns` was cut off at its own
      ceiling, so the `ceilings:` line names its peak as a floor on what that
      cell needed rather than as what it used.
    witness: tests/test_spec_loop_driver.py::test_the_ceilings_line_calls_a_cut_off_rows_peak_a_floor
  - claim: >-
      Each past cell's own line, and the header, carry the same fields they
      carry today.
    witness: tests/test_spec_loop_driver.py::test_history_splits_a_cells_spend_by_phase_and_names_how_attempts_ended
    preserves: true
---

## Context

Backlog item 123. The spec review's 2026-09-14 backtest
(`docs/evidence/2026-09-14-spec-reviewer-backtest.md`) failed its promotion bar,
and check 4 — ceilings against history — was wrong in both directions. It
missed every recorded ceilings defect: `SA-0031` (`EXHAUSTED` at 141 of 140
turns) and `SA-0087@24edb32` (60 turns against a 47-turn plan checkpoint) both
read `checked`, and `SA-0059`'s finding blamed a cause the record rejects. It
also raised two blockers the cells contradicted: `SA-0060` and `SA-0027` each
finished inside the ceilings it called too low. Those two are among the five
false blockers the operator ruled on, which is what failed the bar.

The check asks a model to compare numbers by eye across up to twelve rows.
`history` already computes every number the comparison needs: the header holds
the target's `max_turns` and `budget_usd`, and each row holds `peak` and the
per-phase spend. Nothing subtracts them, so the reviewer re-derives the
comparison in prose each time, and the backtest measured how that goes.

## Problem

`history` prints the target's ceilings and the rows to judge them against, and
never compares them.

## Out of scope

**Check 4's own wording in `.claude/agents/spec-reviewer.md`.** Once the line
exists, what the check should say about it is prose, and no test can watch a
prompt. It is the by-hand half of item 123 and is `forbidden` here.

**Check 3's "witness already green at base" blockers** (item 124) and **the
backtest's own method** (item 125, and how to measure the spec review again,
filed in #268). Neither is this change.

**Which rows `history` prints, and their order.** The closest-shape ranking and
the `--before` blindness are as they are.

## Notes for the agent

**Three criteria, two witnesses and no mutants, plus one `preserves`.** The
comparison is new code, so no text exists at base that a mutant could pin
honestly, and `witness` reports `skip` for the first two. That is expected; see
the same shape in `SA-0091`. The third names a test that exists today and must
stay green.

**`_spend` already returns a `Spend(turns, usd)`**, and `PastCell` carries
`peak_turns`, `plan`, `implement` and `repair`. The pre-REVIEW total the second
number compares against is plan plus implement plus repair, which is what check
4 asks for and what the budget must cover before REVIEW spends anything.

**`max_turns` bounds one session, not their sum.** That is why the comparison
is against `peak`, the largest single attempt, and not against any total. A row
that ended `error_max_turns` hit its own ceiling, so its peak is a floor: the
cell needed at least that and may have needed more.

**A spec of a shape with no rows still gets a line.** When `history` prints no
rows, say so rather than printing a comparison against nothing.

**Four existing assertions in `tests/test_spec_loop_driver.py` read the
history output exactly, and an appended line breaks them.** The no-rows
case asserts the output carries nothing after the header — the opposite of
what the note above requires — and three more read the first token of each
line. All four are inside `touches`, so update them: criterion 3's
`preserves` is about the fields each row and the header carry, not about
leaving these tests alone.

**The tests load the driver by path** (`importlib`, top of
`tests/test_spec_loop_driver.py`), and the history tests build a ledger with
`_ledger_with_one_cell` and specs with `_spec`. Put the new tests beside them
and use those helpers. `uv run pytest tests/test_spec_loop_driver.py` runs the
file.

**Both new witnesses must fail with `driver.py` reverted.** Reverted, there is
no `ceilings:` line at all, so an honest test of either criterion fails. Import
nothing new at module scope: a module-scope import of a name you add turns the
reverted run into a collection error, which `revert` reads as `skip`.

**This spec edits a file the cell's own agent may also read.**
`.claude/skills/run-saffron-spec-loop/driver.py` is part of a skill in this
repo. Edit it as ordinary source; do not run the spec loop, and do not rely on
anything the skill says at run time.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included, and this change is well inside that.
