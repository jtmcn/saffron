---
id: SA-0121
title: two copies of the diff pins win over `DIFF_FLAGS`, so a change to a pin reaches no test built on them
type: bug
priority: 3
depends_on: []
touches:
  - harness/recovery.py
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - images/**
  - docs/**
  - saffron/**
  - harness/corpus.py
  - harness/lens_scoring.py
  - tests/test_corpus.py
  - tests/test_worktree.py
  - .git/**
budget_usd: 12
max_attempts: 3
max_turns: 60
risk: elevated
acceptance:
  - claim: >-
      `pinned_diff` takes its hunk context width from `worktree.DIFF_FLAGS`
      alone, and every shipped fixture still reproduces through it. Today its
      own copy of the flag follows `DIFF_FLAGS` and wins, so a change to that
      pin reaches no harness test.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--unified=3",'
      replace: '"--unified=4",'
  - claim: >-
      `pinned_diff` takes its `index` line abbreviation from
      `worktree.DIFF_FLAGS` alone, and every shipped fixture still reproduces
      through it. Today its own copy wins in the same way.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--abbrev=7",'
      replace: '"--abbrev=9",'
  - claim: >-
      `pinned_diff` takes its diff algorithm from `worktree.DIFF_FLAGS` alone,
      and every shipped fixture still reproduces through it. Today its own copy
      wins in the same way.
    witness: tests/test_corpus.py::test_every_shipped_fixture_reproduces_its_own_declared_range
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--diff-algorithm=myers",'
      replace: '"--diff-algorithm=histogram",'
  - claim: >-
      The `cell_patch` fixture in `tests/test_package.py`, which calls itself
      shaped exactly like `export_patch`'s output, builds its patch with
      `worktree.DIFF_FLAGS`. Today it uses the module's own list, which holds
      five of those flags.
    witness: tests/test_package.py::test_a_patch_applies_onto_a_base_that_moved_elsewhere
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--no-color",'
      replace: '"--color=always",'
  - claim: >-
      The `packageable` fixture in `tests/test_package.py`, the green cell that
      49 of the module's 99 tests start from, builds its patch with
      `worktree.DIFF_FLAGS` too.
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--no-color",'
      replace: '"--color=always",'
  - claim: >-
      The degraded-apply test in `tests/test_package.py`, which builds its own
      patch rather than take a fixture's, builds it with `worktree.DIFF_FLAGS`
      too.
    witness: tests/test_package.py::test_a_degraded_apply_is_an_error_not_a_success
    preserves: true
    mutant:
      file: saffron/cell/worktree.py
      find: '"--no-color",'
      replace: '"--color=always",'
---

## Context

Backlog item **89**, its "Done looks like" remainder. `SA-0072` (commit
`29b5049f`) added the three pins `pinned_diff` measured to `DIFF_FLAGS`, and
`SA-0082` (commit `1e4b3b61`) added three more. Two copies of the old flags
are left.

`DIFF_FLAGS` (`saffron/cell/worktree.py:131-165`) holds eleven flags. They
include `--abbrev=7` at `:146`, `--unified=3` at `:149` and
`--diff-algorithm=myers` at `:151`.

**`pinned_diff`** (`harness/recovery.py:70-106`) runs `git diff` with
`*DIFF_FLAGS` at `harness/recovery.py:101`. Then it passes the same three
flags again at `harness/recovery.py:102-104`. Git takes the last value of a
repeated flag, so the copies win (measured below). Its docstring
(`harness/recovery.py:71-93`) says it starts from `DIFF_FLAGS` "and its
`_git`'s two `-c` overrides" (`harness/recovery.py:76`). The worktree's
`git_argv` (`saffron/cell/worktree.py:168-204`) now holds six `-c` pins.
Two of them, `core.quotePath=false` and `diff.suppressBlankEmpty=false`, are
passed at `harness/recovery.py:95-98`. They go through the module's own
`_git` (`harness/recovery.py:64-67`). The docstring then argues
that `DIFF_FLAGS` "is not enough by itself" (`harness/recovery.py:76-77`).
With the copies gone, the hostile-config test in the corpus module still
passes (measured below).

**`tests/test_package.py:361-367`** defines its own `DIFF_FLAGS`, a list of
five flags. The `cell_patch` fixture (`tests/test_package.py:370-386`) calls
its output "shaped exactly like `worktree.export_patch`'s output"
(`tests/test_package.py:372`). It builds that patch from the five-flag list
(`tests/test_package.py:385`). Thirteen more sites in the module do the same.
Among them are the `packageable` fixture (defined at `tests/test_package.py:866`,
reading the list at `:905`) and
`test_a_degraded_apply_is_an_error_not_a_success` (`tests/test_package.py:411`).

One site knows the list is short. At `tests/test_package.py:3077-3079` a
comment says the module's own list "lacks --ignore-submodules=none". The diff
call after it (`tests/test_package.py:3080-3089`) passes that flag explicitly
after the list.

**Measured 2026-09-21 on this base**, host git 2.54, with each copy replaced
by the real tuple in a scratch worktree. A mutant swapped one entry of
`DIFF_FLAGS` for the value each claim's mutant names. With the copies in
place, every mutant leaves its witness green. With them gone, each witness
fails. `tests/test_package.py` and `tests/test_corpus.py` then pass whole
(188 tests).

A second probe compared each shipped fixture's `diff.patch` with `git diff`
under the eleven flags and `pinned_diff`'s two `-c` overrides. It ran under git
2.39.5 in `saffron/cell-base:python` and under git 2.54, and both printed the
same counts. The flags as they stand reproduce all eight fixtures. A context
width of 4 moves seven of them, an abbreviation of 9 moves all eight, and the
`histogram` algorithm moves one.

## Problem

A mutant is the only evidence that a witness guards its claim (§5.4.1). A
copy of a pin, passed after `DIFF_FLAGS`, makes a change to that pin
invisible. Such a change moves the diff every lens, `integrity` and `size`
read (§2). The harness test that compares a pinned diff with recorded bytes
exists to see such a change. The copies in `pinned_diff` hide three pins from it.
And the five-flag list leaves six pins out of every patch the PACKAGE tests
build, under a fixture that says it matches the cell's export.

## Out of scope

**Closing item 89.** `docs/**` is `forbidden`, so the operator closes it by
hand after merge.

**`DIFF_FLAGS` itself.** `SA-0118` edits `saffron/cell/worktree.py`, and it is
forbidden here. Every mutant names that file, since a mutant needs no
`touches` entry.

**`pinned_diff`'s two `-c` overrides.** They stay. It takes none of the other
four pins `git_argv` holds.

**`tests/test_corpus.py`.** Its fixture heads reach a cell only through
branches the mirror carries. The seed's plain `git fetch` takes branches, not
`refs/fixtures/*` (`saffron/cell/worktree.py:93`). That was true before this
spec. At `SA-0117`'s base the cell's `tests` gate collected the reproduction
test and reported no failure (`~/.saffron/batches/v0/SA-0117/baseline.json`).

## Notes for the agent

**Every criterion is `preserves`.** Each witness exists and passes now. Each
mutant swaps one entry of `DIFF_FLAGS` for another value. It survives while a
copy of that flag stays in the file under test, and it fails the witness once
the copy is gone. That was measured on this base (see Context). The change is
an edit to code that exists, so each criterion carries a mutant.

**In `harness/recovery.py`.** Drop the three flags that follow `*DIFF_FLAGS`
in `pinned_diff`. Keep both `-c` overrides. Rewrite the docstring so it says
what the function does now. It passes `DIFF_FLAGS` and two of `git_argv`'s
`-c` pins. The measurement against the eight fixtures is now the provenance
of the three pins `DIFF_FLAGS` carries, not a reason for a second copy. Keep
the reason seven digits was chosen over `auto`. The new docstring stays within
ten lines and takes no em-dash, semicolon or contraction. The `prose` gate
counts each rule per file.

**In `tests/test_package.py`.** Replace the module's list with an import of
`DIFF_FLAGS` from `saffron.cell.worktree`, at module scope beside the other
`saffron` imports. No call site needs to change. Keep the explicit
`--ignore-submodules=none` after `*DIFF_FLAGS` at `tests/test_package.py:3085`.
`SA-0097`'s criterion 1 uses that test as its witness, with a mutant that
deletes the flag from `DIFF_FLAGS`
(`.saffron/specs/done/SA-0097-two-name-only-reads-miss-a-hidden-gitlink.md:34-43`).
The explicit flag keeps the gitlink in the test's own patch under that mutant,
so only the listing under test decides the result (`:162-169`). Rewrite the
comment at `tests/test_package.py:3077-3079` to give that reason. It must no
longer say the module's list lacks the flag.

**What each witness drives.** Criteria 1 to 3 drive the three flags
`pinned_diff` copies, one mutant each. Criteria 4 to 6 drive the module-scope
name through three kinds of site: the `cell_patch` fixture, the `packageable`
fixture, and a test that builds its own patch. A local import in one fixture,
with the module's list left in place, fails at least one of them.

**What no witness drives.** Three edits carry no witness:

- The docstring rewrite.
- The rewrite of the comment at `tests/test_package.py:3077-3079`.
- The explicit flag kept at `tests/test_package.py:3085`. The imported tuple
  carries the same flag, so removing the explicit one leaves every test
  green. `SA-0097`'s mutant would then kill its witness whatever the listing
  does, and only review catches the removal.

The `--no-color` mutant kills most of `tests/test_package.py` once the change
lands. Of the fourteen sites that read the list, three have no test it kills
after the change and spares before it: `tests/test_package.py:799`,
`tests/test_package.py:2345` and `tests/test_package.py:2692`. Five sit in
tests that take the fixture criterion 5 drives. Those tests fail through that
fixture alone: `tests/test_package.py:1261`, `tests/test_package.py:1511`,
`tests/test_package.py:2962`, `tests/test_package.py:3045` and
`tests/test_package.py:3084`. Three have such a test and no criterion:
`tests/test_package.py:466`, `tests/test_package.py:2482` and
`tests/test_package.py:2575`. All of them read the module-scope name that
criteria 4 to 6 pin.

**Do not edit `tests/test_corpus.py`.** Its reproduction test is the witness
for criteria 1 to 3, and its hostile-config test already covers the same
range. Both pass after the change.

**The `size` gate counts tests.** A `bug` gets 300 changed lines. This change
is about 60: 27 for the two copies, measured, and about 30 for the docstring.

**Leave no copy anywhere in the call.** A flag passed before `*DIFF_FLAGS`
loses to it, so its mutant still dies. That keeps a copy the witnesses cannot
see, and the review reads for it.
