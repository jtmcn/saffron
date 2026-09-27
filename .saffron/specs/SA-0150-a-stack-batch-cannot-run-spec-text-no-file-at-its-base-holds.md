---
id: SA-0150
title: A stack batch cannot run a spec text that no file at its base holds, so a revised or follow-up spec has nowhere to live
type: feature
priority: 1
depends_on: [SA-0182]
touches:
  - saffron/task.py
  - tests/test_task.py
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
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/scheduler.py
  - saffron/intake.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/events.py
  - saffron/projection.py
  - saffron/reconcile.py
  - saffron/record/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - tests/test_batch.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_session.py
  - tests/test_spec_review.py
  - tests/test_consumes.py
  - tests/test_record.py
budget_usd: 22
max_attempts: 3
max_turns: 130
estimated_lines: 500
pending_symbols:
  - saffron/ledger.py::record_spec_text
acceptance:
  - claim: >-
      Given a `task_id` whose task holds a spec text, `run_task` runs the
      latest one in place of the spec it was handed. The `CellSpec` takes
      that text's `spec_sha`, and its body, `touches`, `forbidden`,
      `acceptance`, `risk` and type from the text. Its three ceilings, and
      the `Ceilings` event's values and sources, are `spec_ceilings` of the
      text. PACKAGE, or the push of unpackaged work, gets the text's parsed
      spec. A task whose one text is a follow-up at a path no file at
      `base_sha` holds runs it. So does a revision at the path of an earlier
      text on its task. Given a task that holds none, it runs the spec it was handed, and reads neither the
      policy nor the markers. Given no `task_id`, it never reads a spec
      text.
    witness: tests/test_task.py::test_a_task_with_a_recorded_spec_text_runs_its_latest_text
  - claim: >-
      Before any cell, `run_task` runs gate 0 again on a recorded spec
      text. Its integrity check refuses a text whose SHA-256 is not its
      recorded `spec_sha`. It refuses one `parse_spec` refuses, one whose id
      is not the handed spec's, and one whose `depends_on` list differs
      from the handed spec's. It refuses one whose `budget_usd`,
      `max_attempts` or `max_turns` exceeds the handed spec's, declared or
      defaulted, and passes one equal to it. On a task whose first text is
      a follow-up, it refuses a text whose `touches` is not a subset of that
      first text's. A queued spec's revision may widen `touches`. It
      refuses a revision whose
      path is neither the task's spec file at `base_sha` nor the path of an
      earlier text on its task. The task's spec file is one whose parsed id
      is the task's. It refuses one that `protected_touch_refusal`, the
      criterion path check or `retirement_refusal` refuses, read at the
      pinned `base_sha`. A refusal returns a `Refused` whose reason holds
      the phrase the notes give and no run of two spaces. It prints one
      line, the spec id padded to ten, then ` refused  `, then that reason.
      It calls no cell, and writes no state and no attempt. A base the
      mirror lacks, a base with no `.saffron`, and a base whose policy does
      not load each raise, and no cell is called. The witness drives each
      rule, each of `parse_spec`'s seven refusals, a `depends_on` entry
      added, dropped and reordered, each ceiling over by one step, a
      default ceiling over the handed spec's declared one, a revision at
      another spec's file and at a file only the mirror's `HEAD` holds, and
      a follow-up's revision that adds a `touches` entry.
    witness: tests/test_task.py::test_gate_zero_refuses_a_recorded_spec_text_before_its_cell
---

## Context

Backlog item **b-792ab2**, step 7 of its Done. It cites `DESIGN.md` §4.2
and §4.2.1. ADR 7
(`docs/adr/0007-a-stack-batch-runs-the-spec-dag-and-writes-its-own-follow-ups.md`)
decides that a stack batch runs spec text that is not at `base_sha`. That
text is a spec review's revision or a follow-up spec, and nothing else.
Section 3 of `docs/superpowers/specs/2026-09-23-stack-batch-design.md`
holds each one as a record fact with its text and `spec_sha`, and the cell
runs that text. The finishing layer commits the files. §4.2.1 already
names this exception (`DESIGN.md:386`).

Principle 54 says a control applied at one call site is not applied
(`docs/appendices/N-what-pinning-the-base-and-the-gate-runner-found.md:86-89`).
ADR 7 holds principle 54 only once gate 0 runs again on every revised and
follow-up spec. `parse_spec`'s refusals run again too, not only on files
at `base_sha`. This spec runs each of them in `run_task` but the two open
pull request refusals, which `SA-0162` runs in the batch.

