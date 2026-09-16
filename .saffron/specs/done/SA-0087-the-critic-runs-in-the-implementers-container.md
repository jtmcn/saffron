---
id: SA-0087
title: every REVIEW lens runs in the container the implementer just had root in, and reads the tree through that container's own git
type: feature
priority: 1
depends_on: []
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
budget_usd: 20
max_attempts: 3
max_turns: 90
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
      implementer's worktree. That includes a finding cited outside every
      diff hunk, whose file content is read in the critic cell.
    witness: tests/test_session.py::test_a_finding_outside_the_diff_is_anchored_against_the_critic_cells_tree
  - claim: >-
      A patch that does not apply to its own base in that fresh tree ends the
      task `EXHAUSTED` before any lens runs, and the reason it reports names
      the patch that failed to apply, so the end cannot be read as a task
      that ran out of attempts on its gates.
    witness: tests/test_session.py::test_a_patch_that_does_not_apply_to_its_base_never_reaches_review
  - claim: >-
      A patch that could never apply, because the export carries a binary
      change as a `Binary files ... differ` stub, ends the task `GATE_ERROR`
      before any lens runs, not `EXHAUSTED`, and the reason names the binary
      change. The export cannot carry a binary change, and PACKAGE's
      `apply_patch` already treats the stub as an error, not the task's.
    witness: tests/test_session.py::test_a_binary_change_the_export_cannot_carry_ends_in_gate_error
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

backlog item **118**, from threat-modelling Saffron on 2026-09-13.
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

**The gate table the lenses are shown.** It stays the implementer cell's last
suite here. Running the suite in the critic cell instead would execute
model-authored code as root in the container the lenses then re-exec their
runner from. That is `SA-0089`.

**Changing `saffron/cell/worktree.py` or `saffron/cell/runtime.py`.** Both are
forbidden. Call their existing functions; build anything new in `session.py`.
Giving the export `--binary` would change every patch PACKAGE applies, and is
not this spec's to decide.

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
  `cell_up` does not keep it. It returns `str | None` and `cell_env` takes
  `str`, so `None` needs a branch or `types` fails: an unreadable proxy
  address is infrastructure, and raises `CellRuntimeError`;
- the environment: `cell_env(...)`, which carries the token the lenses need;
- the repo's cell image, whose tag `cell_up` already built;
- a worktree: `worktree.prepare_worktree(...)` with its own volume and state
  volume, at `spec.tree_base`, with `network`, `env` and `gates_dir` passed
  explicitly. Appendix I is why they are required.

Record every name in the run's `created` ledger before the call that creates
it, and remove the container and both volumes in a `finally`. Before creating
each, remove any leftover of the same name, tolerating absence, as `cell_up`
does for the implementer cell. A run killed mid-REVIEW skips the `finally`,
and the next run's create would then fail after IMPLEMENT was paid for.

**Print nothing new on the green path.**
`tests/test_events.py::test_watch_output_matches_the_golden_fixture` drives a
green run through REVIEW with this file's stubs and compares every printed
line to `tests/fixtures/watch-golden.txt`. Both files are outside `touches`.
The critic cell emits a line only on its `EXHAUSTED` or `GATE_ERROR` exit, or
when a removal leaves something behind.

**Apply the patch inside the critic cell, with its own git.** The patch is
`worktree.export_patch(container, spec.tree_base)` from the implementer's
cell, the same bytes the operator gets. Hand it to `git apply` on stdin, with
`runtime.exec_stream(..., stdin_data=patch, ...)`, not as an argument the way
`worktree.source_mutated` moves bytes (base64 through `sh -c`). Linux caps a
single argument at 128 KiB, and a limit that is Saffron's must not end a task
the agent is charged for. Commit it with a direct `git add` and `git commit`
in the critic cell, not through `commits_ahead` or `commit_dirty`: their
stubs in `tests/test_session.py` answer by call order and record into
`cell.checkpointed`, which the `preserves` witnesses depend on.

