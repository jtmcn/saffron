---
id: SA-0174
title: A stack batch leaves the delegate no findings file to file its backlog from
type: feature
priority: 1
depends_on: [SA-0151]
touches:
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/cli.py
  - tests/test_finish.py
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
  - saffron/batch.py
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
  - tests/test_batch.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_end_review.py
  - tests/test_task.py
budget_usd: 23
max_attempts: 3
max_turns: 130
estimated_lines: 490
estimate_measured: true
acceptance:
  - claim: >-
      `finish.write_findings(ledger, batch_id, unrun, dest, *, pooled=())`
      writes `dest` as a JSON object of `batch`, `findings` and
      `follow_ups`, makes its directory, and returns `dest`. `batch` is the
      batch's id as an `int`. `findings`
      walks the batch's layers in position order, and each layer's
      `qualifications` rows in the order recorded. A `qualified` row is
      `pooled`, with that `Pooled`'s reason, when a `Pooled` in `pooled`
      holds its finding. The `Pooled` must name the layer's `task_key` and
      the row's file, and its group must hold a `Qualified` whose `finding`
      has the row's lens, line and claim. That `Qualified` can sit at any
      place in the group. Where two such `Pooled` hold it, the first one's
      reason wins. Every other `qualified` row is `follow_up`, with an
      empty reason. A row whose outcome is `unverified`, `unanchored` or
      `note` is listed as it stands, and a `killed` row is left out. For a
      generation 1 layer, every finding its own critic left follows, in the
      order recorded, as `left_by_critic`. That is each finding of a lens
      in `review.LENSES`, of any severity, anchored or not, with a verdict
      or without one. Its reason is its verdict, or empty when it has none.
      After the layers, each follow-up in `follow_ups` adds the findings
      its own critic left the same way, in task order, whatever state it
      ended in. Each entry holds the keys `spec_id`, `head`, `lens`,
      `severity`, `file`, `line`, `claim`, `outcome` and `reason`. Its
      `head` is the task's `pushed_sha`, `null` when it has none.
      `follow_ups` lists each follow-up task of the batch that is no
      layer and not in `unrun`, in task order. Each holds the keys
      `spec_id`, `state`, `path` and `text`, the last two from its latest
      `spec_texts` row. A task is a follow-up when
      its first `spec_texts` row has the origin `follow_up`. A batch with
      no layer writes both lists empty. The witness drives all five
      outcomes, and a pooled finding whose severity a probe promoted. On the
      pooled file it drives a killed and an unverified row of the same
      finding, a qualified row of another finding on the same layer, and
      one of the same finding on another layer. It drives four qualified
      rows that differ from the pooled finding in its line alone, its file
      alone, its lens alone and its claim alone. It drives two `Pooled`
      holding one finding, the first holding it second in its group. It
      drives another batch's pooled group, a generation 0
      layer's in-cell concern, and layers recorded out of position order.
      On a follow-up layer it drives a concern, a blocker with each of the
      two verdicts, a blocker with a rebuttal alone, an unanchored note, a
      `conventions` concern and a `spec` lens concern. It drives a
      follow-up that ran and missed after a revision, one that gate 0
      refused, an unrun one, a revised queued spec with no layer, and
      another batch's follow-up. It drives follow-ups whose critic left
      findings and that ended `EXHAUSTED`, `REVIEWING`, `REBUTTING` and
      `GATE_ERROR`, created out of spec id order. It drives findings on the
      revised queued spec and on another batch's follow-up.
    witness: tests/test_finish.py::test_findings_json_holds_each_layers_findings_and_each_follow_up_that_added_no_layer
    wrong_versions:
      - Pool membership checked before the outcome, which pools the killed and unverified rows.
      - A `qualified` row matched by no `Pooled` left `qualified` rather than `follow_up`.
      - A pooled finding matched by its layer and file alone.
      - A pooled finding matched by the finding alone, whatever the group's layer and file.
      - A match through `group.findings[0]` alone.
      - A match that compares the severity too, so the promoted finding matches no row.
      - The last `Pooled`'s reason winning.
      - Each entry's head taken from its layer's `predecessor_head`.
      - A generation 0 layer's in-cell concern kept.
      - A lens set hard-coded to `correctness`, `contract` and `adequacy` rather than read from `review.LENSES`, which drops the `conventions` concern.
      - A rebuttal put in the reason when there is no verdict.
      - Critic findings added only for follow-ups not ended `EXHAUSTED`, which drops `TE-22`'s concern.
      - A follow-up's kind read off its latest `spec_texts` row, which drops `TE-22`.
      - The layers in the order recorded, not by position.
      - Follow-ups, and their critic findings, ordered by spec id.
  - claim: >-
      `cli._stack_finish` takes `pooled`, and `saffron batch --stack` passes
      it the very list it passes `_stack_follow_ups`. Given a batch id and
      `unrun`, the finish calls `finish.write_findings` with them, a `dest`
      of `out_dir / "finish" / <batch id> / finish.FINDINGS_NAME`, and that
      list as `pooled`. It does so before `finish.commit_finish`, and prints
      `finish: findings at <path>`. The findings call sits in a `try` of its
      own that catches `Exception`, as `_stack_follow_ups` does. Any raise
      from `write_findings` prints one line naming its type and message,
      the commit still runs, and the night's exit code stays its stop
      reason's. The witness appends a `Pooled` to the list after
      `_stack_finish` is built and before the finish runs. It drives a
      findings file, then a `GitError`, a `ValueError` and a `KeyError`
      from `write_findings`, and a `GitError` from `commit_finish`.
    witness: tests/test_cli.py::test_a_stack_batch_writes_its_findings_from_the_pooled_list_its_writer_filled
    wrong_versions:
      - A new list passed as `pooled`.
      - A copied list passed as `pooled`.
      - No `pooled` passed, with an empty default in its place.
      - A copy of the list taken when `_stack_finish` is built, which misses the sentinel.
      - One `try` around both calls, so a findings raise skips the commit.
      - A guard on named types, such as `(GitError, OSError, ValueError)`, which lets the `KeyError` reach `main`.
      - No guard on the findings call, so its raise reaches `main` and exits 2.
      - The findings written after the commit.
      - A `dest` outside `out_dir / "finish" / <batch id>`.
      - A `dest` inside the finishing tree's own workdir.
  - claim: >-
      `saffron batch` without `--stack` still hands `run_batch` its budget
      and its defaults.
    witness: tests/test_cli.py::test_saffron_batch_runs_a_night_with_the_defaults_4_2_1_fixes
    preserves: true
