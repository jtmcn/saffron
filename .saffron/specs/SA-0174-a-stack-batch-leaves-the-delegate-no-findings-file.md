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
budget_usd: 22
max_attempts: 3
max_turns: 130
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
      the row's file, and its group must hold a finding of the row's lens,
      line and claim. Where two such `Pooled` hold it, the first one's
      reason wins. Every other `qualified` row is `follow_up`, with an
      empty reason. A row whose outcome is `unverified`, `unanchored` or
      `note` is listed as it stands, and a `killed` row is left out. For a
      generation 1 layer, every finding its own critic left follows, in the
      order recorded, as `left_by_critic`. That is each finding of a lens
      in `review.LENSES`, of any severity, anchored or not, with a verdict
      or without one. Its reason is its verdict, or empty when it has none.
      After the layers, each follow-up in `follow_ups` adds the findings
      its own critic left the same way, in task order, whatever state it
      ended in. Each entry holds the task's spec id and its `pushed_sha`,
      `null` when it has none, as `head`. Then come the lens, severity,
      file, line, claim, outcome and reason. `follow_ups` lists each follow-up task of the batch that is no
      layer and not in `unrun`, in task order. Each holds its spec id, its
      state, and its latest `spec_texts` row's `path` and `text`. A task is a follow-up when
      its first `spec_texts` row has the origin `follow_up`. A batch with
      no layer writes both lists empty. The witness drives all five
      outcomes, and a pooled finding whose severity a probe promoted. On the
      pooled file it drives a killed and an unverified row of the same
      finding, a qualified row of another finding on the same layer, and
      one of the same finding on another layer. It drives four qualified
      rows that differ from the pooled finding in its line alone, its file
      alone, its lens alone and its claim alone. It drives two `Pooled`
      holding one finding, another batch's pooled group, a generation 0
      layer's in-cell concern, and layers recorded out of position order.
      On a follow-up layer it drives a concern, a blocker with each of the
      two verdicts, a blocker with a rebuttal alone, an unanchored note and
      a `spec` lens concern. It drives a follow-up that ran and missed after
      a revision, one that gate 0 refused, an unrun one, a revised queued
      spec with no layer, and another batch's follow-up. It drives
      follow-ups whose critic left findings and that ended `REVIEWING`,
      `REBUTTING` and `GATE_ERROR`. It drives findings on the revised
      queued spec and on another batch's follow-up.
    witness: tests/test_finish.py::test_findings_json_holds_each_layers_findings_and_each_follow_up_that_added_no_layer
  - claim: >-
      `cli._stack_finish` takes `pooled`, and `saffron batch --stack` passes
      it the very list it passes `_stack_follow_ups`. Given a batch id and
      `unrun`, the finish calls `finish.write_findings` with them, a `dest`
      of `out_dir / "finish" / <batch id> / finish.FINDINGS_NAME`, and that
      list as `pooled`. It does so before `finish.commit_finish`, and prints
      `finish: findings at <path>`. A raise from `write_findings` prints
      one line naming its type and message, the commit still runs, and the
      night's exit code stays its stop reason's. The witness appends a
      `Pooled` to the list after `_stack_finish` is built and before the
      finish runs. It drives a findings file, a `GitError` and a
      `ValueError` from `write_findings`, and a raise from `commit_finish`.
    witness: tests/test_cli.py::test_a_stack_batch_writes_its_findings_from_the_pooled_list_its_writer_filled
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
`out_dir / <spec id>` (`saffron/cell/session.py:1646`, `:2652-2654`). The
two files share a name and nothing else.

**Step 8 is four specs.** `SA-0151` builds the finishing commit and runs
it at the end of the batch. This spec writes `findings.json` beside it.
`SA-0167` follows. It runs the gate suite on the finishing tree, pushes
the commit to the finishing layer's own branch, and opens its pull
request. `SA-0170` links the stack.

**What the tree base holds.** This spec's tree base is `SA-0151`'s head.
Only `depends_on[0]` stacks (`saffron/task.py:144-147`). None of the chain
from `SA-0142` on exists at `ead4c8ee`, where every line number below was
read. So chain names are cited by symbol. This spec consumes these.

