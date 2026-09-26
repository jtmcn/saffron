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
      later task of the top layer's spec outside the batch.
    witness: tests/test_finish.py::test_the_finishing_commit_writes_each_layers_and_unrun_texts_and_retires_each_layers_spec
  - claim: >-
      `commit_finish` raises `ValueError` when a text it would write has a
      `path` that is not a `.md` file directly in `.saffron/specs/`, or a
      `text` whose SHA-256 is not its row's `spec_sha`. It raises before it
      calls `add_worktree` or writes any object. The witness drives four
      such paths, one through `..`, one in `done/`, one at the repository
      root and one ending in `.txt`, and one text off its hash. It drives
      each on a layer's row and, separately, on an unrun task's row.
    witness: tests/test_finish.py::test_a_spec_text_outside_the_spec_directory_or_off_its_hash_is_refused_before_any_commit
  - claim: >-
      `run_stack_batch` takes `finish`, `None` by default. Given one, it
      calls it once as `finish(batch_id, unrun)`, positionally, with the
      batch's id as an `int`. It calls it after the follow-ups and while
      the batch row is still open. `unrun` is the list `SA-0162` keeps,
      passed on as it stands: the task of each follow-up whose review never
      reached a verdict route (`run`, `escalate` or `revise`), in the order
      the batch met them. It calls `finish` after an `UNTIL`, a `DRAINED`
      and a `BUDGET` stop. The witness drives a follow-up that became a
      layer, one refused on the open pull request overlap, and one whose
      review escalated. It drives one that ran and missed, and one refused
      by `run_task`'s gate 0 after its review. It drives one whose review
      routed `wait` before the batch stopped, one the batch never reached,
      and a night whose `follow_ups` returns none.
    witness: tests/test_batch.py::test_the_finish_runs_once_after_the_follow_ups_while_the_batch_row_is_open
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
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). None of the chain
from `SA-0142` on exists at `475929b1`, where every line number below was
read. So chain names are cited by symbol. This spec consumes these.

- From `SA-0145`: the `stack_layers` table, keyed on `task_key`, with
  `batch_key` (the batch id as text), `position`, `spec_id`,
  `predecessor_key`, `predecessor_head` and `generation`, and
  `Ledger.record_stack_layer`.
- From `SA-0150`: the `spec_texts` table, `Ledger.record_spec_text`,
  `Ledger.spec_text(task_id)`, which returns a task's latest row or `None`,
  and `Ledger.spec_texts(task_id)`. A row's `spec_sha` is the SHA-256 of its
  text. A task's kind is its first row's origin, `revision` or
  `follow_up`. A revision's path is the queued spec's own file at
  `base_sha`, whatever its name, or an earlier row's path. A follow-up's
  path is `.saffron/specs/<id>-<slug>.md`, and the slug is required.
- From `SA-0155`, `SA-0156` and `SA-0168`: `run_stack_batch` mints a
  fresh task for every spec it reviews, every night, and runs its cell on
  that task. A withheld spec keeps its task and runs no cell.
- From `SA-0160` and `SA-0164`: a `revise` route revises the spec on its
  own task, up to three rounds.
- From `SA-0161` and `SA-0165`: `run_stack_batch`'s `follow_ups` keyword
  returns a list of `Candidate`s, each with a minted task and a
  `spec_text` row of origin `follow_up`. `SA-0165`'s callable catches
  every raise, so `follow_ups` never raises in production.
- From `SA-0162`: the follow-ups run on top, as generation 1 layers, only
  after generation 0 drained. Before its review, each meets gate 0's open
  pull request overlap refusal, and a refused one is never reviewed. Its
  Problem step 5 keeps `unrun`. That is the task id of each follow-up whose
  review never reached a verdict route, as an `int`, in the order met. That holds each one the overlap refused, each one whose review
  routed `wait` before the batch stopped, and each one the batch never
  reached. The batch row closes once, after the follow-ups. A raise from `end_review`
  or `follow_ups` closes it `INFRASTRUCTURE` and leaves `run_stack_batch`.
- From `SA-0144`, `SA-0156` and `SA-0157`: `_batch`'s `--stack` path builds
  `_stack_runner`, `_stack_review`, `_stack_mint` and `_stack_end_review`
  where readiness passed and `pinned` is bound. It passes each to
  `run_stack_batch`, and passes `end_review=None` when readiness fails.
  `SA-0157`'s callable catches every raise too.

