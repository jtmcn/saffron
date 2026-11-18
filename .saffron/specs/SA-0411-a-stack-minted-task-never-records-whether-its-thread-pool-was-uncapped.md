---
id: SA-0411
title: A task a `--stack` batch mints never records whether its thread pool was uncapped
type: bug
priority: 3
risk: elevated
estimated_lines: 145
estimate_measured: true
depends_on: [SA-0407, SA-0408, SA-0409]
touches:
  - saffron/cli.py
  - saffron/cell/runtime.py
  - saffron/cell/session.py
  - tests/test_cli.py
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
  - hooks/**
  - saffron/ledger.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/cell/runtimes/**
  - saffron/batch.py
  - saffron/task.py
  - saffron/preflight.py
  - tests/conftest.py
  - tests/test_session.py
  - tests/test_runtime.py
  - tests/test_ledger.py
budget_usd: 34
max_attempts: 3
max_turns: 190
acceptance:
  - claim: >-
      A task a `--stack` batch's `_stack_mint` mints carries
      `thread_pool_uncapped` on its own `task_created` fact. The value comes
      from the `.saffron/policy.yaml` at the pinned `base_sha`, never from
      another commit of the mirror. It is true on a dialect that shares the
      host kernel when that policy's `thread_env` names no entry, for
      podman's dialect and for a shared-kernel dialect under another binary,
      each with `thread_env` absent and with it empty. Under podman an empty
      `policy.yaml` is true too. It is false when `thread_env` names an
      entry, and false on apple/container's dialect, and on a dialect with
      its own kernel whose `unattended` is false. It is `None` when the
      pinned `base_sha` holds no policy, under podman's dialect and under
      apple/container's. A policy there that is not valid YAML, or whose
      `thread_env` or another field does not validate, raises `PolicyError`
      from the call to the mint under each of those two dialects, and no run
      and no task are written.
    witness: tests/test_cli.py::test_the_stack_mint_records_whether_the_thread_pool_is_uncapped_from_the_policy_at_the_pinned_base
    wrong_versions:
      - The mint passes no `thread_pool_uncapped`, as at base, so every case reads `None`.
      - The mint reads the policy at the mirror's `HEAD`, so a case whose newest commit answers differently fails.
      - The mint reads the policy at the pinned `base_sha`'s parent, so a case whose parent commit answers differently fails.
      - The mint keeps its own copy of the rule and reads `not unattended` where `shares_kernel` belongs, so the unproven VM dialect reads true.
      - The mint keeps its own copy of the rule and compares the dialect's binary with `podman`, so the shared kernel under another binary reads false.
      - The mint reads an absent policy as an empty `thread_env`, so the no-policy case reads true where `None` belongs.
      - The mint files the negation of the rule's answer.
      - The shared rule ignores `thread_env`, so podman with an entry reads true.
      - The shared rule ignores the dialect, so apple/container with no entry reads true.
      - The shared rule reads `not unattended` in place of `shares_kernel`.
      - The mint catches `PolicyError` and files `None`, so a broken policy mints a task.
      - The mint catches a YAML error alone and files `None` for a policy whose fields do not validate.
      - The mint reads the policy after it opens the run, so a broken policy leaves a run row behind.
      - The mint reads no policy on a dialect with its own kernel and files false there, so apple/container with no policy reads false where `None` belongs.
      - The mint files `None` for any falsy policy text, so an empty `policy.yaml` under podman reads `None` where true belongs.
      - The mint reads the policy once in `_stack_mint`'s own body, outside its minting closure, so a broken policy raises when the mint is built and not when it is called.
      - "The mint reads `thread_env` from the YAML itself and validates no other field, so `nope: 1` mints a task."
  - claim: >-
      A task a cell mints still records `thread_pool_uncapped` true on a
      shared kernel with no `thread_env` entry and false otherwise, and warns
      once at preflight exactly where it is true.
    witness: tests/test_session.py::test_a_shared_kernel_task_with_no_thread_env_entries_warns_and_records_an_uncapped_pool
    preserves: true
    wrong_versions:
      - The cell never warns at preflight, whatever the rule answers.
      - The cell passes an empty `thread_env` to the shared rule, so podman with an entry reads true.
      - The cell's call drops the dialect and reads `not policy.thread_env` alone, so apple/container reads true.
---

## Context

Backlog item **b-e9153f**, tier 2, cites `DESIGN.md` §5.1. It was found
reviewing `SA-0282`, which closed its related item **b-0569f7**. Every line
below was read at `main` once #1249 merged.

**ADR 10's principle 7.** A repo that declares no `thread_env` runs with an
uncapped thread pool on a shared kernel. The departure is accepted because
the engine "records the uncapped pool on the task"
(`docs/adr/0010-saffron-ships-as-an-engine-each-operator-deploys.md:79-84`).
§5.1 says why the record matters. Under a shared-kernel runtime `thread_env`
is the only control over a thread pool sized from `sysconf`
(`DESIGN.md:733`).

**The rule and its one caller.** `_drive_cell` loads the policy from the
export at `spec.base_sha` (`saffron/cell/session.py:2383`,
`saffron/cell/session.py:2401`). It computes the rule inline as
`runtime.dialect().shares_kernel and not policy.thread_env`
(`saffron/cell/session.py:2413`). A true value draws a `thread_env`
preflight warning (`saffron/cell/session.py:2414-2419`).

**Where the value reaches the record.** Only a task the cell mints itself
carries it. When `spec.task_id` is set, the cell reads that task's run and
creates nothing (`saffron/cell/session.py:2438-2446`). Otherwise it calls
`ledger.create_task` with `thread_pool_uncapped=thread_pool_uncapped`
(`saffron/cell/session.py:2447-2468`). `create_task` writes the value onto
the `task_created` fact's payload, `None` where the caller passed none
(`saffron/ledger.py:1528`, `saffron/ledger.py:1565-1567`). No `tasks`
column holds it. Nothing else in `saffron/` writes the key
(`git grep thread_pool_uncapped -- saffron`).

**The stack batch's mint.** `_stack_mint` upserts the repo, opens a run at
the pinned `base_sha`, and calls `create_task` with no
`thread_pool_uncapped` (`saffron/cli.py:1598-1626`). It reads no policy. Its
task then reaches the cell with `task_id` set, through `run_task`, so the
cell's branch above never mints it (`saffron/cli.py:935-940`). Measured at
that `main`, a mint over a mirror whose policy at the pinned `base_sha`
declares no `thread_env`, under podman's dialect, filed
`thread_pool_uncapped: None`.

**Which dialects reach the mint.** A `saffron batch` refuses every dialect
whose `unattended` is false (`saffron/cli.py:2429`), podman's included
(`saffron/cell/runtimes/podman.py:94-97`). So a `--stack` night records
false under apple/container. True is reachable only through the follow-up
mint `saffron finish` builds (`saffron/cli.py:2886`), under podman.

**The same policy.** `run_task` builds the cell's `CellSpec` with
`base_sha=base.base_sha` (`saffron/task.py:863`). Its `base` is the same
`PinnedBase` the mint is given (`saffron/cli.py:939`). So the cell exports
its policy from the commit the mint reads. A `--stack` batch pins that base
from its readiness check (`saffron/cli.py:2515`), and readiness fails a
policy that is present and broken (`saffron/preflight.py:568-576`).

**The mint's other callers.** `_stack_follow_ups` builds one for follow-up
specs (`saffron/cli.py:1916`). A `--stack` batch builds one
(`saffron/cli.py:2626`), and so does `saffron finish` (`saffron/cli.py:2886`).
A mint that raises is a miss, and `run_stack_batch` re-raises it
(`saffron/batch.py:703-710`).

**The reads this needs.** `git_mirror.file_at(mirror, sha, path)` returns
`None` for an absent path and raises `GitError` for one it cannot read
(`saffron/repos/mirror.py:267-273`). `parse_policy` parses bytes with no
file or gate read, and raises `PolicyError` (`saffron/repos/policy.py:310-319`).
`saffron/cli.py:69` imports `Policy`, `PolicyError` and `load_policy` from
that module. `cli.py` already imports `runtime` (`saffron/cli.py:44`).

## Problem

A `--stack` night is the default way the operator runs the queue, and
none of its tasks says whether its thread pool was uncapped.

1. **One rule.** Move the rule into a module-level function in
   `saffron/cell/runtime.py`. It takes a policy's `thread_env` and returns
   whether the selected dialect shares the host kernel and that mapping is
   empty. `_drive_cell` calls it in place of its inline expression. The
   warning and the `create_task` argument read its answer as today.
2. **The mint reads the policy.** `_stack_mint`'s minting closure reads
   `.saffron/policy.yaml` at `pinned.base_sha` from `pinned.mirror`, first,
   before it upserts the repo. It parses it and calls the function from 1
   with its `thread_env`. It passes the answer to `create_task`. With no
   policy at that commit it passes `None`, the value for a caller that
   never decided. A policy that does not parse raises out of the mint, as
   the cell's own load would, before any row exists.

## Out of scope

- **`saffron draft`'s task.** `_draft` calls `create_task` with no value
  either (`saffron/cli.py:1779-1785`). No implementing cell runs on that
  task, so nothing it records depends on a thread pool.
- **`policy_sha` at mint.** `_stack_mint` still files `policy_sha=None`.
  The cell records the policy on a given task through `record_policy`
  (`saffron/cell/session.py:2470-2473`).
- **A policy whose gates are missing.** `parse_policy` checks no gate file.
  `load_policy` does (`saffron/repos/policy.py:301-305`). Such a policy mints
  a task with a value, and its cell then refuses it. Readiness refuses it
  first on a `--stack` batch.
- **An unreadable mirror.** `file_at`'s `GitError` propagates from the mint
  unchanged. A pinned `base_sha` the mirror does not hold is not a state a
  batch reaches. Swallowing it would file `None` for a policy the mint
  could not read, and `file_at`'s own docstring separates absent from
  unreadable.
- **A `tasks` column.** `SA-0282` left the value on the fact alone, since
  nothing reads it from the ledger.
- **A witness for the one rule.** No witness can see that the mint and the
  cell share one function. An identical copy of the rule inline in
  `_stack_mint` passes every test. Problem 1 asks for the move, and
  criterion 1's wrong versions kill only a copy that diverges.

## Notes for the agent

**Mutants, edit and new.** Criterion 1 is new code. Its read in
`_stack_mint` is spelled by you, so it declares a witness and no mutant,
and `witness` will report `skip` for it. Criterion 2 is an edit. Its
mutant on the ref pins text in `saffron/cell/session.py` that the move
leaves alone. Its witness exists at your base and must stay green. It
already drives six dialect and policy pairs through the cell, and the
move in Problem 1 must keep all six.

**When this can run.** A plain batch refuses it until all but one of its
parents' chains merge (`saffron/scheduler.py:1044-1056`). A `--stack`
scan skips that check (`saffron/scheduler.py:1020`,
`saffron/scheduler.py:1444`). It runs this spec only with `SA-0408` and
`SA-0409` in the same order, stacked on `SA-0407`'s pull request
(`saffron/scheduler.py:1227-1261`, `saffron/scheduler.py:1114-1172`). If
`SA-0408` and `SA-0409` reach pull requests in an earlier batch, this spec
waits for merges (`saffron/scheduler.py:296-320`).

**Three existing tests hand `_stack_mint` a base its mirror lacks.** Each
must change. The mint now reads the mirror at the pinned `base_sha`, and
`file_at` raises `GitError` there.
`test_the_stack_mint_opens_a_run_at_the_pinned_base_and_a_task_per_call`
(`tests/test_cli.py:10050`) and
`test_the_stack_mint_records_the_declared_tier_and_null_where_none`
(`tests/test_cli.py:10146`) pass `tmp_path / "m.git"`, which does not
exist, with `base_sha="a" * 40`. Give each a real repo from
`_repo_with_commit` and its `HEAD` as the base. The first also asserts
each row's `base_sha` equals `"a" * 40` (`tests/test_cli.py:10104`). Make
that the real commit.
`test_the_stack_mint_records_the_mutants_refs_commit_and_null_without_one`
(`tests/test_cli.py:10235`) inits a bare mirror and pins `"a" * 40`. Give it
one commit of the empty tree on that mirror, from `git mktree` and
`git commit-tree`, and pin that. None of the three commits holds a policy,
so each mint files `None` and nothing else those tests assert moves.

**The witness.** Add it to `tests/test_cli.py` beside those three. Unmarked
tests run under apple/container's dialect (`tests/conftest.py:54-66`), so
an "always false" build passes any case left on it. Set
`runtime._selected` and `runtime._admitted` with `monkeypatch` per case, as
`tests/test_session.py:5058-5059` does. Define two local stub dialects in
`tests/test_cli.py`, shaped as `_UnprovenVM` and `_OtherSharedKernel` are
(`tests/test_session.py:5018-5028`, `tests/test_session.py:5032-5037`).
Import neither from `test_session.py`. Import `podman` beside `apple`
from `saffron.cell.runtimes` at module scope. It exists at base. Reference
the new function nowhere in the test, so the witness collects with the
source reverted.

Drive ten cases with one `MemoryRecord` and one `Ledger`. Each case
builds its own repo of four commits. The third is the pinned `base_sha`
and holds the case's policy, or none. The other three hold a policy that
answers differently wherever the case's dialect lets a policy change the
answer. That is a `thread_env` entry where the case expects true or
`None`, and `gates: {}` where it expects false. Under apple/container or
the unproven VM with `gates: {}`, no policy answers differently, and
those two cases test the dialect alone. The cases run in this order.
Apple and the unproven VM each take `gates: {}`. Podman takes an entry,
then `gates: {}`. The other shared kernel takes `gates: {}`. Podman takes
`thread_env: {}`, then an empty `policy.yaml`. The other shared kernel
takes `thread_env: {}`. Last, podman and then apple each take no policy.
The expected values are false, false, false, true, true, true, true,
true, `None` and `None`. Read each value from the task's `task_created`
fact through `ledger.record_key` and `record.read`. Compare it with `is`.
Before and after each call to the mint, count the rows of `runs` and
`tasks`, and assert each grew by one. That is the positive case for the
last step.

Then build six more mints, under podman and under apple, over three
broken policies each. One is `gates: [`, which is not valid YAML. One is
`thread_env: [1]` beside `gates: {}`, and one is `nope: 1`. Neither
validates. Build each mint and its candidate outside `pytest.raises`.
Wrap only the call, as `run_stack_batch` reads only a raise from the call
as a miss (`saffron/batch.py:703-710`). Assert each call raises
`cli.PolicyError` and leaves both counts unchanged. A mint that skips the
read under apple fails here, and on the last case above.

**Witness red at base.** Measured at that `main`, the first case fails,
since the mint files `None` where false belongs.

**Measured on a prototype, 2026-11-17.** The change above and the witness
were built at that `main`. The witness failed with `saffron/` reverted.
One harness applied each wrong version as one edit. Each of the
seventeen under criterion 1 failed its witness. Each of the three under
criterion 2 failed criterion 2's witness. The whole suite passed with the
three fixtures changed, before the witness took its later cases. Before
those fixtures changed, the three tests failed on `GitError`, and no other
test in the file did. By `size_gate` the diff counted 580 changed tokens,
491 of them in the test. With the policy's `tests/**` test paths declared,
it counts 89.

**The `prose` gate** reads every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Size.** The `bug` ceiling is 1300 changed tokens. `saffron/cell/**` is
in `elevate_on`, so `size` blocks here.

**Why three parents.** `SA-0407` edits `saffron/cell/session.py`, which
Problem 1 must edit. `SA-0408` edits `tests/test_cli.py`, which the three
fixtures and the witness must edit. `SA-0409` edits `saffron/cli.py`,
where `_stack_mint` lives.
