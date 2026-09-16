---
id: SA-0089
title: every REVIEW lens is shown the gate table the implementer's own cell computed, so a forged toolchain still writes what the critic reads about the gates
type: feature
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
budget_usd: 18
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
`_gate_cell` inside `reverify` in `saffron/phases/package.py` and copy its
shape — it is a nested function, so there is nothing to import even though
importing would be fine: `forbidden` bounds this spec's diff, not its import
graph, and `_drive_cell` already imports `saffron.phases.package` and
`saffron.repos.mirror` at base. That is also why calling
`saffron.repos.image.cell_tag` below is allowed. What to copy: a network from
`runtime.create_network`, which is always `--internal`; a volume;
`worktree.prepare_worktree` with `network`, `env=dict(policy.thread_env)` and
`gates_dir` passed explicitly, at `spec.tree_base`; teardown in a `finally`.
Appendix I is why `network` and `env` are required. `prepare_worktree` also
requires `mirror`, which `_drive_cell` already takes, and `image`, which is
`saffron.repos.image.cell_tag(repo)` because `cell_up` discards the tag it
built.

**Pass that network an explicit subnet, and pre-clean every name.**
`runtime.create_network` defaults to `DEFAULT_SUBNET`, and an overlapping
create raises `CellRuntimeError`. `reverify` gets away with the default
because PACKAGE runs after the cell is down; REVIEW does not — the
implementer's `saffron-cells` network holds that subnet until `cell_down`
in `_drive_cell`'s `finally`. Two subnets are held, not one: `saffron-cells`
on `runtime.DEFAULT_SUBNET` (`10.88.0.0/24`), and the proxy's `saffron-egress`
on `proxy.EGRESS_SUBNET` (`10.89.0.0/24`), which `_ensure_egress_network`
creates once and neither `cell_down` nor `stop_proxy` removes — so
`10.89.0.0/24`, the obvious next pick after reading `10.88.0.0/24`, is taken.
Use `10.90.0.0/24`: those two are the only subnets `saffron/` declares.
Write it at the call site in `session.py`, since `runtime.py` is forbidden.
Then, before creating each name, remove any leftover of the same name,
tolerating absence, as `cell_up` does and `reverify` does not need to: its names
change every attempt and a `spec_id`-keyed name does not. Both failures
land at REVIEW, after IMPLEMENT is paid for. Then apply the patch
inside it the way `SA-0087`'s critic cell does, with the same function if it
can take the container as an argument. Record every name in the run's
`created` ledger before the call that creates it.

**Run the suite against the run's own pre-turn baseline** —
`suite.against(tree, baseline)`, with the baseline the task already took before
the agent had a single turn, not `suite.baseline(tree)`. A suite with an empty
prior makes `census`, `criteria` and `revert` all report `skip`, and those are
the three gates that speak to test honesty: `census: skip — no gate reported
collected tests at base_sha` reads to a lens as "the suite did not enumerate",
which is a worse table than the one this spec replaces. That baseline predates
the agent's first turn, so it is not a forged-toolchain input in the sense this
spec exists to close. `suite_drift` cannot fire either — not because the gate
dict is the same, but because it keys on a gate's `tool` changing between the
two suites and on one that ran at baseline skipping at head, and both execute
the same image's toolchain over the same declared gates. An `error` means the
gate broke: end the task
the way `_judge`'s callers end an aborted suite, `GATE_ERROR`, never
`READY_FOR_REVIEW` (§5.4). The advisory set for `gate_summary` is that run's
own.

**Test through `_drive`.** `_stub_the_runtime` records every *removal*, and
`cell.system_prompts` holds each lens's system prompt. It does not record
creations: `create_network` and `create_volume` are no-op stubs, and
`_prepare_worktree` keeps only `base_sha`. Criterion 2 needs the gate
cell's `env` and needs removal ordered against the first lens, so add that
recording to the stub — including the subnet, so a witness can assert the
gate cell is not on the implementer's. Make the stubbed gate report something different in
the implementer's container and in the gate cell, and assert which one the
lens prompts carry. Every new witness must fail with `session.py` reverted.
Reverted, the lenses are shown the implementer's results and no gate cell
exists, so honest tests of both criteria fail. Import nothing new at module
scope: a module-scope import of a name you add turns the reverted run into a
collection error, which `revert` reads as `skip`.

**Criterion 2's witness must assert the gate cell was created, not only that
nothing leaked.** "Holds no credential", "no route out" and "removed before the
first lens starts" are all trivially true of the reverted source, where no gate
cell exists at all, and `revert` blocks a non-`preserves` witness that still
passes reverted — a repair round spent on a defect item 118 already records
against `SA-0087`'s second criterion. Assert the cell's name was recorded and
its arguments read, then that it was removed, both before the first lens turn.
The claim's "holds no credential and no route out" is a property a stubbed test
cannot establish; what it can pin is the arguments. Item 131 carries the
`cell`-marked test that probes the property itself.

**Pass `state_volume` explicitly.** `_gate_cell` leaves it to
`prepare_worktree`'s default, but the `tests/test_session.py` stub reads
`k["state_volume"]` unconditionally, so a verbatim copy raises `KeyError` on the
first driven test.

**The gate-cell suite is the lens table only.** `latest` stays the
implementer's: `_judge` reassigns it with `nonlocal`, so reassigning is the
locally natural move, and `latest` also feeds `CellOutcome.gates`,
`effective_risk` and `advisory_gates`. Bind the gate cell's suite to its own
name.

**Print nothing new on the green path.**
`tests/test_events.py::test_watch_output_matches_the_golden_fixture` drives a
green run through REVIEW with this file's stubs and compares every printed
line to `tests/fixtures/watch-golden.txt`. Both files are outside `touches`.
`_rebut_gates`' callers `emit` an attempt event for every suite; the gate
cell must emit a line only on its `GATE_ERROR` exit, or when a removal
leaves something behind.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `feature` gets 600 changed lines, tests
included.
