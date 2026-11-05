---
id: SA-0337
title: "`saffron migrate` refuses every ref a live cell started, so a merged task's later facts never reach its record"
type: bug
priority: 1
estimated_lines: 80
estimate_measured: true
touches:
  - saffron/record/migrate.py
  - tests/test_record_migrate.py
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
  - saffron/record/fold.py
  - saffron/record/memory.py
  - saffron/record/refs.py
  - saffron/record/routed.py
  - saffron/repos/**
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/events.py
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/phases/**
  - tests/test_fold.py
  - tests/test_cli.py
  - tests/test_ledger.py
budget_usd: 30
max_attempts: 3
max_turns: 150
risk: standard
acceptance:
  - claim: >-
      `migrate` tops up a ref a live cell started. The witness's ledger holds
      a merged task with every one of the thirteen compared kinds. Its ref
      holds a live cell's `task_created`, which differs from the ledger's in
      `at`, `batch_key`, `policy_sha`, `risk` and one extra key. The ref also
      holds `task_engine`, `task_policy` and `spec_finding`, each with a
      payload the fold can place. It holds two `task_state` facts and a
      `task_push`. It holds the first fact of each compared kind it holds, and
      both gate results of the first attempt. The
      task counts as migrated and keeps every held fact. The rest of each
      compared kind follows in `_facts_for_task`'s order, then the ledger's
      `MERGED` `task_state`, and nothing else. A fold of that ref gives
      `MERGED`, the merged head, `READY_FOR_REVIEW` as the pushed state, and
      every attempt, finding, end review, qualification, stack layer and stack
      finish row. A second ref, the pushed `EXHAUSTED` task's exact prefix
      cut short before its `task_push`, is completed as today, `task_push`
      included.
    witness: tests/test_record_migrate.py::test_a_ref_a_live_cell_started_is_topped_up_and_folds_to_the_ledgers_rows
    wrong_versions:
      - Every ref with facts takes the top-up, so a ref cut short before its `task_push` never gains it.
      - The tail is grouped by kind rather than kept in `_facts_for_task`'s order.
      - The ledger's `task_state` is put before the tail rather than after it.
      - "`task_created` is compared like any other kind, so the live cell's `policy_sha`, `risk` and extra key refuse the ref."
      - The ledger's `task_created` is appended again after the record's own.
      - Every held fact of a kind is appended again, not only those past the record's count.
      - A held fact's `at` is compared, so the live cell's microseconds refuse the ref.
      - A null `batch_key` on a held fact is compared, so a fact written before its run joined a batch refuses the ref.
  - claim: >-
      For each of the thirteen compared kinds, a ref holding a live
      `task_created` and the ledger's first fact of that kind is migrated. It
      gains the rest of every compared kind, then the ledger's state. The
      same ref holding every fact of that kind, the last one's payload
      carrying one extra key, is refused with today's reason and gains no
      fact. So is the ref holding every fact of that kind and one more. For
      each kind with two facts, a ref holding both true facts is migrated and
      gains the rest of every other compared kind, then the ledger's state.
      A ref holding only the second is refused. So is a ref holding both, the
      first carrying one extra key. A ref holding
      no `task_created` is refused the same way.
    witness: tests/test_record_migrate.py::test_each_compared_kind_that_disagrees_or_runs_past_the_ledger_is_refused
    wrong_versions:
      - Facts are compared by count alone, so a held fact with a different payload agrees.
      - Only the first held fact of each kind is compared.
      - Only the last held fact of each kind is compared.
      - A held fact agrees when it equals any ledger fact of its kind and the count fits.
      - A held payload agrees when it holds every key the ledger's does, extra keys and all.
      - A kind the record holds more of than the ledger is let through, with nothing appended for it.
      - The compare is correct, but any ref holding two or more facts of one compared kind is refused.
      - A ref with no `task_created` is topped up, which leaves a ref the fold refuses.
      - The refusal reason is reworded.
  - claim: >-
      The top-up sets aside exactly these differences between a held fact and
      the ledger's. Its `at`. On a `gate_result`, `schema_version`,
      `collected` and `uncollected`. A null `batch_key`. Anything in
      `task_created`. Any fact of a kind `migrate` never writes, which the
      witness drives for every member of `KINDS` outside the sixteen. Each
      alone, on a ref that otherwise holds every fact the ledger owes, leaves
      the task migrated with nothing appended. A differing `summary` on a
      `gate_result`, a `schema_version` key on an `attempt_closed`, and a set
      `batch_key` that differs on an `attempt_closed` each refuse the ref.
    witness: tests/test_record_migrate.py::test_the_top_up_sets_aside_only_its_named_differences
    wrong_versions:
      - The three gate result keys are set aside on every kind.
      - A held fact's `batch_key` is never compared, null or not.
      - Only `task_engine`, `task_policy` and `spec_finding` are set aside, so another kind `migrate` never writes refuses the ref.
      - The ledger's `task_state` is appended to a ref that already agrees in full.
  - claim: >-
      A topped-up ref gains the ledger's `task_state` last, and only where
      the record's own state differs from the ledger's. The record's state
      is the `state` of its last `task_state` or `task_package` fact, held or
      appended, and `QUEUED` where it holds neither. The witness drives five
      refs. One
      ends on an `EXHAUSTED` `task_state` and then a package carrying the
      ledger's `READY_FOR_REVIEW`. One holds the ledger's `PLAN_REJECTED`. One
      holds a live `task_created` alone for a `QUEUED` task. Each of those gains
      nothing. The fourth ends on `READY_FOR_REVIEW` then a `task_push`, for
      an `EXHAUSTED` task whose ledger facts hold a `task_push`. It gains the
      `EXHAUSTED` `task_state` alone. The fifth ends on a `REVIEWING`
      `task_state` with no package, for a `READY_FOR_REVIEW` task. It gains
      the ledger's package alone, and no `task_state`.
    witness: tests/test_record_migrate.py::test_a_topped_up_ref_ends_on_the_ledgers_state_only_where_its_own_differs
    wrong_versions:
      - Only the last `task_state` fact is read, so the packaged ref gains a second `READY_FOR_REVIEW`.
      - The ledger's state is always appended.
      - A ref holding no state fact reads as no state rather than `QUEUED`, so it gains a `QUEUED` `task_state`.
      - The ledger's `task_push` is appended with its `task_state`.
      - The state is read from held facts only, so the ref that gains a package gains a `READY_FOR_REVIEW` `task_state` too.
  - claim: >-
      A ref holding no facts is migrated exactly as today, every fact
      `_facts_for_task` writes included, and folds back to the rows its task
      held.
    witness: tests/test_record_migrate.py::test_a_migrated_ledger_folds_back_to_the_rows_its_tasks_held
    preserves: true
    wrong_versions:
      - An empty ref takes the top-up path, and is refused for holding no `task_created`.
---

## Context

Backlog item **b-9c7001**, under item 170 and the record design
(`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md`).
Every line here was read at `5b8814fb`. The operator chose the arm in which
migrate tops up by kind.

**What `migrate` does today.** For each task it builds the full fact list
from the ledger's rows (`saffron/record/migrate.py:103`). It reads what the
record holds under the task's key (`saffron/record/migrate.py:104`). It
refuses the task unless that list equals the first facts it would write
(`saffron/record/migrate.py:105-109`). Otherwise it appends the rest and
counts the task migrated (`saffron/record/migrate.py:110-112`).
`migrate_and_push` pushes every migrated key to its origin
(`saffron/record/migrate.py:620-628`).

**Why a live ref never passes.** The ledger's `task_created` is rebuilt from
the task row. Its `at` is the row's whole-second time
(`saffron/ledger.py:357-360`), given an offset
(`saffron/record/migrate.py:68-72`). A live fact's `at` keeps microseconds
(`saffron/ledger.py:644`).
Its `batch_key` is the run's batch (`saffron/record/migrate.py:305`). Its
`risk` is `None` for `standard` (`saffron/record/migrate.py:325`). A live fact
takes its `batch_key` from the run's batch at the time it is written
(`saffron/ledger.py:632-646`). Measured on 34 of the live refs,
`task_created` holds a null `batch_key` where the ledger's is set. A live `gate_result` carries the whole
`GateResult` dump (`saffron/ledger.py:2200`). The payload `_gate_result_facts` builds has
no `schema_version`, `collected` or `uncollected` key
(`saffron/record/migrate.py:276-292`). A live ref also holds kinds `migrate`
never writes, and a `task_state` per state.

**What a fold makes of the order.** `task_state` sets the row's state
(`saffron/ledger.py:871-877`). `task_package` sets the state and sets
`pushed_in_state` to its own `state` (`saffron/ledger.py:879-899`).
`task_push` sets `pushed_in_state` to the state the row holds before it
(`saffron/ledger.py:901-908`). `task_created` inserts the row at `QUEUED`
(`saffron/ledger.py:791`). So a `task_state` appended after the record's own
`task_push` and `task_package` changes the state and leaves
`pushed_in_state` as the record set it. The fold refuses a task with no
`task_created` fact (`saffron/record/fold.py:76-79`).

**Measured on the live refs, 2026-11-04.** `saffron migrate` refused 35 of 371
tasks. Read-only against `~/.saffron/ledger.db` and
`~/.saffron/mirrors/saffron-f6b7e296a444.git`, each of the 35 holds, per
compared kind, the first facts the ledger's list holds. That holds once
the five differences criterion 3 names are set aside. Without the null
`batch_key` member, `SA-0323`'s ref is refused. Its first attempt facts
were written before its run joined batch 58. A prototype of this change,
run in memory over those 35 refs, refused none. A fold of the result gave
31 `MERGED`, 2 `PLAN_REJECTED`, 1 `NOT_IMPLEMENTED` and 1
`READY_FOR_REVIEW`, the ledger's own states. It matched the ledger's
`merged_head_sha`, `pushed_sha`, `pr_url` and spend, and its row counts per
task. `pushed_in_state` differed on 32, where the ledger holds null and the
fold holds the record's pushed state.

## Problem

1. **Top up a ref that is no prefix.** Compare such a ref kind by kind. The
   compared kinds are the thirteen `migrate` writes other than
   `task_created`, `task_push` and `task_state`. These are `attempt_opened`,
   `attempt_closed`, `gate_result`, `finding`, `rebuttal`,
   `task_merged_head`, `task_package`, `stack_layer`, `end_review`,
   `qualification`, `spec_review`, `spec_text` and `stack_finish`. For each,
   the record's facts must be the first of the ledger's facts of that kind,
   in order, under the normalisation below. Then append every ledger fact
   of a compared kind past the record's count. Keep `_facts_for_task`'s
   order across kinds. The task counts as migrated, and the existing push
   path pushes it.
2. **The normalisation is closed.** Once these are set aside, a held fact
   must equal the ledger's. The fact's `at`. On a
   `gate_result`, the `schema_version`, `collected` and `uncollected` keys,
   which the ledger's fact never carries. A `batch_key` that is null on the
   held fact. Nothing else. Do not treat a held payload with extra keys as
   agreeing.
3. **The three kinds a live cell writes its own way.** The record's
   `task_created` is never compared and never appended again, and its own
   copy wins. A record holding none is refused. `task_push` is never
   compared and never appended by a top-up. `task_state` is not compared.
   After the tail, append the ledger's `task_state` once, last, where the
   record's state differs from the ledger's. Read the record's state from
   its last `task_state` or `task_package` fact, held or appended, and as
   `QUEUED` where it holds neither.
4. **Kinds `migrate` never writes are set aside.** A held fact of a kind
   outside `migrate`'s sixteen is not compared, and keeps its place.
5. **Everything else is refused as today.** That covers a held fact of a
   compared kind that disagrees. It also covers a kind the record holds more
   of than the ledger. Each keeps today's reason, and nothing is appended.
6. **Leave today's path alone.** A ref that is empty, or an exact prefix of
   the list, is completed exactly as today.

## Out of scope

- The repair of the 35 live refs. It is the operator's run of
  `saffron migrate --from ~/.saffron/ledger.db` after this pull request
  merges. No criterion reaches the live ledger, the live mirror or origin.
- The push. A topped-up key is counted migrated, and `migrate_and_push`
  already pushes every migrated key (`saffron/record/migrate.py:620-628`).
  No new witness drives a top-up through a git origin.
- A ledger `task_push` the record lacks. A top-up never appends one. None
  of the 35 live refs is owed one, measured.
- `pushed_in_state`. The fold of a topped-up ref keeps the record's own,
  where the ledger often holds null.
- A stale spend. A ref that gains `attempt_closed` facts but no
  `task_state` or `task_package` folds to the old `spent_usd_est`. The fold
  rolls spend up on those two kinds alone (`saffron/ledger.py:871-899`).
  Measured on the 35 live refs, no ref gains `attempt_closed` without one.
- A top-up the fold rejects. A held `gate_result`, `attempt_closed` or
  `rebuttal` whose `attempt_opened` or `finding` is appended after it counts
  as migrated. The fold cannot place it. Measured on the 35 live refs, no
  held fact has its owner appended.
- `saffron/cli.py`, `saffron fold` and the record backends.

## Notes for the agent

**Mutants and new code.** The top-up is new code inside `migrate`, so
criteria 1 to 4 declare no mutant and `witness` reports `skip` for them.
Criterion 5 names a test that exists today and passes unchanged.

**Keep the prefix path first.** Run the top-up only where today's whole-list
compare fails. A ref cut short before `task_push` must still gain it, and
the top-up never appends one.

**Name the closed sets once.** Spell the thirteen compared kinds and the
three gate result keys once each in `saffron/record/migrate.py`. A comment
there stays within two lines.

**The witnesses.** Each builds its source with a `Ledger` under `tmp_path`,
then runs `migrate` into a fresh `MemoryRecord` for the list it owes. Build
each live ref from that list, with `dataclasses.replace`. A live `at` keeps
microseconds. A live `task_created` has a null `batch_key` and `policy_sha`,
`risk` set to `standard`, and an extra key. Set the ledger row's
`policy_sha`, so the live null differs from it. Attach the helper's run to a
batch with `attach_run_to_batch` (`saffron/ledger.py:1302`). Every ledger
fact then carries a set `batch_key`, so a null one on a held fact is a real
difference. Criterion 1 puts it on the first held `attempt_opened`, and
criterion 3 on the first `attempt_closed`. Criterion 3's differing set
`batch_key` sits on that `attempt_closed` too. The helper's two gate results
per attempt name different gates. For every kind with two facts, the
second differs from the first in payload once normalised. So a ref holding
only the second is a real disagreement. One source helper can serve all
four new witnesses. Its merged task needs two facts of each compared kind
where the ledger allows it. `task_merged_head`, `task_package`,
`stack_layer` and `stack_finish` carry one each. A single-layer stack files
its `stack_finish` under that layer's task (`saffron/ledger.py:1807-1825`).
Criterion 1's live ref holds no `task_merged_head`, `stack_layer` or
`stack_finish`, and the first of every other compared kind. It also holds
the first two gate results, which both belong to the first attempt, and
the package. Its `task_engine`, `task_policy` and `spec_finding` carry
payloads the fold can place. A `spec_finding` needs `n`, `position`,
`severity`, `fixes`, `claim`, `criterion`, `file` and `line`
(`saffron/ledger.py:1004-1020`). Criterion 1's second ref is the helper's
pushed `EXHAUSTED` task. A task with a `pr_url` writes a package and no
`task_push` (`saffron/record/migrate.py:452-471`). Criterion 3 reads the sixteen
as the kinds `migrate` wrote for the helper's two tasks, and loops over
`KINDS` from `saffron.record.contract` minus those. Its extra fact carries
an empty payload. Criterion 4's `EXHAUSTED` task gets `record_push` before
its state, so the ledger's list holds a `task_push` the witness can see.
Its fifth task gets `set_task_package` with `READY_FOR_REVIEW`. Assert the
ledger's list holds that package before asserting the ref gains it.

**Every new test must fail with the source reverted.** Each new witness
does. At base the whole-list compare refuses every live ref.

**Two existing tests change.** A prototype of this change failed two tests in
`tests/test_record_migrate.py`. Each seeded a refusal the top-up now accepts.

- `test_a_rerun_completes_a_migration_cut_short_and_refuses_a_record_that_disagrees`.
  Key 4 corrupts `task_created`'s `spec_sha`, which the top-up never
  compares. Corrupt key 4's second fact instead, the `attempt_opened`, and
  follow it with the true third. The suite then still pins an earlier fact
  that disagrees before a later one that agrees. Key 6
  differs in `at` alone. It is now migrated and gains nothing, so move it
  to the migrated list. The `batch_key` check at its end sets `batch_key` on
  `task_created`. Set it on the second fact instead, behind the true first.
  Its comment says facts compare whole, which is no longer true. Say that a
  set `batch_key` that differs disagrees.
- `test_migrate_writes_each_repos_tasks_to_its_own_origin_and_refuses_a_disagreeing_one`.
  The bad task's ref holds a lone `task_created`, which now agrees. Have the
  other writer and the seeded record also hold an `attempt_opened` for it.
  The ledger holds no attempt for that task, so the ref is still refused.

Change no other assertion in either test.

**The docstrings.** The module docstring describes the whole-list compare
(`saffron/record/migrate.py:1-24`). Add a sentence for the top-up. The
`Migration` docstring says a migrated key holds the full fact list
(`saffron/record/migrate.py:47-51`). A topped-up key does not, so correct it.
A new docstring stays within ten lines.