**What the base already offers.** `RETIRED_DIRNAME` is `"done"`
(`saffron/scheduler.py:504`). A spec in `done/` means its work is on the
default branch (`.saffron/specs/done/README.md:3-5`). A retired spec's id
is read from its frontmatter, never its filename (`saffron/scheduler.py:516`).
`discover_specs` globs `*.md` in one directory, not below it
(`saffron/intake.py:356`, `:385`). `add_worktree` checks a detached tree out
of the mirror at a sha, and `remove_worktree` removes it
(`saffron/repos/mirror.py:122-133`). `_git` raises `GitError` on a non-zero
exit (`:58-61`). PACKAGE commits with its identity on the command line,
because a `--mirror` clone inherits none (`saffron/phases/package.py:342-350`).
`saffron batch` writes its batch tree under `out_dir`, which is
`<home>/batches/v0` by default (`saffron/cli.py:182`).

**Why the parent is remembered, not fetched.** §5.7 says a parent's head is
fetched, never remembered (`DESIGN.md:1114`). The finish departs from it on
purpose. Its parent is the top layer's recorded `pushed_sha`, because
`SA-0167` compares the top layer's branch with that sha before any push.
A branch moved since then escalates in place of a push.

## Problem

Build four things.

1. **The read.** Add `Ledger.stack_layers(batch_id)`: the batch's
   `stack_layers` rows, with `batch_key` equal to the id as text,
   `ORDER BY position`. Join each to its task by `tasks.record_key =
   task_key`, for the task's `task_id`, `state`, `budget_usd`, `pr_url`,
   `branch` and `pushed_sha`. `SA-0152` reads the same rows for the queue
   page's stack view. If the tree base already holds a `Ledger` method
   returning these rows, use it and add no second one.
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
   criterion 3 states. Pass it `SA-0162`'s `unrun` list as it stands, once
   the follow-ups settle, and never recompute it. Call `finish(batch_id,
   unrun)` positionally then, and before the row closes, so the row's `spent_usd_est` and `ended_at` come
   after it. A raise out of the loop propagates, and `finish` does not run,
   as `end_review` does not.
4. **The callable.** Add `_stack_finish(*, pinned, ledger, out_dir)` to
   `saffron/cli.py`, beside `_stack_end_review`, as criterion 4 states.
   Name the returned closure `run_finish`, since `finish` is the module
   it calls. Build it where `_stack_end_review` is built, and pass it as
   `finish`.
   Pass `finish=None` when readiness fails. Reach `finish.commit_finish`
   through the module at call time, since the witness replaces it there.

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

**Why the path and hash checks repeat `SA-0150`'s.** `record_spec_text`
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
test body, so the reverted run fails rather than failing to collect.
Criteria 5 and 6 name tests that pass now.

**Other fakes of `run_stack_batch`.** `SA-0144`, `SA-0156`, `SA-0157`,
`SA-0162` and `SA-0165` fake it in `tests/test_cli.py`. Each must accept
the new `finish` keyword, through `**kwargs` or by name. The file is in
`touches`, so edit each fake that refuses it.

**Criteria 1 and 2 share one fixture, `stack`,** in `tests/test_finish.py`. Point
`HOME`, `XDG_CONFIG_HOME`, `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` at
nothing, as `tests/test_package.py:1647-1652` does. Build an origin repo
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
text. Then it creates an empty batch and asserts `None` and the refs
unchanged. These fail it:

- a task's first text, not its latest
- the layers' texts alone, with `unrun` left out
- the texts of every task of the batch, or of every task in the ledger
- the specs retired before the texts are written
- a spec found by a filename prefix, or by `<id>-` in its filename
- the parent read from the top layer's branch in the mirror
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
ledger instance with one that changes one field of one task's row and
passes every other call through. It changes the path to
`.saffron/specs/../CLAUDE.md`, `.saffron/specs/done/x.md`, `CLAUDE.md` and
`.saffron/specs/x.txt`, and the `spec_sha` to 64 zeros, in turn. It does
each once on `TE-7`'s row, a layer's, and once on `TE-21`'s, the unrun
one's. It wraps `git_mirror.add_worktree` in a spy that records each call
and passes it on. Before each call it keeps `git count-objects -v`. It
asserts `ValueError`, the same count, and no call to `add_worktree`. These
fail it:

- no path check, or a path check on `..` alone
- no hash check
- the checks made on the unrun rows alone
- the checks made inside the worktree, as each text is written