---

## Context

Backlog item **b-792ab2**, step 8 of its Done. It cites `DESIGN.md` §4.2,
§4.2.1 and §5.5. Section 4 of
`docs/superpowers/specs/2026-09-23-stack-batch-design.md`, "The finishing
layer", is the design. The finish writes the backlog pool to
`findings.json` in the batch tree. The delegate files the backlog, its
`rejections.md` lines and the origin items from it, in a pull request on
top of the stack. A program core runs that is not a gate would break ADR 2,
so core writes the file and files nothing. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
sends "the findings a follow-up's own critic leaves" to the backlog, not
to a second generation. It sends every end-review `note` to the backlog
pool too. So the file lists every finding a follow-up's critic left,
notes included.

**Which `findings.json` this is.** It lives at `out_dir / "finish" /
<batch id> / "findings.json"`, one per stack batch. Each cell already
writes its own critic's `findings.json` into its task directory,
`out_dir / <spec id>` (`saffron/cell/session.py:2850`). The
two files share a name and nothing else.

**Step 8 is four specs.** `SA-0151` builds the finishing commit and runs
it at the end of the batch. This spec writes `findings.json` beside it.
`SA-0167` follows. It runs the gate suite on the finishing tree, pushes
the commit to the finishing layer's own branch, and opens its pull
request. `SA-0170` links the stack.

