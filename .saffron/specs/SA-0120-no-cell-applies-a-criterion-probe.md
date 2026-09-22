---
id: SA-0120
title: A criterion probe is named and recorded, and no cell applies it or runs its criterion's witness over it
type: feature
priority: 1
depends_on: [SA-0119]
touches:
  - saffron/cell/session.py
  - saffron/phases/review.py
  - tests/test_session.py
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
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/probe.py
  - saffron/intake.py
  - saffron/ledger.py
  - saffron/task.py
  - saffron/batch.py
  - saffron/cli.py
  - saffron/events.py
  - saffron/report/**
  - saffron/repos/**
  - saffron/agents/**
  - saffron/phases/rebut.py
  - saffron/phases/implement.py
  - saffron/phases/package.py
  - saffron/cell/worktree.py
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - tests/fixtures/**
  - tests/test_worktree.py
  - tests/test_witness_gate.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_events.py
  - tests/test_corpus.py
budget_usd: 24
max_attempts: 3
max_turns: 130
risk: elevated
acceptance:
  - claim: >-
      A criterion probe whose criterion's witness stays green under it is
      filed as a `blocker` from the `adequacy` lens. The finding carries the
      edit as its probe, with `probe_verdict` `survived`, at the line where
      the edit's `find` begins in the file at head. It is anchored against
      the diff the lenses judged, as every lens finding is. The witness
      drives two survivors. The one that anchors routes the task to REBUT
      and is the one blocker in `rebuttal.json`. The one that does not
      anchor is recorded in `findings.json` and routes nothing. For each, the
      host ran that criterion's own witness node id alone, and each entry in
      `criterion-probes.json` records `survived`.
    witness: tests/test_session.py::test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker
  - claim: >-
      A criterion probe its criterion's witness kills records `killed` and
      files nothing. One under which the `tests` gate answers `error` records
      `error` with `witness_gate`'s summary and files nothing. The edit after it
      is still applied and its witness still run, and the task ends
      `READY_FOR_REVIEW`. The witness drives three edits in that order:
      killed, `error`, killed.
    witness: tests/test_session.py::test_a_killed_or_errored_criterion_probe_files_nothing_and_stops_nothing
  - claim: >-
      Five entries nothing could answer each record `unproven` and file
      nothing. They are an entry whose session named no edit, an edit on a
      declared test path, an edit on a path outside the tree, an edit the
      mutator refuses to apply, and an edit whose criterion's witness is not
      in the set the `tests` gate collected. The mutator is entered for the
      refused edit alone, and its reason is recorded word for word. No
      witness runs, and the task ends `READY_FOR_REVIEW`.
    witness: tests/test_session.py::test_a_criterion_probe_nothing_could_answer_is_unproven_and_files_nothing
  - claim: >-
      `criterion-probes.json` still pairs each criterion's witness and claim
      with the edit its own session named and that session's reason, in the
      spec's own order. A spec that declares no criterion still writes no
      such record.
    witness: tests/test_session.py::test_the_record_pairs_each_claim_with_the_edit_its_own_session_named
    preserves: true
  - claim: >-
      An adequacy finding whose vacuity probe survives is still promoted to a
      blocker and rebutted, beside a correctness blocker.
    witness: tests/test_session.py::test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker
    preserves: true
---

## Context

Backlog item **b-2750d5** is
`docs/backlog/b-2750d5-no-cell-mutates-the-line-that-satisfies-each-criterion.md`,
tier 1. This spec is the child half `SA-0113` named under its "Out of scope"
("Applying the edit, and the verdict"). `SA-0113` merged in #403.

Every sentence below about current code was read at `c9c3c369` on
2026-09-21. `SA-0119` lands first and moves line numbers in
`saffron/cell/session.py` and `tests/test_session.py`. Find each cited name
by its name at the base you are cut from.

**The edits are named and recorded, and nothing applies them.**
`review.run_criterion_probes` (`saffron/phases/review.py:405`) buys one
fresh session per acceptance entry. It returns one entry per criterion, in
the spec's order, holding `witness`, `claim`, `edit`, `reason`, `cost_usd`
and `error` (`saffron/phases/review.py:440-449`). `edit` is a `Mutant`'s
`model_dump()` or `None`. It is called inside the critic cell
(`saffron/cell/session.py:2341`). The list is written to
`criterion-probes.json` at `saffron/cell/session.py:2398-2400`, and nothing
reads an edit back.

**A gate that applies one edit and runs one witness already exists.**
`witness_gate` (`saffron/gates/core/witness.py:96`) takes criteria, a
`mutate` context manager and a `run_tests` callable. It keeps the criteria
whose `mutant` is set. For each it checks the witness against `collected`
before touching the tree (`:147`), applies the mutant through `mutate`, and
calls `run_tests([criterion.witness])`. A reason the mutator yields is
appended to `unproven` (`:165`). A `tests` gate `error` returns `error`
(`:228`), `fail` counts as the witness dying (`:240`), and `pass` is a
survivor (`:244`). With nothing trustworthy it returns `skip` (`:293-297`).
So its status over one criterion is the outcome: `pass` killed, `fail`
survived, `error` error, `skip` unproven.

**The adequacy probe path is the precedent for running model-authored edits
host-side.** `_probe_adequacy` (`saffron/cell/session.py:1255`) runs after
REVIEW's critic cell is torn down (`:2373`). It enters a Gate-only cell
through `critic_cell`, with `network=None` and the repo's `thread_env` alone
(`:1361-1380`). The entry sits on an `ExitStack`. So a cell that never comes
up is recorded rather than raised. It runs the `tests` gate through
`runner.run_gate(..., executor=runner.CellExecutor(container))`
(`:1351-1358`), and applies edits through `worktree.source_mutated`
(`:1396`). A raise from an apply or undo stops every later probe
(`:1400-1419`). A surviving probe promotes its finding in place through
`review.apply_probe_verdict` (`saffron/phases/review.py:516`). REBUT then
reads it through `review.anchored_blockers` (`saffron/cell/session.py:2438`).

**A blocker reaches a verdict only under a lens `LENSES` names.** REBUT
asks one verdict session per lens in `review.LENSES` that filed a blocker
(`saffron/phases/rebut.py:554-557`). A blocker under any other lens name
gets no verdict session. Then `rebut_state` (`saffron/phases/rebut.py:308`)
finds nothing confirmed. The task's line then reads "every blocker withdrawn
by its own lens" (`saffron/phases/rebut.py:349`). So a survivor is
filed under `adequacy`, whose remit is whether the tests notice the code
being wrong (`DESIGN.md` §5.5). `rebut._blocker_line`
(`saffron/phases/rebut.py:126-138`) already shows the implementer a
survived probe's edit. `rebut.py` and the ontology need no change.

**The collected set is already in hand.** The Gate-only cell's comparison
the lenses were shown, `gate_comparison`, is in scope at the call site
(`saffron/cell/session.py:2229`, `:2287`). Its `run.results` carry the
`tests` gate's result over the same rebuilt tree, with `collected`.

## Problem

Nothing puts a criterion's witness under the edit a fresh session named
against its claim. So the witness hole item b-2750d5 found in five pull
requests still ships, and the spec loop's Spec seat still probes by hand.

Apply each recorded edit in a Gate-only cell, run that criterion's witness
over it through `witness_gate`, and file a survivor as a blocker for REBUT.

1. **Where it runs.** A new Gate-only cell entry after `_probe_adequacy`'s,
   in the same `else:` branch, before `criterion-probes.json` is written.
   Enter it the way `_probe_adequacy` does: `critic_cell` with
   `network=None`, `env=dict(policy.thread_env)`, the patch the lenses
   judged, the same `created` and `note`, on an `ExitStack`. Never inside
   the critic cell, which runs no model-authored code (`SA-0087`). Enter no
   cell when no entry is left to apply.
2. **Which entries are applied.** Pair each entry with its criterion from
   `spec.acceptance` by position, strictly. These are recorded `unproven`
   and never applied.
   - An entry with no edit.
   - An edit the one test-path rule refuses. That is the function `SA-0119`
     adds to `saffron/probe.py` (its Problem step 1), which answers why a
     probe on a file is refused. `SA-0119`'s criteria drive its refusals
     through `check_probe` and the host loop, not by the function's name. So
     read `saffron/probe.py` at your base and call the one function that
     answers all three refusals. It refuses a path outside the tree, an empty `test_paths`, and
     a declared test path. An edit to the witness's own test would survive
     by construction, so refusing it is the point.
   - Every remaining edit in a repo whose head declares no `tests` gate.
   - Every remaining edit, where the cell cannot be entered.
3. **How each is asked.** Call `witness_gate` once per edit. Hand it one
   criterion, the entry's own with the edit as its `mutant`
   (`criterion.model_copy(update={"mutant": edit})`). Give it the
   `collected` of the `tests` result in `gate_comparison.run.results`, or
   `None` when there is none. `run_tests` is the `tests` gate in the cell,
   built as `_probe_adequacy` builds it. `mutate` is
   `worktree.source_mutated` on that container. One call per edit, never one
   over every criterion, because an inner `error` ends a `witness_gate` call
   and would discard the verdicts beside it.
4. **What is recorded.** On each entry, in place, an outcome and a summary.
   The outcome is one of `killed`, `survived`, `unproven` and `error`, read
   from the returned status as the Context says. The summary is
   `witness_gate`'s summary, or the host's own reason where no call was
   made. The record keeps every field `SA-0113` gave it.
5. **What is filed.** A survivor alone. Build one `Finding` for it. Its
   lens is `adequacy` and its severity `blocker`. Its file is the edit's,
   and its line is where `find` begins in that file at head. Read it with
   `worktree.read_at_head` in the Gate-only cell. Its `probe` is the edit,
   and its `probe_verdict` is `survived`. Its claim
   names the criterion's witness, quotes its claim, and says that only that
   witness ran under the edit. REBUT renders every surviving probe as "the
   tests stayed green" (`saffron/phases/rebut.py:133-136`), which reads as
   the whole suite. Pass it through
   `findings.anchor` against the reviewed diff, with `read_head` reading
   the Gate-only cell, while that cell is up. Append it to the `adequacy`
   `LensReview`'s findings. That list is what `findings.json`,
   `ledger.record_findings` and `review.review_state` read after it.
6. **When a raise stops the rest.** A `CellRuntimeError` out of the
   mutator's entry or exit leaves the tree unknown. `witness_gate` reports
   it as `error`, the same status a `tests` gate `error` gets
   (`saffron/gates/core/witness.py:183-206` against `:228-239`). So wrap
   `mutate` in the host's own context manager that notes a raise. Tell the
   two apart by that note, never by parsing the summary. After a noted
   raise, apply no later edit in that cell. Record each later edit
   `unproven`, saying an earlier edit left the tree unknown. A
   `CellRuntimeError` out of `run_tests`, which `witness_gate` also reports
   as `error`, means the cell died. Stop the same way, as `_probe_adequacy`
   stops on one (`saffron/cell/session.py:1400-1417`). A `tests` gate that
   answered `error` under an edit stops nothing, since the mutator's exit
   restored the file.

## Out of scope

- How edits are authored. `review.run_criterion_probes`, its prompts and its
  sessions keep `SA-0113`'s behaviour. No cap on sessions.
- `saffron/gates/**`. `witness_gate` is reused unchanged. Its declared-mutant
  role in GATE is untouched.
- `saffron/probe.py`. `SA-0119` owns the test-path rule, and this spec calls
  it.
- A REVIEW line counting the outcomes. The record carries them, and the
  `review_state` line already counts the blockers.
- The glossary and the design record. `CONTEXT.md`'s *Criterion probe*
  entry and `DESIGN.md` §5.4.1 both say "No gate applies one yet (backlog
  item b-2750d5)". That stays true, because the host applies one and no gate
  does. Both files are `protected`, and this spec edits neither.
- `SA-0118`'s files, `saffron/cell/worktree.py` and `tests/test_worktree.py`.
  Both are in `forbidden`.

## Notes for the agent

**This change is new code, so no criterion declares a mutant** (§5.4.1).
The `witness` gate will report `skip` for this spec. Nothing at base
determines the spelling of the new function, its outcome field or its reason
text. Criteria 4 and 5 are `preserves` and name tests that pass at base.

**Name the wrong implementation each witness must kill.** Each of these
failed its witness on a prototype of this change.

- Criterion 1: filing the survivor under a lens name `LENSES` does not
  hold, filing it as a `concern`, and setting `anchored` without calling
  `anchor`. Running the whole suite rather than the one witness fails its
  subset assertion. So record each `subset` the probe cell's `run_gate`
  was handed, and assert one list per edit holding that criterion's own
  witness.
- Criterion 2: stopping after an `error`, and recording `error` as
  `unproven`.
- Criterion 3: handing `witness_gate` `collected=None`, and a host-side
  glob check that lets a path outside the tree reach the mutator.

**The witnesses.** Put all three in `tests/test_session.py`, beside the
criterion-probe witnesses `SA-0113` added. Drive each through `_drive` with
`_PROBE_POLICY` and `gates=("tests",)`. Script turns with `_probe_turns` and
`_probe_answer`. Build the criteria inside each test body. Give each its own
witness id, so a subset names which criterion ran.

- Stub `saffron.gates.runner.run_gate` for `saffron-gate-` containers alone,
  as `_stub_probe_gates` does, and record the subset. That helper records
  none, so write a sibling or extend it without changing what its callers
  see.
- Stub `saffron.cell.worktree.source_mutated` to append to `cell.mutated`
  and yield `None`, or a reason for the file it refuses.
- Criterion 1 anchors one edit on `_ANCHORING_DIFF`'s one line in
  `src/x.py`. Its other edit sits on a line `read_at_head` returns for
  another file, with no token the diff changed. Put that edit's `find` on a
  line other than 1 of that file, and assert each finding's `line`. A
  hard-coded line then fails. `_rebuttable` stubs `read_at_head` for every
  path, so override it after calling that helper. Make the override return
  `None` for any `saffron-critic-` container. The critic cell is torn down
  by then, so a read aimed at it must fail the witness.
  Script REBUT as `test_a_concern_whose_probe_survives_is_rebutted_as_a_blocker`
  does, with `rebut_commits=0` and `_CLAIMED_FIX`. The task then stops at
  `REBUTTING` with `rebuttal.json` written.
- Criterion 3 scripts the collected set through `_stub_the_runtime`'s
  `gate_cell_suite`. Pass that alone. On the prototype, adding `suites=` as
  well ended the task `GATE_ERROR` before REVIEW. Use `spec/t.py` for the
  test path and `../outside.py` for the escape. Neither needs a
  `run_gate` answer, so an empty answer list fails loudly if one is asked.
- Run no baseline suite in the probe cell. The collected set comes from
  `gate_comparison`, and each witness scripts one answer per witness run.

**Each witness must fail with your source reverted.** All three did on the
prototype: criterion 1 ended `READY_FOR_REVIEW`, and criteria 2 and 3 found
no outcome on the entries. Import any name this change adds inside the test
body. A module-scope import of a new name turns `revert`'s reverted run into
a collection error, which it reads as `skip`.

**Each witness is a plain `def`, never parametrised.** `criteria` matches a
bare node id by exact string.

**The existing drives stay as they are.** `_drive`'s default policy is
`gates: {}` with no test paths. So the `SA-0113` witnesses that name an edit
record it `unproven` and enter no cell. The ten `acceptance=` drives take
`_drive`'s fallback turn, which names no edit. Every `_probe_adequacy`
witness declares no criterion. On the prototype, `tests/test_session.py`,
`tests/test_review.py` and `tests/test_probe_check.py` all stayed green.

**Where the code lives.** The cell, the loop and the call site go in
`saffron/cell/session.py`, beside `_probe_adequacy`. Pure pieces go in
`saffron/phases/review.py`, as `SA-0109` split them: the status-to-outcome
reading and building the survivor's `Finding`. `review.py` cannot import
`session.py` (`saffron/cell/session.py:48` imports `review`).

**Every record field needs a reader.** The `dead` gate reports a function no
production caller reaches. Call every new function from the call site.

**`size` blocks at 600 changed lines here.** `saffron/cell/**` is in
`.saffron/policy.yaml`'s `elevate_on`, so this diff auto-elevates. A
prototype of this change measured 351 changed lines. That was 143 in
`saffron/cell/session.py`, 31 in `saffron/phases/review.py` and 177 in
`tests/test_session.py`, with terse comments. Keep each comment to one or
two lines and each docstring under ten. Share one stub helper across the
three witnesses.

**What is left unwitnessed.** Four `unproven` paths follow
`_probe_adequacy`'s precedent and no criterion drives them. They are a repo
with no `tests` gate, an empty `test_paths`, a cell that never comes up, and
a raise that stops later edits. `SA-0119`'s own witness drives the empty
`test_paths` refusal. Write the code for each. A test you add for one is
judged by `revert` like any declared witness.

**Rename no existing test.** `census` reads a rename as a removal.

Commit after each coherent step. Uncommitted work dies with the cell.
