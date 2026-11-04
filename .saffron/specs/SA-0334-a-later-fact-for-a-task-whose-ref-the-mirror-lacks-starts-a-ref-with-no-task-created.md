---
id: SA-0334
title: "A later fact for a task whose ref the mirror lacks starts a ref with no `task_created`, which the fold refuses"
type: bug
priority: 1
estimated_lines: 48
estimate_measured: true
touches:
  - saffron/record/refs.py
  - saffron/record/routed.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_cli.py
  - tests/test_regate.py
  - tests/test_commit_review.py
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
  - saffron/record/migrate.py
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
  - tests/test_record_migrate.py
budget_usd: 46
max_attempts: 3
max_turns: 235
risk: standard
acceptance:
  - claim: >-
      Through the `Ledger`'s `RoutedRecord`, a `task_state` fact for a task
      whose ref its mirror lacks first fetches that one ref from the task's own
      origin, then appends on it. The witness drives two mirrors: a pruned one
      that lost the ref, and a fresh one that `upsert_repo` points the repo row
      at. In each, the new commit's parent is the origin's head, the push is a
      fast-forward, and the mirror then reads what the origin reads. The fetch
      takes no other ref and prunes none. The pruned mirror keeps a ref only it
      holds, and neither mirror gains a ref of the origin's that it did not
      ask for.
    witness: tests/test_record_routed.py::test_a_later_fact_for_a_ref_the_mirror_lacks_lands_on_the_origins_history
    wrong_versions:
      - The fetch calls `RefsRecord.fetch`, whose `--prune` over every task ref drops the ref the mirror holds alone.
      - The fetch takes every task ref with no prune, so the mirror gains the origin's other ref.
      - The fetch reads only the record's own `remote`, which the routed record never has, so the routed append raises where the origin holds the ref.
      - The fetch lands only in `FETCH_HEAD`, and the append then starts a root ref beside the origin's history.
      - Only the pruned mirror is handled, because the fetch runs only where the mirror already holds some task ref.
  - claim: >-
      Where the origin lacks the ref too, an append through the `RoutedRecord`
      raises `RecordError`, and neither the mirror nor the origin gains a ref.
      The witness drives a task that a ledger with no record created, whose
      next state write goes through a `RoutedRecord`. In the same mirror, a
      routed `create_task` and a later fact on the ref it starts each run no
      `git fetch`. The witness records the argv of every `git` call
      `saffron.record.refs` makes, and asserts that none of them is a fetch.
    witness: tests/test_record_routed.py::test_a_later_fact_neither_the_mirror_nor_the_origin_holds_writes_no_ref
    wrong_versions:
      - The fetch's failure is caught and the append writes the lone ref as it does today.
      - The refusal is a `ValueError` rather than a `RecordError`.
      - Every append fetches first, so a ref the mirror alone holds raises on its next fact.
      - The lone ref is written to the mirror and then refused, so the mirror keeps it.
      - Every append but `task_created` tries the one-ref fetch and ignores its failure, then raises only if the ref is still absent, so a ref the mirror holds costs a fetch on each fact.
      - A `task_created` fact tries the fetch too and ignores its failure, so every new task costs a fetch.
  - claim: >-
      `RefsRecord.append` raises `RecordError` for every kind in `KINDS` but
      `task_created` on a ref its repo lacks. For each kind the witness uses a
      fresh bare repo, and refuses with a record that has no origin and with
      one whose `remote` lacks the ref. Neither repo gains a ref. A `RefsRecord` built with a `remote` that holds the ref
      fetches it before it appends, for every one of those kinds, so each push
      is a fast-forward.
    witness: tests/test_record_refs.py::test_a_ref_is_never_started_by_a_fact_other_than_task_created
    mutant:
      file: saffron/record/refs.py
      find: '"task_created"'
      replace: '"task_state"'
    wrong_versions:
      - Only `task_state` is refused, so another kind still starts a lone ref.
      - A record with no origin appends the lone ref as it does today, and only a record with one refuses.
      - A record built with a `remote` never fetches from it, so a later fact in a new repo raises.
      - Only a `task_state` fact fetches, so another kind raises where its remote holds the ref.
      - A record with a `remote` ignores the fetch's failure and writes the lone ref, then pushes it.
  - claim: >-
      A `task_created` fact on a ref the repo lacks still starts that ref with
      no fetch from a `RefsRecord`'s `remote`. So a second writer's diverged
      history is still refused at its push as `StaleWriter`.
    witness: tests/test_record_refs.py::test_a_diverged_push_is_refused_not_forced
    preserves: true
    wrong_versions:
      - Every fact on an absent ref fetches first, `task_created` included, and an origin lacking the ref is passed over, so the second writer appends onto the first's history and its push lands.
