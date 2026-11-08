---
id: SA-0342
title: "`revert` never runs an old test the diff rewrote, so a rewritten test that checks nothing passes unseen"
type: feature
priority: 1
depends_on: [SA-0341]
estimated_lines: 165
estimate_measured: true
touches:
  - saffron/gates/contract.py
  - saffron/gates/core/revert.py
  - saffron/gates/suite.py
  - saffron/record/migrate.py
  - tests/test_contract.py
  - tests/test_revert.py
  - tests/test_suite.py
  - tests/test_record_migrate.py
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
  - saffron/phases/**
  - saffron/cell/**
  - saffron/report/**
  - saffron/ledger.py
  - saffron/intake.py
  - saffron/record/contract.py
  - saffron/record/fold.py
  - saffron/gates/runner.py
  - saffron/gates/core/integrity.py
  - saffron/gates/core/census.py
  - saffron/gates/core/criteria.py
  - saffron/gates/core/witness.py
  - saffron/gates/core/scope.py
  - tests/test_scheduler.py
  - tests/test_integrity.py
budget_usd: 92
max_attempts: 3
max_turns: 270
risk: elevated
acceptance:
  - claim: >-
      A gate result carries an optional `locations`, read from a gate's JSON.
      It maps a collected name to a value with a `file`, a `first` line and a
      `last` line. A gate that sends a map, an empty map or no key gives three
      different values, and no key gives `None`.
    witness: tests/test_contract.py::test_a_gate_may_report_where_each_collected_test_is_defined
    wrong_versions:
      - "`locations` holds plain dicts, so a value has no `first` attribute."
      - An empty map is read as `None`.
  - claim: >-
      With `locations` reported at head, `revert` hands the `tests` gate a
      second subset in a second run, inside the same revert as the first.
      The subset is each name collected at base and at head whose head
      location names a file under `test_paths` and holds a line the diff
      changes. An added line is changed. A removed line marks the new-side
      line on each side of it. A context line marks nothing. The witness
      drives an added line inside a test and one at its first line. It also
      drives a removed last line and a line removed directly above a test.
      It leaves out a test only context lines reach, one in a file the diff
      left alone, one located outside `test_paths` and one with no location.
      It leaves out a test touched only by its base location, with a head
      location and without one, and one collected at base alone. It leaves out each name in the first subset, a
      `preserves` witness, an exempt name and a name reading as an option.
    witness: tests/test_revert.py::test_the_second_subset_is_each_old_test_a_changed_line_falls_inside
    wrong_versions:
      - Every located test in a changed test file joins, whatever its lines.
      - A hunk's context lines count as changed, as `parse_diff`'s `hunk_lines` does.
      - Only added lines count, so a test that lost its last assertion never joins.
      - A removed line marks only the new-side line after it.
      - A removed line marks only the new-side line before it.
      - A changed line on a test's first line does not count.
      - A changed line on a test's last line does not count.
      - A changed line counts in whatever file it sits in, matched by number alone.
      - A hunk outside `test_paths` counts too.
      - Locations are read from the base results as well as the head ones.
      - Locations are read from the base results alone.
      - A name with no location falls back to the file its name begins with.
      - A declared witness collected at base joins both subsets.
      - A `preserves` witness joins.
      - An exempt name joins.
      - A name reading as a command-line option joins.
      - A name collected at base or at head joins, not at both.
      - The second run happens after the restore.
  - claim: >-
      The second subset never changes `revert`'s status, failures or tool,
      except that a checkout or restore that fails is `error`, as today. The
      witness takes seven first-run outcomes, and a diff that adds no new
      test. These are a pass verdict, a fail verdict, an errored run and a run
      that did not enumerate. They are also failures keyed on something other
      than a name, a handed name left unaccounted for, and a raised exception.
      It crosses each with eight second-run outcomes. These are one test
      passing, all passing, all failing, an errored run and a raised
      exception. They are also a run that did not enumerate, failures keyed
      elsewhere and every name uncollected. Each result matches the same
      call without `locations`, which runs only the first subset. A checkout
      that fails and a restore that fails each give `error`, with no failures
      and no tool, with a first subset and without one.
    witness: tests/test_revert.py::test_the_second_subset_never_changes_what_revert_decides
    wrong_versions:
      - One run hands the union of both subsets to the `tests` gate, and its result answers both.
      - An exception out of the second run escapes the gate.
      - The second run is skipped when the diff adds no new test.
      - A rewritten test that passes makes the gate `fail`.
      - A second run that raised makes the gate `error`.
      - A rewritten test that passes joins the failures of a `fail` verdict.
      - A checkout or restore that fails reads as `skip` when the diff adds no new test.
  - claim: >-
      After the reverted run, the summary of every `pass`, `fail` and `skip`
      carries an advisory clause that begins `advisory, does not block: `.
      That covers a
      pass verdict and a fail verdict. It also covers the three skips for a
      first run with no readable verdict, and the skip for a diff that adds
      no new test. The witness crosses each with the eight second-run outcomes
      criterion 3 names. The clause names each rewritten test that ran and
      passed, and no rewritten test that failed. Where one passed of two, it
      reads `advisory, does not block: 1 of 2 rewritten test(s) passed
      without their source: ` and then the passing name. Where both passed,
      it reads the same with `2 of 2` and both names, comma-separated. An
      unreadable second run names no test.
    witness: tests/test_revert.py::test_each_verdict_after_the_reverted_run_carries_the_advisory
    wrong_versions:
      - The clause rides only the `pass` and `fail` summaries.
      - The clause is left off the skip for a run that did not enumerate.
      - The clause is left off the skip for failures keyed elsewhere.
      - The clause is left off the skip for a diff that adds no new test.
      - The clause names every rewritten test, passed or not.
      - The clause is empty when every rewritten test failed.
      - The clause is empty when the second run errored or raised.
      - Failures keyed elsewhere read as every rewritten test passing.
      - The clause begins `advisory:` alone, so a lens cannot tell it blocks nothing.
  - claim: >-
      With no `locations` at head, `revert` behaves exactly as today. The
      witness drives `None` and an empty map. Each runs the first subset
      once and no second subset, and its summary is today's sentence with
      nothing appended. That holds for a readable diff and for one `revert`
      cannot read, because nothing reads the diff.
    witness: tests/test_revert.py::test_with_no_locations_the_rewritten_tests_are_never_run
    wrong_versions:
      - With no locations, every test collected on both sides in a changed test file joins a second run.
      - The diff is read whenever `locations` is not `None`, so an empty map and an unreadable diff append a clause.
  - claim: >-
      With `locations` reported and a diff `revert` cannot read, no second
      run happens, and the summary carries the advisory clause. With a first
      subset, its verdict stands. Without one, the gate gives today's skip
      for a diff that adds no new test and runs nothing.
    witness: tests/test_revert.py::test_a_diff_revert_cannot_read_leaves_the_second_subset_unrun_and_says_so
    wrong_versions:
      - The parse error escapes the gate.
      - The second subset is silently empty.
      - The clause is appended only when the diff adds a new test.
  - claim: >-
      `GateSuite` hands `revert` the patch every other core gate reads. Run
      end to end, the `tests` gate's JSON carries `locations` and a rewritten
      test passes with the source reverted. `revert`'s head result names that
      test in its summary, and the suite reports no new failure.
    witness: tests/test_suite.py::test_the_suite_hands_revert_its_diff_so_a_rewritten_test_is_reported
    wrong_versions:
      - The suite never passes the patch, so `revert` sees an empty diff.
  - claim: >-
      `saffron migrate` sets aside a `gate_result`'s `locations` key, as it
      does `collected`. A held fact carrying `locations` as `null`, and one
      carrying a map, each agree with the ledger's fact and gain nothing.
    witness: tests/test_record_migrate.py::test_a_gate_results_locations_is_set_aside_like_collected
    wrong_versions:
      - "`locations` is compared, so every live `gate_result` refuses its ref."
---

## Context

Backlog item **49**, the changed-body-same-name half. Every line cited here
was read at `7d08c0e7`. Two hand commits amend `DESIGN.md` §5.4 before it,
and this spec makes them true. The `collected` paragraph's sibling reads
"`locations` is optional, and only `revert` reads it". Core compares a
location with "the lines the diff changes, never a hunk's context". The
`revert` paragraph reads "A test rewritten under its old name is a second
subset, and it is advisory". It selects a test when "a changed line under
`test_paths` reaches" its lines: "an added line inside them, or a removed
line beside them". A pass there "is reported as advisory". It now says "One
extra test run, or two when the second subset below holds a name". It also
says "A checkout or restore that fails is still `error`." The `criteria`
paragraph on what it cannot see ends on that second subset.

**What `revert` judges today.** Its subset is the names new at head and
every declared witness collected at head. It leaves out `preserves`
witnesses and the exempt (`saffron/gates/core/revert.py:130-136`). A name starting
with `-` is dropped (`saffron/gates/core/revert.py:53-76`). Source is decided
by file: any changed path outside `test_paths`
(`saffron/gates/core/revert.py:172-174`). The reverted run is one call to
`run_tests` inside `reverted(source)`
(`saffron/gates/core/revert.py:243-255`). The verdict reads that run's
`collected`, `uncollected` and `failures` by name
(`saffron/gates/core/revert.py:331-387`). The module docstring names this
gap (`saffron/gates/core/revert.py:5-9`), and so does a `ponytail:`
(`saffron/gates/core/revert.py:158-160`). So a test that exists at base and
is rewritten to check nothing is never run without its source.

**The contract.** `GateResult` holds `collected`, `uncollected`, `failures`
and `summary` (`saffron/gates/contract.py:61-89`). No field says where a
test is defined. Pydantic's default drops an unknown key, so a gate that
sent `locations` today would lose it.

**The wiring.** `GateSuite._run` reads the patch once
(`saffron/gates/suite.py:158`). It passes `changed`, never the patch, to
`revert_gate` (`saffron/gates/suite.py:180-200`).

**Two hunk parsers exist.** `parse_diff` marks every line a hunk covers,
context included (`saffron/agents/findings.py:157-160`). The pinned diff
flags carry three lines of context (`saffron/cell/worktree.py:211`).
`integrity`'s `_split_blocks` and `_parse_block` record each hunk line's
kind and new-side number (`saffron/gates/core/integrity.py:103-198`).
`witness` already imports both (`saffron/gates/core/witness.py:55-60`).

**Where an operator reads a passing gate.** The PR body's gate table prints
every result's `summary`, whatever its status
(`saffron/report/pr_body.py:502-531`). REVIEW's lenses read the same field
(`saffron/phases/review.py:183-187`). The ledger stores it
(`saffron/ledger.py:2198`). No gate result has a non-blocking channel of its
own. So the summary is the smallest channel that reaches the PR body, and
this spec adds no other.

**What else reads the contract's fields.** A live `gate_result` fact carries
the whole `GateResult` dump (`saffron/ledger.py:2230`).
`_GATE_RESULT_SET_ASIDE` lists the dump's keys the ledger's own fact lacks
(`saffron/record/migrate.py:82-84`). `_gate_result_facts` builds that fact
without them (`saffron/record/migrate.py:385-399`). After this change every dump holds
`locations`, null or not. `tests/test_setup_saffron.py:196-200` requires
`.claude/skills/setup-saffron/GATES.md` to name every contract field. A cell
cannot write under `.claude`, so the commit adding this spec adds that
bullet by hand.

## Problem

1. **Add the field.** `GateResult` gains an optional `locations`: a map from
   a collected name to its file and its first and last lines at head. Core
   never parses a key. `None` means the gate does not report it.
2. **Find the rewritten tests.** With `locations` at head, read the diff's
   changed new-side lines in files under `test_paths`. An added line is
   changed. A removed line marks the new-side line on each side of it, so a
   removed last assertion still reaches its test. Context lines mark
   nothing. The second subset is each name collected at base and at head
   whose location holds a changed line in its own file. Leave out the first
   subset's candidates, `preserves` witnesses, the exempt and any name
   reading as an option.
3. **Run it in the same reverted tree, in its own run.** Inside the one
   `reverted(source)` block, run the first subset as today. Then run the
   second subset. A second run keeps every first-subset verdict exactly as today.
   No rewritten name can enter its accounting, and a broken second run can
   only change the advisory clause. The cost is one more `tests` call, and
   only when the second subset holds a name.
4. **Report it, never block on it.** The second run sets no status, adds no
   failure and supplies no tool. Its outcome rides the summary as an
   advisory clause, which the PR body's gate table prints.
5. **Leave today's behaviour alone without `locations`.** No runner reports
   it yet, so every repo today must see no change at all.
6. **Pass the patch.** `GateSuite` hands `revert` the patch it already read.
7. **Keep `migrate` agreeing.** Set `locations` aside as `collected` is.

## Out of scope

- **This repo's `tests` gate.** `.saffron/**` is `protected`, so
  `.saffron/gates/tests.py` reports no `locations` after this merges. The
  operator adds a pytest plugin there by hand afterwards. Until then
  `revert` here behaves exactly as today, which criterion 5 pins.
- **Blocking on the second subset.** A cosmetic edit passes reverted too.
  `DESIGN.md` §5.4 keeps it advisory until runs measure how often.
- **Edits that move no test's lines.** A changed helper, fixture or
  `conftest.py` reaches no test's location, so this subset never sees it.
- **The `setup-saffron` skill.** `GATES.md` names `locations` already at
  this spec's base, added with the spec. A target repo's `tests` template
  stays as it is.
- **The verdict's error paths.** An `error` from the first run aborts the
  attempt, and its summary carries no advisory clause.

## Notes for the agent

**New code, so no mutants.** The second subset, its run and its clause are
new code. So are the `diff` argument and the set-aside key. Every
criterion declares a witness and no mutant, and `witness` reports `skip`.

**Every new test fails with the source reverted.** Each one passes the new
`diff` argument, reads `locations`, or relies on the new set-aside key. Add
no module-scope import of a new name to a test file. Build a result's
`locations` through `GateResult.model_validate` from plain dicts, so a test
module still collects against the base contract.

**The `diff` argument.** Give `revert_gate` a required keyword `diff`, with
no default, like every other argument it takes
(`saffron/gates/core/revert.py:79-90`). A default fails open: a caller that
forgets it loses the second subset in silence. Add `diff=""` to each
existing call in `tests/test_revert.py`, and change nothing else in those
calls. Criterion 7 pins the one production caller.

**Read the diff with `integrity`'s parser, not `parse_diff`.** `parse_diff`
counts context lines, so a test within three lines of a change would join.
Import `_split_blocks`, `_parse_block` and `_DiffError` as `witness` does.
Read the diff only when `locations` holds a name. An unreadable diff then
appends the clause and leaves the second subset empty.

**A known false advisory.** A removed line marks the new-side line on each
side of it, as `DESIGN.md` §5.4 says. So deleting a whole test, with one
blank line between tests, marks the next test's first line. That neighbour
joins the second subset, and if it passes reverted the clause names it.
This is accepted, because the subset blocks nothing.

**Where `locations` comes from.** Merge every head result's map, as
`_collected` merges `collected`. Never read the base results' map. A
location's `file` is compared with the diff's new-side path as a string.
No witness drives a map split across two head results, since one `tests`
gate fills it.

**The clause.** Begin it with `advisory, does not block: `, after the
separator the other notes use. REVIEW's lenses read every summary unmarked
(`saffron/phases/review.py:183-187`). An unmarked advisory draws a lens
blocker and a REBUT round (`saffron/phases/review.py:176-179`), so the words
must say it blocks nothing. Name each rewritten test that ran and passed, as the first
subset's verdict defines a pass. Give a count when none passed. Say the run
gave no readable verdict when it errored, raised, did not enumerate, or
keyed its failures elsewhere. Append it to the `pass` and `fail` summaries
and to the three skips at `saffron/gates/core/revert.py:281-330` and
`:373-381`. Add a skip for a diff with no first subset whose second subset
ran. Leave every summary unchanged when the clause is empty.

**Today's skips still come first.** A diff with neither subset skips where
it does today, with today's summary. Where `locations` is reported and the
diff is unreadable, that summary also carries the clause (criterion 6). A diff with only the second subset
passes the `test_paths`, source and dirty-path checks as today, then runs.

**No queued spec edits `saffron/gates/core/revert.py`.** SA-0338 cites
`saffron/gates/core/revert.py:187-200` as a reader of a criterion's mutant,
and its `touches` leaves the file out. Leave those lines as they are
anyway, since the second subset needs nothing from them.

**No suppression comments.** `# noqa` is an `integrity` suppression token
(`.saffron/policy.yaml:91`), so an added line holding one fails the attempt.
Keep `saffron/gates/core/revert.py:254` byte-identical, indentation and
comment included, so the diff never re-adds it. Guard the first call with a
condition inside its `try`, not around it. The second run's `except` carries
no suppression token. Ruff selects no `BLE` rule (`pyproject.toml:86`), so a
bare `except Exception` needs none.

**Stale prose to correct.** Rewrite the module docstring's last sentence
(`saffron/gates/core/revert.py:5-9`). Correct `revert_gate`'s docstring
(`saffron/gates/core/revert.py:91-101`), which says no skip touches
`reverted` or `run_tests`, "a diff that adds no test" included. With a
second subset, that diff now runs. Drop the item 49 clause from the
`ponytail:` (`saffron/gates/core/revert.py:158-160`). Update the module
docstring and the comments that count the set-aside keys
(`saffron/record/migrate.py:20-24`, `:82-89`).

**The fixtures.** Criterion 2's diff is a real `git diff` of one test file
and one source file, taken under the pinned flags. Give each excluded name a
location the diff would reach if its exclusion were missing. Put the name
with no head location in the changed test file, spelled with that file's
path. Give it and one located but untouched test a touched base location.
Criterion 3's and 4's witnesses share one helper. It answers the first
subset and the second from separate tables, keyed on whether the new name is
in the handed list.

**Stack order.** `depends_on: [SA-0341]` is for stack order only. This spec
reads nothing SA-0341 adds.
