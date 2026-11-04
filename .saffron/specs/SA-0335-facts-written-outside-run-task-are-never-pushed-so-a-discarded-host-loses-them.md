---
id: SA-0335
title: "Facts written outside `run_task` reach the mirror and are never pushed, so a discarded host loses them"
type: bug
priority: 1
estimated_lines: 33
estimate_measured: true
depends_on: [SA-0334]
touches:
  - saffron/record/routed.py
  - saffron/cli.py
  - tests/conftest.py
  - tests/test_record_routed.py
  - tests/test_cli.py
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_finish.py
  - tests/test_qualify.py
  - tests/test_follow_up.py
  - tests/test_draft.py
  - tests/test_reconcile.py
  - tests/test_session.py
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
  - saffron/record/__init__.py
  - saffron/record/contract.py
  - saffron/record/refs.py
  - saffron/record/fold.py
  - saffron/record/memory.py
  - saffron/record/migrate.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/finish.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/draft.py
  - saffron/reconcile.py
  - saffron/replay.py
  - saffron/events.py
  - saffron/repos/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - tests/test_task_record.py
  - tests/test_record_refs.py
budget_usd: 64
max_attempts: 3
max_turns: 320
risk: standard
acceptance:
  - claim: >-
      `RoutedRecord.push_unpushed` pushes each task key appended through the
      record since that key's last push, once, to that task's own origin, and
      returns an empty list. The witness drives every kind in `KINDS`, two
      tasks in two repos with two origins, a key appended three times, a key
      `push` carried after its last append, a key `push` carried and then
      appended again, and a key whose ref an earlier record started and pushed.
      A second call pushes nothing.
    witness: tests/test_record_routed.py::test_the_exit_push_carries_each_appended_key_once_to_its_own_origin
    wrong_versions:
      - Every append pushes at once, so a key appended three times is pushed three times.
      - The exit pushes every key ever appended, so a key `push` already carried with no later fact is pushed again.
      - A key is kept only from its `task_created` fact, so a key an earlier record started is never pushed.
      - A key is kept only from `task_created` and `task_state` facts, so a later `decision` or `finding` stays on the mirror.
      - The keys are kept in `Ledger._commit_and_append` rather than in the `RoutedRecord`, so an append made on the record directly is never pushed.
      - Every key is pushed to the first key's origin.
      - The exit pushes each key without dropping it, so a second call pushes it again.
      - "`push` leaves its key kept, so the exit pushes a key `run_task` already carried."
      - Each key is pushed once, when it is first kept, so its later facts stay on the mirror.
  - claim: >-
      A refused exit push is returned beside its key and never raised. The
      witness drives two refusals: a diverged origin, returned as
      `StaleWriter`, and an origin that is not a repository, returned as a
      `RecordError` that is not a `StaleWriter`. A key kept after both is
      still pushed. A second call pushes neither refused key again. A key whose
      own `push` raised is not pushed at exit until a later fact lands on it.
    witness: tests/test_record_routed.py::test_a_refused_exit_push_is_returned_with_its_key_and_never_pushed_again
    wrong_versions:
      - The first refusal raises out of the call.
      - A refusal stops the loop, so the key kept after it is never pushed.
      - A non-fast-forward is returned as a plain `RecordError`, so it no longer reads as `StaleWriter`.
      - Only `StaleWriter` is caught, so an origin that is not a repository raises.
      - A refused key stays kept, so the second call pushes it again.
      - "`push` drops its key only when the push lands, so a key `run_task` failed to push is pushed again at exit."
  - claim: >-
      `saffron`'s entry point pushes every key the command appended before it
      returns. The witness drives each of the twelve commands it dispatches
      over its shared `Ledger`: `cell`, `batch`, `draft`, `queue`, `reconcile`,
      `regate`, `review`, `adopt`, `package`, `finish`, `chains` and `replay`.
      It drives five ways out: a return of 0, a return of 1, a raise read as
      exit 2, a SIGTERM read as exit 143, and a `KeyboardInterrupt` that
      leaves `main`. In each the origin holds the command's fact, and the exit
      code is the command's own.
    witness: tests/test_cli.py::test_every_command_pushes_the_facts_it_appended_before_it_exits
    wrong_versions:
      - The exit push sits after the `try` rather than in its `finally`, so a command that returns from inside it pushes nothing.
      - The exit push sits in the `except Exception` branch, so a command that returns pushes nothing.
      - The exit push runs only for the commands `_guarding_sigterm` wraps, so `draft`, `queue`, `reconcile`, `package`, `chains` and `replay` push nothing.
      - The exit push is skipped while an exception is in flight, so a `KeyboardInterrupt` leaves the fact on the mirror.
      - The exit push runs after `ledger.close()`, so the lookup of each key's origin raises.
  - claim: >-
      A command whose exit push is refused prints one line for each refused
      key, naming the key and the refusal's type, and exits with its own code.
      The witness drives a `StaleWriter` and a plain `RecordError` in one
      command that returns 0, and a `StaleWriter` in one that raises and exits
      2. A refusal's text spans several lines, and no line of it is printed on
      its own. A key the same command pushed is named on no line.
    witness: tests/test_cli.py::test_a_refused_record_push_is_printed_with_its_key_and_leaves_the_exit_code
    wrong_versions:
      - A refusal raises out of `main`.
      - A refusal turns a 0 exit into 2.
      - The refused key is printed with no type, so a stale writer reads like a dead origin.
      - Every kept key is printed, the pushed one included.
      - Nothing is printed.
      - The refusal's text is printed as git wrote it, so its `hint:` lines stand alone.
  - claim: >-
      Each fact `run_stack_batch` writes reaches the origin at the exit push.
      The witness drives the `stack_layer` fact on each layer the batch
      records, and the three spec review terminals, `GATE_ERROR`,
      `RATE_LIMITED` and `SPEC_WITHHELD`, each on its own minted task.
    witness: tests/test_batch.py::test_a_stack_batchs_layer_and_spec_review_facts_reach_the_origin_at_exit
    wrong_versions:
      - Each key is pushed once, when it is first kept, so a layer's `stack_layer` fact and a terminal state stay on the mirror.
      - A key is kept only from `task_created` and `task_state` facts, so a layer whose only new fact is `stack_layer` stays on the mirror.
  - claim: >-
      The `end_review` and `finding` facts `review_stack` writes reach the
      origin at the exit push, on layers an earlier command pushed.
    witness: tests/test_end_review.py::test_an_end_reviews_facts_reach_the_origin_at_exit
    wrong_versions:
      - A key is kept only from `task_created` and `task_state` facts.
      - A key is kept only from its `task_created` fact.
  - claim: >-
      The `stack_finish` fact `publish_finish` writes reaches the origin at the
      exit push, on a top layer an earlier command pushed.
    witness: tests/test_finish.py::test_a_finishing_layers_fact_reaches_the_origin_at_exit
    wrong_versions:
      - A key is kept only from `task_created` and `task_state` facts.
      - A key is kept only from its `task_created` fact.
  - claim: >-
      The `qualification` facts `qualify` writes reach the origin at the exit
      push, on both layers an earlier command pushed.
    witness: tests/test_qualify.py::test_a_qualification_fact_reaches_the_origin_at_exit
    wrong_versions:
      - A key is kept only from `task_created` and `task_state` facts.
  - claim: >-
      The facts `write_follow_ups` writes reach the origin at the exit push.
      The witness drives the accepted follow-up's attempt and `spec_text`
      facts on its minted task, and the attempts it charges to a pooled layer
      an earlier command pushed.
    witness: tests/test_follow_up.py::test_a_follow_up_writers_facts_reach_the_origin_at_exit
    wrong_versions:
      - A key is kept only from `task_created` and `task_state` facts, so the pooled layer's attempts stay on the mirror.
  - claim: >-
      Every fact a `draft_spec` task carries reaches the origin at the exit
      push. The witness drives five endings: a draft that runs with its spec
      text recorded, one escalated, one that waits, one that errors, and one
      whose review raises.
    witness: tests/test_draft.py::test_a_drafts_facts_reach_the_origin_at_exit
    wrong_versions:
      - Each key is pushed once, when it is first kept, so a draft's later facts stay on the mirror.
  - claim: >-
      Each state `reconcile` writes reaches the origin at the exit push, on
      tasks an earlier command pushed. The witness drives one task for each of
      five: `MERGED` with its `task_merged_head`, `REJECTED`,
      `CHANGES_REQUESTED`, `APPROVED`, and the `ORPHANED` stamp
      `stamp_orphaned` writes.
    witness: tests/test_reconcile.py::test_each_state_reconcile_writes_reaches_the_origin_at_exit
    wrong_versions:
      - A key is kept only from its `task_created` fact, so a task an earlier command created is never pushed.
  - claim: >-
      The `ORPHANED` state `_drive_cell` writes when the cell raises reaches
      the origin at the exit push, though `run_task` re-raises before its own
      push.
    witness: tests/test_session.py::test_an_orphaned_stamp_from_a_raising_cell_reaches_the_origin_at_exit
    wrong_versions:
      - Each key is pushed once, when it is first kept, so the `ORPHANED` state stays on the mirror.
  - claim: >-
      `saffron adopt` leaves its `task_push` and `task_package` facts on the
      origin when it exits 0, on a task an earlier command pushed.
    witness: tests/test_cli.py::test_an_adopted_pull_request_reaches_the_origin_before_adopt_exits
    wrong_versions:
      - A key is kept only from its `task_created` fact, so the adopted task is never pushed.
  - claim: >-
      `saffron package` leaves the facts PACKAGE writes through
      `package_ready_task` on the origin when it exits 0, on a task an earlier
      command pushed.
    witness: tests/test_cli.py::test_a_package_commands_facts_reach_the_origin_before_it_exits
    wrong_versions:
      - A key is kept only from its `task_created` fact, so the packaged task is never pushed.
  - claim: >-
      Every fact `replay` writes for its task reaches the origin at the exit
      push, and the origin's ref then reads what the mirror's reads.
    witness: tests/test_replay.py::test_a_replayed_tasks_facts_reach_the_origin_at_exit
    wrong_versions:
      - Each key is pushed once, when it is first kept, so the replayed task's later facts stay on the mirror.