---

## Context

Backlog item **b-d4b847**, under item 170 and §3 of
`docs/superpowers/specs/2026-09-20-the-record-on-git-refs-design.md` (the
record design below). Every line here was read at `4c53e0bb`. This is the
writer-fetches-first arm of that item's Done looks like, which the operator
chose. The fold stays as it is.

**How a fact reaches a ref today.** Every `saffron` command shares one `Ledger`
built with a `RoutedRecord` (`saffron/cli.py:357-360`). Each write method
commits its row, then appends one fact (`saffron/ledger.py:650-654`).
`RoutedRecord.append` reads the task's mirror and origin from `record_home`
(`saffron/ledger.py:601-616`). It hands the fact to a `RefsRecord` over that
mirror with no remote (`saffron/record/routed.py:26-38`). `RefsRecord.append`
resolves the task's ref (`saffron/record/refs.py:58`). An absent ref gets a
commit with no parent, whatever the fact's kind
(`saffron/record/refs.py:63-69`).

**Why the mirror lacks the ref.** A repo row's mirror path is named by a digest
of the checkout's path (`saffron/cli.py:1994-2000`). `upsert_repo` repoints the
row's `mirror_path` on a conflict over `origin` (`saffron/ledger.py:1092-1099`). So a run from another
checkout routes every older task of that origin to a fresh mirror.
`ensure_mirror` clones a fresh one from the checkout, which holds no task refs
(`saffron/repos/mirror.py:69-92`). A mirror can also lose a ref.
`RefsRecord.fetch` prunes every task ref the remote lacks
(`saffron/record/refs.py:94-98`). `ensure_mirror`'s own fetch no longer does,
since it excludes `refs/saffron/*` (`saffron/repos/mirror.py:72-81`).

**What the lone ref costs.** `_facts_of` refuses a task with no `task_created`
fact (`saffron/record/fold.py:68-80`). A strict `saffron fold` raises
`UnreadableTask`, and `--skip-unreadable` folds the task to no rows. Measured on
2026-11-04, `~/.saffron/mirrors/saffron-f6b7e296a444.git` holds 65 task refs.
Eleven hold no `task_created`. Each holds `task_merged_head` then a `MERGED`
`task_state`, which is `reconcile`'s merge stamp (`saffron/reconcile.py:218-219`).
None of the eleven is on
this repo's origin, which holds 35. The other 37 mirrors under
`~/.saffron/mirrors/` hold no task ref at all.

**The protected text, as amended by hand.** No cell edits these.
The last sentence of `DESIGN.md` §4.6's rule 1 says a skipped `saffron migrate`
starts a ref with no `task_created`. It now says that fact raises instead. The record design's
§3 says the wiring appends with no remote. It now says a later fact on an absent
ref fetches that one ref from the origin first.

## Problem

1. **Refuse the lone ref.** Take a fact in `RefsRecord.append` whose kind is not
   `task_created`, on a ref the repo lacks. It must find that ref before it writes.
   Fetch the one ref from the task's origin into the same ref name. Then
   resolve it again as the parent. Where there is no origin, or the origin
   lacks the ref, raise `RecordError` and write nothing.
2. **Name the origin.** A `RefsRecord` built with a `remote` fetches from it.
   `RoutedRecord.append` already has the task's origin from its lookup
   (`saffron/record/routed.py:26-33`). Pass it through, since that record has
   no remote and must keep its appends local.
3. **Leave `task_created` alone.** A fresh key's first fact still starts its
   ref with no fetch. `new_task_key` mints 16 random bytes
   (`saffron/record/contract.py:50-54`), so the origin cannot hold the key. A fetch there would cost every task
   one round trip to the forge. It would also let a second writer append onto
   the first's history, which `test_a_diverged_push_is_refused_not_forced`
   refuses.