**How the list was measured.** A throwaway run on 2026-09-24 at
`68892367` stood in for `SA-0145`'s and `SA-0150`'s tables and writers.
The stand-in `record_spec_text` refused a path by its origin, as
`SA-0150` does. It loaded a prototype of the read and of
`saffron/finish.py`. It ran prototypes of criteria 1 and 2's witnesses on
the host's git, 2.54.0. The right build passed both. Each wrong build
above was applied as a text edit to the prototype, and each failed its
witness.

**Criterion 3's witness** reuses the tree base's fakes of the runner,
`review`, `mint`, `sleep`, `end_review`, `follow_ups` and `open_prs` in
`tests/test_batch.py`. Its fake `finish` records its arguments and reads
the batch row's `status` and `ended_at` when called. It takes exactly two
positional parameters. The first night runs `SP-1` to `READY_FOR_REVIEW`.
`follow_ups` returns seven candidates in this order.

- Task 40 reaches `READY_FOR_REVIEW`.
- Task 41 touches a file an open pull request of another branch holds,
  so the overlap refuses it.
- Task 42's review routes `escalate`.
- Task 43 ends `EXHAUSTED`.
- Task 47's review routes `run`, and its runner returns a `Refused`, as
  `run_task`'s gate 0 does after a review.
- Task 44's review routes `wait`, and the clock passes the deadline
  during the wait.
- Task 45 is never reached.

It asserts `UNTIL`, one call with the batch's id and `[41, 44, 45]` while
the row was open, and the row `UNTIL` afterwards. A second night drains,
and its `follow_ups` returns none. It asserts `DRAINED` and one call with
`[]`. A third night's budget is below its only spec's. Its `follow_ups`
returns task 60. It asserts `BUDGET` and one call with `[60]`. These fail
it:

- `finish` called before the follow-ups, or after the row closes
- `finish` called on a `DRAINED` stop alone
- a night whose `follow_ups` returns none left with no call
- `unrun` as every follow-up, or as each one that added no layer
- a follow-up whose review escalated, that ran and missed, or that
  `run_task`'s gate 0 refused, kept
- a follow-up whose review routed `wait` left out
- `unrun` sorted, or a `None` kept
- the batch id passed as text, or `unrun` passed by keyword

**Criterion 4's witness** follows `SA-0157`'s witness for `saffron batch
--stack`, with `_readiness_passes` (`tests/test_cli.py:2603-2621`) and
`_fake_batch_resolution` (`:2624-2640`). The mirror is the one
`_readiness_passes` pins. Its fake `run_stack_batch` calls `finish` with
the `int` 3 and `[5, 6]`, positionally, and returns `UNTIL`. It replaces
`finish.commit_finish` with a recorder returning `"c" * 40`. It asserts
exit 0, the call with its batch id, `unrun`, mirror and `workdir`, and the
printed line. Then, under `monkeypatch.context()`, the commit raises
`GitError("mirror gone")`, then `ValueError("path off")`. Each run exits 0
and prints the raise. Last, the commit returns `None`, once with
`Ledger.stack_layers` replaced to return no row and once one row. Each run
prints its own line. These fail it:

- a `workdir` outside `out_dir / "finish" / <batch id>`
- the repository or its working tree passed as the mirror
- a guard around `GitError` alone, which lets the `ValueError` reach
  `main`
- a raise that reaches `main`, which exits 2
- one line for both kinds of `None`
- the batch id turned to text before the call

Criteria 3 and 4 are unmeasured. `run_stack_batch` and the `--stack` path
do not exist at `68892367`.

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
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of the whole change, with its witnesses and their docstrings,
formatted with `ruff`, was measured with `size_gate` at `68892367`. It came
to 1909 tokens, 64% of the ceiling.

| part | lines | tokens |
|---|---|---|
| `saffron/finish.py` | 89 | 367 |
| the read in `saffron/ledger.py` | 15 | 57 |
| `tests/test_finish.py` | 220 | 845 |
| `run_stack_batch` in `saffron/batch.py` | 16 | 101 |
| criterion 3's witness | 84 | 215 |
| `_stack_finish` and its wiring in `saffron/cli.py` | 32 | 116 |
| criterion 4's witness | 54 | 208 |

The `batch.py` row measured a version that built `unrun` itself, so it
runs high now that `SA-0162` keeps the list. The whole finish with
`findings.json` measured 2718 tokens, past 80% of the ceiling. So
`findings.json` is `SA-0174`'s.