A stack batch runs the queued specs into one pull request stack. Each task
that reaches `READY_FOR_REVIEW` is a **layer**, and the next task is cut
from the last layer, its **predecessor**.

**Step 7 is seven specs, and this is the second.** `SA-0182` holds the text
in the ledger and the record. This spec runs it. `SA-0176` and `SA-0160`
build the spec writer's prompt and session. `SA-0164` runs the revision
rounds, which record a revision with `record_spec_text(origin="revision")`.
`SA-0161` writes follow-up specs, each recorded with `origin="follow_up"`.
`SA-0162` runs the follow-ups as layers. It runs gate 0's open pull
request refusals on each follow-up before its review. It runs the overlap
refusal again on a revised spec of the order. A revised follow-up needs no
second check, because this spec holds its `touches` to a subset of its
first text's. Step 8's `SA-0151` is the finish. It commits the latest text
of each task at its `path`.

**This spec and `SA-0182` were one.** A pricing of the queue on 2026-09-27
put that one at the `feature` ceiling of 3000 changed tokens.
`saffron/ledger.py` is in `elevate_on`, so `size` would block its plan.
This spec forbids `saffron/ledger.py`, so it runs at `standard`.

**What the tree base holds.** This spec's tree base is `SA-0182`'s head.
Every line number below was read at `f492629e`, `SA-0168`'s head, where
`SA-0135`'s `Refused` and `consumes` check and `SA-0168`'s `task_id` are.
No spec between edits `saffron/task.py` or `tests/test_task.py`. This spec
consumes these names.

- From `SA-0182`, the seam its `## Problem` names:
  `ledger.SPEC_TEXT_ORIGINS`, `("revision", "follow_up")`.
  `Ledger.spec_text(task_id) -> sqlite3.Row | None`, the task's row with
  the highest `n`, and `Ledger.spec_texts(task_id) -> list[sqlite3.Row]`,
  every row in rising `n`. Each row's keys are `task_key`, `n`, `origin`,
  `spec_id`, `path`, `text` and `spec_sha`.
  `Ledger.record_spec_text(task_id, *, origin, spec_id, path, text) -> int`
  writes one. All three raise `ValueError` for a task id that names no
  task.
- From `SA-0135`: `Refused` in `saffron/task.py`, a frozen dataclass
  holding only `reason` (`saffron/task.py:250-259`). `run_task` returns
  `CellOutcome | Refused` (`:262-278`). It refuses a spec whose `consumes`
  entry does not resolve at its tree base, after the `CellSpec` is built
  (`:377-392`). It prints `f"{spec.id:<10} refused  {reason}"` first.
- From `SA-0168`: `run_task`'s keyword `task_id` (`:276`), which reaches
  `CellSpec.task_id`. `cli._stack_runner` passes it the candidate's task.
  `cli._batch_runner` and `saffron cell` pass no `task_id`.
- From `SA-0156`: `cli._stack_mint`. A stack batch mints a fresh task
  for each spec every night, with the candidate's `spec_sha`, the file's
  at `base_sha`.

**Where a spec reaches a cell today.** `run_task` takes the parsed spec
and its `spec_sha` (`saffron/task.py:262-264`). It emits the `Ceilings`
event from its `ceilings` argument (`:323-334`). It builds the `CellSpec`
from the spec's fields (`:360-376`). It hands the spec to PACKAGE
(`:403`), or to the push of unpackaged work (`:425`). `cli._batch_runner`
resolves the ceilings with `spec_ceilings` of the candidate's spec
(`saffron/cli.py:503`).

**Gate 0 at the base.** §4.2 refuses a spec that is malformed or whose
`spec_sha` moved (`DESIGN.md:363`). §4.2.1 counts eight refusals
(`DESIGN.md:398`). `build_queue` runs them at scan time
(`saffron/scheduler.py:800`). `saffron cell` runs the two that need no
ledger and no GitHub before its cell. It reads `protected` from
`.saffron/` at `base_sha` and the retirement markers from the mirror at
`base_sha` (`saffron/cli.py:318-351`). `_unmatched_criterion_path` needs
the spec alone (`saffron/scheduler.py:312`), and `_refuse` words its
refusal (`:624`). `protected_touch_refusal` and `retirement_refusal` are
at `:346` and `:418`. Inside the cell, `spec_drift` compares the spec file
at `base_sha` with `CellSpec.spec_sha`, and reports a difference without
refusing (`saffron/cell/session.py:91`).

