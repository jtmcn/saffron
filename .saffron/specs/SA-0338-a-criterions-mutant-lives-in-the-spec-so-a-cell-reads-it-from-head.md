---
id: SA-0338
title: A criterion's mutant lives in the spec, so a cell reads it from HEAD
type: feature
priority: 1
estimated_lines: 300
estimate_measured: true
touches:
  - saffron/mutants.py
  - saffron/intake.py
  - saffron/repos/mirror.py
  - saffron/task.py
  - saffron/cell/session.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/scheduler.py
  - saffron/follow_up.py
  - saffron/agents/prompts/spec-writer.md
  - docs/agents/issue-tracker.md
  - docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py
  - tests/test_mutants.py
  - tests/test_mirror.py
  - tests/test_intake.py
  - tests/test_task.py
  - tests/test_session.py
  - tests/test_ledger.py
  - tests/test_ledger_fold_task.py
  - tests/test_cli.py
  - tests/test_worktree.py
  - tests/test_scheduler.py
  - tests/test_follow_up.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/backlog/**
  - docs/appendices/**
  - docs/adr/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  # A git ref, never a file. Forbidden so the criteria may name it.
  - refs/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/agents/*.py
  - saffron/phases/**
  - saffron/cell/worktree.py
  - saffron/regate.py
  - saffron/commit_review.py
budget_usd: 62
max_attempts: 3
max_turns: 300
acceptance:
  - claim: >-
      `ensure_mirror` on an existing mirror fetches `refs/saffron/mutants`
      from the checkout in a second fetch. It takes the ref when the
      checkout gains it and follows a move to an unrelated commit. It drops
      the ref once the checkout deletes it. A checkout without the ref
      fetches cleanly. A record ref the checkout holds at another commit
      keeps the mirror's own commit throughout.
    witness: tests/test_mirror.py::test_a_mirror_fetch_takes_the_mutants_ref_and_still_spares_the_records_refs
    wrong_versions:
      - The mutants refspec joins the existing fetch beside `^refs/saffron/*`, so the exclusion drops it.
      - The second fetch names `refs/saffron/mutants` exactly, so a checkout without the ref fails the fetch.
      - The second fetch has no `--prune`, so a ref the checkout deleted stays in the mirror.
      - The refspec has no leading `+`, so a move to an unrelated commit is rejected.
      - The second fetch takes `refs/saffron/*`, so the checkout's record ref overwrites the mirror's.
  - claim: >-
      `saffron.mutants.ref_commit` names the commit `refs/saffron/mutants`
      points at in a mirror, and `None` where the ref is absent.
      `read_mutants` reads `<spec id>.yaml` at the commit it is given, never
      the ref's head, and parses it with `parse_mutants`. It returns each
      witness's `Mutant`, `replace` defaulted to the empty string. It
      returns no mutants for a `None` commit, for a tree with no such file,
      and for an empty mapping. `parse_mutants` over the same text returns
      the same dict.
    witness: tests/test_mutants.py::test_mutants_are_read_from_the_ref_by_spec_id_and_witness
    wrong_versions:
      - "`read_mutants` reads the file at the ref's head and ignores the commit it is given."
      - The file is looked up under another name, such as `<spec id>.yml`.
      - A tree with no file for the spec raises in place of returning no mutants.
      - "`ref_commit` returns a revision that names the commit's tree, not the commit."
  - claim: >-
      `attach_mutants` returns a copy of the spec in which each criterion
      carries the mutant its own witness names in the file. The file's
      entry order does not decide the match. A criterion with no entry
      carries `None`. The criteria keep their order, and the spec it was
      handed keeps no mutant.
    witness: tests/test_mutants.py::test_each_criterion_takes_its_own_witnesses_mutant_from_the_ref
    wrong_versions:
      - Entries are matched to criteria by their position in the file.
      - The handed spec's own criteria are given the mutants in place.
  - claim: >-
      A mutants file that cannot apply to its spec raises a `SpecError`
      subclass that names the file or the witness. `parse_mutants` raises
      for six shapes. They are a YAML error, a top-level value that is not
      a mapping, an entry that is not a mapping, an entry with no `file`,
      an entry with an empty `find`, and an entry with a key `Mutant` does
      not declare. `attach_mutants` raises for three more. They
      are a witness no criterion declares, a witness two criteria declare,
      and a criterion that declares `subject:` and gets no mutant. A mutant
      whose `find` the spec's body, a claim or a wrong version spells out
      raises `DisclosedMutantError` carrying the spec.
    witness: tests/test_mutants.py::test_a_mutants_file_that_cannot_apply_to_its_spec_is_refused
    wrong_versions:
      - An entry naming a witness no criterion declares is skipped.
      - A witness two criteria declare gives its mutant to both.
      - A criterion declaring `subject:` with no mutant is accepted.
      - The disclosure check stays in `parse_spec` alone, so a mutant from the ref that the body spells out passes.
      - A top-level list reads as no mutants.
      - A YAML error escapes as the YAML library's own exception.
      - An entry is read key by key, so a key `Mutant` does not declare is ignored.
      - Only some validation errors are wrapped, so a malformed entry escapes as pydantic's own error.
  - claim: >-
      `discover_specs` refuses a spec any of whose criteria declares
      `mutant:` inline. The refusal is a `DiscoveryFailure` carrying the
      parsed spec, and its reason names the witness. Called with
      `retired=True`, it parses that spec with its inline mutant intact.
      `refuse_inline_mutants` raises `InlineMutantError`, a `SpecError`
      carrying the spec. A criterion that declares `subject:` and no inline
      mutant now parses.
    witness: tests/test_intake.py::test_a_queued_spec_declaring_an_inline_mutant_is_refused_and_a_retired_one_parses
    wrong_versions:
      - The refusal lives in `parse_spec`, so a `done/` scan loses the spec.
      - The check reads the first criterion alone, so a mutant on the second passes.
      - The failure carries no spec, so its id is lost to the retired credit.
      - "`retired=True` is ignored."
      - A `subject:` still needs an inline mutant at parse.
  - claim: >-
      `run_task` hands its cell a `CellSpec` whose criteria carry the
      mutants `<spec id>.yaml` holds, and whose `mutants_commit` names the
      commit they were read at. A call with no `task_id` reads at the ref's
      head. A task it is given reads at the commit that task's row
      records, so a later move of the ref leaves it alone. A given task
      whose row records none runs with no mutants. A mirror with no ref
      runs with no mutants and `None`.
    witness: tests/test_task.py::test_run_task_hands_its_cell_the_mutants_the_ref_holds_at_the_tasks_commit
    wrong_versions:
      - A given task reads the ref's head, not the commit its row records.
      - The mutants are read and never put on the spec the `CellSpec` is built from.
      - "`mutants_commit` is never set on the `CellSpec`."
      - A given task whose row records no commit falls back to the ref's head.
  - claim: >-
      `run_task` returns `Refused` before any cell starts, and prints its
      one refused line, in five cases. They are a handed spec that declares
      `mutant:` inline, a task's recorded spec text that declares one, a
      `<spec id>.yaml` that is not valid YAML, and a mutant on the ref whose
      `find` the spec's body spells out. The fifth is a given task whose
      recorded commit the mirror does not hold, which never raises
      `GitError`. The reason names the witness, the file, the disclosure or
      the commit.
    witness: tests/test_task.py::test_run_task_refuses_an_inline_mutant_or_an_unreadable_mutants_file_before_its_cell
    wrong_versions:
      - The inline check runs before the recorded text replaces the handed spec, so an inline mutant in a recorded text reaches its cell.
      - The inline check runs in `discover_specs` alone, so a handed spec reaches its cell.
      - A `MutantsError` is left to raise out of `run_task`.
      - Only `MutantsError` and `InlineMutantError` are caught, so a disclosed mutant from the ref raises.
      - The refusal prints nothing.
      - The recorded commit is read without checking the mirror holds it, so `GitError` escapes `run_task`.
  - claim: >-
      `create_task` takes a keyword `mutants_commit` and writes it into the
      `task_created` fact, `None` included, and into a `tasks` column of
      that name. `task_mutants_commit` reads the column back. A fold
      rebuilds the column from the fact. A fact written without the key
      folds to `None`, and a ledger built before the column gains it on open.
    witness: tests/test_ledger.py::test_a_tasks_mutants_commit_is_a_task_created_fact_the_fold_keeps
    wrong_versions:
      - The fold subscripts the payload, so a fact written without the key raises.
      - The fact carries the key and the fold never writes the column.
      - The column joins the schema alone, so an existing ledger never gains it.
      - The key is written only when a commit is given.
  - claim: >-
      A cell that mints its own task passes `CellSpec.mutants_commit` to
      `create_task`. Its `task_created` fact and its row carry the commit,
      and `None` where the `CellSpec` carries none.
    witness: tests/test_session.py::test_a_cell_that_mints_its_task_records_the_mutants_commit_it_was_handed
    wrong_versions:
      - "`_drive_cell` never passes the commit, so every fact carries `None`."
  - claim: >-
      `_stack_mint` records the mirror's `refs/saffron/mutants` commit on
      each task it mints, read at that mint. A mirror with no such ref
      records `None`.
    witness: tests/test_cli.py::test_the_stack_mint_records_the_mutants_refs_commit_and_null_without_one
    wrong_versions:
      - The adapter reads the ref once when it is built, so a later move is missed.
      - The mint passes no commit.
  - claim: >-
      A follow-up candidate any of whose criteria declares `mutant:` inline
      is refused by `follow_up._validate`, whatever edit it names, and its
      reason names the witness. A candidate with no inline mutant passes
      it. The spec-writer prompt tells the writer to declare no mutant in
      the spec.
    witness: tests/test_follow_up.py::test_a_follow_up_declaring_any_mutant_inline_is_refused
    wrong_versions:
      - Only a mutant naming a probe the group's findings wrote is refused, as at base.
      - The check reads the first criterion alone, so a mutant on the second passes.
      - The prompt keeps saying only that new code declares no mutant.
---

## Context

Backlog item **80**, part 1 of 2. It cites `DESIGN.md` §5.4.1, which the
operator amended by hand at this spec's base. Its paragraph "A mutant lives
on `refs/saffron/mutants`, never in the spec" says what this spec makes true.
The mirror takes the ref in a second fetch of its own, and `run_task` reads
each criterion's mutant. Three older sentences there now put the mutant on
the ref, supplied by the spec's author. `SA-0339` depends on this spec and
adds `saffron mutant`, the command that writes the ref. Every line number
below was read at `20adc839`.

**A cell reads its mutant from `HEAD`.** A criterion declares its mutant
inline (`saffron/intake.py:138`). A batch runs committed specs, and the cell
checks out `base_sha`. So `git show HEAD:<spec>` reads the mutant whatever the
prompt withholds. Item 80's Record holds the measurement.

**What already holds.** The seed fetch names `+refs/heads/*` and takes no
tags (`saffron/cell/worktree.py:74-75`, `SA-0237`). A ref outside the
branches never reaches a cell. `SA-0237`'s cell-marked test proves it for a
hand-made `refs/saffron/mutants` (`tests/test_worktree.py`).

**The mirror.** `ensure_mirror` clones a new mirror with `--mirror`, which
takes every ref (`saffron/repos/mirror.py:86-90`). On an existing mirror it
fetches `+refs/*:refs/*` with `^refs/saffron/*`
(`saffron/repos/mirror.py:75-81`, `SA-0278`). Its
`origin` is the checkout it was given, not GitHub. So today a ref the
checkout gains after the clone never reaches the mirror.

**Measured in scratch mirrors, with git 2.54.0 on the host and git 2.47.3
in `saffron/cell-base:python`.** Both gave the same answers. The negative
refspec wins over a positive one in the same fetch, exact or glob. That
fetch exits 0, and the ref does not arrive. A second fetch naming the ref
exactly exits 128 with "couldn't find remote ref" when the checkout lacks
it. A second fetch of `+refs/saffron/mutants*:refs/saffron/mutants*` with
`--prune` takes the ref and exits 0 without one. It deletes the mirror's
copy once the checkout does. Without the `+`, a move to an unrelated commit
is rejected as non-fast-forward and the fetch exits 1. In both, that glob
pruned only names that start `refs/saffron/mutants`. A
`refs/saffron/tasks/*` ref and a `refs/saffron/values/*` ref stayed.

**Every reader of a criterion's mutant reads the parsed spec.** They are
`witness_gate` (`saffron/gates/core/witness.py:146`), `run_witness`
(`saffron/gates/runner.py:234`), `revert_gate`
(`saffron/gates/core/revert.py:187-200`), `source_mutated`
(`saffron/cell/worktree.py:660`) and the probe at
`saffron/cell/session.py:2062`. `follow_up._validate` reads a follow-up
candidate's, and refuses only a mutant naming a probe the group's own
findings wrote (`saffron/follow_up.py:216-227`). An inline mutant naming any
other edit passes, so that follow-up is minted and then refused at
`run_task` on every run. The spec-writer prompt says only that new code
declares no mutant (`saffron/agents/prompts/spec-writer.md:4-5`). `saffron/gates/baseline.py:28-32` reads a
`survived-mutant` code, never a mutant. So filling `Criterion.mutant` from the ref before the `CellSpec` is
built changes none of them.

**Where a task's spec arrives.** `saffron cell` and `saffron batch` both
call `run_task` (`saffron/task.py:726`). Given a `task_id`, it first
replaces the handed spec with the task's recorded text (`:756-763`). It
builds the `CellSpec` at `:828-846`. `CellSpec.acceptance` reaches every
gate (`saffron/cell/session.py:366`). A task is minted in one of two
places. `_drive_cell` calls `create_task` when `CellSpec.task_id` is `None`
(`saffron/cell/session.py:2254-2270`). `_stack_mint` mints a stack batch's
task before its cell (`saffron/cli.py:1449-1473`).

**Where `spec_sha` is recorded.** `create_task` writes it into the
`task_created` fact's payload (`saffron/ledger.py:1494`, `:1531-1544`). The
fold inserts it into `tasks.spec_sha` (`:817-833`). A column an existing
ledger lacks is added by the guarded `ALTER TABLE` loop (`:427-438`).

**Intake today.** `parse_spec` refuses a disclosed mutant inline at
`saffron/intake.py:366-414`. `DisclosedMutantError` carries the spec (`:60`).
`discover_specs` turns it into a `DiscoveryFailure` with `spec` set
(`:499-502`). `_retired_ids` credits a `done/` spec refused that way
(`saffron/scheduler.py:650-658`). A criterion's `subject` without an inline
mutant is refused at parse (`saffron/intake.py:172-185`).

## Problem

Move a criterion's mutant onto `refs/saffron/mutants`, read it on the host,
and refuse it inline in a queued spec.

**The file format.** The ref's tree holds one `<spec id>.yaml` per spec.
The file is a mapping from a criterion's witness to that witness's mutant,
with `Mutant`'s own keys: `file`, `find` and an optional `replace`. Keyed by
witness, not by position. A criterion carries no other id, and the gates
already name a criterion by its witness. A spec edit that reorders or adds
criteria then leaves each mutant on its own witness. A renamed witness
leaves a stale key, which is refused loudly rather than misapplied.

**A new module, `saffron/mutants.py`.** `SA-0339` extends it with the
writer. It holds:

- `MUTANTS_REF`, the string `refs/saffron/mutants`.
- `MutantsError`, a `SpecError` subclass.
- `ref_commit(mirror)`, the commit the ref names, or `None` where it is
  absent. Run `git rev-parse --verify --quiet` on the ref and read a nonzero
  exit as absent.
- `parse_mutants(text, where)`, a dict from witness to `Mutant`. `where`
  names the file in each error. Validate each entry with
  `Mutant.model_validate`, and wrap every YAML and validation error in
  `MutantsError`. `SA-0339` parses its `--from` file with this function, so
  the writer and the reader share one parser.
- `read_mutants(mirror, commit, spec_id)`. Read `<spec_id>.yaml` at
  `commit` with `file_at` (`saffron/repos/mirror.py:254`) and hand the text
  to `parse_mutants`. Return no mutants for a `None` commit or a missing
  file.
- `attach_mutants(spec, found)`, a copy of the spec with each criterion's
  mutant set from `found`. It raises `MutantsError` for the three shapes
  criterion 4 names, then runs the disclosure check on the copy.

**Intake.** Move the disclosure block at `saffron/intake.py:366-414` into a
public `refuse_disclosed_mutants(spec)`, reading `spec.body`. `parse_spec`
calls it as it does today, so a `done/` spec is refused the same way. Add
`InlineMutantError`, shaped like `DisclosedMutantError`, and
`refuse_inline_mutants(spec)`. Give `discover_specs` a keyword `retired`,
default `False`. Unless it is set, run `refuse_inline_mutants` after
`load_spec` and record the error as a `DiscoveryFailure` with `spec` set.
Narrow `_subject_needs_a_mutant_and_a_canonical_path` to the canonical-path
rule, since the mutant arrives after parse. Update the docstrings of
`Criterion.mutant` and `DiscoveryFailure.spec` to match.

**`run_task`.** After the recorded-text rebind and before the `CellSpec`,
pick the commit. A given `task_id` takes `ledger.task_mutants_commit`. A
call with no `task_id` takes `ref_commit(base.mirror)`. A commit the mirror
does not hold, as after a re-clone, refuses the task and names the commit.
Check it with `has_commit` (`saffron/repos/mirror.py:285`) before any read,
since `file_at` raises `GitError` for it. Then run
`refuse_inline_mutants`, `read_mutants` and `attach_mutants`. On a
`SpecError`, print the refused line and return `Refused`, as the recorded
text refusals do (`saffron/task.py:758-760`). Collapse the reason onto one
line. Build the `CellSpec` from the attached spec, and give it a field
`mutants_commit: str | None = None`. PACKAGE then reads the same spec.

**The record.** Give `create_task` a keyword `mutants_commit`, default
`None`, written into the `task_created` payload beside `spec_sha`. Add a
nullable `mutants_commit` column to `tasks`, to the guarded `ALTER TABLE`
loop and to the fold's insert. Read the payload with `.get`. Add
`task_mutants_commit(task_id)`, shaped like `task_policy_sha`
(`saffron/ledger.py:1669`). `_drive_cell` passes `spec.mutants_commit`.
`_stack_mint` passes `mutants.ref_commit(pinned.mirror)`, read inside the
minting closure.

**Follow-ups.** In `follow_up._validate`, refuse a candidate any of whose
criteria declares a mutant inline, and name the witness in the reason. This
replaces the probe comparison at `saffron/follow_up.py:216-227`, which the
new rule covers. Change `saffron/agents/prompts/spec-writer.md:4-5` to tell
the writer to declare no mutant in the spec. Keep that prompt free of any
`saffron/` or `docs/` path, and of the ref's name, since `test_cores_spec_writer_prompts_fill_every_slot_and_name_no_repo_tool`
(`tests/test_spec_review.py`) refuses one.

**The mirror.** After the existing fetch in `ensure_mirror`, add a second
`fetch --prune origin` of `+refs/saffron/mutants*:refs/saffron/mutants*`.
Say in a one-line comment why it is a second fetch and why it is a glob.

**Done-only readers.** `_retired_ids` and the backtest script read `done/`
alone. Pass `retired=True` in both
(`saffron/scheduler.py:650`,
`docs/evidence/scripts/2026-09-14-spec-reviewer-backtest.py:124`). For
`_retired_ids` this changes no outcome, since a refusal carrying its spec
is already credited there. It keeps that function's comment at
`saffron/scheduler.py:652-654` true.

**Update what the change makes false or breaks:**

- `test_a_subject_needs_a_mutant_and_a_canonical_path`
  (`tests/test_intake.py:676`) asserts a bare `subject` is refused at parse
  (`:697-709`). Keep the name. Assert instead that it parses with its
  subject, and keep the canonical-path cases.
- `_TASKS_COLUMN_READERS` (`tests/test_ledger.py:1048`) needs
  `"mutants_commit": "saffron/ledger.py::Ledger.task_mutants_commit"`.
- `_drive_every_kind` (`tests/test_ledger_fold_task.py:164`) mints its task
  with every `create_task` field set, and the test asserts no folded column
  is `None` (`:231-236`). Pass `mutants_commit` there too.
- `tests/test_scheduler.py` promotes retired specs to the top level and scans
  them as queued. A retired spec declaring a mutant inline is now refused
  there. Measured on the prototype, 41 of the smoke test's measured specs
  turn into such refusals. Re-pin both lists of
  `test_saffron_queue_smoke_reproduces_this_repos_measured_queue` to what
  the scan prints at your head. Leave its docstring and `measured` set
  alone.
- `test_no_real_spec_is_refused_on_its_own_acceptance_criteria`
  (`tests/test_scheduler.py:4738`) names ten `.claude/` refusals. `SA-0282`
  now refuses earlier for its inline mutant, so drop it from that list.
  Assert the inline refusals are exactly the promoted specs that declare a
  mutant, `SA-0063` aside, and that they number more than 30. Measured, they
  number 64. Leave them out of its final `depends_on` check.
- `tests/test_follow_up.py` hands four accepted candidates an inline
  mutant, at `:437`, `:488`, `:845` and `:983`. Drop the mutant from each,
  so each is still accepted. Case 9 at `:457-461` is still refused, and its
  reason still holds the word `mutant`. A draft refused for an inline mutant
  is pooled like any other `_validate` reason, with no resend.
- Pass `retired=True` to `discover_specs` in `_origin_file_text`
  (`saffron/follow_up.py:120`), which needs only the parse. A deferred finish
  across this change can hold an origin layer that declares a mutant inline.
- Pass `retired=True` in
  `test_no_real_spec_names_a_criterion_path_its_touches_do_not_cover`
  (`tests/test_scheduler.py:4257`), so its scan still reads every spec.
- `spec_drift`'s docstring (`saffron/cell/session.py:146-150`) says the
  worktree copy defeats the withholding of `mutant`. Say instead that this
  was item 80's measurement, and a queued spec now carries no mutant.
- `docs/agents/issue-tracker.md:57-73` shows `mutant:` inside `acceptance:`.
  Drop `mutant` from the criterion's fields and from the example. Add a
  short paragraph and a second YAML example. They say the mutant lives on
  `refs/saffron/mutants` in `<spec id>.yaml`, keyed by witness. They say an
  inline `mutant:` in a queued spec is refused.
  `docs/agents/issue-tracker.md:126-129` says the cell can read the spec
  file for its mutant. Say instead that the mutant moved to
  a ref the cell never fetches.

**A cell-marked test, beside `SA-0237`'s in `tests/test_worktree.py`.**
Name it
`test_a_cell_seeded_from_a_mirror_that_fetched_the_mutants_ref_holds_no_mutant`.
Build the mirror with `ensure_mirror` from a checkout with no ref. Then point
the checkout's `refs/saffron/mutants` at a commit holding `SY-1.yaml`, and
call `ensure_mirror` again. Assert `ref_commit` and `read_mutants` read the
mutant from the mirror. Seed a real cell from that mirror with
`prepare_worktree`, as `_drive_cell` does, on `image.BASE_TAG`. Assert the
cell's refs are its branch alone. Assert `git cat-file -e` fails in the cell
for the blob, the tree and the commit. Import `saffron.mutants` inside the
test body.

## Out of scope

- **`saffron mutant`.** `SA-0339` writes and pushes the ref. Tests here
  create it with plain git.
- **`saffron regate`, `saffron adopt`, `saffron package` and `saffron review`.**
  Each reads a spec file or a recorded text on its own. `regate` loads one
  at `saffron/regate.py:91`, and `ready_task` at `saffron/task.py:1298`.
  `commit_review` loads one at `saffron/commit_review.py:138`. After this
  spec none of them sees a ref mutant. A backlog item for that is filed
  with this spec.
- **A requeued task whose pinned file does not parse.** A task given to
  `run_task` reads at the commit its row recorded. If `<spec id>.yaml`
  there raises `MutantsError`, a requeued task outside a stack is refused
  at every run, and fixing the ref never reaches it. That is the price of
  a record that says what ran. A stack task re-mints at `_stack_mint`
  (`saffron/cli.py:1449`) and picks up the fix. Retiring or re-queueing the
  spec as a new task clears it.
- **`saffron/record/migrate.py`.** It writes `task_created` from a stored
  row and carries no `mutants_commit` (`saffron/record/migrate.py:428-440`).
  A migrated task folds to `None`. Every task that predates this spec had
  no ref to record.
- **Edits under `.claude/`.** `SA-0279` refuses them in `touches`. Each
  lands in the cell PR's review commit, by hand. None can land in the spec
  PR, since `discover_specs` takes no `retired` keyword until this cell
  lands.
  - `.claude/skills/run-saffron-spec-loop/driver.py:1871`. `_known_specs`
    reads `done/` with `discover_specs`, and needs `retired=True`.
    Without it, `driver.py check` and `history` drop every done spec that
    declares a mutant inline, the worst-case rows of the ceilings line
    among them.
  - `.claude/skills/run-saffron-spec-loop/driver.py:2251-2256`.
    `_subject_concerns` reads inline mutants, so it never fires on a
    queued spec after this. It reads the ref instead.
  - `.claude/agents/spec-reviewer.md:42` and `:64-65`. They describe a
    criterion declaring a mutant in the spec.
  - `.claude/skills/run-saffron-spec-loop/SKILL.md:84`. It describes the
    subject concern.
- **`DESIGN.md` §5.4.1.** Amended by hand at this spec's base.
- **A spec in `done/`.** It keeps its inline mutants as history and is
  never run. No migration.

## Notes for the agent

**Witness and mutant.** Every criterion pins code this spec adds, or a
rewrite whose spelling is yours. So each declares a witness and no mutant,
and `witness` reports `skip`. This spec also cannot carry a mutant inline
once its own change lands.

**At the tree base each witness fails.** `saffron.mutants` does not exist.
The mirror's existing fetch never takes the ref. `create_task` takes no
`mutants_commit`, `CellSpec` has no such field, and `discover_specs` takes
no `retired`. Import every name this spec adds inside the test body, never
at module scope, so `revert` reads a real failure and not a collection
error.

**Criterion 1** extends `tests/test_mirror.py`'s `origin` fixture. Isolate
git config as `test_a_mirror_fetch_neither_prunes_nor_overwrites_the_records_refs`
does (`tests/test_mirror.py:76`). Build each mutants commit with
`hash-object`, `mktree` and `commit-tree`, with no parent. So the second
commit is unrelated to the first, and only a forced update moves the
mirror's copy. Call `ensure_mirror` once after the clone with no ref, which
kills the exact-name version. Hold a `refs/saffron/tasks/<key>` ref in the
mirror and the same name at another commit in the checkout.

**Criterion 2** builds a bare mirror. Before any ref exists, assert
`ref_commit` is `None` and `read_mutants` at a `None` commit returns `{}`. Write one commit holding `SA-1.yaml`
with two entries, one without `replace`, and `SA-2.yaml` holding `{}`. Then
move the ref to a commit holding a different `SA-1.yaml` and a decoy
`SA-1.yml`. Read at both commits. Compare whole dicts of `Mutant` with `==`.

**Criterion 3** writes the file's entries in the reverse of the criteria's
order, and gives the third criterion no entry. Assert the handed spec's
criteria all still carry `None`.

**Criterion 4** drives each of the nine shapes in one test. Assert
`isinstance(exc, SpecError)` for the six parse failures. Drive the
disclosure through the body, a sibling's claim and a wrong version.

**Criterion 5** writes two files into `tmp_path`. One declares its mutant on
its second criterion. The other declares `subject:` and no mutant.

**Criteria 6 and 7** use `_recorded_ledger` (`tests/test_task.py:1032`).
Its mirror is a real repository, so point `refs/saffron/mutants` there with
`commit-tree` and `update-ref`. Stub `run_one_cell` to record each
`CellSpec`, and stub `push_unpackaged_work` with `_push`
(`tests/test_task.py:123`). For the given-task cases, mint the row with `create_task(..., mutants_commit=)`
before moving the ref. Use `_rev_text` for the handed spec. Its default
passes gate 0, and `mutant_find=` adds an inline mutant (`:914-962`). Pick a
`find` the text does not otherwise spell. For criterion 7's recorded-text
case, hand a clean spec and record the inline text on the task. Otherwise
the handed spec alone refuses it, and the first wrong version passes. For
the disclosed case, give the ref's entry a `find` of `revised body`, which
`_rev_text`'s default body spells. For the missing commit, mint a row with
`mutants_commit="f" * 40` and assert the reason holds its first twelve
characters.

**Criterion 8** follows
`test_an_engine_commit_is_a_fact_the_fold_keeps` (`tests/test_ledger.py:1008`).
Rebuild one task's facts with `mutants_commit` removed from the payload
before folding it. For the old ledger, strip the column from `SCHEMA` and
assert the stripped text no longer names it.

**Criterion 9** follows
`test_the_task_created_fact_carries_the_cells_declared_tier_and_null_where_none`
(`tests/test_session.py:4334`), with `_spec(mutants_commit=...)`.

**Criterion 10** follows
`test_the_stack_mint_records_the_declared_tier_and_null_where_none`
(`tests/test_cli.py:9599`), over a real bare mirror. Mint once with no ref,
then once after each of two moves.

**Criterion 11** calls `follow_up._validate` directly, with a
`FollowUpGroup` holding no findings. Build one candidate with
`_candidate(..., mutant=...)`, which puts the mutant on the first criterion,
and one with `_spec_text` that puts it on the second. Read the prompt with
its whitespace collapsed, since a sentence can wrap.

**The cell-marked test is the operator's to run.** `pyproject.toml`'s
`addopts` deselects `-m cell`, so no gate in the cell runs it, and no
criterion names it. The operator runs `uv run pytest -m cell` with that
test's name on the cell's head before the pull request merges.

**A mirror path that does not exist.** Many `run_task` and `_stack_mint`
tests pass a mirror path that is no repository. `ref_commit` reads any
nonzero exit as no ref, so they run unchanged. Say so in a `ponytail:`
comment beside it.

**`saffron/cell/session.py` and `saffron/ledger.py` match `elevate_on`,** so
this task runs `elevated` and `size` blocks.

**The `prose` gate** counts every new comment and docstring, and the new
lines in `docs/agents/issue-tracker.md`. Write none with an em dash, a
semicolon, a contraction, the perfect tense or a sentence over 25 words.
Keep each docstring within ten lines.

**Size.** A prototype at `8c024ec6` measured 989 changed tokens with
`size_gate`'s counter outside the test paths, about 247 lines. It held every
source edit above, the tracker and prompt edits, the eleven witnesses, the
test edits and the cell-marked test. Every wrong version above failed its
witness there. The cell-marked test passed against apple/container with
`saffron/cell-base:python`. A margin of about 50 lines for docstrings makes
`estimated_lines` 300. The `feature` ceiling is 3000 tokens.