- From `SA-0145`: the `stack_layers` table and `Ledger.record_stack_layer`.
- From `SA-0147`: the `qualifications` table, one row per end-review
  finding under its layer's task, with `lens`, `severity`, `file`,
  `line`, `claim`, `outcome` and `reason`. `severity` is the one the lens
  filed, captured before a survived probe promotes the finding to a
  `blocker`. `outcome` is one of `qualified`, `killed`, `unverified`,
  `unanchored` and `note`. A killed probe drops its finding.
  `Ledger.record_qualification` writes it. `qualify.FollowUpGroup` holds a
  `task_key`, a `file` and a tuple of `Finding`s.
- From `SA-0150`: the `spec_texts` table, `Ledger.record_spec_text` and
  `Ledger.spec_text`. A task's kind is its first row's origin.
- From `SA-0161` and `SA-0165`: `follow_up.Pooled`, of `group` and
  `reason`. `write_follow_ups` appends one to a caller-owned list as each
  group pools. A group can be narrowed to the findings it pooled.
  `SA-0165`'s `_batch` creates `pooled: list[follow_up.Pooled] = []` on
  the `--stack` path, and passes it to `_stack_follow_ups(..., pooled)`.
  The list is complete even after a raise.
- From `SA-0162`: the follow-ups run as generation 1 layers. `unrun` is
  the task id of each follow-up never reviewed, in the order the batch met
  them.
- From `SA-0151`: `Ledger.stack_layers(batch_id)`, the batch's rows by
  `position`, each with its task's `task_id`, `state`, `branch` and
  `pushed_sha`. `finish.commit_finish`. `cli._stack_finish(*, pinned,
  ledger, out_dir)`, whose callable takes the batch id as an `int` and
  `unrun`, commits, and prints one line. `run_stack_batch` calls it once,
  after the follow-ups, whatever the stop reason. The `stack` fixture in
  `tests/test_finish.py`.

**What the base already offers.** `Ledger.findings` returns a task's
findings in the order recorded (`saffron/ledger.py:1190-1196`), and
`record_rebuttal` writes a verdict and a rebuttal (`:1171-1188`).
`review.LENSES` names the three in-cell lenses
(`saffron/phases/review.py:39-43`). REBUT rebuts anchored blockers alone
(`saffron/phases/rebut.py:3-5`). The cell writes a verdict and a rebuttal
onto each anchored blocker's row alone (`saffron/cell/session.py:2785-2790`),
so a concern or a note carries neither. `saffron batch` writes its batch tree under `out_dir`, which is
`<home>/batches/v0` by default (`saffron/cli.py:182`).

## Problem

Build three things.

1. **The reads.** Add two methods to `Ledger`.
   - `qualifications(task_id)`: the task's `qualifications` rows by its
     record key, `ORDER BY position`.
   - `batch_follow_ups(batch_id)`: each task on a run with that
     `batch_id` whose first `spec_texts` row, by `n`, has the origin
     `follow_up`. Order by `task_id`, with the task's `task_id`,
     `spec_id`, `state` and `pushed_sha`.

   If the tree base already holds a `Ledger` method returning either set of
   rows, use it and add no second one.
2. **The file.** Add `FINDINGS_NAME` of `"findings.json"` and
   `write_findings` to `saffron/finish.py`, as criterion 1 states. Match a
   finding to a `Pooled` by lens, line and claim, never by severity, since
   the group holds the promoted one. Read a critic's findings with
   `Ledger.findings`, and keep those whose lens is in `review.LENSES`.
3. **The wiring.** `_stack_finish` gains `pooled`, as criterion 2 states.
   It calls `write_findings` in a `try` of its own, before the commit's.
   The `dest` joins `finish.FINDINGS_NAME`, which is that name's reader.
   In `_batch`'s `--stack` path, pass `_stack_finish` the list `SA-0165`
   creates there.

**Why `batch_follow_ups` reads `runs.batch_id`.** A stack batch mints a
fresh task for every spec each night, and `SA-0161` attaches each
follow-up's run to the batch. So every follow-up of tonight is on a run of
tonight's batch, and no earlier one is.

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