**What the tree base holds.** `SA-0151` merged in #628, so the tree base
is `main` at `2538699c`. Only `depends_on[0]` stacks
(`saffron/task.py:197`, `:245`). Line numbers below were read at
`2538699c`. This spec consumes these.

- From `SA-0145`: the `stack_layers` table (`saffron/ledger.py:220`)
  and `Ledger.record_stack_layer`.
- From `SA-0179` and `SA-0180`: the `qualifications` table
  (`saffron/ledger.py:244`), one row per end-review finding under its
  layer's task, with `lens`, `severity`, `file`, `line`, `claim`,
  `outcome` and `reason`. `severity` is the one the lens filed, captured
  before a survived probe promotes the finding to a `blocker`. `outcome`
  is one of `qualified`, `killed`, `unverified`, `unanchored` and `note`.
  A killed probe drops its finding. `Ledger.record_qualification` writes
  it. `qualify.FollowUpGroup` holds a `task_key`, a `file` and a tuple of
  `Qualified` (`saffron/qualify.py:44-51`). Each `Qualified` holds
  `task_key`, `finding`, `outcome` and `reason`, in that order
  (`:32-41`). Its `finding` is the object a probe promotes in place. A
  production group holds several (`:220-224`).
- From `SA-0182`: the `spec_texts` table, `Ledger.record_spec_text`,
  `Ledger.spec_text` and `Ledger.spec_texts`. A task's kind is its first
  row's origin.
- From `SA-0161` and `SA-0165`: `follow_up.Pooled`, of `group` and
  `reason` (`saffron/follow_up.py:38-47`). `write_follow_ups` appends one
  to a caller-owned list as each group pools. A group can be narrowed to
  the findings it pooled. `_batch`'s `--stack` path creates
  `pooled: list[follow_up.Pooled] = []` and passes it to
  `_stack_follow_ups(..., pooled=pooled)`. That closure catches
  `Exception` and leaves the list complete after a raise.
- From `SA-0162`: the follow-ups run as generation 1 layers. `unrun` is
  the task id of each follow-up never reviewed, in the order the batch met
  them (`saffron/batch.py:812-816`).
- From `SA-0151`: `Ledger.stack_layers(batch_id)`, the batch's rows by
  `position`. Each row carries `position`, `spec_id`, `predecessor_key`,
  `predecessor_head` and `generation`, and its task's `task_id`, `state`,
  `budget_usd`, `pr_url`, `branch` and `pushed_sha`. It selects no
  `task_key`. This spec adds `sl.task_key` to that SELECT and to the
  docstring's column list, so `saffron/ledger.py` is in `touches`. No test
  at the tree base asserts that row's column set. Also from `SA-0151`:
  `finish.commit_finish`, and `cli._stack_finish(*, pinned, ledger,
  out_dir)` (`saffron/cli.py:679-703`). Its callable takes the batch id
  as an `int` and `unrun`, commits, and prints one line. It catches
  `GitError` and `ValueError` from `commit_finish` alone, and its
  docstring says any other raise reaches `main` (`:682-684`).
  `run_stack_batch` calls it once, after the
  follow-ups, as `finish(batch_id, unrun_task_ids)`
  (`saffron/batch.py:817-818`). It does so on each stop reason the drive
  returns. A raise out of `_drive` skips `finish` and closes the batch
  `INFRASTRUCTURE` (`:741-823`). Last, the `stack`
  fixture in `tests/test_finish.py`.

**What the base already offers.** `Ledger.findings` returns a task's
findings in the order recorded (`saffron/ledger.py:1660`).
`record_rebuttal` writes a verdict and a rebuttal (`:1641`).
`review.LENSES` names the four in-cell lenses, `correctness`, `contract`,
`adequacy` and `conventions` (`saffron/phases/review.py:40-45`). REBUT
rebuts anchored blockers alone (`saffron/phases/rebut.py:3-5`). The cell
writes a verdict and a rebuttal onto each anchored blocker's row alone
(`saffron/cell/session.py:2984-2989`), so a concern or a note carries
neither. `saffron batch` writes its batch tree under `out_dir`, which is
`<home>/batches/v0` by default (`saffron/cli.py:204`).