## Problem

**The cell on the recorded text.** In `saffron/task.py`, add a private
function. It takes the ledger, the task id, the handed spec and the
pinned base. It returns the parsed text and its `spec_sha`, a `Refused`,
or `None` when the task holds no text. It checks in this order. The
integrity check, the text's hash against its row's `spec_sha`.
`parse_spec`, catching `SpecError`. The id, then `depends_on` as a list.
Then each of `budget_usd`, `max_attempts` and `max_turns` against the
handed spec's, refusing only a greater one. Compare every field, declared
or defaulted. Then, when the task's first row is a `follow_up`, the
text's `touches` as a subset of that row's parsed `touches`, read through
`spec_texts`. Then, for a text whose row's origin is `revision`, the
path. It passes when an earlier row on the task has the same path.
Otherwise it passes when `git_mirror.file_at` at the pinned `base_sha`
finds a file there, and that file parses to the task's spec id. A file
that does not parse fails the check. Then `.saffron/` exported at the
pinned `base_sha` into a temporary directory, with `load_policy` of it.
`protected_touch_refusal` of the text's `touches`, the policy's
`protected` and the text's `forbidden` comes next. Then
`_unmatched_criterion_path`, worded as `_refuse` words it. Then
`retirement_refusal` over `git_mirror.retirement_markers` at the pinned
`base_sha`.

Call it first thing in `run_task`, only when `task_id` is set. On a
`Refused`, print the refused line and return it. On a text, rebind `spec`
and `spec_sha` to it, and `ceilings` to `spec_ceilings` of it. Everything
after that reads the rebound names, `SA-0135`'s `consumes` check
included.

The ceiling check keeps a revision inside what the batch reserved for
the queued spec. The batch's budget check reads the file's `budget_usd`
(`saffron/batch.py:229`). It mirrors `SA-0161`'s refusal of a
follow-up whose budget exceeds its origin spec's. A follow-up's handed
spec is its own text, so it passes this check by construction. The
`touches` check holds a follow-up to what the host allowed it. A queued
spec's revision is free to widen `touches`, a common `build` fix.

A task's kind is its first row's origin. A follow-up task stays a
follow-up when a later revision row lands on it. The path check follows
from that: a revised follow-up has no file at `base_sha`, and its
earlier row's path is its own.

The reason for each refusal names the text's `n` and the task. A
`SpecError`'s text can span lines, and the refused line is one line, so
collapse it with `" ".join(str(exc).split())`. Let each read failure
propagate: `GitError` from `file_at`, the export or the markers, and
`PolicyError` from `load_policy`.

`saffron/task.py`'s module docstring names the one refusal `run_task`
makes (`saffron/task.py:16-26`), and `Refused`'s names its one cause
(`:254-255`). Add the recorded text's to each.

**One existing test breaks, and this spec mends it.**
`test_run_task_hands_its_cell_the_task_it_was_given`
(`tests/test_task.py:102-142`) passes `task_id=9` on a ledger that holds
no task. `spec_text` raises `ValueError` for it, by `SA-0182`'s contract.
Keep what the test checks, that `task_id` reaches the `CellSpec`. A
prototype replaced `Ledger.spec_text` with a stand-in that returns
`None`, inside that test only.

## Out of scope

- **The table, the fact and the reads.** They are `SA-0182`'s.
- **Recording a revision, and writing a follow-up.** They are `SA-0164`'s
  and `SA-0161`'s. No code in `saffron/` calls `record_spec_text` until
  `SA-0164`. So it stays a `pending_symbols` entry here too. The `dead`
  gate defers it while this spec is open.
- **The open pull request refusals.** Two of gate 0's refusals need
  GitHub: another task's open pull request on this spec, and a `touches`
  overlap with an open pull request's files. `run_task` holds no slug and
  no `gh`, so neither runs here. `SA-0162` runs both on each follow-up
  before its review. It runs the overlap refusal again on a revised spec
  of the order, with its exemption for the batch's own layers. A revised
  follow-up's `touches` stay a subset of its first text's, which already
  passed.
- **Pinning the text a review approved.** ADR 7 leaves open gate 0's
  "`spec_sha` moved" rule for a revised spec. A revision changes the
  pinned `spec_sha`. The integrity check compares a row with
  itself. It catches a corrupted or hand-edited row. It is not §4.2's
  "`spec_sha` moved" rule, which asks whether the text changed after it
  was approved. Until the ADR answers it, this spec runs the latest text
  with no such check. Within a batch `SA-0164` meets the rule by
  construction, since the cell runs straight after the review that passed
  the latest text. That is reasoned, and no check enforces it. The
  `spec_review` fact records no text `n`, so no fact ties a review to the
  text it read.
