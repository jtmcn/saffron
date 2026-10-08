---
id: SA-0221
title: A task-created fact files the default tier as declared, so the record cannot tell a spec that declared standard from one that declared nothing
type: feature
priority: 1
depends_on: [SA-0220]
estimated_lines: 205
estimate_measured: true
touches:
  - saffron/intake.py
  - saffron/cell/session.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/replay.py
  - tests/test_intake.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_cli.py
  - tests/test_replay.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/view/**
  - saffron/record/**
  - saffron/gates/**
  - saffron/report/**
  - saffron/ledger.py
  - saffron/projection.py
  - saffron/chain_walk.py
  - saffron/batch.py
  - tests/test_ledger.py
  - tests/test_ledger_appends.py
  - tests/test_ledger_fold_task.py
  - tests/test_fold.py
  - tests/test_view_graph.py
  - tests/test_view_server.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 32
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      `intake.Spec` gains a read-only `declared_risk`. It is the tier the
      frontmatter set, and `None` where it set none. `risk` still reads
      `standard` for a spec that set none, so the gate suite keeps a
      string. The witness parses four frontmatters and reads both fields
      from each. They are an omitted `risk:` key, an empty `risk:`,
      `risk: standard` and `risk: elevated`.
    witness: tests/test_intake.py::test_a_spec_declares_a_tier_only_where_its_frontmatter_sets_one
    wrong_versions:
      - The accessor returns `risk`, so an undeclared spec reads `standard`.
      - The accessor compares `risk` with its default, so a declared `standard` reads as none.
      - "`risk` becomes optional, so an undeclared spec hands the suite `None`."
  - claim: >-
      `run_task` hands `run_one_cell` a `CellSpec` whose new
      `declared_risk` field is the spec's `declared_risk`, and whose `risk`
      is still the spec's `risk`. The witness drives `run_task` over the
      same four frontmatters, parsed from text, and reads both fields off
      the `CellSpec` each call built.
    witness: tests/test_task.py::test_the_cell_spec_carries_the_tier_the_spec_declared_and_none_where_it_declared_none
    wrong_versions:
      - "`run_task` passes the spec's `risk` as the cell's declared tier."
      - "`run_task` leaves the cell's declared tier unset."
      - "`run_task` passes the declared tier as `risk`, so an undeclared spec hands the suite `None`."
  - claim: >-
      A cell that mints its own task files `CellSpec.declared_risk` as the
      `task_created` fact's `risk`, a null value included. The task's
      `tasks.risk` column reads `standard` where that value is null. The
      witness drives `run_one_cell` with a record-backed ledger three times.
      Each drive's `CellSpec` has `risk` `elevated` and a declared tier of
      `None`, `standard` or `elevated`.
    witness: tests/test_session.py::test_the_task_created_fact_carries_the_cells_declared_tier_and_null_where_none
    wrong_versions:
      - "`run_one_cell` files the cell's `risk` on the fact."
      - "`run_one_cell` files `standard` where the cell declares no tier."
      - The fold writes the fact's null tier into `tasks.risk`.
  - claim: >-
      A stack batch's `_stack_mint` files the candidate spec's
      `declared_risk` as the `task_created` fact's `risk`. The `tasks.risk`
      column reads `standard` where that value is null, in the live ledger
      and in a fresh ledger the record is folded into. The witness mints one
      task for each of the four frontmatters, parsed from text, on one
      record-backed ledger. It reads each fact and each live row, then folds
      the record into a fresh ledger and reads every folded row.
    witness: tests/test_cli.py::test_the_stack_mint_records_the_declared_tier_and_null_where_none
    wrong_versions:
      - "`_stack_mint` files the candidate's `risk` on the fact."
      - "`_stack_mint` files `standard` where the spec declares no tier."
      - The fold writes the fact's null tier into `tasks.risk`.
      - The fold writes `standard` into `tasks.risk` whatever the fact carries.
  - claim: >-
      `replay` files the spec's `declared_risk` as the `task_created`
      fact's `risk`. The `tasks.risk` column and the returned queue line's
      `risk` both read `standard` where that value is null. The witness
      replays one pull request four times, once for each of the four
      frontmatters, each on its own record-backed ledger.
    witness: tests/test_replay.py::test_a_replayed_task_records_the_declared_tier_and_null_where_none
    wrong_versions:
      - "`replay` files the spec's `risk` on the fact."
      - "`replay`'s queue line carries the declared tier, so an undeclared spec's line reads null."
      - The fold writes the fact's null tier into `tasks.risk`.
---

## Context

Backlog item **170**, which cites `DESIGN.md` §4.1, §4.4, §4.6 and §6. Its
design is `docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`.
This spec is the second of four for that design's step 3, the migration.
`SA-0220` is first and changes the gate-result fact. `SA-0222` and `SA-0223`
write the migration itself. The design's §7 says the declared tier "is written
where the spec declared a tier, and left absent otherwise". A fact a cell
writes today breaks that, so the migration would import the same ambiguity it
exists to remove.

Line numbers below were read at `66552540`.

**The fact already has room for a null.** `Ledger.create_task`
(`saffron/ledger.py:1272-1319`) takes `risk: str | None = None`. Its
docstring says `None` "means the spec declared no tier"
(`saffron/ledger.py:1290-1292`). The payload files it as given, as
`"risk": declared_risk` (`saffron/ledger.py:1312`). The fold's `task_created`
branch writes `standard` into `tasks.risk` where that value is null
(`saffron/ledger.py:669`). The column is `NOT NULL DEFAULT 'standard'`
(`saffron/ledger.py:128`).

**No caller ever passes `None`.** `intake.Spec.risk` defaults to
`standard`, and its `ponytail:` says so (`saffron/intake.py:197-199`). Each
caller of `create_task` passes that string:

- The cell passes `risk=spec.risk` at `saffron/cell/session.py:1968`.
  `CellSpec` declares `risk: str = "standard"` (`saffron/cell/session.py:323`).
  `run_task` copies it from the spec as `risk=spec.risk` (`saffron/task.py:543`).
- A stack batch's mint passes `risk=candidate.spec.risk` (`saffron/cli.py:1056`).
- `replay` passes `risk=spec.risk` (`saffron/replay.py:60`).

**An empty `risk:` is already no declaration.** Its parse drops every
frontmatter key whose value is null, with `if v is not None`
(`saffron/intake.py:264`). So an empty
`risk:` and an omitted one reach `Spec` alike.

**The suite needs the string.** `GateSuite._run` computes the effective tier
with `effective_risk(spec.risk, ...)` (`saffron/gates/suite.py:145`). The plan
checkpoint reads `spec.risk` too (`saffron/cell/session.py:644`). Both keep
reading `risk`, unchanged.

## Problem

1. **The accessor.** Add a `declared_risk` property to `intake.Spec`. It is
   `risk` where `risk` is in the model's set fields, and `None` otherwise.
   Replace the `ponytail:` at `saffron/intake.py:197-198` with a comment
   naming the accessor. `risk` and its default stay as they are.
2. **The cell.** Add `declared_risk: str | None = None` to `CellSpec`, beside
   `risk`. `run_task` sets it from the spec in its `cell_spec = CellSpec(`
   call (`saffron/task.py:533-548`).
   The `create_task` call at `saffron/cell/session.py:1968` passes it in
   place of `spec.risk`.
3. **The other two callers.** `risk=candidate.spec.risk`
   (`saffron/cli.py:1056`) and `risk=spec.risk` (`saffron/replay.py:60`)
   pass the spec's `declared_risk` instead.
4. **The test this changes.**
   `tests/test_session.py::test_the_task_is_recorded_with_the_specs_declared_risk`
   (`tests/test_session.py:3177-3190`) builds its `CellSpec` with
   `risk="elevated"` alone, and asserts the column reads `elevated`. With
   the new field's `None` default, the column reads `standard`. Give it
   `declared_risk="elevated"` as well.

## Out of scope

- `tasks.risk` keeps `NOT NULL DEFAULT 'standard'`, and the fold keeps writing
  `standard` for a null tier (`saffron/ledger.py:669`). The record tells a
  declared `standard` from no declaration. The column is the defaulted value
  its readers expect. The operator chose this so the view needs no change.
  `saffron/view/graph.py:205-208` leaves out a task whose `risk` names no
  tier in the shapes.
- Every other reader of a tier keeps `risk`. The queue's live row keeps
  `risk=spec.risk` (`saffron/task.py:578`), and so does `replay`'s queue line
  (`saffron/replay.py:138`).
  The gate suite and the plan checkpoint keep it as well. So does PACKAGE's
  PR body, which reads the effective tier or `spec.risk`
  (`saffron/report/pr_body.py:104`).
- `docs/evidence/scripts/2026-08-25-queue-from-ledger.py:128` escapes a
  task's `risk` read from the column. The column is never null, so this
  change cannot reach it.
- The earned tier is `SA-0220`'s. The migration is `SA-0222`'s and
  `SA-0223`'s.
- `DESIGN.md` §4.1 gains one sentence by hand in this spec's pull request,
  since `DESIGN.md` is protected.

## Notes for the agent

**New code at existing call sites.** The accessor and the field are new.
No text at base fixes how a caller spells either. So
each criterion declares a witness and no mutant, and the `witness` gate
reports `skip` for all five. The wrong versions under each criterion are
what its witness must kill. Do not run them yourself.

**Commit as each witness passes.** Five witnesses, five commits at least.

**Every witness must fail with the source reverted.** Import nothing at
module scope that this change adds. `MemoryRecord` and `fold` exist at base,
so either import is safe.

**Read a fact from the record.** Construct the ledger as
`Ledger(path, record=MemoryRecord())`. `ledger.record_key(task_id)` names the
task's key, and the record's `read` returns its facts in order. Take the one
whose `kind` is `task_created`.

**Criterion 1.** Build each frontmatter from one shared head, adding nothing,
`risk:`, `risk: standard` or `risk: elevated`. Assert `declared_risk` and
`risk` on each.

**Criterion 2.** Copy the shape of
`tests/test_task.py::test_a_handoff_replaces_the_stacking_resolver`. Stub
`run_one_cell` to keep the `CellSpec` it is given, and stub
`package_phase.package`. Pass `handoff=Handoff(stacked_on=None,
target_branch=None)`, so nothing resolves a parent. Give each call its own
ledger file.

**Criterion 3.** Give `_drive` in `tests/test_session.py` a `record`
keyword, `None` by default, that it passes to the `Ledger` it builds
(`tests/test_session.py:1466`). Give each drive its own directory under
`tmp_path`. Use `_stub_the_runtime` and the two turns the test above it
uses. Set `risk="elevated"` on every drive, so a write of `risk` shows as
`elevated` where the declared tier is `None`.

**Criterion 4.** Use `cli._stack_mint` as
`tests/test_cli.py::test_the_stack_mint_opens_a_run_at_the_pinned_base_and_a_task_per_call`
does. Parse each spec from text with its own id, so the folded rows map one
to one by `spec_id`. Fold with `saffron.record.fold.fold(record, into)`.

**Criterion 5.** Write each spec file by inserting the `risk:` line into
`tests/test_replay.py`'s `SPEC`, and pass it as `spec_path`. Share one
`mirrors_dir`, and give each replay its own ledger and `out_dir`.

**Measured on a prototype at `66552540`.** A prototype passed all five
witnesses, and each failed with its source reverted. Its diff measured 817
changed tokens. Each of the 16 wrong versions above was applied to it as an
edit, and each failed its own criterion's witness. The rest of the suite
passed on it.
