---
id: SA-0305
title: A deferred stack batch has no command to run its end review, follow-ups and finish once the review commits land
type: feature
priority: 2
depends_on: [SA-0303, SA-0304, SA-0306]
estimated_lines: 395
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
budget_usd: 45
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
      batch row. It runs the readiness probe `_batch` runs once, on the
      resolved `--repo`, the home's mirror path and the home, before
      `run_stack_batch`. It prints `finish: <reason>` for the reason the tail
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
      - "`stop_reason` is the newest batch's `status`, not the finished batch's."
      - "The adapters are built on the operator's checkout, not the recorded mirror."
      - "The stack view gets no specs."
      - "The citation check gets a cache of its own, so it and the review fetch twice."
      - "The readiness probe reads the recorded mirror, not the home's mirror path for `--repo`."
  - claim: >-
      `saffron finish` prints one line starting `saffron: finish refused:`,
      naming why, exits 2, and never calls `run_stack_batch`, in each
      case below. The batch has no `deferred.json`. That file's `batch_id`
      is not the id on the command line. The resolved `--repo` is not the
      `repo` that file names. The ledger has no `batches` row
      for the id. The row has no `status`. The batch has no layer. A layer
      holds an `end_reviews` row whose status is `reviewed`, `error` or
      `not_reached`. The batch holds a `stack_finish` row.
      `CLAUDE_CODE_OAUTH_TOKEN` is unset. The readiness probe fails, and
      the line names its step and detail.
    witness: tests/test_cli.py::test_saffron_finish_refuses_a_batch_it_cannot_finish_before_any_cell
    wrong_versions:
      - "Only a `reviewed` row refuses, so a batch whose end review errored runs again and its first lens write raises on the primary key."
      - "Any row but an `error` row refuses, so an errored batch runs again."
      - "`--repo` is compared unresolved, so a relative path is refused for a batch it ran."
      - "The token is not checked, so every lens errors and the batch can never be finished."
      - "An open row is resumed, though its `status` is no stop reason."
      - "A batch with a finishing layer is resumed."
      - "A refusal exits 1."
      - "A `deferred.json` naming another batch is run under the command line's id."
      - "A failed readiness probe is printed and the tail runs anyway."
      - "No readiness probe runs, so an outage reaches the end review and every lens writes an `error` row."
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
findings already fixed on the branches. This is the last of the six specs
that item splits into, and it adds the command the other five build
toward. Every line cited below was read in `saffron/` as it stands at
`a8ec9d97`, the head of `saffron/SA-0306`, which holds all five specs'
code. `SA-0301` to `SA-0304` and `SA-0306` each edit `saffron/cli.py`
first, so find each function there by name.

**What the five specs below give this spec.**

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
  `heads` mapping from task key to head. SA-0306's module-level
  end-review wrapper, `cli._keeping_graded_heads(end_review, heads)`, fills that mapping. It copies
  each `StackReview.fields` entry's head, and only from a `StackReview`.
  `write_stack_view` takes a `batch_id` keyword.

**`_batch` builds the stack adapters.** Under `--stack` it builds them once
the scan resolves (`saffron/cli.py:2126-2287`). `_stack_review` and
`_stack_cite` share one commit cache there (`:2250-2262`). That covers
`_stack_runner`, `_stack_end_review`, `_stack_review`, `_stack_cite`,
`_stack_revise`, `_stack_mint`, `_stack_base_alive`, `_stack_follow_ups`
with `cap_usd=writer_usd`, `_stack_open_prs` and `_stack_finish`. It then
calls `run_stack_batch` (`:2322-2340`). It then writes the stack view
(`:2343`). `_stack_base_alive` takes the pinned base positionally
(`:734`). `_stack_open_prs` takes the repo's slug (`:1700`), which
`_resolve_queue` reads with `package_phase.github_slug(url)` (`:1818`).
`_batch` maps a stop reason to an exit code at `:2322-2379`.
`run_stack_batch` takes `readiness_check` with no default
(`saffron/batch.py:448`).