---

## Context

Backlog item **b-4eaaa4**, under item 170 and §3 of
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md` (the
record design below). Every line here was read at `ae94968f`, with
`SA-0334`'s change applied. This is the push-at-command-exit arm of the
item's Done looks like, which the operator chose.

**How a fact reaches the origin today.** Every command but `fold`, `migrate`,
`serve` and `next-id` opens one `Ledger` built with a `RoutedRecord`
(`saffron/cli.py:355-360`). `watch` never writes to it. Each write method
appends one fact after its row commits (`saffron/ledger.py:650-661`).
`record_findings` calls `_append` on its own (`saffron/ledger.py:2110-2113`).
`RoutedRecord.append` writes the fact into the task's mirror with no remote.
So nothing reaches the origin until `RoutedRecord.push`, and only
`Ledger.push_record` calls that (`saffron/ledger.py:618-627`). Only `run_task`
calls `push_record`, once, in a `finally` after its cell returned
(`saffron/task.py:1060-1071`). `main` closes the ledger in its own `finally`
(`saffron/cli.py:415-416`).

**What stays on the mirror.** Twelve writers append after that push, or with
no `run_task` at all. A stack batch writes its layers after each task
(`saffron/batch.py:603`). Its spec review ends a task `GATE_ERROR`,
`RATE_LIMITED` or `SPEC_WITHHELD` before any cell (`saffron/batch.py:741`,
`:781`, `:791`, `:800`). The end review writes findings and `end_review`
facts (`saffron/end_review.py:529-541`). The finishing layer writes
`stack_finish` (`saffron/finish.py:532`, `:543`). `qualify`'s
`_qualify_range` writes `qualification` (`saffron/qualify.py:108`, `:198`). The follow-up writer charges its
attempts and records its text (`saffron/follow_up.py:278-279`, `:462`). A
draft's facts never meet `run_task` (`saffron/draft.py:137-289`).
`reconcile` writes each state it reads from GitHub, and the scan's
`ORPHANED` stamp (`saffron/reconcile.py:186`, `:218-219`, `:225`). `adopt`
records its pull request (`saffron/cli.py:2954`, `:2961`). `replay` writes a
whole task (`saffron/replay.py:53-109`). `package_ready_task` runs PACKAGE
with no `run_task` (`saffron/task.py:1391`). A raising cell stamps `ORPHANED`
(`saffron/cell/session.py:3839-3846`), and `run_task` re-raises before its
push (`saffron/task.py:897-923`).

ADR 10 says the record on `refs/saffron/*` lets a host VM be discarded
(`docs/adr/0010-saffron-ships-as-an-engine-each-operator-deploys.md:126-127`).
That holds only once these facts leave the host.

**The protected text, as amended by hand.** No cell edits it. The record
design's §3 says `run_task` pushes the task's ref once as the task ends, and
that a refused push is an event. It now says each command also pushes, as it
exits, every ref it appended to since that ref's last push. A refused exit push
is a printed line.

## Problem

1. **Keep the keys.** `RoutedRecord.append` keeps each task key it appended,
   once its fact lands. `RoutedRecord.push` drops its key before it pushes,
   whether the push lands or not. So a key `run_task` pushed is not pushed
   again unless a later fact lands on it.
2. **Push them once.** Add `RoutedRecord.push_unpushed`. It pushes each kept
   key once, through `push`, in append order. It catches every `Exception` a
   push raises and returns `(key, exception)` for each one. It never raises
   for a push.
3. **Push at exit.** In `saffron/cli.py`'s `main`, bind the `RoutedRecord` to a
   name before the `Ledger` is built. In the `finally` that closes the ledger,
   call `push_unpushed` before `close`. Print one line for each refusal,
   naming the key and the exception's type. Fold the exception's text onto
   that line, since git's refusal spans several. Leave the command's exit
   code as it was.
4. **Keep the tests off the network.** Several `tests/test_cli.py` tests name
   an `https://github.com/` origin, and their exit push now reaches it. Add an
   autouse fixture to `tests/conftest.py` that sets `GIT_ALLOW_PROTOCOL` to
   `file`, skipped for `cell`-marked tests as `no_host_tool_exec` is.

## Out of scope

- `run_task`'s own push, which stays as it is (`saffron/task.py:1060-1071`).
- A second push of a refused key. A refusal is reported and never pushed again
  by this command. A non-fast-forward stays `StaleWriter`, as `refs.py` raises
  it.
- The event each append emits (b-6677b6, `SA-0336`), which stacks on this
  spec.
- `saffron migrate`, which pushes each ref it writes on its own
  (`saffron/record/migrate.py:619-622`). `saffron fold` builds a `Ledger` with
  no record (`saffron/cli.py:2674`).
- A SIGKILL, or a SIGTERM that lands during the exit push itself.
  `_guarding_sigterm` restores the old handler in its own `finally`, before
  `main`'s runs (`saffron/cli.py:590-595`).
- The protected sentences above.

## Notes for the agent

**Mutants and new code.** Every criterion is new code: a new method, a new
loop in an existing `finally`, and new tests. No criterion declares a mutant,
so `witness` reports `skip` for each. Do not run the wrong versions yourself.

**One push per key per command.** A batch's task can be pushed twice in one
command: once by `run_task`, and again at exit when a later fact landed on it.
That is one push per run of facts, never one per append.

**git, measured on the host's git 2.54.0 on 2026-11-04.** With
`GIT_ALLOW_PROTOCOL=file`, a push to an `https` URL exits 128 at once with
`transport 'https' not allowed`. A local path and a `file://` URL still clone
and push. A `url.<path>.pushInsteadOf` entry rewrites a push to that URL onto a
local path, and leaves `git remote get-url` reading the URL.

**Each writer witness runs in one order.** Build a `Ledger` the way `main`
builds it: a `RoutedRecord` whose lookup is `ledger.record_home`, over a repo
row naming a bare mirror and a bare origin under `tmp_path`. Build that once,
as a fixture in `tests/conftest.py`. Seed what the writer needs. Call
`push_unpushed()` as an earlier command's exit would. Run the writer, then call
`push_unpushed()` again, which returns `[]`. For each task the writer wrote,
the origin's ref then resolves to the mirror's, and its facts hold the
writer's kind or state. A writer that mints its own task skips the first call.

**The arrangement for each writer.** Each existing helper below already
drives its writer with a ledger. Where it builds its own `Ledger`, give it an
optional argument that hands it the routed one instead.

- `run_stack_batch`: `tests/test_batch.py`'s `_mint_and_review_arrangement`,
  as `test_each_spec_review_is_a_fact_on_its_specs_minted_task` drives it. It
  ends `TE-2` `SPEC_WITHHELD`, `TE-4` and `TE-6` `GATE_ERROR`, and `TE-5`
  `RATE_LIMITED` first. Read the layers from the ledger's `stack_layers` rows.
- `review_stack`: `tests/test_end_review.py`'s `_stack_ledger`, as
  `test_each_layers_end_review_folds_back_from_the_record` drives it.
- `publish_finish`: `tests/test_finish.py`'s `_stack`, as
  `test_a_green_finish_pushes_its_own_branch_and_opens_its_draft_pull_request`
  drives it. Its `remote.git` serves as the origin.
- `qualify`: `tests/test_qualify.py`'s `_build`, as
  `test_each_layers_qualifications_are_facts_numbered_within_its_task` drives
  it.
- `write_follow_ups`: `tests/test_follow_up.py`'s `_build`, as
  `test_a_follow_up_writers_attempt_records_the_model_its_session_names`
  drives it. Its pooled groups charge `task_102`, a layer seeded first.
- `draft_spec`: `tests/test_draft.py`'s `_build_cases`, one task for each of
  the cases named `run`, `escalate`, `wait1`, `err1` and `raise_r1`.
- `reconcile`: `tests/test_reconcile.py`'s `_task` and `_FakeGh`, with
  `stamp_orphaned=True` and an `IMPLEMENTING` task for the stamp.
- `ORPHANED`: `tests/test_session.py`'s `_drive`, with its `record` argument
  and `saffron.repos.image.build_cell_image` raising `CellRuntimeError`. Make
  `tmp_path / "m.git"` a bare repo first. Point
  `saffron.phases.package.real_remote` at a bare origin, since `run_one_cell`
  names its origin with it (`saffron/cell/session.py:2236-2240`).
- `adopt` and `package` run through `cli.main`. Their commands match the repo
  row by its GitHub origin, so keep that origin in the row. Point
  `GIT_CONFIG_GLOBAL` at a file whose `pushInsteadOf` sends that URL to a bare
  repo on disk. Copy `test_adopt_of_a_ready_task_records_the_url_and_runs_no_regate`
  and `test_package_probes_the_host_then_runs_package_on_the_rebuilt_task`.
  The fake `package` writes `record_push` through the ledger it is handed.
- `replay`: `tests/test_replay.py`'s `target` fixture. `replay` upserts its
  own repo row with the target as origin (`saffron/replay.py:53`).

Criterion 3 replaces each command's handler on `saffron.cli` with a stub that
appends through the `Ledger` it is handed. For `replay` that is
`saffron.cli.replay`, and for `cell` it is `_run_cell`. A stub under
`_guarding_sigterm` reaches exit 143 with `signal.raise_signal`.

**Building the two refusals.** A second writer diverges the origin. It is a
`RefsRecord` with that origin as its `remote`, so its append to the ref pushes
first. An origin that is not a repository is a path the test
removes after seeding.

**Tests this changes.** A prototype of this change on `SA-0334`'s source,
with the fixture in step 4, failed no existing test that `SA-0334` leaves
passing. Without the fixture, eleven `tests/test_cli.py`
tests pushed to `https://github.com/o/r.git` or
`https://github.com/owner/repo.git` at exit.

**What the witnesses leave undriven.** Criteria 5 to 12 and 15 drive each
writer with the routed `Ledger`, then call `push_unpushed` as `main`'s
`finally` does. Criterion 3 drives that `finally` for every command. Their
union holds because no command builds a second `Ledger` with a record.
`main` builds the only one. `_fold` builds its own with no record
(`saffron/cli.py:2674`), and so does `_next_id` (`saffron/cli.py:2739`). Criterion 5 drives each terminal state on
one path. A revision's own raise, wait or error writes the same three states
again (`saffron/batch.py:857`, `:875`, `:880`), and no witness drives that
path. Criterion 6 drives the `record_end_review` calls its script reaches.
Criterion 10 drives five of `_build_cases`'s twenty-three cases.

**Every new test must fail with the source reverted.** Each calls
`push_unpushed`, or reads an origin only the exit push fills. The prototype's
fifteen witnesses all failed with `saffron/` reverted.
