---
id: SA-0398
title: "`_stub_the_runtime` stubs `dirty_paths` but leaves its new sibling `spec_ids` to fall through a catch-all, which only one test's assertion happens to keep honest"
type: bug
priority: 3
estimated_lines: 23
estimate_measured: true
touches:
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
  - docs/**
  - saffron/**
  - tests/test_constant_mutants.py
  - tests/test_integrity.py
  - tests/test_mirror.py
  - tests/test_package.py
  - tests/test_probe_check.py
  - tests/test_review.py
  - tests/test_suite.py
  - tests/test_worktree.py
budget_usd: 10
max_attempts: 2
max_turns: 40
acceptance:
  - claim: >-
      `_stub_the_runtime` (tests/test_session.py:1180) stubs
      `saffron.cell.worktree.dirty_paths` to an empty-list lambda right
      beside its other worktree stubs (tests/test_session.py:1379), but
      stubs no such thing for the sibling `saffron.cell.worktree.spec_ids`
      that `GateSuite._run` also reads off every `Tree` it is handed
      (saffron/gates/suite.py). Left unstubbed, a call to `spec_ids` falls
      through to the fixture's own catch-all `saffron.cell.runtime.exec_`
      double (tests/test_session.py:1281), which logs the real `git grep`
      argv into `cell.execs` and returns it empty. Add
      `monkeypatch.setattr("saffron.cell.worktree.spec_ids", lambda
      container: [])` immediately after the `dirty_paths` line, the same
      shape as its sibling. The witness drives one ordinary two-turn cell
      through `_stub_the_runtime` and `_drive`, reaching
      `READY_FOR_REVIEW`, where `GateSuite.baseline` and `GateSuite.against`
      both read `tree.spec_ids()` on the implementer cell
      (`saffron-cell-SY-1`). It asserts that no entry in `cell.execs` is the
      id-listing `git grep` argv, which only holds once the stub is in
      place.
    witness: tests/test_session.py::test_the_generic_stub_answers_spec_ids_without_a_real_grep_call
    wrong_versions:
      - No stub added for `spec_ids`, so the fixture's catch-all still issues the real `git grep` argv on the implementer cell and the new test's assertion finds it in `cell.execs`.
      - A stub added under the wrong dotted path, such as `saffron.gates.suite.Tree.spec_ids` — the typing-only `Protocol` (saffron/gates/suite.py:59) that `CellTree` (saffron/gates/suite.py:77) satisfies structurally but does not inherit from — so `CellTree.spec_ids` is untouched, `worktree.spec_ids` itself still runs, and the real argv still appears in `cell.execs`.
      - A stub that returns `None` rather than `[]`, which `frozenset(tree.spec_ids())` in `GateSuite._run` then raises on, turning the drive's own `READY_FOR_REVIEW` assertion into an error instead of a pass.
  - claim: >-
      `test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
      (tests/test_session.py:11543) is the one test that asserts the exact,
      ordered list of commands the gate-only cell ran
      (tests/test_session.py:11581-11584), and that list already names
      `_SPEC_IDS` (tests/test_session.py:10327-10344) — the real `git grep`
      argv `spec_ids` issues, captured only because this fixture's
      `spec_ids` call was falling through to the real `exec_` double. Once
      `_stub_the_runtime` stubs `spec_ids` generically to `[]`, this one
      test must restore the real function right after calling
      `_stub_the_runtime`, with
      `monkeypatch.setattr("saffron.cell.worktree.spec_ids", _real_spec_ids)`,
      a module-level alias imported from `saffron.cell.worktree` before any
      test runs. Leave the test's own assertion
      (tests/test_session.py:11581-11584) untouched; restoring the real
      function is what keeps it true. The witness is that same test,
      unmodified in its assertions, checked both before and after this
      spec's own fix, since the claim is that the fixture change does not
      break it.
    witness: tests/test_session.py::test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs
    preserves: true
    wrong_versions:
      - The restoring `monkeypatch.setattr` line left out, so the gate cell's own `spec_ids` call answers `[]` straight from the generic stub, and the recorded command list is one entry short of `_SPEC_IDS`.
      - The restoring line pointed at a lambda that returns a hand-built tuple equal to `_SPEC_IDS` rather than at the real `spec_ids` function, which passes this one test today but stops tracking the production command the moment `spec_ids`'s own argv changes.
      - The restoring line applied to `dirty_paths` again instead of `spec_ids`, leaving `spec_ids` still answering the generic stub and `_SPEC_IDS` still missing from the list.
---

## Context

`b-249808` is the backlog record behind `SA-0393`, named too in `SA-0393`'s
own notes and in the comment above `_SPEC_IDS`
(tests/test_session.py:10327-10328). `SA-0393` gave `integrity_gate` a third
question. It asks whether an added line cites a spec id that no spec file
holds. `SA-0393` wired `GateSuite._run` to answer it by reading
`tree.spec_ids()` off every `Tree` (saffron/gates/suite.py). Its own notes
named four sites that stub `worktree.dirty_paths` and still drive a
`CellTree`. Each one must also stub the new `worktree.spec_ids` beside it,
since otherwise the listing reaches the cell runtime. The notes named
`_stub_the_runtime` (tests/test_session.py:1379) as one of the four.

The landed diff stubbed only the three sites in `tests/test_package.py`
(tests/test_package.py:263, :380, :3417). `_stub_the_runtime`
(tests/test_session.py:1180) still stubs `dirty_paths` alone
(tests/test_session.py:1379). It names no `spec_ids` stub at all. In
practice this broke nothing. This fixture's own
`saffron.cell.runtime.exec_` double (tests/test_session.py:1281) is a
catch-all. It logs every command it is handed into `cell.execs`. It
answers `Completed(0, "", "")`, and `spec_ids`'s own parsing turns an
empty `stdout` into `[]` without raising.
`test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
(tests/test_session.py:11543) asserts the exact, ordered list of commands
the gate-only cell ran (tests/test_session.py:11581-11584). It was
correctly grown to include `_SPEC_IDS`, the real `git grep` argv
`spec_ids` issues (tests/test_session.py:10330-10344). That assertion is
the only thing standing between this gap and silence. It happens to pin
the call that falling through was supposed to avoid.

## Problem

Give `_stub_the_runtime` the stub its own notes called for, beside
`dirty_paths` (tests/test_session.py:1379):
`monkeypatch.setattr("saffron.cell.worktree.spec_ids", lambda container:
[])`. Every ordinary cell this fixture drives then answers `spec_ids`
directly, the same shape as `dirty_paths`, rather than by falling through
`exec_`.

That generic stub would otherwise erase the one real call
`test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs`
depends on. Import `spec_ids` from `saffron.cell.worktree` at module
scope under an alias, `_real_spec_ids`. Capture it before any test can
monkeypatch it. In that one test, right after calling
`_stub_the_runtime`, restore it with
`monkeypatch.setattr("saffron.cell.worktree.spec_ids",
_real_spec_ids)`. Leave that test's own exact-list assertion
(tests/test_session.py:11581-11584) as it is. Restoring the real
function is what keeps it true rather than lucky.

## Out of scope

- **`tests/test_package.py`'s three sites**. These already stub
  `spec_ids` directly (tests/test_package.py:263, :380, :3417). Nothing
  there changes.
- **`saffron/cell/worktree.py`, `saffron/gates/suite.py`,
  `saffron/gates/core/integrity.py`, `saffron/intake.py`**. No production
  code here is wrong. This is a test-fixture gap, not a behavior defect.
- **Any other test using `_stub_the_runtime`**. The generic `[]` stub
  changes nothing any of them asserts. None reads `cell.execs` for a
  `spec_ids`-shaped command.

## Notes for the agent

**Both witnesses are small.** The first is a new, short test modeled on
the other plain two-turn drives beside it (tests/test_session.py:1864,
:1868): call `_stub_the_runtime`, drive `[_turn(_block(_PLAN)), _turn()]`,
assert `READY_FOR_REVIEW`, then assert no entry in `cell.execs` equals
`_SPEC_IDS`. The second witness is the existing lens-gate test with one
restoring line added. Its own assertions do not change.

**Ordering matters for the import.** `_real_spec_ids` must be bound at
module import time, before any test's `monkeypatch` has run. Otherwise it
binds to an already-stubbed function instead of the real one. A plain
module-level `from saffron.cell.worktree import spec_ids as
_real_spec_ids`, placed beside the existing `from
saffron.cell.worktree import DIFF_FLAGS, git_argv` (tests/test_session.py:24),
does this correctly.

**Why the second criterion is `preserves`.** The test already passes
today, before this spec's own fix lands. `_stub_the_runtime` falls
through to the real call, and the test's own list already names
`_SPEC_IDS`. The fix changes the fixture underneath it. The one added
restoring line is what keeps that same test green, rather than letting
the generic stub erase its last real entry. The criterion is a claim that
this change does not break a test that already passes, the shape
`preserves` checks: green at both sides. `witness` declares no mutant
here, so it reports `skip`. The wrong versions above describe the
production-fixture edit a mutant would have to catch once one is
attached.

**Criterion 1's second `wrong_versions` entry names the `Tree` protocol
on purpose.** `CellTree` (saffron/gates/suite.py:77) is a plain
`@dataclass`, not a `Tree` subclass. It satisfies the `Protocol`
structurally. Patching `CellTree.spec_ids` itself replaces the bound
method every `tree.spec_ids()` call reaches. That path is not wrong. It
was tried against this fixture, and the real argv never appeared.
Patching `Tree.spec_ids` instead touches a class `CellTree` never
inherits from. `CellTree.spec_ids` keeps calling the real
`worktree.spec_ids`, and the witness's `cell.execs` assertion catches it.

**Size.** The whole change is additive and test-only: one stub line, one
import line, one restoring line plus its comment, and one new fourteen-line
test. A prototype measured 23 changed lines, all under `tests/`, well
under the `bug` ceiling of 1300 tokens.
