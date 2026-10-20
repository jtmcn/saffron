---
id: SA-0305
title: A deferred stack batch has no command to run its end review, follow-ups and finish once the review commits land
type: feature
priority: 2
depends_on: [SA-0303, SA-0304, SA-0306]
estimated_lines: 370
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_cli.py
  - CLAUDE.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
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
  - saffron/batch.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/preflight.py
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/record/**
  - tests/test_batch.py
  - tests/test_end_review.py
  - tests/test_finish.py
  - tests/test_stack_view.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 42
max_attempts: 3
max_turns: 200
acceptance:
  - claim: >-
      `saffron finish <batch id> --repo <repo>` calls `run_stack_batch` once,
      with an empty order, the batch's own budget, no `until`, and the
      `reserve_usd` and `writer_usd` its `deferred.json` holds. It hands a
      `StackResume` whose seven fields are the batch's id, its
      `batch_budget`, its row's `status`, the highest layer as `top` with
      that layer's task and the spec `deferred.json` holds for it, that
      layer's position, the branch of every layer plus the stack base
      task's own `branch`, and the specs `deferred.json` holds. Every
      adapter it hands is built at the pinned base `deferred.json` holds.
      That covers the runner, the end review, the spec review, the
      citation check, the mint, the spec writer, the follow-up writer, the
      finish and the stack base check. Each of them that takes a repo gets
      the resolved `--repo`. The spec review and the citation check share
      one commit cache, empty at the start. The follow-up writer's cap is the file's `writer_usd`. The open pull
      request reader gets the slug of the file's `url`. The finish gets
      the mapping the end review's graded heads fill. The stack view it
      writes is the finished batch's, over the file's specs. It creates no
      batch row. It prints `finish: <reason>` for the reason the tail
      returns. It exits 0 for `DRAINED`, `BUDGET` and `UNTIL`, and 2 for
      `INCOMPLETE` and `INFRASTRUCTURE`.
    witness: tests/test_cli.py::test_saffron_finish_runs_a_deferred_stack_batchs_tail_on_its_own_id_at_its_pinned_base
    wrong_versions:
      - "`reserve_usd` is recomputed from the batch's budget instead of read from `deferred.json`."
      - "`top` is the lowest layer, not the highest."
      - "`layer_branches` leaves out the stack base's branch."
      - "The stack base's branch is spelled from its spec id, not read from its task's `branch`."
      - "`stop_reason` is always `DRAINED`, whatever the row's `status`."
      - "The finish is handed an empty mapping, so it never sees the graded heads."
      - "The stack view is written for the newest batch, not the finished one."
      - "The follow-up writer's cap is the reserve, not the writer's share."
      - "The open pull request reader gets no slug."
      - "`INCOMPLETE` exits 0."
      - "`budget_usd` is the newest batch's budget, not the finished batch's."
      - "The adapters are built on the operator's checkout, not the recorded mirror."
      - "The stack view gets no specs."
      - "The citation check gets a cache of its own, so it and the review fetch twice."
  - claim: >-
      `saffron finish` prints one line starting `saffron: finish refused:`,
      naming why, exits 2, and never calls `run_stack_batch`, in each
      case below. The batch has no `deferred.json`. The resolved `--repo`
      is not the `repo` that file names. The ledger has no `batches` row
      for the id. The row has no `status`. The batch has no layer. A layer
      holds an `end_reviews` row whose status is `reviewed`, `error` or
      `not_reached`. The batch holds a `stack_finish` row.
      `CLAUDE_CODE_OAUTH_TOKEN` is unset.
    witness: tests/test_cli.py::test_saffron_finish_refuses_a_batch_it_cannot_finish_before_any_cell
    wrong_versions:
      - "Only a `reviewed` row refuses, so a batch whose end review errored runs again and its first lens write raises on the primary key."
      - "Any row but an `error` row refuses, so an errored batch runs again."
      - "`--repo` is compared unresolved, so a relative path is refused for a batch it ran."
      - "The token is not checked, so every lens errors and the batch can never be finished."
      - "An open row is resumed, though its `status` is no stop reason."
      - "A batch with a finishing layer is resumed."
      - "A refusal exits 1."
  - claim: >-
      `saffron batch --stack` still exits 0 for `DRAINED`, `BUDGET` and
      `UNTIL`, and 2 for `INCOMPLETE` and `INFRASTRUCTURE`, and still
      writes the newest batch's stack view.
    witness: tests/test_cli.py::test_a_stack_batch_writes_its_stack_view_into_the_queue_page
    preserves: true
---

## Context

Backlog item **b-8a0c9a**, under ADR 7 and `DESIGN.md` §4.2.1. A stack
batch's end review grades the heads PACKAGE pushed, before the delegate's
review commits land. Runs 32, 33, 35, 44 and 45 each found most of its
findings already fixed on the branches. This is the last of the five specs
`SA-0301`'s notes lay out, and it adds the command the other four build
toward. Every line cited below was read at `45305c7a`, which holds the
five specs and none of their code. `SA-0301` to `SA-0304` and `SA-0306`
each edit `saffron/cli.py` first, so find each function there by name.

**What the four parents give this spec.**

- `SA-0301` adds `saffron batch --stack --defer-end-review`. Its deferring
  callable writes `finish/<batch id>/deferred.json` under the batch tree.
  The file holds exactly `batch_id`, `reserve_usd`, `writer_usd`,
  `base_sha`, `url`, `mirror`, `repo` and `specs`. Each `specs` value is a
  `Spec` dumped with `exclude_unset=True`, so `Spec.model_validate` reads
  it back equal. The deferred batch runs no end review, no follow-up and
  no finish, so it writes no `end_reviews` row and no `stack_finish` row.
- `SA-0302` has the end review fetch each layer's branch and grade its
  current head. `StackReview.fields` maps each task key it resolved to the
  `LayerFields` it graded.
- `SA-0303` has qualification and the follow-up writer read those fields.
- `SA-0304` adds `saffron.batch.StackResume`, a frozen dataclass of
  `batch_id`, `budget_usd`, `stop_reason`, `top`, `position`,
  `layer_branches` and `specs`, and a `resume` keyword on
  `run_stack_batch`. With a resume and an empty order, `run_stack_batch`
  runs the tail on the resumed batch's id. It creates no row, never calls
  `readiness_check`, never writes the row, and returns the tail's reason.
- `SA-0306` has the finishing layer, `findings.json` and the stack view
  read the heads the end review graded. `cli._stack_finish` takes a
  `heads` mapping from task key to head. A wrapper `SA-0306` adds around an
  `end_review` callable fills that mapping from each
  `StackReview.fields` entry's head. `write_stack_view` takes a
  `batch_id` keyword. Find each by name in `SA-0306`'s diff.

**`_batch` builds the stack adapters.** Under `--stack` it builds them once
the scan resolves (`saffron/cli.py:2116-2154`). `_stack_review` and
`_stack_cite` share one commit cache there (`:2119-2131`). That covers
`_stack_runner`, `_stack_end_review`, `_stack_review`, `_stack_cite`,
`_stack_revise`, `_stack_mint`, `_stack_base_alive`, `_stack_follow_ups`
with `cap_usd=writer_usd`, `_stack_open_prs` and `_stack_finish`. It then
calls `run_stack_batch` (`:2189-2207`) and writes the stack view
(`:2210`). `_stack_base_alive` takes the pinned base positionally
(`:713`). `_stack_open_prs` takes the repo's slug (`:1585`), which
`_resolve_queue` reads with `package_phase.github_slug(url)` (`:1702-1705`).
`_batch` maps a stop reason to an exit code at `:2231-2247`.
`run_stack_batch` takes `readiness_check` with no default
(`saffron/batch.py:428`).

**The ledger already reads most of the resume.** `batch_budget` returns a
batch's budget, or `None` for an id with no row (`saffron/ledger.py:1419`).
No method reads a batch's `status`. `stack_layers` returns a batch's
layers, lowest position first, each with `task_id`, `spec_id`,
`predecessor_key` and `position` (`:1768`). `end_reviews` returns every
`end_reviews` row filed under a layer of the batch (`:1428`). `stack_finish`
returns the batch's finishing row, or `None` (`:1816`). A stack base is a
task with no `stack_layers` row of its own. The bottom layer's
`predecessor_key` names it, and `finish.publish_finish` reads its branch
through `tasks.record_key` (`saffron/finish.py:396-403`).

**An end review cannot be recorded twice for one layer.** The
`end_reviews` table's primary key is `(task_key, lens)`
(`saffron/ledger.py:255-262`). `_apply` inserts each `end_review` fact
with a plain `INSERT` (`:929-933`). `review_stack` records each layer's
rows after that layer's lenses run (`saffron/end_review.py:354-369`). So a
second end review over a layer that holds any row pays for that layer's
lenses, then raises on its first write. `_stack_end_review` catches the
raise and files the rest `error` (`saffron/cli.py:869-872`).

**A command that runs a cell is guarded.** `saffron regate` runs through
`_guarding_sigterm` (`saffron/cli.py:324`), which turns a SIGTERM into exit
143 after teardown (`:498-521`).

## Problem

There is no way to run a deferred stack batch's tail. Add
`saffron finish <batch id> --repo <repo>`, defaulting `--repo` to the
working directory as the other commands do. Its help says it reads each
branch at origin and pushes nothing, so the operator pushes review commits
first. `main` runs it through `_guarding_sigterm`, inside the handler that
turns an unexpected raise into `saffron:` and exit 2.

1. **Refuse first, before any cell.** Read
   `<batch tree>/finish/<batch id>/deferred.json`. Print one line starting
   `saffron: finish refused:` that names why, and return 2, in each case
   criterion 2 lists. Compare the resolved `--repo` with the
   file's `repo` as paths.
2. **Build the resume.** `budget_usd` is `ledger.batch_budget`.
   `stop_reason` is the row's `status`, read through `ledger._db`. `top` is
   a `Candidate` for the highest `stack_layers` row. Its `spec` is the one
   `deferred.json` holds for that layer's spec id, its `task_id` is that
   layer's task, and its `spec_sha` is that task's. `position` is that
   row's position. `layer_branches` is `scheduler._branch` of each layer's
   spec id, plus the stack base task's `branch` when the bottom layer has
   a `predecessor_key`. `specs` is every spec in `deferred.json`, each read
   with `Spec.model_validate`.
3. **Build the adapters `_batch` builds,** from a `PinnedBase` of the
   file's `mirror`, `url` and `base_sha`, and on the resolved `--repo`.
   Pass no stack base, since every follow-up's predecessor is `top`. Share
   one commit cache between `_stack_review` and `_stack_cite`, as `_batch`
   does. Name it apart from `SA-0306`'s `heads` mapping. Wrap
   the end review in `SA-0306`'s wrapper, and hand `_stack_finish` the
   mapping that wrapper fills. Hand `_stack_follow_ups` the file's
   `writer_usd` as its cap, and the finish the same `pooled` list.
4. **Run the tail.** Call `run_stack_batch` with an empty order, the
   resume's budget, no `until`, the file's two shares, the adapters and
   the resume. Its `readiness_check` is a callable that raises, since a
   resume never calls it. Then write the stack view for this batch id,
   over the file's specs. Print `finish: <reason>` and exit as `_batch`
   does for that reason.
5. **Two texts name the commands.** `CLAUDE.md` gains this command's line
   in its command list, below `saffron package` (`CLAUDE.md:64`).
   `saffron/cli.py`'s module docstring lists every subcommand
   (`saffron/cli.py:1-3`), so it gains `finish`.

## Out of scope

- **Pushing.** The command reads each branch at origin. The spec loop's
  skill tells the delegate to push and restack first. The operator edits
  it by hand in this spec's pull request.
- **Retrying an end review that errored.** A batch with any `end_reviews`
  row is refused, an errored one included. A rerun would pay for a
  layer's lenses and then fail to record them (see Context). Allowing it
  needs a ledger that replaces a row, and `saffron/ledger.py` is
  `elevate_on`. The token refusal stops the one cause the command can see
  coming.
- **How the heads are graded and read.** `SA-0302`, `SA-0303` and
  `SA-0306` own that.
- **A readiness probe.** Each cell this command opens rebuilds the repo's
  image itself, in `session.cell_up` (`saffron/cell/session.py:1145`).
  The night's own readiness already checked the mirror, the origin and the
  policy at the pinned base. A missing token is refused here.
- **`DESIGN.md` §4.2.1, `CONTEXT.md`, ADR 7 and the spec loop's skill.** The
  operator edits them by hand in this spec's pull request.

## Notes for the agent

**New code, so no criterion declares a mutant.** The command does not
exist at base. `witness` will report `skip` for criteria 1 and 2.
Criterion 3 names a test that exists now, and the change leaves `_batch`
as it is.

**At base each new witness fails in its body.** Each calls `main` with
`finish`, which argparse refuses with `SystemExit`. Import `StackResume`
and `PinnedBase` inside the test body, never at module scope.

**The fixture.** One module-level helper builds a home ledger and batch
tree a deferred batch left, at a fresh home per case. Keep it there, so
both witnesses share it.

- A stack base task with a pushed branch `pr/stack-base` and no batch. Its
  branch is not `scheduler._branch` of its spec id, so a branch spelled
  from the spec id shows.
- A batch of budget 40.0 with two layers, `SY-1` at position 1 on the
  stack base and `SY-2` at position 2. Close it with a given reason, or
  leave it open, or give it no layer, as the case needs.
- A later batch of budget 10.0 with no layer, closed. The newest batch is
  then not the finished one.
- `deferred.json` with `reserve_usd` 6.0 and `writer_usd` 3.0, so neither
  matches a quarter of 40.0 and the two differ. Give one spec a field set
  at its default, such as `priority=3`.

**The first witness.** Close the batch `UNTIL`, so a hardcoded `DRAINED`
shows. `chdir` to the parent of the repo and pass `--repo repo`, relative.
Replace each adapter builder on `cli` with a recorder of its arguments.
The end review's recorder returns a callable that returns an object whose
`fields` maps the top layer's key to an object whose `head` is `"e" * 40`.
Replace `cli.write_stack_view` with a recorder. The faked
`run_stack_batch` records its call, calls the handed `end_review` once,
and returns `DRAINED`. Assert every value criterion 1 names. Assert the
finish's `heads` mapping equals `{top key: "e" * 40}` after the run, and
that the review's and the citation check's caches are one empty dict. Then
rerun `main` with the faked `run_stack_batch` returning each other reason,
and assert each exit code and printed line.

**The second witness.** Make `run_stack_batch` a recorder and assert it
never ran. Drive each case, each end-review status included, with its own home. For the
missing row, copy the batch's `finish/<id>` directory to `finish/99` and
run `finish 99`. For the three end-review statuses, record one row on the
top layer with `Ledger.record_end_review`. For the finishing row, use
`Ledger.record_stack_finish`. Unset the token with `monkeypatch.delenv`
inside a `monkeypatch.context()`, since an autouse fixture sets it
(`tests/test_cli.py:60-65`).

**Measured on a prototype at `45305c7a`.** A commit below it stubbed
`StackResume` and the `resume` keyword. It also stubbed the `heads`
keyword, `SA-0306`'s wrapper and the `batch_id` keyword. The prototype passed both new
witnesses, `ruff` and `ty`. Each failed with `saffron/cli.py` reverted to
the stubs. Each wrong version above was applied as an edit, and its
criterion's witness failed every time. Its diff measured 573 changed
tokens outside `tests/` and 809 inside, about 346 lines. The estimate adds
about 24 lines for docstrings and review.

**The `prose` gate** counts each new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.