## Problem

Build three things.

1. **The reads.** Change `Ledger` in three places.
   - `stack_layers(batch_id)` selects `sl.task_key` too.
   - `qualifications(task_id)`: the task's `qualifications` rows by its
     record key, `ORDER BY position`.
   - `batch_follow_ups(batch_id)`: each task on a run with that
     `batch_id` whose first `spec_texts` row, by `n`, has the origin
     `follow_up`. Order by `task_id`, with the task's `task_id`,
     `spec_id`, `state` and `pushed_sha`.

   If the tree base already holds a `Ledger` method returning either new
   set of rows, use it and add no second one.
2. **The file.** Add `FINDINGS_NAME` of `"findings.json"` and
   `write_findings` to `saffron/finish.py`, as criterion 1 states. Match a
   row to a `Pooled` through each `q.finding` of its group, by lens, line
   and claim. Never match by severity, since the group holds the promoted
   one. Read a critic's findings with
   `Ledger.findings`, and keep those whose lens is in `review.LENSES`.
3. **The wiring.** `_stack_finish` gains `pooled`, as criterion 2 states.
   It calls `write_findings` in a `try` of its own, before the commit's,
   and that `try` catches `Exception`. The `dest` joins
   `finish.FINDINGS_NAME`, which is that name's reader. In `_batch`'s
   `--stack` path, pass `_stack_finish` the list `SA-0165` creates there.
   Leave the commit's own guard on `GitError` and `ValueError` as it is.
   Reword `_stack_finish`'s docstring so it names the findings call and
   its guard. Reword `saffron/finish.py`'s module docstring, which names
   the commit alone, so it names the findings file too.

**Why `batch_follow_ups` reads `runs.batch_id`.** A stack batch mints a
fresh task for every spec each night. `SA-0161` attaches each
follow-up's run to the batch (`saffron/follow_up.py:373`). So every
follow-up of tonight is on a run of tonight's batch, and no earlier one is.

**Which follow-ups the file names.** A follow-up that became a layer is in
the stack. An unrun one is committed by `SA-0151` and queued once the stack
merges. The rest ran and missed, escalated, or met a gate 0 refusal. Each
learned something, so the delegate reads its state here.

## Out of scope

- **A layer the end review never reached.** It records `not_reached`
  (`SA-0153`) and no `qualifications` row, so its findings are in no
  file. The stack view shows it as unreviewed (`SA-0152`).
- **A raise before `qualify` runs.** `SA-0165` names it. No
  `qualifications` row and no `Pooled` exist, so the file lists nothing
  for the batch's layers.
- **A raise that skips `finish`.** A raise out of `_drive`, `end_review`
  or `follow_ups` skips `finish` (`saffron/batch.py:437-440`), so no file
  is written. The command-line closures for the last two catch
  `Exception`, so in production only `_drive` raises past them.
- **A batch with no layer but with follow-ups.** Follow-ups come from the
  layers' end review, so a batch with no layer has none. The witness's
  empty batch therefore holds neither, and does not tell apart a build
  that lists follow-ups whatever the layer count.
- **Why a follow-up is `QUEUED`.** The round 1 review of this spec found
  four causes that leave a listed follow-up `QUEUED`. The file carries the
  state alone, so it does not tell them apart.
- **Which follow-up a finding fed.** A `follow_up` entry names no
  follow-up spec, and a follow-up names no finding. No fact links the two,
  so the file cannot either.
- **Filing the backlog.** The delegate files it from this file, until a
  declared program does (design section 4).
- **The gate suite, the push and the link.** The gate suite and the push are
  `SA-0167`'s, and the link is `SA-0170`'s.
- **Unrun follow-ups after a finish that escalates.** `SA-0151` commits
  their texts, so this file leaves them out. When `SA-0167` escalates,
  that commit reaches no branch, and their texts stay in the record alone.
  In this repo every finish with a layer escalates red, as backlog item
  b-b0cd68 records.