- **An attended run's flags.** `saffron cell` passes no `task_id`, so its
  flags still set its ceilings.
- **The refused task's state.** A refusal writes nothing, as `SA-0135`'s
  does. The task keeps the state its review left, `QUEUED` after a
  `run`. The next night's batch mints a fresh task, which holds no text,
  so the refused text never runs again. A follow-up has no file at
  `base_sha`, so its refused text stays in the record alone. `SA-0151`
  skips committing it.
- **The task row's `spec_sha`.** It stays the file's, which `_stack_mint`
  gave it. `CellSpec` carries the text's hash. The chain's re-queue cap
  compares the task row's column, not `CellSpec.spec_sha`, so a revised
  task's cut counts at its file's hash (`saffron/cell/session.py:388-421`).
  `projection` finds a committed spec by that column
  (`saffron/projection.py:132-160`), so it shows the original.
- **The original in the worktree.** The cell's worktree holds the spec
  file at `base_sha`, the original. `spec_drift` compares it with the
  text's `spec_sha`, and prints one preflight line for a revision.
- **A repo gate's view of the text.** A repo gate reads `.saffron/` from
  the `base_sha` export, so it reads the original too. This repo's `dead`
  gate reads `pending_symbols` there, so a name a revision adds goes
  unseen, and a name it drops stays deferred. That is the principle 20
  residual ADR 7 records.
- **A revision does not carry over.** A revision recorded on last night's
  task stays on it. Tonight's fresh task holds no text, so tonight's
  review revises again.
- **A task's kind.** No column stores it. It is the first row's origin,
  and a later revision row does not change it. A revised follow-up has
  no queued file at `base_sha`, so it is still a follow-up. `SA-0151`
  reads the first row to decide whether it adds a new file or rewrites a
  queued one.
- **The refusal count.** The id, `depends_on`, ceiling, `touches` and
  path checks
  are refusals §4.2.1 does not count (`DESIGN.md:398`). `DESIGN.md` is forbidden, so the
  operator files it.

## Notes for the agent

**Every criterion is new code.** No text at the tree base reads a
recorded spec in `run_task`. So each criterion declares a witness and no
mutant, and `witness` reports `skip` for each.

**Every witness fails with the source reverted.** Revert
`saffron/task.py` to the tree base, and `run_task` runs the handed spec.
So each witness fails on an assertion. Import every new name inside a test body.

**Spell the marker apart.** The arrangement writes a retirement marker
naming `SY-1` into the mirror. Written as one literal in
`tests/test_task.py`, it fails
`tests/test_queued_specs.py::test_every_retired_by_marker_names_a_spec`,
since no spec declares `SY-1`. Build it from a name, as
`tests/test_cli.py:489` does.

**Criteria 3 and 4 share one arrangement** in `tests/test_task.py`. Name
its helpers apart from the chain's, such as `_recorded_mirror` and
`_run_recorded`. Each witness opens one ledger in its `tmp_path` and runs
every one of its cases on it, with one repo and one run at `base`. The
mirror is a git repository in `tmp_path` with four commits.

| commit | `.saffron/policy.yaml` | `src/old.py` | `.saffron/specs/` |
|---|---|---|---|
| `bare` | none | `x = 1` | none |
| `base` | `gates: {}`, `protected: [DESIGN.md]` | a `saffron:retired-by SY-1` comment, then `x = 1` | `SY-1-x.md` holding the file text, `SY-5-other.md` holding it with `id: SY-5` |
| `broken` | `gates: [` | `x = 1` | as at `base` |
| `HEAD` | `gates: {}`, `protected: []` | `x = 1` | as at `base`, plus `SY-1-late.md` holding the file text |

The handed spec is the file text below, parsed, with its own hash. It
declares `max_turns` 55 and leaves the other two ceilings at their
defaults, 12.0 and 4. The `ceilings` argument is 12.0, 4 and 60 from
`default`. `repo_id` is 1, and `emit` appends to a list.

```
---
id: SY-1
title: File
type: feature
depends_on: [SY-8, SY-9]
touches: ['src/**']
max_turns: 55
---
file body
```

