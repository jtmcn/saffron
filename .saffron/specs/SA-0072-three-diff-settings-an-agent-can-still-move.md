---
id: SA-0072
title: three git settings an agent can set in its worktree still move the diff the host reads
type: bug
priority: 3
depends_on: []
touches:
  - saffron/cell/worktree.py
  - tests/test_scope.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/agents/**
  - saffron/cell/session.py
  - saffron/cell/runtime.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/task.py
  - saffron/replay.py
  - tests/test_package.py
budget_usd: 5
max_attempts: 3
max_turns: 40
risk: elevated
acceptance:
  - claim: >-
      A worktree that configures a wider diff context than git's default does
      not widen the diff the host reads. Hunks carry the same context lines they
      carry with no configuration at all. This is the one of the three settings
      with a consequence: `parse_diff` puts every line a hunk's range covers
      into the lines a critic finding may anchor to, so an agent that widens the
      context widens what a finding can land on.
    witness: tests/test_scope.py::test_the_pinned_flags_beat_a_configured_context_width
  - claim: >-
      A worktree that configures its object-name abbreviation or its diff
      algorithm does not move the pinned diff's bytes either. Nothing host-side
      reads an `index` line's hash or cares which algorithm chose a hunk
      boundary, so this is cosmetic today. Together with the first criterion it
      closes the gap `harness/recovery.py`'s `pinned_diff` measured. Other
      settings still move the pinned diff, and they are filed on backlog item
      89 rather than handled here.
    witness: tests/test_scope.py::test_the_pinned_flags_beat_a_configured_abbrev_and_algorithm
  - claim: >-
      The prefix, external-diff and textconv pins still beat repo-local config,
      as they do today.
    witness: tests/test_scope.py::test_the_pinned_flags_beat_repo_local_config
    preserves: true
  - claim: >-
      A gate handed a bent diff still errors rather than passing.
    witness: tests/test_scope.py::test_a_gate_handed_a_bent_diff_errors_rather_than_passing
    preserves: true
---

## Context

`docs/BACKLOG.md` item **89**, found building the lens-corpus harness's
byte-identity check (2026-09-08). Reproducing `export_patch`'s output on a host
it does not control needed three settings `saffron/cell/worktree.py` does not
pin. `DIFF_FLAGS` backs its comment for the prefix settings, `diff.external`,
`diff.textconv` and rename detection, but nothing pins `core.abbrev`,
`diff.context` or `diff.algorithm`. An agent that runs `git config` on any of
them before its own commits changes `export_patch`'s bytes, and nothing in this
module notices.

**The values are already measured.** `harness/recovery.py`'s `pinned_diff`
starts from `DIFF_FLAGS` and adds exactly these three pins. Its docstring
records the measurement behind each: against all eight shipped fixtures, which
width matched every recorded patch's hunk headers, and why the abbreviation is
pinned to what `auto` actually emitted rather than to `auto` itself. Use that
function's values and read its docstring for why. Do not choose new ones.

**Measured in review, 2026-09-11:** adding the three pins to `DIFF_FLAGS` left
the whole suite passing (1745). No test outside `touches` compares bytes they
change. `--name-only -z` accepts all three.

## Problem

Worktree config is the agent's to write (§2), and `DIFF_FLAGS` exists because
command-line flags beat `.git/config`. Three of the settings `pinned_diff`
found it needed are not pinned where the cell's diff is taken, and the one that
matters is the context width, because of what a finding may anchor to.

## Out of scope

**Other settings that still move the pinned diff.** Review measured three more:
`diff.interHunkContext` merges hunks, `color.ui=always` puts escape codes on the
header line so `scope` errors, and `diff.ignoreSubmodules` hides a gitlink from
the name-only listing. Each wants its own flag and its own witness, and none is
a value `pinned_diff` measured. They are filed on backlog item 89.

**The rename pin's test.** `--no-renames` is guarded by no test: removing it
leaves the suite green. Adding one means widening `_hostile_repo`, which this
spec asks you not to do. It is filed on backlog item 89.

**`pinned_diff` itself.** Once `DIFF_FLAGS` carries the three pins,
`pinned_diff` passes each twice. Git takes the last value, and the two are
equal, so this is harmless. Its docstring ("not enough by itself") also goes
stale. `harness/**` is forbidden, so both are a later harness change.

**`tests/test_package.py`'s own copy of the flags, and the
`docs/evidence/scripts/` that import `DIFF_FLAGS`.** Neither shares the defect
or breaks, and both are forbidden here.

## Notes for the agent

**This spec adds new entries to an existing tuple, which is new code, so its
criteria carry witnesses and no mutants.** A mutant would have to pin the
spelling of a flag, and naming that spelling here would put the literal in the
prompt you are reading.

**Every new witness must fail with `worktree.py` reverted, not merely be missing
at base.** The `revert` gate re-runs each new witness against the reverted
source and blocks any that still pass. Both new criteria describe something the
unpinned tuple gets wrong, so an honest test fails reverted.

**Do not widen `_hostile_repo`.** Both preserved criteria read it, and adding
the three settings to it changes their inputs. Build the new tests on a fixture
of their own. The existing `_diff` helper takes flags and is reusable.

**Write the new fixture's runner as a `def`, not a `lambda`.** `_hostile_repo`
uses `run = lambda … # noqa: E731`. Copy that and you add a suppression, which
fails `integrity` even inside `touches`. Drop the `# noqa` and ruff's `E731`
fails `lint` instead.

**Prove the pin, not the config.** A test that sets `diff.context` and checks
that the output is narrow must also show the bare diff under the same config is
wide, the way `test_hostile_worktree_config_bends_a_bare_diff` pairs with the
pinned test. Otherwise it passes on a git that ignores the setting.

**The algorithm half needs an input where the two algorithms disagree.** A
simple edit gives the same hunks under patience and myers, and the pairing
above then proves nothing. Build an edit where they differ, and have the test
assert that the bare diff under `diff.algorithm=patience` is not the default
one before it asserts the pinned one is.