- **The vocabulary.** `CONTEXT.md` has no entry for the backlog pool or
  `findings.json`. Backlog item b-466005 files them by hand.

## Notes for the agent

**Both criteria but the last are new code.** No text at the tree base
writes `findings.json`. So criteria 1 and 2 declare a witness and no
mutant, and `witness` reports `skip` for them. Import `write_findings`
inside the test body, so the reverted run fails rather than failing to
collect. Criterion 3 names a test that passes now.

**`SA-0151`'s command-line witness must pass unedited.** It is
`tests/test_cli.py::test_a_stack_batch_commits_its_finish_and_survives_a_raise`.
With this spec its finish also calls the real `write_findings`. Its last
case replaces `Ledger.stack_layers` with `[{"position": 1}]`. So
`write_findings` raises `KeyError` on that dict row. The `Exception`
guard prints it, the commit still runs, and the night exits 0. A guard on
named types lets the `KeyError` reach `main`, which exits 2, and that
case fails. Do not edit that test.

**Criterion 1's witness** uses the `stack` fixture `SA-0151`'s witnesses
share. In batch B, `TE-10` at position 1 and `TE-7` at 2 are generation
0, and `TE-20` at 3 is generation 1. They are recorded in the order
`TE-7`, `TE-20`, `TE-10`. `TE-5` is a revised queued spec ended
`EXHAUSTED`. `TE-21` is an unrun follow-up left `QUEUED`. `TE-22` is a
follow-up with a later revision row, ended `EXHAUSTED`. `TE-23` is a
follow-up refused by `run_task`'s gate 0 after its review, left `QUEUED`.
`TE-24` holds no spec text. Batch O holds the layer `TE-6` and the
follow-up `TE-26`, ended `EXHAUSTED`. The fixture returns each B layer's
packaged head in `heads`. It returns neither its `_task` helper nor
`repo_id` nor `base_sha`. So extend the fixture to return `_task` as
`task`, which closes over the other two. `heads` lacks `TE-6`, and no B
entry carries `TE-6`'s head, so it needs none. Reach each task by its
spec id. Then record these `qualifications`, each at line 3 unless the
table says otherwise:

| task | lens | filed | outcome | file | claim | reason |
|---|---|---|---|---|---|---|
| `TE-7` | `spec` | concern | `qualified` | `qualified.py` | pooled spec | |
| `TE-10` | `join` | blocker | `qualified` | `qualified.py` | join | |
| `TE-10` | `spec` | concern | `qualified` | `qualified.py` | pooled spec | |
| `TE-10` | `spec` | concern | `qualified` | `written.py` | written | |
| `TE-10` | `spec` | concern | `qualified` | `qualified.py`, line 4 | pooled spec | |
| `TE-10` | `spec` | concern | `qualified` | `written.py` | pooled spec | |
| `TE-10` | `standards` | concern | `qualified` | `qualified.py` | pooled spec | |
| `TE-10` | `spec` | concern | `qualified` | `qualified.py` | other | |
| `TE-10` | `spec` | concern | `killed` | `qualified.py` | pooled spec | |
| `TE-10` | `standards` | concern | `unanchored` | `unanchored.py` | far | |
| `TE-10` | `correctness` | note | `note` | `note.py` | note | |
| `TE-10` | `spec` | concern | `unverified` | `qualified.py` | pooled spec | errored |
| `TE-6` | `spec` | concern | `qualified` | `qualified.py` | pooled spec | |

The `join` row sits on `TE-10`, the bottom layer, though `qualify` files
join findings under the top one (`saffron/qualify.py:226-236`). That is
harmless, since `write_findings` never reads which layer is the top.

It records one `correctness` concern on `TE-10`. On `TE-20` it records
seven findings. They are a `correctness` concern, a `contract` blocker
given the verdict `confirmed` and a rebuttal, and an `adequacy` blocker
given a rebuttal and no verdict. Then come a `correctness` blocker given
the verdict `withdrawn`, a `correctness` note recorded unanchored, a
`conventions` concern and a `spec` concern. It records one `correctness`
concern on `TE-22`.