The revised text `REV` has title `Rev`, type `bug`, the same `depends_on`,
`touches` `['src/**', 'tests/**']`, `forbidden` `['docs/**']`, `risk`
`elevated`, `budget_usd` 9.5, `max_attempts` 4 and `max_turns` 50. Its
`max_attempts` equals the handed spec's default of 4 on purpose. It
declares one criterion, whose claim is `` '`src/a.py` returns 2' `` and
whose witness is `tests/test_a.py::test_two`. Its body is `revised body`.
A backtick cannot start a plain YAML scalar, so quote the claim. Each
task is created on the run at `base`, for `SY-1`, with `spec_sha` `"f" *
64`. Its texts are recorded with origin `revision` at
`.saffron/specs/SY-1-x.md` unless a case says otherwise.

**Criterion 3's witness** replaces `task_module.run_one_cell`,
`package_phase.package` and `package_phase.push_unpackaged_work` with
recorders. The cell returns the state the case sets.

- It records `older`, which is `REV` with `budget_usd` 5.0 and `touches`
  `['src/**']`, then `REV`, on a task, and runs
  it with the cell returning `READY_FOR_REVIEW`. It does the same on a
  fresh task with `EXHAUSTED`. Each `CellSpec` carries `REV`'s hash, its
  parsed body, `touches`, `forbidden` and `acceptance`, `elevated`, `bug`,
  9.5, 4 and 50. The one `Ceilings` event carries 9.5, 4 and 50, and
  `spec` as each of its three sources. PACKAGE then the push each got
  `parse_spec(REV)`.
- It runs a task holding `REV` alone, origin `follow_up`, at
  `.saffron/specs/SY-1-g.md`. It runs a task holding `REV` as
  `follow_up`, then `REV` as `revision`, both at
  `.saffron/specs/SY-1-f.md`. Neither path is at `base`. It clears the
  cell's list before each, and each list is then exactly one `CellSpec`
  with `REV`'s hash.
- After those tasks, on the same ledger, it runs a task with no text on
  a mirror path that does not exist, at `"a" * 40`. The `CellSpec` body
  is `file body\n`.
- It replaces `Ledger.spec_text` with a call that fails the test, and runs
  with no `task_id`. The `CellSpec` carries the file's hash.

These fail it, each measured:

- the caller's ceilings kept, which gives 12.0, 4 and 60
- the caller's ceilings copied with `dataclasses.replace` and the text's
  values, which keeps the sources `default`
- a ceiling equal to the handed spec's refused, which refuses `REV`
- the file's `spec_sha` kept
- the first text in place of the latest, which gives 5.0
- PACKAGE handed the file's spec, or the push handed it
- the `touches` check applied to a queued spec's revision too, which
  refuses `REV` after `older`
- the path check run on a follow-up too, which refuses the `SY-1-g.md`
  task
- no earlier-row rule, which refuses the revised follow-up
- the policy exported for every `task_id`, which raises on the missing
  mirror
- a spec text read with no `task_id`

**Criterion 4's witness** replaces `task_module.run_one_cell` with a call
that fails the test. For each case it creates a task, records the text,
and runs it at `base`. It asserts a `Refused` whose reason holds the
phrase and no run of two spaces. The `yaml` case's error carries runs of
spaces after its line breaks, so it drives the collapse. Standard output
is exactly one line, `SY-1`, six spaces, `refused`, two spaces and the
reason. The task is still `QUEUED` and holds
no attempt.

| case | text | phrase |
|---|---|---|
| tampered | `REV`, then its own row's `spec_sha` set to `"0" * 64` in SQL | `does not hash to its spec_sha` |
| no frontmatter | `revised body\n` | `does not parse` |
| yaml | frontmatter `: [` | `does not parse` |
| list | frontmatter `- a` | `does not parse` |
| reserved | `REV` with `body: x` | `does not parse` |
| invalid | `REV` with `type: nope` | `does not parse` |
| both | `REV` with a `## Acceptance criteria` checklist appended | `does not parse` |
| mutant | `REV` with a mutant on `src/a.py` whose find is `return 2`, and the body `it does return 2` | `does not parse` |
| id | `REV` with `id: SY-2` | `declares SY-2` |
| added | `depends_on: [SY-8, SY-9, SY-7]` | `depends_on` |
| dropped | `depends_on: [SY-8]` | `depends_on` |
| reordered | `depends_on: [SY-9, SY-8]` | `depends_on` |
| budget | `budget_usd: 12.5` | `budget_usd` |
| attempts | `max_attempts: 5` | `max_attempts` |
| turns | `max_turns: 56` | `max_turns` |
| undeclared | `REV` with its `max_turns` line removed, so 60 by default | `max_turns` |
| other spec | `REV` at `.saffron/specs/SY-5-other.md` | `not the task's spec file` |
| late | `REV` at `.saffron/specs/SY-1-late.md` | `not the task's spec file` |
| widened | `REV` as `follow_up`, then `REV` plus `touches` `lib/**` as `revision`, both at `.saffron/specs/SY-1-w.md` | `widens` |
| protected | `touches` plus `DESIGN.md` | `protected` |
| criterion | the claim naming `` `lib/a.py` `` | `lib/a.py` |
| marker | `touches` of `src/a.py` and `tests/**` | `src/old.py` |
| consumes | `consumes: [src/missing.py]` | `src/missing.py` |