**The ledger already reads most of the resume.** `batch_budget` returns a
batch's budget, or `None` for an id with no row (`saffron/ledger.py:1419`).
No method reads a batch's `status`. `stack_layers` returns a batch's
layers, lowest position first, each with `task_id`, `spec_id`,
`predecessor_key` and `position` (`:1768`). `end_reviews` returns every
`end_reviews` row filed under a layer of the batch (`:1428`). `stack_finish`
returns the batch's finishing row, or `None` (`:1816`). A stack base is a
task with no `stack_layers` row of its own. The bottom layer's
`predecessor_key` names it, and `finish.publish_finish` reads its branch
through `tasks.record_key` (`saffron/finish.py:415-422`).

**An end review cannot be recorded twice for one layer.** The
`end_reviews` table's primary key is `(task_key, lens)`
(`saffron/ledger.py:255-262`). `_apply` inserts each `end_review` fact
with a plain `INSERT` (`:929-933`). `review_stack` records each layer's
rows after that layer's lenses run (`saffron/end_review.py:479-545`). So a
second end review over a layer that holds any row pays for that layer's
lenses, then raises on its first write. `_stack_end_review` catches the
raise and files the rest `error` (`saffron/cli.py:894-897`).

**`_batch` probes readiness before its scan.** It calls
`preflight.check_readiness` on the resolved `--repo`, `_mirror_path(repo,
args.home)`, a scratch directory, the home and the token
(`saffron/cli.py:2110-2117`). The probe checks the token, the mirror, the
origin and the default branch. It then checks the policy, the disk and
the images, and returns the first step that fails (`saffron/preflight.py:500-512`).

**A command that runs a cell is guarded.** `saffron regate` runs through
`_guarding_sigterm` (`saffron/cli.py:345`), which turns a SIGTERM into exit
143 after teardown (`:519-542`).

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
   criterion 2 lists. The id on the command line is the batch's id
   throughout, so a file whose `batch_id` differs is refused. Compare the
   resolved `--repo` with the file's `repo` as paths. Run the readiness
   probe last, as `_batch` calls it, and refuse with its step and detail
   when it fails. An outage then stops the command before a lens writes
   an `error` row, which would refuse every later run. The probe's own
   `base_sha` is not read. The tail grades at the pinned base in the
   file.
2. **Build the resume.** `budget_usd` is `ledger.batch_budget`.
   `stop_reason` is the row's `status`, read through `ledger._db`. `top` is
   a `Candidate` for the highest `stack_layers` row. Its `spec` is the one
   `deferred.json` holds for that layer's spec id, its `task_id` is that
   layer's task, and its `spec_sha` is that task's. Its `path` is
   `Path("<spec id>.md")`. Nothing in the tail reads a predecessor's path,
   since the runner and the spec sessions read only `predecessor.spec.id`
   (`saffron/cli.py:689-716`). `position` is that
   row's position. `layer_branches` is `scheduler._branch` of each layer's
   spec id, plus the stack base task's `branch` when the bottom layer has
   a `predecessor_key`. `specs` is every spec in `deferred.json`, each read
   with `Spec.model_validate`.
3. **Build the adapters `_batch` builds,** from a `PinnedBase` of the
   file's `mirror`, `url` and `base_sha`, and on the resolved `--repo`.
   Pass no stack base, since every follow-up's predecessor is `top`. Share
   one commit cache between `_stack_review` and `_stack_cite`, as `_batch`
   does. Name it apart from `SA-0306`'s `heads` mapping. Wrap
   the end review in `_keeping_graded_heads`, and hand `_stack_finish` the
   mapping that wrapper fills. Hand `_stack_follow_ups` the file's
   `writer_usd` as its cap, and the finish the same `pooled` list.
4. **Run the tail.** Call `run_stack_batch` with an empty order, the
   resume's budget, no `until`, the file's two shares, the adapters and
   the resume. Its `readiness_check` is a callable that raises, since a
   resume never calls it, and the probe already ran in step 1. Then write the stack view for this batch id,
   over the file's specs. Print `finish: <reason>` and exit as `_batch`
   does for that reason.
5. **Four texts name the commands.**
   - `CLAUDE.md` gains this command's line in its command list, below
     `saffron package` (`CLAUDE.md:64`).
   - `CLAUDE.md` says a `--stack` night runs its end review from its
     reserve (`:77-78`). Add that a night started with
     `--defer-end-review` defers it to `saffron finish`, which spends that
     reserve.
   - `CLAUDE.md` names the commands that need `CLAUDE_CODE_OAUTH_TOKEN`
     (`:85`). Add `saffron finish`.
   - `saffron/cli.py`'s module docstring gains `finish`. It lists every
     subcommand (`saffron/cli.py:1-3`).