In the test body, not the shared fixture, it creates three more follow-ups
in B with `stack.task`. Each has one `follow_up` text row and no push.
It creates them in the order `TE-29`, `TE-27`, `TE-28`, so task order
differs from spec id order. `TE-29` ends `GATE_ERROR` with an `adequacy`
note, then a `spec` concern. `TE-27` ends `REVIEWING` with a
`correctness` concern. `TE-28` ends `REBUTTING` with a `contract` blocker
and no verdict. It also records a `correctness` concern on `TE-5` and on
`TE-26`.

`pooled` holds three groups on `qualified.py`. They name `TE-10`'s key
with "cap", `TE-6`'s with "O", and `TE-10`'s again with "later". Each
holds `Qualified(task_key, Finding(...), "qualified", "")` whose `Finding`
is a `spec` finding at line 3 with the claim "pooled spec" and the
severity `blocker`. The "cap" group holds a second `Qualified` ahead of
that one, a `spec` blocker at line 9 with the claim "unmatched", which
matches no row. It calls `write_findings` for B with `unrun` of `TE-21`'s
task, and a `dest` in a directory that does not exist. It asserts the
return is `dest`, the whole object, and `batch` an `int` equal to B's
id. Each layer entry's `head` is its layer's packaged head. `findings`
holds `TE-10`'s rows in order:

- `join` as `follow_up`, then the pooled spec as `pooled` with "cap"
- `written`, then the four rows that differ from the pooled finding, each
  as `follow_up`, then the `other` row as `follow_up`
- the `unanchored`, `note` and `unverified` rows

Then comes `TE-7`'s row as `follow_up`. Then come `TE-20`'s first six
findings in the order recorded, each as `left_by_critic`, each with its
severity as filed. Their reasons are empty, `confirmed`, empty,
`withdrawn`, empty and empty. Then comes `TE-22`'s concern as
`left_by_critic` with an empty reason and a `null` head. Then come
`TE-29`'s note, `TE-27`'s concern and `TE-28`'s blocker, each as
`left_by_critic` with an empty reason and a `null` head. `follow_ups`
starts with `TE-22` `EXHAUSTED`, with its path and its revised text. Then
come `TE-23` `QUEUED`, `TE-29` `GATE_ERROR`, `TE-27` `REVIEWING` and
`TE-28` `REBUTTING`, each with its path and text. Last, a fresh batch
with no layer writes both lists empty.

**Wrong builds for review only.** These are not declared, so REVIEW opens
no session on them. Each one fails criterion 1's witness, as measured
below:

- a read of `layer["task_key"]` against the `stack_layers` SELECT at the
  tree base, which raises `IndexError`
- a killed finding kept
- a `qualified` row matched by no `Pooled` dropped
- a match that drops the line, the lens, the claim, the file or the layer
- a pooled finding's reason taken from its row, or its outcome left
  `qualified`
- each entry's head taken from the top layer
- a follow-up's in-cell finding with a verdict, or with a rebuttal,
  dropped
- a follow-up's in-cell blockers or notes dropped, or its concerns alone
  kept
- a follow-up's unanchored in-cell finding dropped
- a verdict left out of the reason, or the reason fixed at `confirmed`
  for any verdict
- a `withdrawn` blocker dropped
- a follow-up that added no layer left without its critic's findings
- the findings of a task that is no follow-up, or of another batch's
  follow-up, kept
- a follow-up with no push given the last layer's head
- an end-review lens's in-cell concern kept
- a follow-up's first text listed, not its latest
- the layers, or the unrun follow-ups, listed as follow-ups too
- the follow-ups of every batch listed, or every task off the stack
- a qualification row's reason dropped
- the qualifications newest first
- no file written for a batch with no layer
- the batch id written as a string
- the directory of `dest` left unmade