**A patch that will not apply is the task's, unless the export could never
have carried it.** A real failure to apply is the agent's. Do not end it
`GATE_ERROR` or raise it as a runtime failure. Both are charged to nobody,
and an agent-controlled failure that is charged to nobody is a free way to
disarm a check (`d3b9c51`). `EXHAUSTED`, with a `why` naming the apply
failure, is the existing state that fits.

The one exception is a binary change. `worktree.DIFF_FLAGS` has no `--binary`
or `--full-index`, so the export carries a binary change as a stub that no
base can apply, and `git apply` reports `without full index line`.
`DESIGN.md` §5.5 carves this case out. PACKAGE already reads that marker as infrastructure
(`_NO_FULL_INDEX` in `saffron/phases/package.py`,
`test_a_binary_patch_is_an_error_not_a_conflict`). Match the same marker,
imported inside the function, and end the task `GATE_ERROR`. Check the
marker whatever the exit code. An exec that cannot launch is Saffron's and
raises `CellRuntimeError`; it is neither end. A *timeout* does not raise:
`exec_stream` reports a fired wall or idle bound as
`Completed(returncode=124, timed_out=True)`. Read `timed_out` and raise
`CellRuntimeError` on it. Reading exit 124 as a refused apply would charge
the agent for Saffron's own bound, which is the `error` ≠ `fail` collapse
`CLAUDE.md` forbids.

The agent can reach the stub on purpose, by committing a file git reads as
binary, and end its task uncharged. That is the ceiling `size` and
`integrity` already carry for a hidden binary (item 103). Nothing ships from
it, since only `READY_FOR_REVIEW` is packaged. Mark the check with a
`ponytail:` comment that names the ceiling.

**Test through `_drive`.** `_stub_the_runtime` and `_drive` in
`tests/test_session.py` already run `_drive_cell` against stubs. The agent
callable receives the container as its first argument, so a stub that records
it can tell a lens turn's container from the implementer's. Every new witness
must fail with `session.py` reverted. Reverted, the lenses get the
implementer's container and no critic cell exists, so honest tests of the
five criteria fail. `_drive(capture=...)` collects the raw events, so the
two apply witnesses can read the reason and not the state alone (principle 55).

**The anchoring witness must script a finding outside every hunk.** `anchor()`
calls `read_head` only for a finding whose line is not in a diff hunk
(`_is_anchored`, `saffron/agents/findings.py`), and a lens stub that returns
`{"findings": []}` never reaches it. Script a lens finding on a line outside
the patch's hunks, and assert that `read_head` ran and ran in the critic
cell's container. A witness that accepts "`read_head` never ran" passes with
`read_head` pointed at the implementer's container, which is the regression
this spec exists to prevent (backlog item 118). Record which container
`export_patch` ran in too, since the criterion claims the diff comes from the
critic cell as well.
Import nothing new at module scope: a module-scope import
of a name you add turns the reverted run into a collection error, which
`revert` reads as `skip`.

**Write any helper as a `def`, not a `lambda`.** A `lambda` assigned to a name
needs a `# noqa: E731` to pass `lint`, and that suppression fails `integrity`
even inside `touches`.

**The `size` gate counts tests.** A `feature` gets 600 changed lines, tests
included. Keep the critic cell's lifecycle in one function that REVIEW calls,
so `SA-0088` can call it again. An earlier build of the other criteria came
to about 290 lines, so share one stub and one setup helper across the
witnesses rather than repeating them. `_stub_the_runtime` stubs none of
`runtime.container_ip`, `runtime.exec_stream` or `runtime.exec_` today; add
all three there once. `tests/conftest.py`'s autouse `no_host_tool_exec`
raises for any unmarked test that reaches a runtime binary, and
`tests/test_events.py` imports this stub, so a missing one fails tests
outside `touches`.
Fold the two apply witnesses onto one helper that takes the apply's stderr
and exit code.
