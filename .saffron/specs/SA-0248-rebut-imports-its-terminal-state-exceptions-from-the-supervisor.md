---
id: SA-0248
title: REBUT imports its terminal-state exceptions from the supervisor that drives it, and two witnesses find the rebuttal by counting turns
type: refactor
priority: 3
depends_on: [SA-0244, SA-0237]
estimated_lines: 194
estimate_measured: true
touches:
  - saffron/cell/worktree.py
  - saffron/cell/session.py
  - saffron/phases/rebut.py
  - tests/test_rebut.py
  - tests/test_session.py
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
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/view/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/proxy.py
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/package.py
  - saffron/task.py
  - saffron/intake.py
  - saffron/ledger.py
  - tests/test_worktree.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 46
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      `CriticPatchRejected`, `CriticPatchEmpty` and
      `CriticPatchUnrepresentable` are defined in `saffron/cell/worktree.py`
      and in no other module. Every `from ... import` of one, in `saffron/`
      and in `tests/`, names `saffron.cell.worktree`. `session.py` imports
      all three and `rebut.py` imports its two at module scope, and no module
      in `saffron/` imports one inside a function. No module reaches one as
      an attribute of a module other than `worktree`. The names bound in
      `session` and in `rebut` are `worktree`'s own classes.
      `CriticPatchEmpty` still subclasses `CriticPatchRejected`, and both
      `reason` methods return the text they return today. The witness parses
      every Python file under `saffron/` and `tests/`. Today all three are
      defined in `session.py`, and `rebut.py` imports two of them from it
      inside `run_rebut`.
    witness: tests/test_rebut.py::test_the_critic_patch_exceptions_are_imported_from_worktree_alone
    wrong_versions:
      - "`session.py` keeps its own copies of the three classes beside the ones `worktree.py` now defines."
      - "`rebut.py` keeps a function-local import, now from `saffron.cell.worktree`."
      - "`tests/test_rebut.py` still imports `CriticPatchEmpty` from `saffron.cell.session`, which resolves because `session` binds the name."
      - "A test raises `session.CriticPatchUnrepresentable`, reaching the class through the supervisor's namespace."
      - "The moved `reason` drops its em-dash separator to satisfy `prose`, so the reason text changes."
      - "`CriticPatchEmpty` is moved as a subclass of `RuntimeError` rather than of `CriticPatchRejected`."
      - "The three classes move to a new module under `saffron/cell/` rather than to `worktree.py`."
  - claim: >-
      REBUT's critic cell is still rebuilt from the post-rebuttal patch. The
      witness's `export_patch` stub now tells the pre- from the post-rebuttal
      diff through one helper in `tests/test_session.py`. The helper answers
      whether a turn whose prompt begins with `REBUT_PROMPT`'s text before
      `{blockers}` has run, and reads no count of turns. The witness asserts
      the helper is false for nine turns with no rebuttal prompt, and true
      for a rebuttal prompt alone. It asserts that this test and
      `test_the_verdict_prompt_carries_the_diff_the_lenses_were_shown` each
      call the helper on their cell, and that neither reads the length of a
      `turns` list. Today both stubs answer from `len(cell.turns) > 5`.
    witness: tests/test_session.py::test_rebut_verdicts_read_a_tree_rebuilt_from_the_post_rebuttal_patch
    preserves: true
    wrong_versions:
      - The helper returns `len(cell.turns) > 5`, today's threshold.
      - The helper returns `len(cell.turns) > 8`, one past the turn the critic cell is built at.
      - The helper always returns false.
      - The helper always returns true.
      - The helper reads only the last turn's prompt, so the extraction turn after the rebuttal hides it.
      - "The verdict-prompt test's stub keeps `len(cell.turns) > 5` and never calls the helper."
      - "The verdict-prompt test's stub calls the helper and also keeps `len(cell.turns) > 5`."
      - "This test's own stub keeps a turn count."
  - claim: >-
      The verdict prompt still carries the reviewed diff and the
      post-rebuttal diff under their own headings, with its stub's boundary
      read through the same helper.
    witness: tests/test_session.py::test_the_verdict_prompt_carries_the_diff_the_lenses_were_shown
    preserves: true
    wrong_versions:
      - The helper returns `len(cell.turns) > 8`.
      - The helper always returns false.
      - The helper always returns true.
      - The helper reads only the last turn's prompt.
  - claim: >-
      A post-rebuttal patch that will not apply still ends REBUT
      `EXHAUSTED`, with a reason saying it did not apply.
    witness: tests/test_rebut.py::test_a_post_rebuttal_patch_that_will_not_apply_ends_exhausted
    preserves: true
    wrong_versions:
      - "`run_rebut`'s `except CriticPatchRejected` clause is dropped with the local import, so the exception escapes."
  - claim: >-
      A post-rebuttal patch with no change still ends REBUT `EXHAUSTED`, and
      its reason does not say it did not apply.
    witness: tests/test_rebut.py::test_a_post_rebuttal_patch_with_no_change_ends_exhausted_and_says_so
    preserves: true
    wrong_versions:
      - "`CriticPatchEmpty` is moved without its own `reason`, so it inherits the one that says the patch did not apply."
  - claim: >-
      A post-rebuttal binary change still ends REBUT `GATE_ERROR`.
    witness: tests/test_rebut.py::test_a_post_rebuttal_binary_change_ends_gate_error
    preserves: true
    wrong_versions:
      - "`CriticPatchUnrepresentable` is moved as a subclass of `CriticPatchRejected`, so `run_rebut`'s first clause catches it as `EXHAUSTED`."
  - claim: >-
      A patch that does not apply in the Gate-only cell still ends the task
      `EXHAUSTED` before any lens runs.
    witness: tests/test_session.py::test_a_patch_that_does_not_apply_to_its_base_never_reaches_review
    preserves: true
    wrong_versions:
      - "The Gate-only cell's `except CriticPatchRejected` clause is dropped, so the exception escapes `_drive_cell`."
  - claim: >-
      Commits that net to no change still end the task `EXHAUSTED` with a
      reason that says so.
    witness: tests/test_session.py::test_commits_that_net_to_no_change_end_exhausted_with_a_reason_that_says_so
    preserves: true
    wrong_versions:
      - "`_apply_and_commit_patch` raises `CriticPatchRejected` where it raised `CriticPatchEmpty`."
  - claim: >-
      A binary change the export cannot carry still ends the task
      `GATE_ERROR` at the Gate-only cell.
    witness: tests/test_session.py::test_a_binary_change_the_export_cannot_carry_ends_in_gate_error
    preserves: true
    wrong_versions:
      - "`CriticPatchUnrepresentable` is moved as a subclass of `CriticPatchRejected`, so the Gate-only cell's first clause catches it as `EXHAUSTED`."