Last, it makes one more task holding `REV` as `follow_up`, then as
`revision`, both at `.saffron/specs/SY-1-z.md`. So the path check passes
it without a read. It runs that task at three more bases. `"b" * 40`
raises `GitError`, `bare` raises `GitError`, and `broken` raises
`PolicyError`. The cell is never called. A valid `REV` reaches the
export, so it also shows a ceiling equal to the handed spec's passes.

These fail it, each measured unless marked:

- no integrity check
- only `budget_usd` compared, which runs the `attempts` and `turns` cases
- only the ceilings the text declares compared, which runs `undeclared`
- no path check, which runs `other spec`
- a path checked by existence alone, which runs `other spec`
- the path read at the mirror's `HEAD`, which runs `late`
- no `touches` check, or one against the latest row, which runs
  `widened`
- the latest row counted as its own earlier row, which runs both path
  cases
- no earlier-row rule, which refuses the last task where it raises
- a ceiling equal to the handed spec's refused, which returns a
  `Refused` where the export raises
- line breaks replaced but spaces kept, which leaves runs of spaces in the
  `yaml` reason
- a `DisclosedMutantError` run on the spec it carries
- no id check
- `depends_on` compared as sets, or by its first entry
- the policy read at the mirror's `HEAD`, or the markers read there
- no criterion path check
- no refused line printed, or one printed by the helper and again by
  `run_task`, unmeasured
- a refusal that ends the task `SPEC_WITHHELD`
- a parse failure raised in place of a `Refused`
- the parse error's raw text, which prints the YAML error over five lines
- a `PolicyError` or a `GitError` from the export read as no protected
  paths, as `cli._protected_paths_at` reads it
- the text rebound after `SA-0135`'s `consumes` check, unmeasured

**How the lists were measured.** A prototype ran on 2026-09-27 at
`f492629e`, over `SA-0182`'s prototype, ported from this spec's of
2026-09-24. Both witnesses passed, and the whole suite and `ty` stayed
green once the `task_id=9` test and the marker were mended. Each wrong
version above was applied as a text edit, with no bytecode cache, and
each failed its own witness. The `consumes` case and the text rebound
after the `consumes` check were measured this time. With `saffron/task.py`
reverted to `SA-0182`'s head, both witnesses failed, and neither failed
collection.

**What the witnesses leave undriven.**

- A text whose `parse_spec` refusal comes from `SA-0136`'s malformed
  `consumes` shapes. `parse_spec` raises `SpecError` for each, which the
  same catch takes.

**`ty` reads the tests.** `ty` checks `tests/` as well. Build `Refused`
with its keyword, since it is `kw_only`.

**Measure with no bytecode cache.** Two text edits of equal length in one
second leave a stale `.pyc`. The second edit then runs as the first. Set
`PYTHONDONTWRITEBYTECODE=1` when you try a wrong build.

**The `prose` gate** counts every new comment and docstring. Write none
with an em dash, a semicolon, a contraction, the perfect tense or a
sentence over 25 words. Keep each docstring within ten lines.

**Commit as each witness passes**, before the full suite runs.

**Size.** Neither file this spec touches is in `elevate_on`, so `size` is
advisory at the `feature` ceiling of 3000 changed tokens
(`saffron/gates/core/size.py:26`). The prototype, formatted with
`ruff format`, measured 1426 changed tokens with `size_gate`'s own count:
437 in `task.py` and 989 in `tests/test_task.py`. Sibling cells landed at
1.4 times their authors' estimates, so about 1996 tokens, 67% of the
ceiling. The plan's `estimated_lines` counts lines, and the checkpoint
prices each line at 4 tokens (`saffron/gates/core/size.py:39`). So plan
this at about 500 changed lines, not at a token count.
