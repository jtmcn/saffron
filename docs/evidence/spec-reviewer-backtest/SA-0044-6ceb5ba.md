**Findings**

- **Blocker: a golden fixture and its test pin the baseline gate list, and neither is in `touches`.**
  - **Why the change reaches them.** `_suite` adds the core gates to every call, the baseline call included: `session.py:993-997` returns `[*results, census_gate(...), criteria_gate(...)]`, `:1008` runs `baseline = _suite([])`, and `:1019` emits `gates=tuple(r.gate for r in baseline)`. The spec's criterion 4 says the baseline call yields a result: *"No names at base … is `skip`"* (spec:58-61). So the baseline line gains `revert=skip`.
  - **What breaks.**
    - `tests/fixtures/watch-golden.txt:8,27` read `baseline: scope=pass, … census=skip, criteria=skip`.
    - `tests/test_events.py:922-950` compares a driven run against that file.
    - `tests/test_events.py:1005-1012` pins the same six-gate line as a `_JOINED` entry, and `:1113-1118` asserts every joined line is a captured one.
  - **Precedent.** SA-0043 changed the session's output and listed both files (its spec:13,15).
  - **Fix:** add `tests/test_events.py` and `tests/fixtures/watch-golden.txt` to `touches`.

- **Blocker: the spec never says what `revert` does when the `tests` gate returns `error` with the source reverted. With this repo's gate, two of the spec's three "acceptable answers" arrive as exactly that.**
  - **What the spec says.** *"Reverting the source can make a test fail, error, or vanish from collection, and all three are acceptable answers"* (spec:172-174). It also says a new module plus its tests *"fail on the import, and the gate reports green"* (spec:109-110).
  - **What the gate does at base.**
    - When `--collect-only` fails, `collected` is `None` (`.saffron/gates/tests.py:44-48`).
    - The only fallback for node ids parses `FAILED ` lines (`tests.py:89-94`).
    - A nonzero exit with no parsed failures is emitted as `"status": "error"` with no `collected` (`tests.py:96-104`).
    - So an import error or a "not found" node id comes back as a gate `error`. **Unverified:** I reasoned pytest's output for these cases from the regex at `tests.py:87`; I did not run it.
  - **Why neither reading is safe.** Criterion 5 covers only a failed checkout (spec:62-66), so the cell has to pick a mapping:
    - `error` → `error` aborts every attempt (`session.py:525-537` returns `GATE_ERROR`) for any spec whose new tests import a new module. SA-0044's own shape is one of those.
    - `error` → `pass` turns a timed-out or unrunnable gate (`runner.py:131-135`) into green.
  - `.saffron/**` is forbidden, so the cell cannot make the runner tell these cases apart.
  - **Fix:** decide it in a criterion with a witness. `skip` with a summary naming the runner's `error` matches criterion 4's *"none of them is evidence"* and the way `criteria` degrades (`criteria.py:129-140`). Also correct spec:109-110.

- **Blocker: the "passed" rule the spec prescribes leaves out the readability guard the `criteria` gate depends on.**
  - **The instruction.** *"a name that is in `collected` and is not among the failure codes"* (spec:175-176).
  - **What `criteria` actually does.** It first treats a side as unreadable when failures exist and none of them is a collected name (`criteria.py:31-57`, `_side`). `DESIGN.md:835` records why, as a measured result: one printed `path:N: word: message` line makes this repo's gate key failures on something other than node ids (`tests.py:80-88`), *"and the naive rule then reports `pass` for a witness that failed."*
  - **What goes wrong here.** In `revert` the naive rule runs the other way: every reverted test reads as "passed", so the task gets a false theatre `fail` on each attempt and ends `EXHAUSTED`. A witness driven by a clean fake runner passes the naive rule.
  - **Fix:** say to reuse `criteria._side`/`_green`. Importing them is not editing a forbidden file. Add a witness where failures are keyed on something other than node ids.

- **Blocker: no criterion has a mutant, and two witnesses pass plausible wrong implementations.**
  - **No mutants at all.** The spec edits existing code (`session.py`, `worktree.py`) but declares no mutant. A `mutant:` key would be rejected at parse time: `Criterion` has `extra="forbid"` with only `claim`/`witness`/`preserves` (`intake.py:44-60`).
  - **Criterion 3.** `test_the_source_is_restored_when_the_run_raises` passes an implementation that restores in a `finally` and never checks the tree afterwards. The claim's *"a tree it cannot restore is an `error`"* (spec:53-55) has no witness.
  - **Criterion 1.** `test_a_new_test_that_passes_without_the_source_is_a_failure` passes an implementation that emits one combined failure, if the fixture has a single passing test. The claim requires *"One failure per test that did — named"* (spec:40-41).
  - **Fix:** add witnesses for "restored but still dirty → `error`" and "two passing tests → two named failures". List the mutants in the body.

