---
id: SA-0264
title: "No command names a by-hand pull request as a task's, so a `NOT_IMPLEMENTED` parent's child stays refused after it merges"
type: feature
priority: 2
depends_on: [SA-0254]
estimated_lines: 415
estimate_measured: true
touches:
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/reconcile.py
  - tests/test_cli.py
  - tests/test_reconcile.py
  - CLAUDE.md
  - README.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/record/**
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/phases/**
  - saffron/report/**
  - saffron/view/**
  - saffron/cell/**
  - saffron/gates/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 48
max_attempts: 3
max_turns: 230
risk: standard
acceptance:
  - claim: >-
      `reconcile` asks GitHub about a `NOT_IMPLEMENTED` row that carries a
      `pr_url`, and moves it on a merge alone. A merged answer writes
      `MERGED`, records the reported head in `merged_head_sha`, and lands
      the id in `merged`. Every other answer leaves the row
      `NOT_IMPLEMENTED`, and its id reaches none of `rejected`,
      `changes_requested` or `approved`. The witness drives every answer
      `_pr_status` can return as an object: closed, open with changes
      requested, open and marked ready, open as a draft, open with no
      `isDraft` field, and an unrecognised `state`. It drives the three it
      turns into `None` too: a non-zero exit, unparseable output and a JSON
      value that is not an object. Each of those three lands in `unasked`.
      A `NOT_IMPLEMENTED` row with a NULL `pr_url` and one with an empty
      `pr_url` are never asked.
    witness: tests/test_reconcile.py::test_a_not_implemented_task_with_an_adopted_pull_request_moves_only_on_a_merge
    mutant:
      file: saffron/reconcile.py
      find: 'if state == "MERGED":'
      replace: 'if state == "MERGED!":'
    wrong_versions:
      - A version that adds `NOT_IMPLEMENTED` to the pending set alone, so a closed pull request writes `REJECTED` and a ready one writes `APPROVED`.
      - A version that asks about a `NOT_IMPLEMENTED` row whose `pr_url` is the empty string.
      - A version that writes `MERGED` for a `NOT_IMPLEMENTED` row and never records its merged head.
      - A version that drops a `NOT_IMPLEMENTED` row silently when `gh` gives no answer, so it never reaches `unasked`.
  - claim: >-
      `saffron adopt <spec id> <pr> --repo <path>` asks `gh pr view` for
      pull request `<pr>` in the repository the checkout's `origin` names.
      It writes the URL `gh` prints onto the spec's newest task in that
      repo's ledger, and exits 0. The row's `state`, `branch`,
      `pushed_sha`, `added` and `removed` are unchanged, and an older task
      of the same spec is untouched. The witness drives a newest task in
      each state `adopt` takes. `NOT_IMPLEMENTED` and `READY_FOR_REVIEW`
      carry a NULL `pr_url`, and `EXHAUSTED` carries an empty one beside a
      recorded push and diff stat. Its fake `gh` prints a URL whose owner
      and repository differ in case from the slug, so a URL built from the
      slug fails it.
    witness: tests/test_cli.py::test_adopt_writes_the_url_gh_names_onto_the_specs_newest_task
    wrong_versions:
      - A version that writes onto the spec's oldest task rather than its newest.
      - A version that takes a `NOT_IMPLEMENTED` task alone.
      - A version that reads an empty `pr_url` as a pull request already carried.
      - A version that builds the URL from the slug and the number without asking `gh`.
      - A version whose write sets `added` and `removed` to NULL.
      - A version whose write sets the state to `READY_FOR_REVIEW`.
  - claim: >-
      `saffron adopt` exits 1 and leaves every task row exactly as it was
      when it refuses. It refuses a repo with no ledger row and a spec with
      no task in the repo, and its line names the spec id. It refuses a
      newest task that already carries a `pr_url`, and the line names that
      URL. The witness drives one such task in each of the three states the
      command takes. It refuses a newest task in any state but the three it takes,
      and the line names the state. The witness drives every other member
      of `saffron.ledger.TaskState`, and a refused newest task above an
      older task `adopt` would take. None of these asks `gh` anything. It
      also refuses when `gh` names no pull request, and the line names the
      number. The witness drives a non-zero exit and a zero exit that
      prints nothing.
    witness: tests/test_cli.py::test_adopt_refuses_with_exit_one_and_writes_nothing
    wrong_versions:
      - A version that falls back to an older task the command would take when the newest is refused.
      - A version that refuses a carried `pr_url` on a `READY_FOR_REVIEW` task alone, and overwrites one on a `NOT_IMPLEMENTED` or `EXHAUSTED` task.
      - A version that asks `gh` before it reads the ledger.
      - A version that accepts a zero exit from `gh` that printed no URL.
      - A version that refuses `MERGED` and `REJECTED` alone among the other states.
      - A version that exits 0 for a spec with no task.
  - claim: >-
      An adoption is a fact in the record. On a ledger built with a record,
      the write `saffron adopt` makes appends to it. A `fold` of that
      record into a fresh ledger rebuilds the adopted row with the adopted
      URL as its `pr_url`. Its `state`, `branch`, `pushed_sha`, `added`
      and `removed` are what they were before the adoption. The witness
      runs the command over a record-backed ledger for a `NOT_IMPLEMENTED`
      row and for an `EXHAUSTED` row with a recorded push and diff stat.
    witness: tests/test_cli.py::test_an_adopted_pull_request_is_a_fact_the_fold_keeps
    wrong_versions:
      - A version that writes `pr_url` with a bare SQL update and appends no fact.
      - A version whose fact carries `added` and `removed` as NULL.
  - claim: >-
      A parent spec whose only task ended `NOT_IMPLEMENTED`, with no push
      and no pull request, refuses its child, and the reason names
      `NOT_IMPLEMENTED`. After `saffron adopt` names a pull request for that
      task the child is still refused. After `saffron reconcile` reads that
      the pull request merged, the parent's task is `MERGED` with no
      `pushed_sha`. `build_queue` over the same specs then admits the child
      and refuses nothing. The witness drives both commands through
      `saffron.cli.main` and scans after each.
    witness: tests/test_cli.py::test_a_merged_adopted_pull_request_admits_the_child_of_a_not_implemented_parent
    mutant:
      file: saffron/scheduler.py
      find: 'DEPENDENCY_MERGED = "MERGED"'
      replace: 'DEPENDENCY_MERGED = "MERGED_ANYWHERE"'
    wrong_versions:
      - A version that adds the command and leaves `reconcile` skipping a `NOT_IMPLEMENTED` row.
  - claim: >-
      An `EXHAUSTED` row with a draft still moves on no answer but a merge.
    witness: tests/test_reconcile.py::test_an_exhausted_task_moves_on_no_answer_but_a_merge
    preserves: true
  - claim: >-
      A `READY_FOR_REVIEW` row still moves on a closed pull request and on
      changes requested, as well as on a merge.
    witness: tests/test_reconcile.py::test_a_head_is_recorded_only_for_an_observed_merge
    preserves: true
---

## Context

Backlog item **b-a7e5f3**, found in the spec loop's run 16 on `SA-0129`.
It cites `DESIGN.md` §4.2 and §5.7. Its related item b-111c56 is done.
Every line number below was read at `0a5e3e5c`.

**`SA-0129` left nothing to follow.** Its one task row is task 143 in
the operator's ledger. It reads `NOT_IMPLEMENTED` with a NULL `pr_url`
and a NULL `pushed_sha` (read on 2026-10-10). The operator
took it by hand as #502, and #502 merged.

**The scheduler then refuses the child.** A parent in `merged_anywhere`
admits its child first (`saffron/scheduler.py:590`). That set holds a
spec with a `MERGED` row under any spec sha (`saffron/scheduler.py:923-927`).
`SA-0131`'s landed-push admission reads a recorded `pushed_sha` and skips
a row without one (`saffron/scheduler.py:931-946`, `:942`). So
`SA-0129`'s child met the last refusal. That refusal names the parent's
newest state and says it is not merged (`saffron/scheduler.py:641`).

**`reconcile` never asks about the row.** It skips a row with no
`pr_url`, or a state outside `PR_PENDING_STATES` other than `EXHAUSTED`
(`saffron/reconcile.py:162`). `PR_PENDING_STATES` holds
`READY_FOR_REVIEW`, `APPROVED` and `CHANGES_REQUESTED`
(`saffron/reconcile.py:42`). `SA-0251` added the `EXHAUSTED` half, and
only a merged answer moves such a row (`saffron/reconcile.py:182`).

**Nothing writes a `pr_url` but PACKAGE.** The one write is the
`task_package` fact `set_task_package` builds
(`saffron/ledger.py:1554-1585`), applied by `_apply`
(`saffron/ledger.py:818-838`). Its one caller is PACKAGE's `_finish`
(`saffron/phases/package.py:998-1007`). No subcommand names a pull request
as a task's (`saffron/cli.py:110-236`).

**Every ledger write is a fact.** A write method builds its fact with
`_build_fact` and applies it with `_commit_and_append`
(`saffron/ledger.py:569-601`). `Fact` refuses a kind
outside `KINDS` (`saffron/record/contract.py:19-45`, `:82`). A fold
deletes a task's rows and re-applies its facts (`saffron/ledger.py:603-609`).
So a `pr_url` written without a fact is gone after a fold. `KINDS` must
equal `factory:FactKind` (`tests/ontology/test_vocabulary_agrees_with_code.py:174`).

**`reconcile` already runs before every scan.** `_resolve_queue` calls it
before `build_queue` (`saffron/cli.py:1510`). `saffron reconcile` calls it
on its own (`saffron/cli.py:2081-2097`).

## Problem

A pull request opened by hand for a task whose cell pushed nothing can
merge, and the ledger never learns of it. The task stays
`NOT_IMPLEMENTED`, so every spec that depends on it stays refused. The
workaround was to retire the parent to `done/` early, in #503.

Add a `saffron adopt` subcommand that names a by-hand pull request as a
task's. Have `reconcile` ask GitHub about a `NOT_IMPLEMENTED` row that
carries one. A merged answer then writes `MERGED`, and the child is
admitted by the rule a cell's merged pull request already uses.

**The argument shape is `saffron adopt <spec id> <pr> --repo <path>`.**
`watch` names a task by its spec id (`saffron/cli.py:168-176`). `replay`
takes a pull request as a bare integer (`saffron/cli.py:114`). Every
command that reads one repo's ledger takes `--repo`, defaulting to the
working directory (`saffron/cli.py:134`, `:165`). No command takes a
`task_id`.

**The command picks the spec's newest task.** That is the highest
`task_id` among the repo's rows for the spec, under any spec sha.
`tasks_by_repo` orders by `task_id` and carries `pr_url`
(`saffron/ledger.py:1060-1077`). It takes a newest task that is
`NOT_IMPLEMENTED`, `READY_FOR_REVIEW` or `EXHAUSTED` and carries no pull
request, which is a NULL or an empty `pr_url`. Those are the states
`reconcile` will ask about. A `READY_FOR_REVIEW` row lacks one when
PACKAGE raised (`saffron/ledger.py:1432-1435`). An `EXHAUSTED` row lacks
one when PACKAGE opened none or never ran. It refuses every other case, and reads the
ledger before it asks `gh` anything.

**The URL is the one `gh` prints.** `open_draft_pr` already finds a pull
request this way, with `gh pr view` under `--repo <slug>`
(`saffron/phases/package.py:457-459`). `real_remote` and `github_slug`
give the slug (`saffron/phases/package.py:103-121`). A gh binary that cannot
start raises to the dispatch's own handler, which exits 2
(`saffron/cli.py:302-309`).

**The write is a `task_package` fact**, carrying the row's own `state`,
`branch`, `pushed_sha`, `added` and `removed` beside the adopted URL. The
fold then keeps it, and no new kind is needed. A new kind would have to
enter `ontology/factory.ttl` and the generated `CONTEXT.md`, which this
spec forbids.

**`reconcile` moves a `NOT_IMPLEMENTED` row on a merge alone**, the rule
`EXHAUSTED` already follows. A ready answer would write `APPROVED`, a
waiting state, and a child would then stack on a `saffron/<spec id>`
branch the cell never pushed. A closed answer leaves the row as it was.

Add the command to the command list in `CLAUDE.md` and to the usage in
`README.md`, one line each, beside `reconcile`.

## Out of scope

- **`driver.py`.** `.claude/skills/run-saffron-spec-loop/driver.py`
  still refuses a by-hand pull request in `size`, `record` and `stack`.
  The operator edits it by hand.
- **Protected text.** `DESIGN.md` §3.3 says `EXHAUSTED` leaves only for a
  draft PACKAGE opened, and gives `NOT_IMPLEMENTED` no way out. §6 and
  `CONTEXT.md`'s "Settled task" call `NOT_IMPLEMENTED` settled. The
  operator edits both in this spec's own pull request.
- **A new fact kind.** `saffron/record/**` and `ontology/**` are
  `forbidden`. Reuse `task_package`.
- **The accept rate.** A merged adopted pull request moves its task to
  `MERGED`, so `trailing_accept_rate` counts it as merged
  (`saffron/report/index.py:198-207`). That is the decision this spec
  builds. Do not change the rate.
- **Stacking on an adopted pull request's branch.** A child of an
  adopted `READY_FOR_REVIEW` or `APPROVED` row still stacks on the row's
  own `branch`. The command does not rewrite `branch`.
- **An adopted `EXHAUSTED` row and the unpackaged push.**
  `push_unpackaged_work` refuses to push while another row of the spec is
  `EXHAUSTED` with a `pr_url` (`saffron/phases/package.py:1150-1158`). An
  adopted row counts there too. Leave it.
- **`MERGE_FAILED`.** `reconcile` never asks about it, so the command
  refuses it with every other state.
- **A closed adopted pull request is asked again on every scan**, one
  `gh pr view` per row, as for an `EXHAUSTED` row.

## Notes for the agent

**Which criteria are edits.** Criterion 1 edits `reconcile`, so its
mutant pins `_next_state`'s merged branch, which the change leaves in
place. Keep that line as it is. Criterion 5's mutant pins the
scheduler's merged state, which the child's admission reads, and
`saffron/scheduler.py` is `forbidden` because nothing here edits it.
Criteria 2, 3 and 4 are a new command and a new write. So they declare a
witness alone, and `witness` will report `skip` for them. Criteria 6 and
7 name tests that pass now.

**At base every new witness fails.** `adopt` is not a subcommand, so
`main` raises `SystemExit` from argparse in criteria 2 to 5. Criterion
1's merged row stays `NOT_IMPLEMENTED`.

**The checkout in criteria 2 to 5** is a `git init` directory whose
`origin` is a GitHub URL added with `git remote add`. `real_remote` reads
it and nothing fetches it. Seed the repo row with that URL through
`_seed_repo` (`tests/test_cli.py:1969`). Fake `gh` by replacing
`saffron.cli.run_gh`, as the reconcile test does
(`tests/test_cli.py:2045`). One fake answers both a number, with a URL,
and a URL, with a state.

**Seeding rows.** Write the `EXHAUSTED` row through `set_task_package`
with an empty `pr_url` and a diff stat, as a refused PACKAGE does. Give
the `READY_FOR_REVIEW` row a `record_push` first.

**Criterion 3's states.** Take them from `typing.get_args(TaskState)`
inside the test, minus the three. That is 23 at base. Seed the carried
`pr_url` case three times, once in each state the command takes. One task per state, each its own spec
id. Record every `gh` call. Assert none was made before the two `gh`
cases, and that the whole `tasks` table reads the same afterwards.

**Two conventions meet in the adoption fact.** PACKAGE writes a
`task_package` fact only in a state it ends a task in.
`migrate._outcome_facts` keeps that true: a stored state outside
`_PACKAGED` becomes `READY_FOR_REVIEW` or `MERGE_FAILED` in the fact
(`saffron/record/migrate.py:439-454`). So migrate is no precedent here.
The adoption fact breaks that convention on purpose. It carries the row's
own state, such as `NOT_IMPLEMENTED`. The fold writes the state from the
payload, and it must rebuild the row as it stood. The only reader that
keys on the kind is the fold's `task_package` branch
(`saffron/ledger.py:818`). So no fold, view or report reads the fact as
PACKAGE's.

**PACKAGE's write method cannot carry the adoption.** `set_task_package`
types `branch` and `pushed_sha` as `str` (`saffron/ledger.py:1554-1560`).
An adopted row with a NULL `pushed_sha` then fails the `types` gate.
`tasks_by_repo` selects neither the branch nor the diff stat
(`saffron/ledger.py:1060-1077`). A ledger method that reads the row
itself and builds the fact through `_build_fact` avoids both.

**Criterion 4's ledger.** `main` opens `Ledger(args.home / "ledger.db")`
(`saffron/cli.py:270`). Replace `saffron.cli.Ledger` with a callable
that passes a `MemoryRecord` as `record`, then `fold` that record into a
fresh ledger (`saffron/record/fold.py:42`). Compare the folded columns
with the row read before the adoption, plus the URL.

**Criterion 5's specs** sit in a temporary directory, and the parent's
task carries the parent's own `spec_sha` from `load_spec`. Call
`build_queue` over that directory with the repo's ledger, with no
`pushed_landed`.

**Imports.** Import nothing at a witness module's top that the change
adds. The reverted run would then be a collection error, which `revert`
reads as `skip`.

**Wrong versions.** Each criterion lists the ones its witness must kill.
A prototype's witnesses killed all of them on 2026-10-10, and passed
with the change.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words.

**Size.** `saffron/ledger.py` is in `elevate_on`, so a diff that edits it
is `elevated` and `size` blocks. A prototype with all five new witnesses
measured 1630 tokens with `size_gate`'s counter, against the `feature`
ceiling of 3000. The tests were 1267 of them. `estimated_lines` is that
count over four, plus the two documentation lines.
