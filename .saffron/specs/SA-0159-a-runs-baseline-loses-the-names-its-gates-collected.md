---
id: SA-0159
title: A run's baseline loses the names its gates collected, so no host reader can tell which tests a diff added
type: bug
priority: 1
depends_on: [SA-0157]
touches:
  - saffron/ledger.py
  - tests/test_ledger.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/probe.py
  - saffron/end_review.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/**
  - tests/test_session.py
  - tests/test_ledger_fold_task.py
budget_usd: 15
max_attempts: 3
max_turns: 60
acceptance:
  - claim: >-
      `Ledger.baseline_results(run_id)` returns each result's `collected`
      as the run recorded it. A list of names comes back in its own order,
      an empty list as an empty list, and `None` as `None`. A ledger opened
      again on the same file returns the same.
    witness: tests/test_ledger.py::test_a_runs_baseline_keeps_the_names_each_gate_collected
  - claim: >-
      The `gate_results` table still carries exactly the columns §4.1
      lists.
    witness: tests/test_ledger.py::test_the_gate_results_table_carries_exactly_the_fields_4_1_names
    preserves: true
  - claim: >-
      An attempt's gate result is still recorded and read as before.
    witness: tests/test_ledger.py::test_a_task_result_belongs_to_an_attempt
    preserves: true
  - claim: >-
      A run's baseline result still keeps its gate and its failures.
    witness: tests/test_ledger.py::test_a_baseline_result_belongs_to_a_run
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 4 of its Done. It cites `DESIGN.md` §4.1.
`SA-0147` qualifies an end review's findings, and runs each finding's probe
under ADR 3's kill rule
(`docs/adr/0003-a-test-is-judged-by-an-edit-chosen-to-break-it.md:58-59`).
Only a failure of a test the diff adds kills a probe. `SA-0138` builds that
rule. Its `probe.added_tests(base, head)` reads the names the base's
`tests` result collected, and returns `None` when that `collected` is
`None`. A probe with a new failure then reads `unproven`. The in-cell path
holds its pre-turn suite in memory, so it has the names. `SA-0147` runs
after the cell is gone, and reads a layer's base from the ledger.

**This spec's tree base is `SA-0157`'s head.** Only `depends_on[0]` stacks
(`saffron/task.py:133-136`). The chain `SA-0142` to `SA-0157` edits
`saffron/ledger.py`, so find each name below by its name. Every line
number was read at `3699aeb8`.

**A run's baseline loses its names today.** Each cell makes its own run
(`saffron/cell/session.py:1689`). It takes the pre-turn suite on the
task's tree base (`:1745`) and records each result under the run
(`:1762-1763`). A result carries `collected`, the node ids its gate
enumerated, or `None` for a gate that does not enumerate
(`saffron/gates/contract.py:71`). `record_gate_result` writes a run's result
with no `collected` (`saffron/ledger.py:1205-1233`). A baseline result
names a run and is no task fact (`:1209`, item 177). `_results` builds each
`GateResult` with no `collected` (`:1274-1303`). So `baseline_results`
returns `collected=None` for every result.

**Why a table of its own.** `tests/test_ledger.py:665-682` pins the
columns of `gate_results` to §4.1's listing, and `DESIGN.md` is protected.
So the names cannot be a new column there.

**What it gains on its own.** A host reader can tell, from the ledger
alone, which tests a run's base collected. With a task's head suite, that
answers which tests its diff added, after its cell is torn down. The spec
loop's driver reads the ledger for a task's results, and can use it the
same way.

## Problem

`baseline_results` cannot say which tests existed at a run's base.

Add `baseline_collected` to `SCHEMA` in `saffron/ledger.py`, with
`gate_result_id INTEGER PRIMARY KEY` and `names TEXT NOT NULL`, and no
reference to another table. When `record_gate_result` writes a run's
result whose `collected` is not `None`, it writes one row in the same
transaction, the names as a JSON list. `_results` reads that row back into
`collected`, and a result with no row reads as `None`. An attempt's result
writes no row, and reads as it does today. The module docstring names the
tables the ledger holds, and `baseline_collected` joins them.

## Out of scope

- **An attempt's names.** An attempt's result is a `gate_result` fact, and
  the fold rebuilds it. Keeping its names is a record change, and no
  reader needs them yet.
- **A ledger written before this spec.** Its baselines have no rows, so
  they read as `None`, as they do today.
- **Reading the names.** `SA-0147` passes them to `SA-0138`'s
  `added_tests`.

## Notes for the agent

**Criterion 1 is new code.** No text at the tree base keeps a baseline's
names. So it declares a witness and no mutant, and `witness` reports `skip`
for it. Criteria 2 to 4 are `preserves` and name tests that pass
now.

**Criterion 1's witness** opens a `Ledger` with no record in `tmp_path`,
and creates one repo and one run. It records three results under the run,
in order: `tests` collecting `["t.py::b", "t.py::a"]`, `census` collecting
`[]`, and `lint` collecting `None`. `baseline_results` returns the three
`collected` values in that order. It opens a second `Ledger` on the same
file and asserts the same. These fail it, each measured:

- no names kept
- an empty list kept as `None`, or `None` kept as an empty list
- a result with no row read as an empty list
- the names sorted, or kept as a set

**How the list was measured.** A throwaway script ran on 2026-09-23 at
`3699aeb8`. It subclassed `Ledger` with the table and both methods, and
ran the witness above. The right build passed, and each wrong version
listed failed.

**What the witness leaves undriven.** A run recorded before the table
existed. `SCHEMA` runs on every open, so the table is created then, and
that run reads `None`.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`bug` ceiling of 1300 tokens (`saffron/gates/core/size.py:26`). A
prototype counted by `size_gate` itself came to 119, 69 in `ledger.py` and
50 in the test. Docstrings and comments bring it to about 200.
