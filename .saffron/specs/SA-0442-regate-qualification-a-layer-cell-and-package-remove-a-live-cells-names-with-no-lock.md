---
id: SA-0442
title: "`regate`, qualification, a layer cell and `saffron package` remove a live cell's names with no lock"
type: bug
priority: 2
depends_on: [SA-0431]
estimated_lines: 73
estimate_measured: true
touches:
  - saffron/regate.py
  - saffron/qualify.py
  - saffron/end_review.py
  - saffron/task.py
  - tests/test_spec_id_lock_callers.py
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
  - saffron/cell/**
  - saffron/cell_name_lock.py
  - saffron/home_lock.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/batch.py
  - saffron/follow_up.py
  - saffron/commit_review.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/parent_versions.py
  - saffron/report/**
  - tests/conftest.py
  - tests/test_cell_name_lock.py
  - tests/test_regate.py
  - tests/test_qualify.py
  - tests/test_end_review.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_parent_versions.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
budget_usd: 60
max_attempts: 3
max_turns: 210
acceptance:
  - claim: >-
      `run_regate` declines a task whose spec id another process holds,
      before its first runtime call. It prints one `regate:` line naming the
      holder's pid and the text the holder wrote, and returns 1. Otherwise it
      holds the spec id's lock, with the text `saffron regate <task id>`,
      from before its probe network through `record_regate`, and lets it go
      when it returns or raises. The witness holds the lock in this process,
      through a second open of its file, with a spy at `runtime._call`.
      Held as `SA-0005`, then as `sa-0005`, regate returns 1 and prints that
      line, and neither the spy nor `reverify` is reached. Beside a holder of
      `SA-0006`, the spy's first call is `network rm
      saffron-regate-probe-<task id>`, and a take of `SA-0005` there is
      refused naming that text. A take succeeds after the spy's raise. With
      the probe faked, a green regate is refused a take inside `reverify`
      and inside `record_regate`, returns 0, and a take then succeeds.
    witness: tests/test_spec_id_lock_callers.py::test_regate_declines_a_spec_id_another_process_holds_before_any_runtime_call
    positive_case: >-
      Beside a holder of `SA-0006`, the same spy records `network rm` of the
      task's probe network as regate's first runtime call.
    wrong_versions:
      - "`run_regate` takes no lock, as at your base, so its probes pre-clean a live task's Gate-only cell."
      - "The lock is taken after `_probe`, so the probe network is removed first."
      - "The lock is taken and let go before `_probe`, so nothing holds it while regate works."
      - "The lock is held around `_probe` alone and let go before `reverify`."
      - "The lock is let go before `record_regate`, so the criterion probes go unlocked."
      - "Regate takes a lock keyed `regate-<spec id>`, which a task's lock on the spec id never meets."
      - "A held lock raises out of `run_regate` rather than declining."
      - "Regate writes an empty text into the lock file, so a refused task reads no holder."
    covers:
      - set: the spec ids a holder's lock reaches
        members:
          - member: the spec id the task names
            driven_by: "`run_regate` takes no lock, as at your base, so its probes pre-clean a live task's Gate-only cell."
          - member: the same spec id lowercased
            driven_by: tests/test_spec_id_lock_callers.py::test_regate_declines_a_spec_id_another_process_holds_before_any_runtime_call
          - member: another spec id
            driven_by: tests/test_spec_id_lock_callers.py::test_regate_declines_a_spec_id_another_process_holds_before_any_runtime_call
          - member: a key of regate's own
            driven_by: "Regate takes a lock keyed `regate-<spec id>`, which a task's lock on the spec id never meets."
      - set: when the lock is read
        members:
          - member: at the first runtime call
            driven_by: "The lock is taken after `_probe`, so the probe network is removed first."
          - member: held, not only checked
            driven_by: "The lock is taken and let go before `_probe`, so nothing holds it while regate works."
          - member: during `reverify`
            driven_by: "The lock is held around `_probe` alone and let go before `reverify`."
          - member: at `record_regate`
            driven_by: "The lock is let go before `record_regate`, so the criterion probes go unlocked."
          - member: after a raise, and after a return
            driven_by: tests/test_spec_id_lock_callers.py::test_regate_declines_a_spec_id_another_process_holds_before_any_runtime_call
      - set: how a held lock ends regate
        members:
          - member: one `regate:` line and exit 1
            driven_by: "A held lock raises out of `run_regate` rather than declining."
      - set: what the holder's line names
        members:
          - member: "`saffron regate <task id>`"
            driven_by: "Regate writes an empty text into the lock file, so a refused task reads no holder."
  - claim: >-
      `_qualify_range` holds the spec id's lock, with the text
      `qualification`, around `session.probe_findings`. While another
      process holds it, no probe is made, and each probed finding is recorded
      `unverified` with a reason naming the holder's pid and text. The
      witness builds `tests/test_qualify.py`'s two-layer fixture with its
      `_build` helper, and wraps its probe double. Held as `TE-2`, then as
      `te-2`, `qualify` makes no probe call. Each of `f1`, `f2`, `f3`, `f4`,
      `f7`, `f8` and `f10` lands in the pool `unverified`, its reason naming
      the holder. Beside a holder of `TE-1`, one probe call is made for
      `TE-2`, and a take of `TE-2` inside it is refused naming
      `qualification`. A take succeeds after `qualify` returns.
    witness: tests/test_spec_id_lock_callers.py::test_qualification_probes_nothing_for_a_held_spec_id_and_says_why
    positive_case: >-
      Beside a holder of `TE-1`, the wrapped double records one call, for
      `TE-2`.
    wrong_versions:
      - "`_qualify_range` takes no lock, as at your base."
      - "A held lock raises out of `qualify` rather than marking the probes `unverified`."
      - "The lock is taken and let go before `session.probe_findings`."
      - "Qualification takes a lock keyed `qualify-<spec id>`, which a task's lock never meets."
      - "A held lock records each probed finding `unverified` with an empty reason."
      - "Qualification writes an empty text into the lock file."
    covers:
      - set: the spec ids a holder's lock reaches
        members:
          - member: the layer's spec id
            driven_by: "`_qualify_range` takes no lock, as at your base."
          - member: the same spec id lowercased
            driven_by: tests/test_spec_id_lock_callers.py::test_qualification_probes_nothing_for_a_held_spec_id_and_says_why
          - member: another layer's spec id
            driven_by: tests/test_spec_id_lock_callers.py::test_qualification_probes_nothing_for_a_held_spec_id_and_says_why
          - member: a key of its own
            driven_by: "Qualification takes a lock keyed `qualify-<spec id>`, which a task's lock never meets."
      - set: when the lock is read
        members:
          - member: during the probe call
            driven_by: "The lock is taken and let go before `session.probe_findings`."
          - member: after `qualify` returns
            driven_by: tests/test_spec_id_lock_callers.py::test_qualification_probes_nothing_for_a_held_spec_id_and_says_why
      - set: what a held lock leaves on each probed finding
        members:
          - member: the outcome `unverified`
            driven_by: "A held lock raises out of `qualify` rather than marking the probes `unverified`."
          - member: a reason naming the holder
            driven_by: "A held lock records each probed finding `unverified` with an empty reason."
      - set: the probed findings of the held layer
        members:
          - member: "`f1`, `f2`, `f3`, `f4`, `f7`, `f8` and `f10`, each asserted"
            driven_by: tests/test_spec_id_lock_callers.py::test_qualification_probes_nothing_for_a_held_spec_id_and_says_why
      - set: what the holder's line names
        members:
          - member: "`qualification`"
            driven_by: "Qualification writes an empty text into the lock file."
  - claim: >-
      `layer_cell` raises `cell_name_lock.LockHeld` before any runtime call
      while another process holds its layer's spec id. Otherwise it holds the
      lock, with the text `an end review's layer cell`, from before its first
      runtime call until its block exits by raise or by return. The witness
      holds the lock in this process with a spy at `runtime._call`. Held as
      `SY-1`, a layer cell for `SY-1`, and one for `sy-1`, each raise
      `LockHeld` naming the holder's pid and text, and the spy records
      nothing. Beside a holder of `SY-2`, the spy's first call is `rm -f
      saffron-endreview-SY-1`, and a take of `SY-1` there is refused naming
      that text. A take succeeds after the spy's raise. With `cell_up`,
      `cell_down` and `remove_container` faked, a take inside the block is
      refused, and one after it exits succeeds.
    witness: tests/test_spec_id_lock_callers.py::test_a_layer_cell_beside_a_held_spec_id_raises_before_any_runtime_call
    positive_case: >-
      Beside a holder of `SY-2`, the same spy records `rm -f` of the layer
      cell's container as its first runtime call.
    wrong_versions:
      - "`layer_cell` takes no lock, as at your base."
      - "The lock is taken after `runtime.remove_container`, so the container is removed first."
      - "The lock is taken and let go before the first runtime call."
      - "The layer cell takes a lock keyed `endreview-<spec id>`, which a task's lock never meets."
      - "The layer cell writes an empty text into the lock file."
    covers:
      - set: the spec ids a holder's lock reaches
        members:
          - member: the layer's spec id
            driven_by: "`layer_cell` takes no lock, as at your base."
          - member: the same spec id lowercased
            driven_by: tests/test_spec_id_lock_callers.py::test_a_layer_cell_beside_a_held_spec_id_raises_before_any_runtime_call
          - member: another spec id
            driven_by: tests/test_spec_id_lock_callers.py::test_a_layer_cell_beside_a_held_spec_id_raises_before_any_runtime_call
          - member: a key of its own
            driven_by: "The layer cell takes a lock keyed `endreview-<spec id>`, which a task's lock never meets."
      - set: when the lock is read
        members:
          - member: at the first runtime call
            driven_by: "The lock is taken after `runtime.remove_container`, so the container is removed first."
          - member: held, not only checked
            driven_by: "The lock is taken and let go before the first runtime call."
          - member: after a raise, and after the block exits
            driven_by: tests/test_spec_id_lock_callers.py::test_a_layer_cell_beside_a_held_spec_id_raises_before_any_runtime_call
      - set: what the holder's line names
        members:
          - member: "`an end review's layer cell`"
            driven_by: "The layer cell writes an empty text into the lock file."
  - claim: >-
      `package_ready_task` returns `Refused` while another process holds the
      spec id, before its probe network, and the reason names the holder's
      pid and text. Otherwise it holds the lock, with the batch tree it was
      handed as its text, around the probe network alone, and lets it go
      before `package_phase.package`. The witness fakes `ready_task`, the
      mirror, the mutants and the image, with a spy at `runtime._call`. Held
      as `SY-1`, then as `sy-1`, it returns `Refused` naming the holder, the
      spy records nothing, and `package` is not reached. Beside a holder of `SY-2`, the
      spy's first call is `network rm saffron-hostprobe-sy-1`, and a take of
      `SY-1` there is refused naming the batch tree. A take succeeds after
      the spy's raise. With the probe faked, a take inside the replaced
      `package` succeeds.
    witness: tests/test_spec_id_lock_callers.py::test_package_refuses_a_spec_id_another_process_holds_before_its_probe_network
    positive_case: >-
      Beside a holder of `SY-2`, the same spy records `network rm` of the
      probe network as the first runtime call.
    wrong_versions:
      - "`package_ready_task` takes no lock, as at your base."
      - "The lock is held until `package_ready_task` returns, so `package` is called under it."
      - "The lock is taken and let go before the probe network."
      - "A held lock raises out of `package_ready_task` rather than returning `Refused`."
      - "`package_ready_task` writes an empty text into the lock file."
    covers:
      - set: the spec ids a holder's lock reaches
        members:
          - member: the spec id it packages
            driven_by: "`package_ready_task` takes no lock, as at your base."
          - member: the same spec id lowercased
            driven_by: tests/test_spec_id_lock_callers.py::test_package_refuses_a_spec_id_another_process_holds_before_its_probe_network
          - member: another spec id
            driven_by: tests/test_spec_id_lock_callers.py::test_package_refuses_a_spec_id_another_process_holds_before_its_probe_network
      - set: when the lock is read
        members:
          - member: at the probe network's first runtime call
            driven_by: "The lock is taken and let go before the probe network."
          - member: after a raise
            driven_by: tests/test_spec_id_lock_callers.py::test_package_refuses_a_spec_id_another_process_holds_before_its_probe_network
          - member: while `package` is called
            driven_by: "The lock is held until `package_ready_task` returns, so `package` is called under it."
      - set: how a held lock ends the call
        members:
          - member: "`Refused`, never a raise"
            driven_by: "A held lock raises out of `package_ready_task` rather than returning `Refused`."
      - set: what the holder's line names
        members:
          - member: the batch tree
            driven_by: "`package_ready_task` writes an empty text into the lock file."
---

## Context

Backlog item **b-d9ed45**, tier 2, status `partial`. It cites `DESIGN.md`
§5.1. This spec depends on `SA-0431`, which edits `saffron/regate.py` too.
Every line below was read on `main`, and resolves unchanged on
`SA-0431`'s branch. Where that branch moves a line, the sentence names its
function and no line.

**What `SA-0422` already holds.** `run_task` holds one lock per spec id
around `run_one_cell` (`saffron/task.py:980`). Its root is fixed per user,
`/tmp/saffron-cell-names-<uid>` (`saffron/task.py:634`), so every home of
one user meets at one file. `cell_name_lock.lock` takes it
(`saffron/cell_name_lock.py:80`). A held lock raises `LockHeld` at once
(`saffron/cell_name_lock.py:40`). Its text reads
`"<spec id>'s cell is held by pid <pid>'s <text>"`
(`saffron/cell_name_lock.py:58`). The file is the spec id lowercased. An
autouse fixture points the root at a fresh directory for every test
(`tests/conftest.py:130-144`).

**Four callers pre-clean a spec-keyed name outside that lock.** None of
them is reached from inside `run_task`'s lock. `run_one_cell` imports
none of `regate`, `qualify`, `end_review` or `commit_review`.

- **`saffron regate`.** `_probe` removes `saffron-regate-probe-<task id>`
  before it allocates it (`saffron/regate.py:101-102`). `run_regate` calls
  it (`:228`), then `reverify`, then `session._apply_criterion_probes`
  (`:285`), and calls `record_regate` last. `_apply_criterion_probes`
  (`saffron/cell/session.py:2089`) enters the Gate-only branch of
  `critic_cell`. That branch names
  `saffron-gate-<SPEC>` (`:1592`) and removes it before it creates it
  (`:1607`). A task's own probes name the same cell, as
  `_gate_cell_suite` enters that branch with `network=None`
  (`saffron/cell/session.py:1878-1882`). `saffron regate`
  and `saffron adopt`'s own regate take no home lock
  (`saffron/home_lock.py:3-4` names the commands that take one). So a regate on one home can
  remove the live Gate-only cell of that home's own task for the same spec
  id. That is read from the code, not measured.
- **Qualification.** `_qualify_range` calls `session.probe_findings`
  (`saffron/qualify.py:235`). That enters the same Gate-only branch
  (`saffron/cell/session.py:1992-1998`). A `RuntimeError` there marks each
  probed finding with its text as the reason (`saffron/qualify.py:249-255`).
- **The end review's layer cell.** `layer_cell` names
  `saffron-endreview-<SPEC>` (`saffron/end_review.py:781-783`) and removes
  the container before `cell_up` (`:788`). `saffron review` reaches it
  through `saffron/commit_review.py:275`, with no home lock.
- **`saffron package`'s probe network.** `package_ready_task` removes
  `saffron-hostprobe-<spec id>` before it allocates it
  (`saffron/task.py:1576-1577`). Before that line,
  `package_ready_task` returns `ready_task`'s refusal (`saffron/task.py:1562`).

**How a leftover looks to the cell runtime.** Measured on apple/container
1.7.1, `container run -d --name saffron-cell-PROBE-1 alpine:3 sleep 300`
returned at once. `container ls` then listed it as `running`, and
`container inspect` gave `status.state` `running`, with no field naming who
started it. A cell's container is started the same way, detached with
`sleep infinity` (`saffron/cell/worktree.py:179-182`). So a process killed
with SIGKILL leaves its container `running`. That last step is reasoned
from the two, not measured.

**The settled scope.** The operator settled these. A second process on one
spec id is refused before any container is touched, naming the holder. A
leftover from a dead process is still cleaned up. Refuse rather than
rename.

## Problem

Four callers outside `run_task` remove a spec-keyed runtime name with no
lock. Each takes the spec id's lock through `cell_name_lock.lock`, with
`saffron.task.CELL_NAME_LOCK_ROOT` read at call time, so the test fixture
reaches it.

1. **`run_regate`.** After every decline it makes now, take the lock for
   the task's spec id with the text `saffron regate <task id>`. Hold it
   from before the image build through the return. On a held lock, print
   `regate:` and the raise's text, and return 1.
2. **`_qualify_range`.** Take the lock for its `spec_id` with the text
   `qualification`, around `session.probe_findings`. Treat a held lock as
   the `RuntimeError` there is treated: each probed finding gets the
   raise's text as its reason.
3. **`layer_cell`.** Take the lock for `fields.spec_id` with the text
   `an end review's layer cell`, before `runtime.remove_container`. Hold it
   until the `finally` that calls `cell_down` has run. Let `LockHeld` raise.
   `_review_one_layer` turns it into a lens error
   (`saffron/end_review.py:450-480`). A stack batch's spec review records
   an `error` round and a miss (`saffron/batch.py:770-787`).
4. **`package_ready_task`.** Take the lock for `spec_id` with `str(out_dir)`
   as its text, around the probe network's block alone. On a held lock,
   return `Refused` with the raise's text as its reason.

Name each in its function's docstring, and keep each within ten lines.

## Out of scope

- **`saffron-regate-probe-<task id>`.** Each home mints its own task ids,
  so two homes' regates of two spec ids can share one probe network. The
  spec id's lock does not meet that.
- **`saffron-pkg-<label>-<sha>`.** PACKAGE's own cells carry the packaged
  sha. `run_task` calls PACKAGE after its lock lets go, and so does
  `package_ready_task`. Two homes packaging one sha share those names.
- **A by-hand regate or review on the same home.** Either now holds the
  spec id's lock while it works. A task started beside it returns
  `Refused`, and a plain batch keeps that spec started for the night
  (`saffron/batch.py:312`, `:358`).
- **Two users on one host.** Each user has a root of their own.
- **The batch tree.** Each home has its own, so two homes never share one
  `events.jsonl`.

## Notes for the agent

**Edit or new.** The lock taken in each caller is new code. No `find`
written now pins its spelling, so no mutant on the ref pins one, and
`witness` reports `skip` for all four criteria.

**No `retired_first`.** Each new refusal reads a lock another process holds
while it works. No queued spec is refused by it.

**The arms weighed.** A check that reads the cell runtime for a live
container of the spec's name was the other arm. The measured leftover above
is `running` too, so that check would refuse every task after a SIGKILL. The
lock tells the two apart: the kernel drops an `flock` when its holder dies.

**One key for every name a spec id carries.** The layer cell's and the
probe network's names collide only with their own kind. They take the spec
id's own key anyway, so one rule covers each spec-keyed name, and a name
family added later is covered too. The cost is a layer cell, or `saffron
package`, refused while a task of that spec id is live elsewhere. A stack
batch's spec review opens its layer cell right before that spec's own
`run_task`, which would refuse the spec a moment later.

**A held lock during qualification is recorded.** Each probed finding
keeps its `unverified` fact, though the cause passes. That matches a
`RuntimeError` from the same call.

**`tests/test_spec_id_lock_callers.py`.** Import `saffron.cell_name_lock`
only inside a test body. Hold a lock with `cell_name_lock.lock(root, id,
text)` in this process. A second open of the file in one process conflicts
with the first, measured on macOS, and `tests/test_cell_name_lock.py` relies
on the same. Match the holder's pid with a word boundary.

- **The spy.** Patch `runtime._call` to record its argv, then try the lock
  and record its `LockHeld` text, then raise a `KeyboardInterrupt`
  subclass. Catch `BaseException` around each call and assert its type.
- **Regate.** Import `_build_fixture`, `_seed_task`, `_seeding_ledger`,
  `_gh_pr_view`, `_fake_reverify` and `_install_probe_fakes` from
  `tests/test_regate.py`. Call `regate.run_regate` itself, with
  `repo_image.build_cell_image` replaced. Each case needs its own
  directory. Wrap the ledger's `record_regate` on the instance.
- **Qualification.** Call `tests/test_qualify.py`'s `_build` in a fresh
  directory per case. Wrap the `session.probe_findings` it installed.
- **The layer cell.** Build `end_review.LayerFields` as
  `tests/test_end_review.py:1722-1730` does.
- **Package.** Replace `task.ready_task` with a `ReadyTask` for a parsed
  spec. Replace `preflight.prepare_mirror`, `mutants.attach_mutants_at` and
  `repo_image.build_cell_image`. Use a `Ledger` with a `MemoryRecord`, its
  `task_mutants_commit` replaced on the instance.

**Size.** A prototype on `SA-0431`'s branch measured 293
changed tokens outside the test paths with `size_gate`, docstrings
included. `estimated_lines` is that over four. `ty check`, ruff,
`.saffron/gates/dead` and `.saffron/gates/structure` were clean. Each
witness failed with the source reverted. Every wrong version listed above
failed its witness there. `tests/test_regate.py`, `tests/test_qualify.py`,
`tests/test_end_review.py`, `tests/test_commit_review.py`,
`tests/test_task.py`, `tests/test_follow_up.py`, `tests/test_cli.py`,
`tests/test_adopt_stack_layer.py`, `tests/test_session.py` and
`tests/test_cell_name_lock.py` passed. The whole suite was not driven.