**`SA-0151`'s command-line witness still runs the finish.** With this spec
it also calls `write_findings`, on that test's own ledger. Its last case
replaces `Ledger.stack_layers` to return one row, and `SA-0151` pins no
field of that row. So the findings call writes a file or raises on the
row, and prints its line either way. The commit's line still prints.
Leave that witness as it is unless it fails.

**Criterion 1's witness** uses the `stack` fixture `SA-0151`'s witnesses
share. In batch B its layers are `TE-10` at 1, `TE-7` at 2 and `TE-20` at
3 at generation 1, recorded out of order. `TE-5` is a revised queued spec
ended `EXHAUSTED`. `TE-21` is an unrun follow-up left `QUEUED`. `TE-22`
is a follow-up with a later revision row, ended `EXHAUSTED`. `TE-23` is a
follow-up refused by `run_task`'s gate 0 after its review, left `QUEUED`.
Batch O holds the layer `TE-6` and the follow-up `TE-26`, ended
`EXHAUSTED`. The fixture returns each layer's packaged head. Extend it
where it lacks one, and reach each task by its spec id. Then record these
`qualifications`, each at line 3 unless the table says otherwise:

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

It records one `correctness` concern on `TE-10`. On `TE-20` it records
six findings. They are a `correctness` concern, a `contract` blocker
given the verdict `confirmed` and a rebuttal, and an `adequacy` blocker
given a rebuttal and no verdict. Then come a `correctness` blocker given
the verdict `withdrawn`, a `correctness` note recorded unanchored, and a
`spec` concern.

In the test body, not the shared fixture, it creates three more follow-ups
in B, the way the fixture creates `TE-22`. Each has one `follow_up` text
row and no push. `TE-27` ends `REVIEWING` with a `correctness` concern.
`TE-28` ends `REBUTTING` with a `contract` blocker and no verdict. `TE-29`
ends `GATE_ERROR` with an `adequacy` note, then a `spec` concern. It also
records a `correctness` concern on `TE-5` and on `TE-26`.

`pooled` holds three groups on `qualified.py`, each of one `spec` finding
at line 3 with the claim "pooled spec" and the severity `blocker`. They
name `TE-10`'s key with "cap", `TE-6`'s with "O", and `TE-10`'s again with
"later". It calls `write_findings` for B with `unrun` of `TE-21`'s task,
and a `dest` in a directory that does not exist. It asserts the whole
object, and `batch` equal to B's `int` id. Each entry's `head` is its
layer's packaged head. `findings` holds `TE-10`'s rows in order:

- `join` as `follow_up`, then the pooled spec as `pooled` with "cap"
- `written`, then the four rows that differ from the pooled finding, each
  as `follow_up`
- the `unanchored`, `note` and `unverified` rows

Then comes `TE-7`'s row as `follow_up`. Then come `TE-20`'s first five
findings in the order recorded, each as `left_by_critic`, each with its
severity as filed. Their reasons are empty, `confirmed`, empty,
`withdrawn` and empty. Then come `TE-27`'s concern, `TE-28`'s blocker and
`TE-29`'s note, each as `left_by_critic` with an empty reason and a `null`
head. `follow_ups` starts with `TE-22` `EXHAUSTED`, with its path and its
revised text. Then come `TE-23` `QUEUED`, `TE-27` `REVIEWING`, `TE-28`
`REBUTTING` and `TE-29` `GATE_ERROR`, each with its path and text. Last, an empty batch
writes both lists empty. These fail it:

- a killed finding kept
- pool membership checked before the outcome, which pools the killed and
  unverified rows
- a follow-up's qualified rows dropped, or left `qualified`
- a pooled finding matched by its layer and file alone, or by the finding
  alone
- a match that drops the line, the lens, the claim or the file
- a match that compares the severity too
- the last `Pooled`'s reason winning
- a pooled finding's reason taken from its row, or its outcome left
  `qualified`
- each entry's head taken from its predecessor, or as the top layer's
- a generation 0 layer's in-cell concern kept
- a follow-up's in-cell finding with a verdict, or with a rebuttal, dropped
- a follow-up's in-cell blocker or note dropped, or its concerns alone kept
- a follow-up's unanchored in-cell finding dropped
- a verdict left out of the reason, or a rebuttal put there
- the reason fixed at `confirmed`, or a `withdrawn` blocker dropped
- a follow-up that added no layer left without its critic's findings
- the findings of a task that is no follow-up, or of another batch's
  follow-up, kept