- **Concern: the change size sits right at the 600-line ceiling, and `size` blocks at `elevated`** (spec:191; `DESIGN.md:757`).

  | File | Estimated changed lines |
  |---|---|
  | `saffron/gates/core/revert.py` | ~150 |
  | `saffron/cell/worktree.py` (revert, restore, verify) | ~60 |
  | `saffron/cell/session.py` wiring | ~50 |
  | `tests/test_revert.py` | ~240 |
  | `tests/test_session.py` | ~80 |
  | `docs/BACKLOG.md` | ~20 |
  | golden fixture and `tests/test_events.py` | ~4 |
  | **Total** | **≈600 (range 500–700)** |

  - The `tests/test_session.py` estimate is not small because `_stub_the_runtime` stubs neither `run_gate` nor any revert helper (`test_session.py:671-804`). The tests at `:2975-2990` report a new name `t.py::test_new`, so they will reach the new code path.
  - Comparable rows: SA-0020 at 646 lines ended `EXHAUSTED`, SA-0040 was 683, and SA-0027 was 585.
  - Consider moving the `session.py` wiring into a follow-up spec.

- **Concern: an empty `integrity.test_paths` is not one of the kinds of nothing.** It defaults to `[]` (`policy.py:45`). With nothing declared, every changed file counts as source, so `revert` would check out the new test files too. The subset then vanishes and reads as "not passed". This should be a fourth `skip`.

- **Concern: files the diff adds have nothing to check out.** *"check the changed files … back to `tree_base`"* (spec:132-133) does not cover a source file that does not exist at `tree_base`. Built literally, the checkout fails, and by criterion 5 that is an `error` for every spec that adds a module. **Unverified:** this is git behaviour I did not test. Fix: say that added files are deleted, then restored from HEAD.

- **Note: some sentences become false and cannot be fixed from inside this task.**
  - `saffron/phases/review.py:44`: *"`revert` is unbuilt"* (forbidden file, a code comment).
  - `DESIGN.md:817`: *"which is not built yet"* (forbidden).
  - `CONTEXT.md:208`: core gates *"never execute repo code"* (forbidden).

  The spec's follow-up (spec:156-163) covers only the ontology entry and the `CONTEXT.md` bullet. Ask the cell to list these in the PR body.

- **Note: criterion 6's witness cannot change.** `tests/test_census.py::test_added_tests_alone_pass` exists at base (`test_census.py:45`), but `census.py` is forbidden, so the witness cannot go red. It adds nothing beyond `forbidden`.

**Checks**

- found: criteria vs invariants — findings 2, 3 (a runner `error` has no defined outcome and could be collapsed into `pass`; the "passed" rule leaves out the readability guard from `criteria.py:31-57` / `DESIGN.md:835`)
- found: scope reaches the change — finding 1 (`tests/test_events.py`, `tests/fixtures/watch-golden.txt`); also read `session.py:931-1019`, `baseline.py:58-99` (a baseline `skip` does not register as suite drift), `test_cli.py` (stubs `run_one_cell` entirely), `pr_body.py:347-352` (renders gate results generically)
- found: witness/mutant discipline — finding 4; criterion 6's `preserves` witness exists at base (`test_census.py:45`); `tests/test_revert.py` does not exist at base
- checked: ceilings vs history — `max_turns` 130 against the highest peak, SA-0027's 102t; `budget_usd` $16 against SA-0020's plan plus implement of $9.56, leaving $6.44 for REVIEW and REBUT (SA-0020 spent $4.87, SA-0027 $6.32)
- found: size vs ceiling — finding 5 (≈600 against a blocking 600; SA-0020 646, SA-0040 683, SA-0027 585)
- found: claims about current code — findings 2, 3 (spec:109-110 and 172-174 do not match what `tests.py` does; spec:175-176 describes the `criteria` rule incompletely). These claims check out: `run_gate`'s `subset` (`runner.py:111,126`), the tests gate docstring (`tests.py:2-5`), the only callers being `test_runner.py:68,189`, the `DESIGN.md` quotes (`:817,841,843,851`), `committed` failing one path per dirty file (`committed.py:29-34`), and the ontology/CONTEXT test (`test_vocabulary_agrees_with_context.py:20-61`, `CONTEXT.md:207`, `saffron.ttl:76-82`)

**Assessment:** runnable after the listed fixes: widen `touches` to the two event files, decide what a runner `error` under reversion means, require the readability guard, and add the missing witnesses; the size concern and the empty-test-paths and added-file concerns are your judgement call.