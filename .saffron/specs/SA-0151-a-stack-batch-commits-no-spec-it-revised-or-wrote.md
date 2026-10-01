---
id: SA-0151
title: A stack batch commits no spec it revised or wrote, so its layers never retire their specs
type: feature
priority: 1
depends_on: [SA-0162]
touches:
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/batch.py
  - saffron/cli.py
  - tests/test_finish.py
  - tests/test_batch.py
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
  - saffron/task.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/qualify.py
  - saffron/follow_up.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/events.py
  - saffron/record/**
  - saffron/repos/**
  - saffron/report/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_end_review.py
  - tests/test_task.py
budget_usd: 25
max_attempts: 3
max_turns: 200
estimated_lines: 558
acceptance:
  - claim: >-
      `finish.commit_finish(ledger, batch_id, unrun, *, mirror, workdir,
      emit=print)` makes one commit in `mirror` and returns its sha. Its parent is the
      recorded `pushed_sha` of the batch's layer with the highest position.
      It writes the latest `spec_texts` text of each layer's task, then of
      each task in `unrun`, at that row's `path`. It reads each through
      `Ledger.spec_text`. An unrun task with no row writes nothing, and
      `emit` gets one line naming it. Then each file directly
      in `.saffron/specs/` whose frontmatter declares a layer's spec id
      moves into `.saffron/specs/done/`. The commit changes no other path,
      and its author is `Saffron <saffron@localhost>`. No ref in the mirror
      moves, and no worktree stays registered. A batch with no layer
      returns `None` and commits nothing. The witness drives a layer with no
      text, one revised twice, and a follow-up layer revised once. It
      drives an unrun follow-up, an unrun task with no text, and texts it
      must not write. Those are a revised spec with no layer, a follow-up
      that ran and missed, and one refused by `run_task`'s gate 0 after its
      review. Another batch's layer and follow-up are among them too. It drives a file
      whose name does not carry its id and a file whose id shares a layer's
      prefix. It drives the top layer's branch moved after its push, and a
      later task of the top layer's spec outside the batch. For a batch
      with no layer, it passes an unrun task that holds a text.
    witness: tests/test_finish.py::test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_retires_each_layers_spec
    wrong_versions:
      - A task's first `spec_texts` text written, not its latest.
      - The layers' texts written alone, with `unrun` left out.
      - The texts of every task of the batch written, not only the layers' and the unrun ones.
      - The parent read from the top layer's branch in the mirror, not its recorded `pushed_sha`.
      - A layer's spec found by `<id>-` in its filename, not by its frontmatter id.
  - claim: >-
      `commit_finish` raises `ValueError` when a text it would write has a
      `path` that is not a `.md` file directly in `.saffron/specs/`, or a
      `text` whose SHA-256 is not its row's `spec_sha`. It raises before it
      calls `add_worktree` or writes any object. The witness drives four
      such paths, one through `..`, one in `done/`, one at the repository
      root and one ending in `.txt`, and one text off its hash. It drives
      each on a layer's row and, separately, on an unrun task's row.
    witness: tests/test_finish.py::test_a_spec_text_outside_the_spec_directory_or_off_its_hash_is_refused_before_any_commit
    wrong_versions:
      - A path check that refuses a path through `..` alone.
      - No check of a row's `text` against its `spec_sha`.
      - The checks made on the unrun tasks' rows alone.
      - The checks made inside the worktree, as each text is written.
  - claim: >-
      `run_stack_batch` takes `finish`, `None` by default. Given one, it
      calls it once as `finish(batch_id, unrun)`, positionally, with the
      batch's id as an `int`. It calls it after the follow-ups and while
      the batch row is still open. `unrun` is a list of task ids, each an
      `int`, one for each follow-up whose review never reached a verdict
      route (`run`, `escalate` or `revise`). A review that routed `error`
      or raised reached none. The list keeps the order the batch met them
      in. Each id is the `task_id` its candidate carries. With no
      `end_review` or no `follow_ups`, `unrun` is `[]`. It calls `finish`
      after an `UNTIL`, a `DRAINED` and a `BUDGET` stop. The witness drives
      a follow-up that became a layer, one refused on the open pull request
      overlap, and one whose review escalated. It drives one whose review
      raised and one whose review routed `error`. It drives one that ran
      and missed, and one refused by `run_task`'s gate 0 after its review.
      It drives one whose review routed `wait` before the batch stopped,
      one the batch never reached, and a night whose `follow_ups` returns
      none. It drives a night given `end_review` and no `follow_ups`, and
      one given neither. The follow-ups' task ids do not ascend in the order the batch meets
      them.
    witness: tests/test_batch.py::test_the_finish_runs_once_after_the_follow_ups_while_the_batch_row_is_open
    wrong_versions:
      - '`finish` called before the follow-ups run, so it sees an empty `unrun`.'
      - '`finish` called after the batch row closes.'
      - '`finish` called on a `DRAINED` stop alone.'
      - '`unrun` recomputed as each follow-up that added no layer.'
      - '`unrun` sorted by task id before the call.'
      - '`unrun` passed as the spec ids the `follow-ups unrun` line prints, not task ids.'
      - 'Each task id read from `task_ids`, which a `BUDGET` stop never seeds, not from its candidate.'
      - '`finish` called only inside the `follow_ups is not None` branch.'
      - '`unrun` passed by keyword.'
  - claim: >-
      `saffron batch --stack` passes `run_stack_batch` the `finish` that
      `cli._stack_finish` builds. Given a batch id and `unrun`, it calls
      `finish.commit_finish` with them, the pinned mirror, and a `workdir`
      of `out_dir / "finish" / <batch id> / "tree"`. It prints `finish:
      committed <sha>, not pushed`. For `None` it prints `finish: no layer,
      so nothing committed` when the batch has no layer, and `finish: the
      tree is unchanged, so nothing committed` when it has one. A raise
      prints one line naming its type and message, and the night's exit
      code stays its stop reason's. The witness drives a sha, a `GitError`
      and a `ValueError`, and `None` with and without a layer.
    witness: tests/test_cli.py::test_a_stack_batch_commits_its_finish_and_survives_a_raise
    wrong_versions:
      - A `workdir` outside `out_dir / "finish" / <batch id>`.
      - The repository's working tree passed as the mirror, not the pinned mirror.
      - A guard around `GitError` alone, so the `ValueError` reaches `main`, which exits 2.
      - One line printed for both kinds of `None`.
      - The batch id turned to text before the call.
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
  - claim: >-
      `run_batch` still runs every candidate once, in order, and drains.
    witness: tests/test_batch.py::test_a_drained_queue_runs_every_candidate_once_in_order
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 8 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1 and §5.7. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that the host commits the batch's revised and follow-up specs in
its own finishing layer, which it adds above every task. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The finishing
layer", is the design.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**. A spec review can revise a queued
spec, and the end review can yield follow-up specs. Both live in the record
as spec text until the finish commits them.

**Step 8 is four specs.** This one builds the finishing commit and runs
it at the end of the batch. `SA-0174` follows it and writes
`findings.json` beside the commit. `SA-0167` follows that. It runs the
repo's gate suite on the finishing tree in a cell. Only when the suite is
green does it push the commit, to the finishing layer's own branch, and
open that branch's pull request. It checks each layer's predecessor head
and reads every base back first. `SA-0170` then links the stack with `gh
stack link`. So nothing this spec builds pushes or opens anything.

**What the tree base holds.** This spec's tree base is `SA-0162`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:197`). Line numbers below
were read at `071dc384`, `main` once pull request 626 merged. Each is
named by its symbol too.

- The `stack_layers` table (`saffron/ledger.py:220-228`), keyed on
  `task_key`, with `batch_key` (the batch id as text), `position`,
  `spec_id`, `predecessor_key`, `predecessor_head` and `generation`.
  The writer `record_stack_layer` (`:1386`) takes the batch key from the
  task's own run. No `Ledger` method reads a batch's layers. `end_review.py`'s
  `_BATCH_LAYERS` (`saffron/end_review.py:92-98`) is a private query.
- The `spec_texts` table (`saffron/ledger.py:272-281`), and these
  `Ledger` methods: `record_spec_text` (`:1461`), `spec_text` (`:1517`),
  which returns a task's latest row or `None`, and `spec_texts`
  (`:1530`). A row's `spec_sha` is the
  SHA-256 of its text (`:1511`). `record_spec_text` refuses a path its
  origin's pattern refuses (`_FOLLOW_UP_PATH`, `_REVISION_PATH`, `:72-73`).
  A revision's path is the queued spec's own file at `base_sha`, whatever
  its name. A follow-up's path is `.saffron/specs/<id>-<slug>.md`.
  `spec_text` raises `ValueError` for an id that names no task.
- `run_stack_batch` (`saffron/batch.py:390`) mints a fresh task for every
  spec it reviews, and runs its cell on that task. A `revise` route revises
  the spec on its own task, up to three rounds. A review that raises, or
  whose route is `error`, raises out of the review wrapper (`:553-565`,
  `:616-624`).
- `_batch`'s `--stack` path builds `_stack_runner`, `_stack_end_review`
  (`saffron/cli.py:615`), `_stack_review`, `_stack_mint` and
  `_stack_follow_ups` where readiness passed and `pinned` is bound
  (`:1447-1472`). It passes each to `run_stack_batch` (`:1508`). Each is
  bound to `None` first (`:1384-1401`), so a night whose readiness or scan
  fails passes `end_review=None` and `follow_ups=None`.
- From `SA-0161` and `SA-0165`: `run_stack_batch`'s `follow_ups` keyword
  returns a list of `Candidate`s. `write_follow_ups` mints each one's
  task, records its `spec_text` row of origin `follow_up`, and sets the
  candidate's `task_id` (`saffron/follow_up.py:386`). `_stack_follow_ups`
  catches every raise and returns `[]` (`saffron/cli.py:990-1011`), so
  `follow_ups` never raises in production.
- From `SA-0162`: the follow-ups run on top, as generation 1 layers, only
  after generation 0 drained. Only then does it seed `task_ids` from the
  candidates (`saffron/batch.py:777-779`). Before its review, each meets
  gate 0's open pull request overlap refusal, and a refused one is never
  reviewed. It builds a local `unrun` (`:800-806`) of **spec ids**, as
  `str`, and prints them on one `follow-ups unrun` line. The ids are each
  follow-up's whose review never reached a verdict route, in the order
  met. That holds each one the overlap refused, and each one whose review
  raised or routed `error`. It holds each one whose review routed `wait`
  before the batch stopped, and each one the batch never reached. The
  list exists only inside the `end_review` and `follow_ups` branches.
  The batch row closes once, after the follow-ups (`_stop`, `:807`). A
  raise from `end_review` or `follow_ups` closes it `INFRASTRUCTURE` and
  leaves `run_stack_batch`.

**What the base already offers.** `RETIRED_DIRNAME` is `"done"`
(`saffron/scheduler.py:516`). A retired spec's work is in `main`
(`.saffron/specs/done/README.md:3`). A retired spec's id
is read from its frontmatter, never its filename (`saffron/scheduler.py:528`).
`discover_specs` globs `*.md` in one directory, not below it
(`saffron/intake.py:388`, `:417`). `add_worktree` checks a detached tree out
of the mirror at a sha, and `remove_worktree` removes it
(`saffron/repos/mirror.py:122-133`). `_git` raises `GitError` on a non-zero
exit (`:60-63`). PACKAGE commits with its identity on the command line,
because a `--mirror` clone inherits none (`saffron/phases/package.py:342-349`).
`saffron batch` writes its batch tree under `out_dir`, which is
`<home>/batches/v0` by default (`saffron/cli.py:196`).

**Why the parent is remembered, not fetched.** §5.7 says a parent's head is
fetched, never remembered (`DESIGN.md:1159`). The finish departs from it on
purpose. Its parent is the top layer's recorded `pushed_sha`, because
`SA-0167` compares the top layer's branch with that sha before any push.
A branch moved since then escalates in place of a push. ADR 7 records the
exception, in its paragraph "The finishing layer's parent is the top
layer's recorded head".

## Problem

Build four things.

1. **The read.** Add `Ledger.stack_layers(batch_id)`: the batch's
   `stack_layers` rows, with `batch_key` equal to the id as text,
   `ORDER BY position`. Join each to its task by `tasks.record_key =
   task_key`, for the task's `task_id`, `state`, `budget_usd`, `pr_url`,
   `branch` and `pushed_sha`. `SA-0152`, `SA-0167`, `SA-0170` and
   `SA-0174` read the same rows. If the tree base already holds a `Ledger`
   method returning these rows, use it and add no second one.
2. **The commit.** Add `saffron/finish.py` with `commit_finish`, as
   criteria 1 and 2 state. It reads the layers, then every text it will
   write, and checks each one's path and hash before `add_worktree` runs.
   It checks out the top layer's `pushed_sha` into `workdir` and writes
   the texts. Only then does it find each layer's file with
   `discover_specs`. So a revised spec retires with its latest text, and a
   follow-up layer retires straight into `done/`. It stages with `git add
   -A` and commits with the subject `saffron batch <batch_id>: finishing
   layer`. It passes `-c user.email=saffron@localhost` and `-c
   user.name=Saffron` on the command, as PACKAGE does. It removes the
   worktree in a `finally`. A top layer with no `pushed_sha` raises
   `ValueError`. A tree left unchanged returns `None` with no commit.
   Reach `git_mirror.add_worktree` through its module at call time, since
   the witness spies on it there.
3. **The call in the batch.** Add `finish=None` to `run_stack_batch`, as
   criterion 3 states. `SA-0162`'s `unrun` holds spec ids, and
   `commit_finish` reads task ids, so build the task ids here. Bind an
   empty `list[int]` before the `end_review` block. Beside `SA-0162`'s
   `unrun`, fill it with `c.task_id for c in follow_up_candidates if
   c.spec.id not in follow_up_reviewed`, in the same order. Fill it in a
   loop that asserts each `task_id` is not `None`, as the seeding loop
   does (`saffron/batch.py:778`). A filter that drops a `None` hides one.
   Take each id from its candidate, never from `task_ids`, which only a
   `DRAINED` stop seeds. Keep the `follow-ups unrun` line in spec ids,
   since `SA-0162`'s witnesses assert it, as in `"follow-ups unrun  TE-96
   TE-92 TE-93"` (`tests/test_batch.py:4875`). Call `finish(batch_id,
   <the task ids>)` positionally after the `end_review` block and before
   `_stop`. So the row's `spent_usd_est` and `ended_at` come after it. A
   raise out of the loop propagates, and `finish` does not run, as
   `end_review` does not.
4. **The callable.** Add `_stack_finish(*, pinned, ledger, out_dir)` to
   `saffron/cli.py`, beside `_stack_end_review`, as criterion 4 states.
   Name the returned closure `run_finish`, since `finish` is the module
   it calls. Build it where `_stack_end_review` is built, and pass it as
   `finish`. Bind it to `None` beside the other defaults (`:1384-1401`),
   so a night whose readiness or scan fails passes `finish=None`. Reach
   `finish.commit_finish` through the module at call time, since the
   witness replaces it there.

**Why the layers are read by `batch_key` alone.** A stack batch mints a
fresh task for every spec each night. So every run, attempt and layer
belongs to tonight's batch. Each layer's fact carries tonight's
`batch_key`, and no layer of an earlier batch can join this stack. The
fixture holds no resumed layer, since stack mode makes none.

**Which texts the commit carries.** A layer's text is in the stack, so it
lands with the stack. An unrun follow-up never met a review or a cell.
Committed to `.saffron/specs/`, it is a queued spec once the stack merges.
A follow-up that ran and missed, or one refused by `run_task`'s gate 0
after its review (`SA-0150`), learned something. So its text stays out.
That gate 0 refusal is not the open pull request overlap, which comes
before the review. `SA-0174` lists it in `findings.json`.
A revised queued spec with no layer stays out too.

**The finish holds no dollars.** The design gives the finish a reserve of
its own, so it runs after `--until` passes (principle 16). Nothing here
calls a model, and neither does `SA-0167`'s gate suite. So its reserve is
$0, and it passes no budget check. It runs after the loop, whatever the
stop reason.

**Why the commit moves no ref.** The design pushes no host commit before
the repo's gate suite reads it (items 40 and 97). `SA-0167` runs that
suite, then pushes this sha to the finishing layer's own branch. So the
top layer's branch keeps one writer, PACKAGE.

**Why the path and hash checks repeat `SA-0182`'s.** `record_spec_text`
refuses a path outside the spec directory and hashes the text itself. A
fold writes each row from its fact alone, with neither check. This is the
one host write to a protected path, so it checks again at the write.

## Out of scope

- **`findings.json`.** `SA-0174` writes it, from the `qualifications`
  rows, the pooled groups `SA-0165` collects and the follow-ups that added
  no layer.
- **The gate suite, the push and the link.** The gate suite, the push and
  the finishing layer's pull request are `SA-0167`'s. So are the
  predecessor-head check and each escalation, and how the finishing
  suite's `scope` treats the host's commit to `.saffron/specs/`. The link
  and `--ready` are `SA-0170`'s.
- **A revision that missed.** A revised queued spec with no layer commits
  nothing. A later night mints a fresh task for it, and its review revises
  the original again.
- **A batch with no layer.** It commits nothing, so its unrun follow-ups
  stay in the record alone.
- **A raise from `end_review` or `follow_ups`.** It leaves
  `run_stack_batch`, so `finish` does not run. Neither production callable
  raises, since `SA-0157`'s and `SA-0165`'s catch every raise.
- **Two sentences this makes false.** `CLAUDE.md:70-71` and
  `README.md:123-124` say a night ends at the deadline plus at most one
  task. The finish runs after an `UNTIL` stop too. Both files are forbidden
  here, and backlog item b-1adb50 files them by hand.
- **The vocabulary.** `CONTEXT.md` has no entry for the finishing layer.
  Backlog item b-466005 files it by hand.

## Notes for the agent

**Every criterion but the last two is new code.** No text at the tree base
commits a spec text. So criteria 1 to 4 declare a witness and no mutant,
and `witness` reports `skip` for them. Import `commit_finish` inside each
test body in `tests/test_finish.py`. In `tests/test_cli.py`, import
`saffron.finish` inside the test body and patch `commit_finish` there,
never at module scope. So the reverted run fails rather than failing to
collect, and criterion 5's `preserves` witness still collects. Criteria 5
and 6 name tests that pass now.

**Other fakes of `run_stack_batch`.** `SA-0144`, `SA-0156`, `SA-0157`,
`SA-0162` and `SA-0165` fake it in `tests/test_cli.py`. Each must accept
the new `finish` keyword, through `**kwargs` or by name. The file is in
`touches`, so edit each fake that refuses it.

**Criteria 1 and 2 share one fixture, `stack`,** in `tests/test_finish.py`. Point
`HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` at
nothing, as `tests/test_package.py:1696-1699` does. Build an origin repo
whose base commit holds `a.py` and these files in `.saffron/specs/`:
`TE-1-one.md` (id `TE-1`), `ten.md` (`TE-10`), `TE-7-seven.md` (`TE-7`),
`TE-5-five.md` (`TE-5`), `TE-6-six.md` (`TE-6`) and `done/README.md`.
Each spec parses. On branch `saffron/TE-10` commit a change to `a.py`, then
`saffron/TE-7` on it, then `saffron/TE-20` on that. Keep the three heads,
then commit one more file on `saffron/TE-20`. Clone it with `--mirror`.

On a `Ledger` in `tmp_path`, create batch B and another batch O. Each task
has its own run. In this order, create and package these tasks in B at
their heads: `TE-10`, `TE-20` and `TE-7`. Then create `TE-5` ended
`EXHAUSTED`, `TE-21` left `QUEUED`, `TE-22` ended `EXHAUSTED`, `TE-23` left
`QUEUED` and `TE-24` left `QUEUED`. `TE-23` stands for a follow-up refused
by `run_task`'s gate 0 after its review. `TE-24` stands for an unrun
follow-up minted before its text was recorded. In O create `TE-6`, packaged
at `TE-10`'s head, and `TE-26` ended `EXHAUSTED`. Last, create a task of
`TE-20` on a run with no batch, packaged at the head of that one more
commit. Record the layers in this order: `TE-7` at 2, `TE-20` at 3 at
generation 1, `TE-10` at 1, and `TE-6` at 1 in O. Record these texts, each
a parsing spec whose title names it:

| task | origin | path | title |
|---|---|---|---|
| `TE-7` | revision | `TE-7-seven.md` | Seven r1, then Seven r2 |
| `TE-5` | revision | `TE-5-five.md` | Five r1 |
| `TE-20` | follow_up, then revision | `TE-20-follow.md` | Twenty, then Twenty r1 |
| `TE-21` | follow_up | `TE-21-other.md` | Twenty-one |
| `TE-22` | follow_up, then revision | `TE-22-missed.md` | Twenty-two, then r1 |
| `TE-23` | follow_up | `TE-23-refused.md` | Twenty-three |
| `TE-6` | revision | `TE-6-six.md` | Six r1 |
| `TE-26` | follow_up | `TE-26-other.md` | Twenty-six |

Each path is under `.saffron/specs/`. `TE-24` holds no text.

**Criterion 1's witness** keeps `git for-each-ref` of the mirror, then
calls `commit_finish` for B with `unrun` of `TE-24`'s task then `TE-21`'s.
It asserts the one line `emit` printed names `TE-24`'s task. It asserts the
commit's parent is `TE-20`'s kept head, its author, the refs unchanged,
and one worktree listed. It asserts `git diff --no-renames --name-status`
from that head is exactly six lines. `ten.md` and `TE-7-seven.md` are
deleted. `done/ten.md`, `done/TE-7-seven.md`, `done/TE-20-follow.md` and
`TE-21-other.md` are added. It asserts `done/TE-7-seven.md` holds Seven
r2, `done/TE-20-follow.md` holds Twenty r1, and each other file its own
text. Then it creates an empty batch and calls `commit_finish` for it
with `unrun` of `TE-21`'s task. It asserts `None` and the refs unchanged.
Beyond its `wrong_versions:`, these fail it too. They are for REVIEW and
the Spec seat, not for the cell to run.

- the texts of every task in the ledger
- the specs retired before the texts are written
- a file's id matched as a prefix of a layer's id, so `TE-1` retires
  with `TE-10`
- the top taken as the last layer recorded, the highest task id, or the
  bottom
- a commit made on a branch
- a commit with no identity of its own
- a worktree left registered
- the layers of every batch
- every written spec retired, the unrun follow-up included
- a commit on the mirror's `HEAD` for a batch with no layer
- a layer joined to its spec's newest task, not by `record_key`
- an unrun task with no text skipped with no line

**Criterion 2's witness** cannot record a bad row, since
`record_spec_text` refuses it. So it replaces `Ledger.spec_text` on the
ledger instance. The stand-in returns a `dict` copy of one task's row,
with one field changed, and passes every other call through. It changes the path to
`.saffron/specs/../CLAUDE.md`, `.saffron/specs/done/x.md`, `CLAUDE.md` and
`.saffron/specs/x.txt`, and the `spec_sha` to 64 zeros, in turn. It does
each once on `TE-7`'s row, a layer's, and once on `TE-21`'s, the unrun
one's. It wraps `git_mirror.add_worktree` in a spy that records each call
and passes it on. Before each call it keeps `git count-objects -v`. It
asserts `ValueError`, the same count, and no call to `add_worktree`. Its
`wrong_versions:` list the builds it must kill. So do "no path check" and
"the checks made on the layers' rows alone".

**How criteria 1 and 2 were measured.** On 2026-10-01 a prototype of the
read and of `saffron/finish.py` ran at `b6a701a6`. It used the real
`Ledger`, `record_stack_layer` and `record_spec_text` there, and the real
`add_worktree`, `discover_specs` and `RETIRED_DIRNAME`. It built the
`stack` fixture above in a scratch directory outside the repository. It
ran both witnesses as plain functions, under `uv run python`. The right
build passed both. Each wrong build in criteria 1 and 2's
`wrong_versions:` and in the two lists above was applied as a text edit.
Each failed its witness.

The first run used the host's git, 2.54.0. A second run used the cell
image `saffron/cell:saffron` at `071dc384`, with its git 2.47.3 and Python
3.12. Both runs gave the same verdicts. One kill turns on the version.
With no identity of its own, git 2.54.0 committed under a name it derived,
and the author assertion failed. Git 2.47.3 refused to commit and raised
`GitError`, and the witness failed there too.

**Criterion 3's witness** reuses the tree base's fakes of the runner,
`review`, `mint`, `sleep`, `end_review` and `open_prs` in
`tests/test_batch.py`. `StackDoubles.runner` cannot return a `Refused`,
so the witness gives task 47 a runner of its own. Its fake `finish` is written `def finish(batch_id,
unrun, /)`. It records its arguments and reads the batch row's `status`
and `ended_at` when called. The first night runs `SP-1` to
`READY_FOR_REVIEW`. Its own `follow_ups` creates nine tasks in the order
of their labels, 40 to 48, then returns their candidates in the order
below. The labels name tasks, not ids. Each list it asserts holds the
real ids its candidates carry, so task 48's id sits above task 46's and
task 44's.

- Task 40 reaches `READY_FOR_REVIEW`.
- Task 41 touches a file an open pull request of another branch holds,
  so the overlap refuses it.
- Task 42's review routes `escalate`.
- Task 48's review raises `RuntimeError`.
- Task 43 ends `EXHAUSTED`.
- Task 46's review routes `error`.
- Task 47's review routes `run`, and its runner returns a `Refused`, as
  `run_task`'s gate 0 does after a review.
- Task 44's review routes `wait`, and the clock passes the deadline
  during the wait.
- Task 45 is never reached.

Tasks 48 and 46 each count one abort. Task 43's `EXHAUSTED` resets the
breaker's count between them, so the breaker does not fire. It asserts
`UNTIL` and one call, made while the row was open. The call carries the
batch's id and the ids of tasks 41, 48, 46, 44 and 45, in that order. It
asserts the row `UNTIL` afterwards. A second night drains, and its `follow_ups` returns none. It
asserts `DRAINED` and one call with `[]`. A third night's budget is below
its only spec's. Its `follow_ups` returns one follow-up, task 60. It
asserts `BUDGET` and one call with task 60's id. A fourth night drains one
spec, given `end_review` and no `follow_ups`. A fifth is the same, given
neither. Each asserts `DRAINED` and one call with `[]`. Beyond its `wrong_versions:`, these fail it too,
for REVIEW and not for the cell:

- a night whose `follow_ups` returns none left with no call
- `unrun` as every follow-up
- a follow-up whose review escalated, that ran and missed, or that
  `run_task`'s gate 0 refused, kept
- a follow-up whose review routed `wait` or `error`, or raised, left out
- a `None` kept in `unrun`
- the batch id passed as text
- `finish` called only inside the `end_review is not None` branch

**How criterion 3's list was worked.** It needs code the tree base lacks,
so it was worked by hand against `saffron/batch.py` at `b6a701a6`. That
covers `_drive` (`:181-331`), the review wrapper `wrapped` (`:509-734`),
`_wait_out_rate_limit` (`:332-357`) and `_BREAKER_THRESHOLD = 2` (`:65`).
The first night stops `UNTIL` at task 44's wait, before task 45. So the
right list is tasks 41, 48, 46, 44 and 45.

- Sorted by id, the list reads 41, 44, 45, 46, 48, which fails the first
  night.
- Spec ids are `str`, and the first and third nights compare `int`s.
- A `BUDGET` stop never seeds `task_ids`. So the third night reads `None`
  through `.get`, and a `KeyError` through `[]` leaves the batch.
- The fourth and fifth nights get no call from a build that calls
  `finish` inside the `follow_ups` branch alone. The fifth gets none from
  one that calls it inside the `end_review` branch alone.
- A keyword call raises `TypeError` against the positional-only fake, and
  the batch leaves with it.
- The other wrong builds fail as this spec's review at `b6a701a6`
  worked them. A call before the follow-ups sees `[]`. A call after the close
  reads `status` set. A `DRAINED`-only call skips the first and third
  nights. A list of the follow-ups that added no layer holds tasks 42, 43
  and 47.

**Criterion 4's witness** follows `SA-0157`'s witness for `saffron batch
--stack`, with `_readiness_passes` (`tests/test_cli.py:2951-2969`) and
`_fake_batch_resolution` (`:2972-2988`). The mirror is the one
`_readiness_passes` pins. Its fake `run_stack_batch` calls `finish` with
the `int` 3 and `[5, 6]`, positionally, and returns `UNTIL`. It replaces
`finish.commit_finish` with a recorder returning `"c" * 40`. It asserts
exit 0, the call with its batch id, `unrun`, mirror and `workdir`, and the
printed line. Then, under `monkeypatch.context()`, the commit raises
`GitError("mirror gone")`, then `ValueError("path off")`. Each run exits 0
and prints the raise. Last, the commit returns `None`, once with
`Ledger.stack_layers` replaced to return no row and once one row. Each run
prints its own line. Its `wrong_versions:` list the builds it must kill,
and so does a raise that reaches `main`, which exits 2. Its list was
worked by reading at `b6a701a6`, since `_stack_finish` does not exist
there. No kill turns on the arrangement. Each wrong build fails an
assertion named above.

**What the witnesses leave undriven.** They drive no `INFRASTRUCTURE` or
`INCOMPLETE` stop, and no raise out of the loop. They drive no top layer
without a `pushed_sha`, and no tree the commit leaves unchanged. Nor do
they drive `finish=None` when readiness fails. Build each as the Problem
states.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
read stays in `saffron/ledger.py`, since `SA-0152`, `SA-0167`, `SA-0170`
and `SA-0174` consume `Ledger.stack_layers`. A prototype of criteria 1 and
2's part, formatted with `ruff`, was measured with `size_gate` at
`68892367`. No ancestor takes any of it, so those rows hold at
`b6a701a6`. The other rows are estimates, priced at the gate's 4.19
tokens a line.

| part | lines | tokens | how |
|---|---|---|---|
| `saffron/finish.py` | 89 | 367 | measured |
| the read in `saffron/ledger.py` | 15 | 57 | measured |
| `tests/test_finish.py` | 220 | 845 | measured |
| `run_stack_batch` in `saffron/batch.py` | 24 | 101 | measured |
| criterion 3's witness | 120 | 500 | estimated |
| `_stack_finish` and its wiring in `saffron/cli.py` | 32 | 134 | estimated |
| criterion 4's witness | 54 | 226 | estimated |

That totals about 2230 tokens, 74% of the ceiling, and `estimated_lines`
is that over four. The `batch.py` row was measured at `68892367` for a
version that built its own `unrun` list, as this one now does. The
witness row adds two nights and its own `follow_ups`. The spec
review's own estimate ran to 2500 tokens, 83%, still under the ceiling. The whole finish with
`findings.json` measured 2718 tokens, past 80% of the ceiling. So
`findings.json` is `SA-0174`'s.