---

## Context

Backlog items **149** and **148**, under `DESIGN.md` §5.5 and §5.6. Both
tidy the boundary between REBUT, the supervisor that drives it, and the
tests that drive both. Every line below was read at `958db033`.

**Three exceptions live in the supervisor.**
`saffron/cell/session.py:1221-1247` defines `CriticPatchRejected`, its
subclass `CriticPatchEmpty`, and `CriticPatchUnrepresentable`. The patch
apply raises `CriticPatchEmpty` (`saffron/cell/session.py:1274`),
`CriticPatchUnrepresentable` (`:1300`) and `CriticPatchRejected` (`:1302`,
`:1316`). The supervisor catches `CriticPatchRejected` and
`CriticPatchUnrepresentable` at the Gate-only cell
(`saffron/cell/session.py:2756`, `:2767`). It catches them again at the
critic cell (`saffron/cell/session.py:2884`, `:2891`).

**REBUT reaches into the supervisor for them.**
`saffron/phases/rebut.py:729` imports `CriticPatchRejected` and
`CriticPatchUnrepresentable` from `saffron.cell.session` inside the function.
Its comment says a module-scope import would cycle
(`saffron/phases/rebut.py:726-728`). The supervisor imports `rebut` at module
scope (`saffron/cell/session.py:46`). REBUT turns `CriticPatchRejected` into
`EXHAUSTED` and `CriticPatchUnrepresentable` into `GATE_ERROR`
(`saffron/phases/rebut.py:731-745`).

**The worktree module sits below both.** It imports only `runtime` and
`Mutant` from Saffron (`saffron/cell/worktree.py:17-18`). Neither of those
imports the supervisor or a phase. It already owns `DIFF_FLAGS`
(`saffron/cell/worktree.py:134`). That tuple's missing `--binary` is why
`CriticPatchUnrepresentable` exists (`saffron/cell/session.py:1241-1243`).
Phases already import from it at module scope
(`saffron/phases/implement.py:20`, `saffron/phases/package.py:26`).

**The tests import them from the supervisor too.** `tests/test_rebut.py`
imports one each from `saffron.cell.session`, inside the test
(`tests/test_rebut.py:379`, `:391`, `:405`). No other file under `saffron/`
or `tests/` names any of the three.