## Out of scope

- The fold, and `--skip-unreadable`. The operator chose the writer's arm.
- The eleven lone refs already in the live mirror. A later fact on one of them
  finds its ref present, so it appends with no fetch, as today. A push of one
  still publishes it.
- A ref fetched from the origin that itself holds no `task_created`. None of
  the origin's 35 refs is one of the eleven.
- `MemoryRecord`. Tests use it to build the lone logs the fold must refuse
  (`tests/test_fold.py:292`, `:356`).
- Pushing the keys a command appended before it exits (b-4eaaa4), and the
  event each append emits (b-6677b6). Both stack on this spec. Keep the fetch
  inside `RefsRecord` and `RoutedRecord.append`, so neither has to move it.
- A strict append can stop a whole `reconcile` run from another checkout's mirror.
  One task with no ref anywhere raises, and no row catches it. The
  operator settled on strictness, with `saffron migrate` run before this spec's
  pull request merges. b-4eaaa4's push at command exit narrows the gap.
- `saffron migrate`'s up-front fetch (`saffron/record/migrate.py:614-616`). Its
  first fact for a task it holds no ref for is `task_created`.

## Notes for the agent

**Mutants and new code.** The refusal and the fetch are new code inside two
existing methods. Write the kind literal the refusal compares against once in
`saffron/record/refs.py`, and no second time. Criteria 1 and 2 declare no mutant, so `witness` reports `skip` for
them. Criterion 4 names a test that exists. Do not run the wrong versions
yourself.

**git's answer to a missing ref.** Measured on the host's git 2.54.0 on
2026-11-04, `git fetch <url> <ref>:<ref>` for a ref the remote lacks exits 128
with `couldn't find remote ref`. A remote that is not a repository also exits
128. Both are a `RecordError` from `_git` already
(`saffron/record/refs.py:38-52`), so neither needs telling apart. Say in the
raised message that the fact needs a ref that opens on `task_created`.
The same probe found that the fetch left the mirror's other task refs as they
were, and took none of the remote's others.

**No credential prompt.** Run the fetch with `GIT_TERMINAL_PROMPT=0` in its
environment. An https origin that wants a credential then fails at once rather
than waiting on a terminal. `_git_bytes` passes the parent's environment today
(`saffron/record/refs.py:39-43`). A failed fetch and a missing ref then both read
as no ref, and nothing is written either way. No witness drives the prompt.

**The witnesses.** Each runs against a real bare origin under `tmp_path`.
`tests/test_record_routed.py` isolates git config with its autouse fixture,
and a new test there inherits it. Simulate the pruned mirror with
`git update-ref -d` on the task's ref. Simulate the fresh mirror by calling
`upsert_repo` again with the same origin and a new bare mirror, which is the
production path above. Criterion 1's witness also seeds a ref only the mirror
holds, and one only the origin holds. Criterion 2's witness creates its task
through a `Ledger` built with no record, closes it, and reopens the same file
with a `RoutedRecord`. Criterion 3's witness loops over `KINDS` from
`saffron.record.contract`, so a kind added later is driven too. It loops twice.
For each kind, the first loop inits a fresh bare repo. It refuses that kind there
with a no-remote record and with a record whose remote lacks the ref. The second
loop appends each kind into its own fresh bare repo, built with a remote that
holds the ref. So each append finds its ref absent. Criterion 2's witness spies
by monkeypatching `subprocess.run` as `saffron.record.refs` reaches it, and
records each argv.

**What the witnesses leave undriven.** Criterion 1 writes `task_state` alone
through the routed path. The routed code does not branch on kind, and
criterion 3 drives every kind one layer down. Criterion 2's spy watches one
routed `task_created` and one `task_state` on a present ref. No witness drives a
routed `task_created` past an origin that holds its key, since a minted key is
on no origin.

**Every new test must fail with the source reverted.** Each new witness above
does. At base the lone ref is written, the push is refused as stale, or no
error is raised.

**Comments that become false.** The comment above `RefsRecord(mirror)` in
`saffron/record/routed.py:30-31` says every append is local. Keep its point,
that the push is the only write to the origin. Add that a later fact on an
absent ref reads the origin first. `RefsRecord.append` carries no docstring
today. A new one stays within ten lines.