- a follow-up with no push given another task's head
- an end-review lens's concern kept
- a follow-up's kind read off its latest row, which drops `TE-22`
- a follow-up's first text, not its latest
- the layers and the unrun follow-ups listed as follow-ups too
- the follow-ups of every batch, or every task off the stack
- a row's reason dropped
- the qualifications newest first
- the layers as recorded, not by position
- no file written for a batch with no layer

**How the list was measured.** A throwaway run on 2026-09-25 at
`68892367` stood in for `SA-0145`'s, `SA-0147`'s and `SA-0150`'s tables
and writers. It stood in for `SA-0161`'s `Pooled` and `FollowUpGroup`
too. It loaded a prototype of the two reads and of `write_findings`, and
ran a prototype of criterion 1's witness. The right build passed. Each
wrong build that run named was applied as a text edit to the prototype,
and each failed the witness. That prototype listed a follow-up layer's
concerns with no verdict and no rebuttal alone. ADR 7 names every finding
a follow-up's own critic leaves, layer or not. So the nine wrong builds on
that list are unmeasured, and so are `TE-27` to `TE-29`.

**Criterion 2's witness** follows `SA-0151`'s command-line witness, with
`_readiness_passes` (`tests/test_cli.py:2603-2621`) and
`_fake_batch_resolution` (`:2624-2640`). It wraps `cli._stack_follow_ups`
and `cli._stack_finish` in spies that record the `pooled` each got and
call the real one. Its fake `run_stack_batch` appends a sentinel `Pooled`
to the list `_stack_follow_ups` got. Then it calls `finish` with the `int`
3 and `[5, 6]`, and returns `UNTIL`. It replaces `finish.write_findings`
and `finish.commit_finish` with recorders in one shared list, the
findings recorder copying the `pooled` it got. It asserts exit 0, that
the two `pooled` are one object by `is`, and the calls in order. The
findings call gets 3, `[5, 6]`, the `dest` and a list holding the
sentinel alone. It asserts the `finish: findings at <path>` line. Then,
under `monkeypatch.context()`, `write_findings` raises `GitError("disk")`,
then `ValueError("bad row")`. Each run exits 0, prints the raise, and
still records the commit. Last, `commit_finish` raises, and the findings
call is still recorded. These fail it:

- a new or copied list passed as `pooled`, or none
- a copy of the list taken at build time, which misses the sentinel
- the findings written after the commit
- one `try` around both calls, so a findings raise skips the commit
- a guard around `GitError` or `OSError` alone, which lets the
  `ValueError` reach `main`
- a `dest` outside `out_dir / "finish" / <batch id>`
- a raise that reaches `main`, which exits 2

This criterion is unmeasured. The `--stack` path does not exist at
`ead4c8ee`.

**What the witnesses leave undriven.** A `Pooled` whose finding matches no
row of its layer. It adds no entry, and no row changes outcome.

**The `prose` gate** reads every new comment and docstring
(`.saffron/gates/prose.py`). Write no em dash, semicolon, contraction,
perfect tense, hedge or sentence over 25 words. Keep each docstring within
ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** `saffron/ledger.py` is in `elevate_on`, so `size` blocks at the
`feature` ceiling of 3000 tokens (`saffron/gates/core/size.py:26`). A
prototype of the change, with its witnesses and their docstrings,
formatted with `ruff`, was measured with `size_gate` at `68892367`. It came
to 1139 tokens. The critic's findings for every follow-up, the `withdrawn`
blocker and the three new follow-ups add about 200 more, estimated and not
measured. So the estimate is about 1340 tokens, 45% of the ceiling.

| part | lines | tokens |
|---|---|---|
| `write_findings` and its helpers in `saffron/finish.py` | 85 | 267 |
| the two reads in `saffron/ledger.py` | 28 | 113 |
| criterion 1's witness in `tests/test_finish.py` | 176 | 480 |
| `_stack_finish`'s findings call in `saffron/cli.py` | 10 | 35 |
| criterion 2's witness in `tests/test_cli.py` | 67 | 244 |