**Criterion 1 is measured.** A run on 2026-10-01 at `2538699c` built a
prototype of the three reads and of `write_findings`. It lives outside
the repository, in `measure-174/` under the session scratchpad. It ran
criterion 1's witness as written above, on the `stack` fixture extended
as above. Its output is `measure-174/out-c1.txt`, one row per build,
labelled in this spec's own words. The right build passed. Each declared
wrong version, and each one in the review-only list, failed the witness.
`out-c1-old-arrangement.txt` reruns the two holes the parent-branch
review found against that review's arrangement. With one `Qualified` in
"cap", a match through `group.findings[0]` alone passed. With `TE-27`
created first, follow-ups ordered by spec id passed. Both fail the
arrangement above. A build ordering the layers by `(generation,
task_id)` passes, since that order is position order here. The review
judged that build harmless, so no row drives it.

**Criterion 2's witness** follows `SA-0151`'s command-line witness, with
`_readiness_passes` and `_fake_batch_resolution` from
`tests/test_cli.py`. It wraps `cli._stack_follow_ups` and
`cli._stack_finish` in spies that record the `pooled` each got by
keyword and call the real one. Its fake `run_stack_batch` appends a
sentinel `Pooled` to the list `_stack_follow_ups` got. Then it calls
`finish` with the `int` 3 and `[5, 6]`, and returns `UNTIL`. It replaces
`finish.write_findings` and `finish.commit_finish` with recorders in one
shared list, the findings recorder copying the `pooled` it got. It
asserts exit 0, that the two `pooled` are one object by `is`, and the
calls in order. The findings call gets 3, `[5, 6]`, the `dest` and a
list holding the sentinel alone. It asserts the `finish: findings at
<path>` line. Then, under `monkeypatch.context()`, `write_findings`
raises `GitError("disk")`, then `ValueError("bad row")`, then
`KeyError("task_id")`. Each run exits 0, prints the raise's type and
message, and still records the commit. Last, `commit_finish` raises
`GitError("gone")`, and the findings call is still recorded.

**Criterion 2 is measured.** The same run copied `saffron/` at
`2538699c` outside the repository and applied the change to the copy. It
ran criterion 2's witness and `SA-0151`'s command-line witness against
it. Its output is `measure-174/out-c2.txt`. The right build passed both.
Each of criterion 2's wrong versions failed criterion 2's witness. A
guard on `(GitError, OSError, ValueError)` failed `SA-0151`'s witness
too, on its `KeyError` case.

**What the witnesses leave undriven.** A `Pooled` whose finding matches no
row of its layer at all. It adds no entry, and no row changes outcome.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). The
prototype of the whole change, with both witnesses and both docstring
rewordings, was formatted with `ruff` and measured with `size_gate` at
`2538699c`. Its output is `measure-174/out-size.txt`. It came to 1381
tokens over 490 changed lines. `estimated_lines` is that line count, and
`estimate_measured` prices it at 1960 tokens, 65% of the ceiling.

| part | lines | tokens |
|---|---|---|
| `write_findings`, its helpers and the module docstring in `saffron/finish.py` | 86 | 268 |
| the `task_key` column and the two reads in `saffron/ledger.py` | 28 | 108 |
| `_stack_finish`'s findings call, docstring and wiring in `saffron/cli.py` | 21 | 64 |
| the fixture's `task` and criterion 1's witness in `tests/test_finish.py` | 273 | 685 |
| criterion 2's witness in `tests/test_cli.py` | 82 | 256 |

**Budget.** REVIEW ran $9 to $18 on this chain's cells. `SA-0151` spent
$9.21 with 23 wrong versions, and `SA-0162` spent $17.64 with 35. REVIEW
opens one wrong-version session per criterion
(`saffron/phases/review.py:577-597`). A session at the $2.00 floor can
run out and leave its versions unproven. So criterion 1 declares 15
wrong versions and criterion 2 declares 10, which keeps each session's
load small. The rest sit in the review-only list above.