**Two stubs find the rebuttal by counting turns.** Two tests in
`tests/test_session.py` replace `worktree.export_patch` with a stub. It
returns the post-rebuttal diff once `len(cell.turns) > 5`
(`tests/test_session.py:7200`, `:7370`). Their comments say eight turns
precede REBUT's critic cell (`tests/test_session.py:7198-7199`,
`:7368-7369`). `_through_rebut` scripts six turns before REBUT's own
(`tests/test_session.py:3935-3949`). The fake turn records each prompt in
`cell.turns` (`tests/test_session.py:1401`). `_rebut_turn_options` already
finds REBUT's turns by prompt, through `REBUT_PROMPT`'s text before
`{blockers}` (`tests/test_session.py:3952-3962`). The count is right today.
A turn added to IMPLEMENT or REVIEW moves it in both stubs at once, and
nothing links them.

## Problem

1. Move the three classes into `saffron/cell/worktree.py`, with their bases
   and `reason` methods unchanged. Delete them from `session.py`.
2. `session.py` imports all three from `saffron.cell.worktree` at module
   scope. Its raise and `except` sites keep their bare names.
3. `rebut.py` imports `CriticPatchRejected` and
   `CriticPatchUnrepresentable` from `saffron.cell.worktree` at module scope.
   Delete the function-local import and its three-line comment.
4. `tests/test_rebut.py`'s three imports name `saffron.cell.worktree`, and
   each stays inside its test. At module scope, a name the change adds makes
   the `revert` gate's re-run fail to collect criterion 1's witness.
5. Add one helper to `tests/test_session.py` that answers whether REBUT's
   rebuttal turn has run, from the prompts in `cell.turns`. Both stubs call
   it in place of their count. Rewrite their turn-count comments.
   `_rebut_turn_options` can share its prompt test.
6. Add the criterion 1 witness to `tests/test_rebut.py`. Add criterion 2's
   assertions to that existing test's body.

No re-export is left behind. `session.py` binds the names because it raises
and catches them, not for any importer.

## Out of scope

- The critic cell's `except` sites at `saffron/cell/session.py:2884` and
  `:2891`. No test drives them alone. Criterion 1 holds the name each one
  resolves to: `session` binds only `worktree`'s classes and defines none.
- Every other function-local import in `session.py`. Each one names a
  module or a name other than these classes.

## Notes for the agent

**This is a refactor.** Behaviour is unchanged, so criteria 2 to 9 are
`preserves`. Criterion 1's witness is new and fails at base. Its subject
is where the classes are defined, and that code does not exist at base. So
it declares no mutant, and `witness` reports `skip` for it. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**The criterion 1 witness.** Walk every `*.py` under `saffron/` and `tests/`
with `ast`, from the repo root found through `Path(__file__)`. Check each
`ClassDef`, `ImportFrom` and `Attribute` naming one of the three. A module
scope import is one in the module's top-level body. Then check the bound
names by identity, `issubclass`, and each `reason` against today's exact
string. Import `session`, `worktree` and the classes inside the test, never
at module scope. The `revert` gate's re-run then fails the test rather than
failing to collect it.

**Criterion 2 adds no new test.** The `revert` gate re-runs every test the
diff adds with its source files reverted. It blocks one that passes
(`saffron/gates/core/revert.py:130`). A test of a helper in
`tests/test_session.py` passes there, because no source file moves it. So
the helper's assertions go in the body of
`test_rebut_verdicts_read_a_tree_rebuilt_from_the_post_rebuttal_patch`,
before it drives the task. Build each fake cell as a `SimpleNamespace` with
`turns`. Parse each stub test's source from `inspect.getsource` with `ast`,
and read its calls rather than its text. The assertion names the text it
looks for, so a plain substring check finds it in the test's own source. Keep
the second stub's container check as it is.

**Rewrite the moved docstrings in house style.** The `prose` gate files
each failure under its file (`.saffron/gates/prose.py:616-617`). So a docstring moved into
`worktree.py` with an em-dash or semicolon is a new failure there. Rewrite
each one in house style, each sentence still true. The gate reads comments
and docstrings, not string literals (`.saffron/gates/prose.py:324-326`). So
leave `reason`'s f-string byte for byte, em-dash included, as criterion 1
requires. The two stub comments you rewrite are prose too.

**Measured on a prototype.** A prototype at `958db033` passed all nine
witnesses. Criterion 1's witness failed with the three source files
reverted. Each of the 25 wrong versions above, applied as an edit, failed
its own criterion's witness. Its diff measured 774 changed tokens.
