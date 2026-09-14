---
id: SA-0086
title: PACKAGE ships the implementer cell's own gate results whenever the base did not move, so nothing outside that cell ever re-runs them
type: bug
priority: 1
depends_on: []
touches:
  - saffron/phases/package.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 6
max_attempts: 3
max_turns: 40
risk: elevated
acceptance:
  - claim: >-
      A task whose default-branch head still equals the base its cell ran on
      is re-verified anyway: PACKAGE runs the whole suite on the packaged
      commit in a fresh gate-only cell, and the gate table it publishes is
      that run's, not the cell's. Today an unmoved base skips re-verification
      and publishes the results the implementer's own cell produced.
    witness: tests/test_package.py::test_an_unmoved_base_still_reverifies_the_packaged_commit
  - claim: >-
      When that re-verification on an unmoved base finds new failures, nothing
      is pushed and no pull request is opened, and the result's note says the
      base did not move, so a reader can tell a verdict that did not reproduce
      from a change that did not survive today's main.
    witness: tests/test_package.py::test_new_failures_on_an_unmoved_base_block_the_push_and_say_the_base_did_not_move
  - claim: >-
      A moved base re-verifies under the policy exported from the commit it
      verifies against, as it does today.
    witness: tests/test_package.py::test_reverify_is_handed_the_policy_from_the_commit_it_verifies_against
    preserves: true
---

## Context

`docs/BACKLOG.md` item **118**, from threat-modelling Saffron on 2026-09-13.

The implementer cell runs as root on a writable rootfs. Every gate it runs
calls tools from `/opt/venv` and `/usr`, and reads the tree through the cell's
own `git`. The agent could have replaced any of them before the final suite
ran. The one check outside that cell is `reverify` in
`saffron/phases/package.py`: the whole suite, in a fresh gate-only cell with no
credential and no route out, on the packaged commit PACKAGE built on the host
from `patch.diff`.

`package()` runs it only when `needs_reverification(target_head, tree_base)` is
true, which means only when the base moved. Its docstring calls a re-run on an
unmoved base "provably redundant". That holds only if the cell's results were
honest, which is the one thing a cell is never trusted with (§2). So on the
path most tasks take, the gate table in the pull request is the implementer
cell's own.

Re-verifying every packaged commit also closes the diff half of the class.
The packaged commit is built from the exported patch by host git. Every gate
in the fresh cell, `scope` and `integrity` included, then measures the tree
that is pushed and the diff a reviewer reads, whatever the implementer's
`.git` said.

## Problem

The verdict a pull request publishes should be computed outside the container
the agent controlled, on every path, not only when the base moved.

## Out of scope

**The critic.** The lenses also run in the implementer's container. That is
`SA-0087` and `SA-0088`.

**`DESIGN.md` §5.7's "only when the base moved".** It is rewritten by hand
(item 118), and so is the vocabulary question of whether a verdict that did
not reproduce needs its own terminal state. Until then it is `MERGE_FAILED`
with a note that says which case it was.

**The pull request body's `"base"` wording.** `saffron/report/pr_body.py` is
forbidden here, and its `_verification("base")` branch becoming unreachable is
listed in item 118.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The fix changes the condition
around `reverify`, and the new spelling is yours, so no text exists yet that a
mutant could pin honestly. `witness` will report `skip`, and that is expected.

**Remove no test and rename no test.** `census` fails any test name collected
at base and missing at head, and no spec field overrides it.
`test_an_unmoved_base_makes_reverification_provably_redundant` and
`test_a_moved_base_requires_reverification` test `needs_reverification`
directly. Keep that function if you can give it an honest job, for example
deciding whether a fresh baseline is needed. Rewrite its docstring and those
tests' docstrings wherever they claim a skip is safe. Update any other test in
`tests/test_package.py` that asserts an unmoved base skips re-verification. It
now asserts the opposite, under the same name.

**Use the seam the file already has.** Tests fake re-verification with
`monkeypatch.setattr("saffron.phases.package.reverify", ...)` and the
`packageable` fixture. `_reverified()` builds a clean comparison. A comparison
carrying new failures is how the second witness gets a red re-run.

**Every new witness must fail with `package.py` reverted.** Reverted, an
unmoved base never calls `reverify`. So a test that records whether the fake
was called, and a test that expects no push after a red fake, both fail. Import
nothing new at module scope: a module-scope import of a name you add turns the
reverted run into a collection error, which `revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included.