## Out of scope

- **Pushing.** The command reads each branch at origin. The spec loop's
  skill tells the delegate to push and restack first. The operator edits
  it by hand in this spec's pull request.
- **Retrying an end review that errored.** A batch with any `end_reviews`
  row is refused, an errored one included. A rerun would pay for a
  layer's lenses and then fail to record them (see Context). Allowing it
  needs a ledger that replaces a row, and `saffron/ledger.py` is
  `elevate_on`. The token refusal and the readiness probe stop the causes
  the command can see coming.
- **How the heads are graded and read.** `SA-0302`, `SA-0303` and
  `SA-0306` own that.
- **Pinning a new base.** The readiness probe fetches the default branch.
  The tail still keeps the night's pinned base, with the night's gates and
  policy.
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
- A later batch of budget 10.0 with no layer, closed `BUDGET`. The newest
  batch is then not the finished one, and its budget and status differ.
- `deferred.json` with `reserve_usd` 6.0 and `writer_usd` 3.0, so neither
  matches a quarter of 40.0 and the two differ. Give one spec a field set
  at its default, such as `priority=3`.

**The first witness.** Close the batch `UNTIL`, so a hardcoded `DRAINED`
shows. `chdir` to the parent of the repo and pass `--repo repo`, relative.
Replace each adapter builder on `cli` with a recorder of its arguments.
The end review's recorder returns a callable that returns a real
`end_review.StackReview`. Its `fields` maps the top layer's key to a full
`end_review.LayerFields`, `diff_base` included, whose `head` is
`"e" * 40`. A plain object would pass a wrapper that reads `fields` off
anything, and SA-0306's wrapper reads only a `StackReview`. Replace
`cli.preflight.check_readiness` with a recorder that passes. Assert it ran
once, with the resolved repo, `cli._mirror_path` of it and the home, and
the home as `home`.
Replace `cli.write_stack_view` with a recorder. The faked
`run_stack_batch` records its call, calls the handed `end_review` once,
and returns `DRAINED`. Assert every value criterion 1 names. Assert the
finish's `heads` mapping equals `{top key: "e" * 40}` after the run, and
that the review's and the citation check's caches are one empty dict. Then
rerun `main` with the faked `run_stack_batch` returning each other reason,
and assert each exit code and printed line.

**The second witness.** Make `run_stack_batch` a recorder and assert it
never ran. Replace `cli.preflight.check_readiness` with one that passes,
except in its own case, where it fails at `mirror` with a detail the line
must carry. For the other id, rewrite the file's `batch_id` before the
run. Drive each case, each end-review status included, with its own home. For the
missing row, copy the batch's `finish/<id>` directory to `finish/99`, set
that file's `batch_id` to 99, and run `finish 99`. For the three end-review statuses, record one row on the
top layer with `Ledger.record_end_review`. For the finishing row, use
`Ledger.record_stack_finish`. An autouse fixture sets the token
(`tests/test_cli.py:62-65`). Unset it with `monkeypatch.delenv` inside a
`monkeypatch.context()`.

**Measured on a prototype at `45305c7a`.** A commit below it stubbed
`StackResume` and the `resume` keyword. It also stubbed the `heads`
keyword, `SA-0306`'s wrapper, the `batch_id` keyword, `diff_base` and
`StackReview.fields`. The prototype passed both new
witnesses, `ruff` and `ty`. Each failed with `saffron/cli.py` reverted to
the stubs. Each wrong version above was applied as an edit, and its
criterion's witness failed every time. Its diff measured 646 changed
tokens outside `tests/` and 932 inside, about 395 lines. The estimate is
that figure, docstrings and the `CLAUDE.md` edits included.

**Exit codes mirror `_batch`.** The reason reports the night. So a finish
over a night closed `INCOMPLETE` or `INFRASTRUCTURE` exits 2, though its own
tail ran. A retry then meets the end-review refusal.

**No unattended refusal.** `_batch` calls `runtime.unattended_refusal()`
before readiness. The finish is attended, so it does not.

**The `prose` gate** counts each new comment and docstring, and each
edited `CLAUDE.md` sentence. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words.
