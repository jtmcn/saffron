---
id: SA-0087
title: every REVIEW lens runs in the container the implementer just had root in, and reads the tree through that container's own git
type: bug
priority: 1
depends_on: [SA-0076]
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
budget_usd: 8
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      Every REVIEW lens session runs in a container other than the one the
      implementer's turns ran in. Today `run_review` is handed the
      implementer's container, so each lens re-execs the runner and the SDK
      from a rootfs the agent could write.
    witness: tests/test_session.py::test_every_lens_runs_in_a_container_the_implementer_never_ran_in
  - claim: >-
      The diff the lenses are shown, and the file contents a finding is
      anchored against, are read from that other container's tree, which is
      the task's base with the exported patch applied, not from the
      implementer's worktree.
    witness: tests/test_session.py::test_the_critic_reads_the_tree_rebuilt_from_the_exported_patch
  - claim: >-
      A patch that does not apply to its own base in that fresh tree ends the
      task before any lens runs, in a state other than `READY_FOR_REVIEW` and
      other than `GATE_ERROR`.
    witness: tests/test_session.py::test_a_patch_that_does_not_apply_to_its_base_never_reaches_review
  - claim: >-
      The container, worktree volume and state volume created for the lenses
      are removed when REVIEW ends, including when a lens raises.
    witness: tests/test_session.py::test_the_critic_cell_is_torn_down_when_review_ends
  - claim: >-
      Every lens still carries `CLAUDE.md` at the base commit, as it does
      today.
    witness: tests/test_session.py::test_every_review_lens_carries_claude_md_at_the_base_commit
    preserves: true
  - claim: >-
      A review still records the findings it dropped as well as the ones it
      kept.
    witness: tests/test_session.py::test_a_review_records_the_findings_it_dropped_as_well_as_the_ones_it_kept
    preserves: true
---

## Context

`docs/BACKLOG.md` item **118**, from threat-modelling Saffron on 2026-09-13.
`SA-0086` moves the gate verdict of record out of the implementer's
container. This spec does the same for the critic.

In `_drive_cell` (`saffron/cell/session.py`), REVIEW calls
`review.run_review(container, ...)` with the implementer's own container. Each
lens is a fresh *session*, as §5.5 requires, but not a fresh *container*. The
implementer ran as root on a writable rootfs for the whole repair loop, so it
could have replaced `/opt/saffron/agent_runner.py` or the SDK that every lens
re-execs. The lenses also Read and Grep `/work`, and `read_at_head` and
`export_patch` read the tree through the implementer's `.git`, which is how
items 2, 89, 102 and 103 each hid an edit from the critic.

The fix is a **critic cell**: a new container from the repo's cell image (a
new container's rootfs is the image's, untouched by the implementer), on the
task's own network and proxy. Its worktree is seeded at the task's tree base,
and the patch exported from the implementer's cell is applied and committed
inside it. The lenses run there, and read the diff and file contents from
there. What the critic judges is then the patch that ships. A forged export
can only hide the agent's own work from the pull request, not from the critic.

## Problem

The critic's independence is a session boundary inside a container the
implementer controlled. It should be a container boundary.

## Out of scope

**REBUT's verdict lenses.** They run through `rebut.run_rebut`, which is
forbidden here. That is `SA-0088`, which depends on this one.

**The gate suites the repair loop runs.** They stay in the implementer's
cell, where their results are feedback. The verdict of record is
`SA-0086`'s.

**Changing `saffron/cell/worktree.py` or `saffron/cell/runtime.py`.** Both are
forbidden: `SA-0074`, `SA-0075` and `SA-0077` are queued against them. Call
their existing functions; build anything new in `session.py`.

**Vocabulary.** "Critic cell" is defined in `CONTEXT.md` §5, and that is the
name to use. Do not edit `ontology/`.

## Notes for the agent

**The criteria carry witnesses and no mutants.** The critic cell is new code,
so no text exists yet that a mutant could pin honestly. `witness` will report
`skip`, and that is expected.

**Bring the critic cell up with the pieces `cell_up` already uses. Do not add
a second `cell_up`.** The network and the proxy are the implementer cell's and
are already running, and `cell_down` removes them. The critic cell must not
start, stop or remove either. What it needs:

- the proxy's address: `runtime.container_ip(proxy.PROXY_NAME)`, because
  `cell_up` does not keep it;
- the environment: `cell_env(...)`, which carries the token the lenses need;
- the repo's cell image, whose tag `cell_up` already built;
- a worktree: `worktree.prepare_worktree(...)` with its own volume and state
  volume, at `spec.tree_base`, with `network`, `env` and `gates_dir` passed
  explicitly. Appendix I is why they are required.

Record every name in the run's `created` ledger before the call that creates
it, and remove the container and both volumes in a `finally`.

**Apply the patch inside the critic cell, with its own git.** The patch is
`worktree.export_patch(container, spec.tree_base)` from the implementer's
cell, the same bytes the operator gets. `worktree.source_mutated` shows how
this module already moves bytes into a cell through `runtime.exec_` (base64
through `sh -c`). Linux caps a single argument at 128 KiB, so a patch too big
for one argument has to end the task honestly, not raise.

**A patch that will not apply is the task's, not infrastructure.** Do not end
it `GATE_ERROR` or raise it as a runtime failure. Both are charged to nobody,
and an agent-controlled failure that is charged to nobody is a free way to
disarm a check (`d3b9c51`). `EXHAUSTED`, with a `why` naming the apply
failure, is the existing state that fits.

**Test through `_drive`.** `_stub_the_runtime` and `_drive` in
`tests/test_session.py` already run `_drive_cell` against stubs. The agent
callable receives the container as its first argument, so a stub that records
it can tell a lens turn's container from the implementer's. Every new witness
must fail with `session.py` reverted. Reverted, the lenses get the
implementer's container and no critic cell exists, so honest tests of the
four criteria fail. Import nothing new at module scope: a module-scope import
of a name you add turns the reverted run into a collection error, which
`revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. Keep the critic cell's lifecycle in one function that REVIEW calls,
so `SA-0088` can call it again.