**Callers this leaves alone.** `saffron fold` builds a `RefsRecord` with no
remote and only reads (`saffron/cli.py:2673`). `saffron migrate` appends
`task_created` first for any task it holds no ref for
(`saffron/record/migrate.py:108-111`).

**Tests that seed a task with no record.** A prototype of this change failed 22
existing tests, measured with `uv run pytest`. Each seeds its task through a
`Ledger` built with no record, so the task has no ref anywhere. The command under
test then writes a later fact through its own `RoutedRecord`, which now raises.
Seed each as a night does, through a `Ledger` built with a `RoutedRecord`. Change
no assertion.

These 22 node ids failed on the prototype, and each passed once reseeded:

- `tests/test_cli.py::test_reconcile_writes_what_gh_says_or_withholds_when_it_cannot_answer[gh-answers]`
- `tests/test_cli.py::test_a_command_files_each_fact_it_writes_in_the_tasks_own_mirror`
- `tests/test_cli.py::test_adopt_writes_the_url_gh_names_onto_the_specs_newest_task`
- `tests/test_cli.py::test_a_merged_adopted_pull_request_admits_the_child_of_a_not_implemented_parent`
- `tests/test_cli.py::test_adopt_moves_a_task_whose_regate_is_green_on_the_adopted_head_to_ready_for_review`
- `tests/test_cli.py::test_adopt_keeps_the_state_of_a_task_whose_regate_is_red_declined_or_on_another_head`
- `tests/test_cli.py::test_adopt_of_a_ready_task_records_the_url_and_runs_no_regate`
- `tests/test_cli.py::test_adopt_whose_regate_raises_exits_two_with_the_pull_request_recorded`
- `tests/test_cli.py::test_queue_reconciles_before_it_scans_so_the_refusal_gate_sees_current_state`
- `tests/test_cli.py::test_queue_schedules_a_task_reconcile_moved_into_a_requeue_state`
- `tests/test_cli.py::test_the_batch_scan_orphans_the_queue_row_of_each_task_it_stamps`
- `tests/test_commit_review.py::test_review_reads_the_review_commits_with_both_end_review_lenses_and_charges_the_task`
- `tests/test_commit_review.py::test_review_starts_a_restacked_branchs_range_at_the_packaged_commits_rebased_copy`
- `tests/test_commit_review.py::test_review_reads_a_task_against_its_newest_recorded_spec_text`
- `tests/test_commit_review.py::test_review_exits_one_when_either_lens_files_a_blocker`
- `tests/test_commit_review.py::test_review_exits_two_when_a_lens_or_its_cell_breaks_and_charges_the_failed_turn`
- `tests/test_commit_review.py::test_review_frames_the_spec_body_as_review_commits_over_a_packaged_head`
- `tests/test_commit_review.py::test_review_stopped_by_sigterm_tears_its_cell_down_and_exits_143`
- `tests/test_regate.py::test_regate_runs_the_tasks_gates_over_the_pull_requests_head_and_records_green`
- `tests/test_regate.py::test_regate_prints_each_new_failure_records_the_count_and_exits_one`
- `tests/test_regate.py::test_regate_prints_the_singular_for_exactly_one_new_failure`
- `tests/test_regate.py::test_regate_passes_reverify_the_exemption_its_task_directory_holds`

How each file is reseeded:

- `tests/test_cli.py`: eleven tests that drive `reconcile`, `queue`, `adopt` and
  the batch scan. `_seed_repo` makes a bare mirror before any task exists
  (`tests/test_cli.py:3588-3590`). So the seeding ledger's lookup can be
  `record_home`, as the command's is. Several name an `https://github.com/`
  origin. Until they are seeded, each tries a fetch from it, which failed at
  once on the host for want of a credential. Once seeded, their mirror holds the
  ref, so no test fetches from it.
- `tests/test_regate.py` and `tests/test_commit_review.py`: four and seven
  tests. Each command makes its own mirror after seeding, so no mirror exists
  then. Route the seeding ledger's facts to the fixture's bare origin
  (`origin_url`). The command's fresh mirror then fetches the ref from there,
  which is criterion 1's path.
