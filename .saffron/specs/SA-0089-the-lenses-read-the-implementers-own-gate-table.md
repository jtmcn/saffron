---
id: SA-0089
title: every REVIEW lens is shown the gate table the implementer's own cell computed, so a forged toolchain still writes what the critic reads about the gates
type: bug
priority: 2
depends_on: [SA-0088]
touches:
  - saffron/cell/session.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 12
max_attempts: 3
max_turns: 90
risk: elevated
acceptance:
  - claim: >-
      The gate table every REVIEW lens is shown comes from a suite run on the
      task's base with the exported patch applied, in a container that is
      neither the implementer's nor the critic cell. Today it is the
      implementer cell's own last suite.
    witness: tests/test_session.py::test_the_lenses_are_shown_a_gate_table_computed_outside_the_implementers_cell
  - claim: >-
      That container is created on a network of its own with the repo's
      declared gate env and nothing else, so it holds no credential and no
      route out, and it is removed before the first lens starts, including
      when a gate in it raises.
    witness: tests/test_session.py::test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs
---

## Context

backlog item **118**, the fourth of four. `SA-0087` moved the lenses
into a critic cell and the diff they read with them. One input stayed behind.
In `_drive_cell` (`saffron/cell/session.py`), REVIEW passes
`gates=review.gate_summary(latest.results, ...)`, and `latest` is the last
suite the implementer's cell ran. Each line of that table carries a status, a
`tool` and a `summary`, all computed with a toolchain the agent had root over.
A forged `pytest` can tell every lens the tests passed, and a gate's `summary`
is text the cell wrote, placed in the lens's system prompt.

`SA-0086` re-verifies the packaged commit, so a forged table cannot ship a red
suite. It can still steer the critic: a lens told the gates are green reads
the diff differently, and never files the blocker that would have sent the
task to REBUT.

## Problem

The critic reads the diff from a container the implementer never ran in, and
reads the gates from the one it did.

## Out of scope

**PACKAGE's re-verification.** It is the verdict of record (`SA-0086`). This
table is the critic's input, not a published result.

**REBUT's verdict lenses.** Their prompts carry no gate table. `rerun_gates`
stays in the implementer's cell, as `SA-0088` left it.

**Changing `GateSuite`, `saffron/cell/worktree.py` or
`saffron/cell/runtime.py`.** All are forbidden. Call their existing functions;
build anything new in `session.py`.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The gate cell and its wiring
are new code, so no text exists yet that a mutant could pin honestly.
`witness` will report `skip`, and that is expected.

**Never run the suite in the critic cell.** A gate executes model-authored
code, the tests the implementer wrote, as root. Run there, it could rewrite
the runner and SDK the lenses re-exec a moment later, which is the hole
`SA-0087` closed. The gates get a cell of their own.

**Build that cell the way `reverify` builds its gate-only cells.** Read
`_gate_cell` inside `reverify` in `saffron/phases/package.py`, which is
forbidden here, so do not import from it: a network from
`runtime.create_network`, which is always `--internal`; a volume;
`worktree.prepare_worktree` with `network`, `env=dict(policy.thread_env)` and
`gates_dir` passed explicitly, at `spec.tree_base`; teardown in a `finally`.
Appendix I is why `network` and `env` are required. Then apply the patch
inside it the way `SA-0087`'s critic cell does, with the same function if it
can take the container as an argument. Record every name in the run's
`created` ledger before the call that creates it.

**One run of the suite is enough.** The lenses need results, not new
failures, so no baseline is needed. `suite.baseline(tree)` is a single run
despite its name. An `error` in that run means the gate broke: end the task
the way `_judge`'s callers end an aborted suite, `GATE_ERROR`, never
`READY_FOR_REVIEW` (§5.4). The advisory set for `gate_summary` is that run's
own.

**Test through `_drive`.** `_stub_the_runtime` records every container,
volume and network created and removed, and `cell.system_prompts` holds each
lens's system prompt. Make the stubbed gate report something different in
the implementer's container and in the gate cell, and assert which one the
lens prompts carry. Every new witness must fail with `session.py` reverted.
Reverted, the lenses are shown the implementer's results and no gate cell
exists, so honest tests of both criteria fail. Import nothing new at module
scope: a module-scope import of a name you add turns the reverted run into a
collection error, which `revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
