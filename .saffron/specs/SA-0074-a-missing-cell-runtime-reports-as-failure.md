---
id: SA-0074
title: a missing cell runtime reports as twenty-one failures rather than as absent
type: bug
priority: 2
depends_on: []
touches:
  - saffron/cell/runtime.py
  - tests/conftest.py
  - tests/test_runtime.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - spikes/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/repos/**
  - saffron/cell/session.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/preflight.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
  - tests/test_worktree.py
  - tests/test_proxy.py
  - tests/test_image.py
  - tests/test_package_cell.py
  - tests/test_agent_runner.py
budget_usd: 8
max_attempts: 3
max_turns: 40
risk: elevated
acceptance:
  - claim: >-
      A cell runtime that is not installed, and one that is on `PATH` but
      cannot be executed, both report as absent. The answer is obtained by
      running the runtime, not by locating it: a file that is present and
      unrunnable reads identically to a working one when the question is asked
      of the filesystem, and that is the failure this criterion is about. A
      runtime that does run reports the version string it printed, so what is
      recorded is what answered.
    witness: tests/test_runtime.py::test_a_runtime_that_cannot_be_executed_reports_as_absent
  - claim: >-
      When the cell runtime reports absent, a `cell`-marked test reports as
      skipped, with a reason naming the cell runtime it did not find. It does
      not fail. Twenty-one failures that all mean "this machine has no cell
      runtime" are indistinguishable from twenty-one defects, which is the
      whole cost: the suite says the code is wrong when the machine is merely
      different.
    witness: tests/test_runtime.py::test_a_cell_marked_test_skips_when_the_runtime_is_absent
  - claim: >-
      A `cell`-marked test still never runs in the default suite, and a test
      without the marker still may not execute the cell runtime or `gh`. The
      existing tripwire in `tests/conftest.py` is unchanged in what it forbids
      and in what it exempts.
    witness: tests/test_runtime.py::test_a_test_without_the_marker_still_may_not_exec_a_host_tool
    preserves: true
---

## Context

Measured 2026-09-11 on Linux, in `docs/evidence/2026-09-11-podman-as-a-second-cell-runtime.md`.
`uv run pytest -m cell` on a host without `apple/container` reports 7 failures
and 14 errors, every one of them the same `CellRuntimeError: container could not
be executed`. The repository is otherwise entirely green there: 1770 passed.

The `cell` marker already exists and already carries the right meaning —
`pyproject.toml` deselects it by default, and `tests/conftest.py` reads it to
decide which tests may exec a host tool. What is missing is the other half of
the same question. The marker says *this test needs a cell runtime*; nothing
asks *is there one*.

This is the same distinction §5.4 draws between `fail` and `error`, one layer
out. A gate that broke is charged to nobody; a suite that cannot run is not the
repository's code being wrong. The suite currently has no way to say so.

## Problem

`saffron/cell/runtime.py` is the module that knows which cell runtime, and it
has no way to answer whether that runtime is there. Every caller finds out the
same way — by executing it and catching `CellRuntimeError` — which is the right
answer for a task that is already under way and the wrong one for a test session
deciding whether to start.

The consequence is not only cosmetic. A contributor on a machine without the
runtime cannot tell their own breakage from the machine's, so the honest move is
to not run the marked suite at all, and then it guards nothing anywhere except
the operator's Mac.

## Out of scope

**A second cell runtime.** This spec adds no backend and changes no behaviour
for a host that has `apple/container`. The seam that would let a second one
exist is backlog item **107**, and it cannot be landed from a cell — it needs a
simultaneous edit to `.saffron/rules/`, which is `protected`.

**Preflight.** `saffron/preflight.py` answers a richer question (§4.2.1) at a
different moment, for a run rather than for a test session, and it is forbidden
here. If it should later share this probe, that is its own change.

**Recording which runtime ran a task.** A ledger column is the natural next
question and a different one; it belongs with item 107, not here.

**The other reasons a marked test cannot run.** A host with the runtime but no
built images fails differently and is not covered. Naming it would mean building
the images to test it.

## Notes for the agent

**This spec creates new code, so its criteria carry witnesses and no mutants.**
There is no existing spelling to pin: naming the probe's own signature here
would put the literal in the prompt you are reading. Expect `witness` to report
`skip` on the two new criteria and read that as honest, not as a gap.

**Do not import the new name at module scope in the witness.** `tests/test_runtime.py`
already imports the module, and the module survives a revert — a missing
attribute on it fails the test, which is what `revert` needs to see. Importing
the new function by name instead turns the reverted run into a collection error,
which `revert` reads as `skip`, and the anti-theater gate then checks nothing.

**Ask the runtime, do not look for it.** A check that consults the filesystem —
whether a file exists, whether `PATH` holds it — passes for a binary that cannot
run, and that is the first criterion's whole subject. Run it and read what it
says. Build the unrunnable case as a real file the test creates; do not simulate
it by patching the thing under test.

**Keep the probe off the non-`cell` path.** `tests/conftest.py`'s autouse
tripwire forbids a test without the marker from exec'ing the cell runtime, and
that includes any probe you add. Consult it only for a test that carries the
marker, or the first unmarked test to run will trip the tripwire it is supposed
to be protected by. It also keeps a reverted run from erroring the whole suite
rather than the marked part of it.

**A probe that runs once per marked test is a probe that runs twenty-one times.**
Each one starts a process that is not there. Answer it once per session.

**The third criterion is the one an edit to `tests/conftest.py` is most likely
to break, and it is why it is declared.** The tripwire's exemption is the `cell`
marker, and the new skip reads the same marker; wiring them through one another
carelessly is how the exemption widens to every test. Its witness should observe
that an unmarked test still cannot exec a host tool, not that the fixture's
source is unchanged.
