---
id: SA-0299
title: A host-filed survivor outside the diff never reaches REBUT, so `SA-0288` packaged past a witness the host watched stay green
type: bug
priority: 1
estimated_lines: 236
estimate_measured: true
touches:
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/report/pr_body.py
  - tests/test_session.py
  - tests/test_review.py
  - tests/test_report.py
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
  - hooks/**
  - saffron/cell/**
  - saffron/agents/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/task.py
  - saffron/ledger.py
  - saffron/qualify.py
  - saffron/end_review.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_rebut.py
  - tests/test_task.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 25
max_attempts: 3
max_turns: 130
acceptance:
  - claim: >-
      A surviving criterion probe and a surviving wrong version reach REBUT
      whether or not they anchor. The witness drives `SA-0288`'s measured
      shape through a whole cell. A wrong version survives at line 330 of
      `saffron/gates/runner.py`, which the diff never touches. Beside it the
      criterion's own edit survives on another line outside the diff. Both are
      recorded `anchored: false` in `findings.json`, both reach
      `rebuttal.json` as blockers 1 and 2 in filing order, and the task does
      not end `READY_FOR_REVIEW`. A correctness lens's own blocker on a line
      outside the diff stays out of `rebuttal.json`.
    witness: tests/test_session.py::test_a_survivor_outside_the_diff_still_reaches_rebut
    mutant:
      file: saffron/phases/review.py
      find: blockers = anchored_blockers(reviews)
      replace: blockers = [f for f in anchored_blockers(reviews) if f.anchored]
    wrong_versions:
      - "`review_state` routes to REBUT on an unanchored survivor while `anchored_blockers` still keeps only anchored findings, so REBUT is handed no blocker."
      - The selection keeps every blocker whatever its anchoring, so the correctness lens's unanchored blocker reaches REBUT too.
      - Anchoring marks a host-filed claim anchored, so `findings.json` no longer records that the survivor lies outside the diff.
  - claim: >-
      `anchored_blockers` draws the boundary between the host's survivors
      and a lens's findings. It selects, in review order, every anchored blocker and every blocker whose
      claim starts with the host's mark, anchored or not. The witness drives
      both survivor forms unanchored, the criterion's own edit and a wrong
      version, between an anchored correctness blocker and an anchored
      conventions blocker. It drives four lens findings that stay out, each
      an unanchored blocker. They are a correctness one, an adequacy one whose
      own probe survived, an adequacy one carrying the host's mark past the
      start of its claim, and one whose report began with the mark. Over
      the lens findings alone the review is `READY_FOR_REVIEW`.
    witness: tests/test_review.py::test_a_host_filed_survivor_is_a_blocker_whether_or_not_it_anchors
    mutant:
      file: saffron/phases/review.py
      find: blockers = anchored_blockers(reviews)
      replace: blockers = [f for f in anchored_blockers(reviews) if f.anchored]
    wrong_versions:
      - Survivors are appended after every anchored blocker, so a survivor filed before the conventions blocker is numbered after it.
      - The selection keeps any blocker whose probe survived, so the adequacy lens's own unanchored finding is selected.
      - The selection keeps every unanchored `adequacy` blocker, so each lens finding the adequacy lens filed is selected.
      - The selection keeps a claim holding the host's mark anywhere, so a lens claim quoting the mark mid-sentence is selected.
  - claim: >-
      The pull request body reports an unanchored survivor as the blocker
      REBUT answered. `Disagreements` numbers it after the anchored blocker
      before it, with its own rebuttal and verdict. An `EXHAUSTED` body
      lists it among the blockers left standing. The `Not covered` line on
      findings that could not be anchored leaves it out and keeps a lens's
      own unanchored blocker.
    witness: tests/test_report.py::test_a_host_filed_survivor_outside_the_diff_is_reported_as_a_blocker
    mutant:
      file: saffron/report/pr_body.py
      find: anchored = anchored_blockers(reviews)
      replace: anchored = [f for f in anchored_blockers(reviews) if f.anchored]
    wrong_versions:
      - The `Not covered` line still counts every unanchored finding, so it says the implementer never saw the survivor REBUT answered.
      - The `Not covered` line leaves out every unanchored blocker, so the lens's own unanchored blocker disappears from it.
      - "`Disagreements` keeps its own anchored-only filter, so the survivor gets no row and its verdict is shown against nothing."
---

## Context

Backlog item **b-e40d09**, which cites `DESIGN.md` §5.4.1 and §5.5. Line
numbers below were read at `e8f5529e`.

**Measured on `SA-0288`** (#914), in the spec loop's run 44. The record is
`~/.saffron/batches/v0/SA-0288/findings.json`. Its one `adequacy` finding is
host-filed, at `saffron/gates/runner.py:330`, with `anchored: false` and
`probe_verdict: survived`. Its claim says the criterion's witness stayed
green under the spec's wrong version "A canned `witness` result stands in
for the gate". So the measured survivor is a wrong version's, not a criterion
probe's own edit. No REBUT ran, and the task ended `READY_FOR_REVIEW`. The
item records that both seats of the loop's review then confirmed the witness
could not fail.

**How a survivor is filed.** `_apply_criterion_probes` applies each
criterion probe's edit, then each wrong version's, in one Gate-only cell
(`saffron/cell/session.py:1942-1963`). The pairs list puts every
criterion-probe entry first, then every wrong version
(`saffron/cell/session.py:3296-3310`). A survivor is built by
`review.survivor_finding`, then passed through `anchor` against the reviewed
diff, then appended to the `adequacy` review
(`saffron/cell/session.py:2086-2097`). `survivor_finding` writes a claim
starting with `review.HOST_FILED`, for both forms
(`saffron/phases/review.py:736-769`). A lens cannot forge that start.
`_from_report` strips every leading copy from a lens's claim
(`saffron/phases/review.py:218-232`).

**Where it is dropped.** `anchored_blockers` keeps a finding only when it is
`anchored` and a `blocker` (`saffron/phases/review.py:787-794`).
`review_state` routes to REBUT only on what that returns
(`saffron/phases/review.py:863-880`). REBUT's own blocker list is the same
call (`saffron/cell/session.py:3394`). So an unanchored survivor is written
to `findings.json` and the ledger, and reaches neither REBUT nor a blocker
count.

**Who else reads that rule.** `_disagreements` numbers its rows from it
(`saffron/report/pr_body.py:311-355`). The `EXHAUSTED` line in
`_not_covered` lists its result (`saffron/report/pr_body.py:566-573`).
`run_task` packages an `EXHAUSTED` task with no REBUT result in its
exhausted mode only when that result is non-empty (`saffron/task.py:650-654`). The body's line on unanchored
findings says neither the implementer nor the concern count saw any of them
(`saffron/report/pr_body.py:611-624`). That sentence turns false for a
survivor REBUT answered.

**The drop rate does not change.** `LensReview.drop_rate` already leaves out
every finding whose claim starts with `HOST_FILED`
(`saffron/phases/review.py:148-158`). A survivor stays recorded
`anchored: false`, so the rate reads the same before and after. No query in
`saffron/` computes a drop rate from the ledger. A case-blind search for the
words finds that property and comments in `saffron/phases/review.py`,
`saffron/agents/findings.py` and `saffron/ledger.py`, none a query. Item b-b431c1 owns that query's half.

## Problem

The host ran a survivor's edit and watched the witness stay green. Anchoring
exists to drop a lens's hallucinated or off-diff finding. A host-filed
survivor is neither, yet anchoring decides whether it reaches REBUT. The
operator chose the first arm of the item's *Done looks like*. A host-filed
survivor reaches REBUT whether or not it anchors. A lens's finding keeps
today's rule.

1. **The rule.** `anchored_blockers` selects every blocker that anchors,
   and every blocker whose claim starts with `HOST_FILED`, in one pass in
   review order. Its docstring says why a survivor is exempt.
   `review_state`'s docstring says the same in one clause.
2. **The record stays honest.** A survivor is still recorded
   `anchored: false`. Nothing marks it anchored.
3. **The body.** The `Not covered` line on unanchored findings leaves out
   any finding `anchored_blockers` selected. Its comment says why.
4. **The prose that turns false.** `rebut.py`'s module docstring ties
   REBUT's blockers to anchoring, and `sustained_blockers`'s docstring says
   an unanchored blocker never reaches REBUT. One test docstring says the
   rule filters on the anchor. The notes name the lines.
5. **The existing assertion.** One test pins the old behaviour. The notes
   name it and what it asserts now.

## Out of scope

- **Renaming `anchored_blockers`.** Its name is now narrower than what it
  selects. A rename reaches `saffron/cell/session.py`, `saffron/ledger.py`
  and `saffron/task.py`, two of them `elevate_on` paths, for no change in
  behaviour. The docstring carries the exception instead.
- **The end review.** It decides its own findings in `_decide`
  (`saffron/qualify.py:176-178`), and reads no REBUT blocker list.
- **The ledger's drop rate.** Item b-b431c1. Nothing here changes
  `findings.anchored`.
- **An adequacy lens's own probe.** `adequacy_probes` still takes anchored
  adequacy findings alone (`saffron/phases/review.py:797-807`). An
  unanchored lens finding is never probed, and stays unselected.
- **The design record and the vocabulary.** `DESIGN.md`, ADR 3, ADR 4 and
  `CONTEXT.md` said only an anchored survivor reaches REBUT. The operator edited them by hand in this spec's pull request.

## Notes for the agent

**An edit, with mutants on lines the change keeps.** Each mutant names a
line that exists at base and that this change leaves alone. Leave the body
of `review_state` as it is, and leave `_disagreements` as it is. Only
`review_state`'s docstring changes. Each mutant puts the anchored-only
filter back at one reader of the rule.

**Where REBUT goes from there needs no change.** REBUT already handles a
survivor that anchors. `_blocker_line` shows the implementer the edit
(`saffron/phases/rebut.py:163-175`). After the rebuttal, `_rebut_gates`
asks every surviving probe again (`saffron/cell/session.py:3400-3416`). A
`preserves` survivor keeps its withdrawal guard, keyed on the claim's start
(`saffron/phases/rebut.py:432-450`). Each reads the blocker list, never
`anchored`. `run_task`'s exhausted mode reads `anchored_blockers` too, so
it follows with no edit. No criterion drives that reader, since
`saffron/task.py` is forbidden here.

**Criterion 1's witness.** Write it in `tests/test_session.py` after
`test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker`
(`tests/test_session.py:11869`), and take that test's shape. Declare one
criterion with one wrong version. Drive the four lens turns by hand, not through `_probe_turns`. The
correctness lens files one blocker on `z.py` line 1, and the other three
file nothing. Then come the criterion-probe answer, the wrong-version
answer, and the two rebuttal turns. The probe's edit targets `src/y.py`'s
second line, as the neighbouring tests' unanchored edit does. The wrong
version's edit targets `saffron/gates/runner.py`. Its stubbed head content
puts the edit's `find` on line 330 after 329 filler lines. Keep every token
of both lines out of `_ANCHORING_DIFF`'s changed lines
(`tests/test_session.py:4841-4847`). Script
both probe-cell suites to `pass`, so both survive. Assert the state, then
`findings.json`'s adequacy entries as `(file, line, anchored)`, then
`rebuttal.json`'s blockers as `(finding, file, line, anchored, probe)`. Also
assert the correctness entry is unanchored and the adequacy `drop_rate` is
`0.0`. The drive ends `REBUTTAL_UNJUDGED` with `_rebuttable(...,
rebut_commits=0)` and `_CLAIMED_FIX`, as the neighbouring tests do.

**Criterion 2's witness.** Write it in `tests/test_review.py` after
`test_a_wrong_versions_survivor_names_the_version_it_came_from`
(`tests/test_review.py:2088`). Build both survivors with `review.survivor_finding` and pass them through
`findings.anchor` over a one-hunk diff on another file, then assert neither
anchored. Build the forged finding through `review._from_report` from a
reported claim starting with `HOST_FILED`. Put the survivors in the
adequacy review after the lens's own probed finding, as REVIEW appends
them. Compare the selection by identity and order, not by `==`. Assert
`review_state`'s state and its reason line.

**Criterion 3's witness.** Write it in `tests/test_report.py` after
`test_disagreement_rows_attribute_the_right_rebuttal_to_the_right_blocker`
(`tests/test_report.py:1184`). One correctness review holds an anchored
blocker and the lens's own unanchored blocker. One adequacy review holds the survivor, unanchored,
at `saffron/gates/runner.py:330`. Give the `RebutResult` a rebuttal and a
verdict on finding 2. Render with `exhausted=True`. Assert exactly two
numbered rows, with the survivor's location and both answers in row 2.
Assert the standing-blockers line's two locations in order. Assert the
unanchored line names one finding under `correctness`.

**Item 5, the existing test.**
`test_a_criterion_probe_its_witness_survives_is_rebutted_as_a_blocker`
(`tests/test_session.py:11527`) unpacks exactly one blocker from
`rebuttal.json` (`tests/test_session.py:11611-11612`). Both of its
survivors now reach it. Keep its name, since `census` reads a renamed test as a removed one. Unpack two
blockers. Keep the five assertions on the first, and assert the second is
line 2 and unanchored. Its docstring
(`tests/test_session.py:11530-11534`) says the unanchored survivor reaches only `findings.json`. Say instead that both reach
`rebuttal.json`. No other test at base pins the old rule.
`test_an_unanchored_blocker_routes_nowhere` (`tests/test_review.py:148`)
drives a lens's own blocker, and stays green.

**Item 4, the prose.** `saffron/phases/rebut.py:3-8` says "Confirmed" is
the host's anchoring. Add that for a survivor the host's run of its edit
is that check. `saffron/phases/rebut.py:604` says an unanchored blocker never
reaches REBUT. Say only a host-filed survivor does. `sustained_blockers`'s
docstring is already ten lines, the `prose` gate's limit, so the
replacement stays on one line. The `prose` gate counts a changed sentence
as new. So a rewritten sentence takes no semicolon or em dash and stays
under 25 words. The module docstring's sentence has a semicolon today, so
split it. `tests/test_report.py:417-419` says `anchored_blockers` filters
on the anchor. Say it does so for a lens's finding. The `retired-vocabulary`
hook reads test claims too. A criterion claim saying a gate "runs" the
witness tripped it on the prototype.

**Measured on a prototype over `e8f5529e`.** The whole change came to 943
changed tokens by the `size` gate's counter, against the `bug` ceiling of
1300. That is 73%. `tests/test_session.py` carried 342 of them, and the
code 149. `prek run --all-files` passed on the final cut. Each witness
failed with the source reverted. Each mutant and each wrong version above,
applied as an edit, failed its criterion's witness. The first two of
criterion 1 failed all three witnesses. The session witness alone takes 0.3
seconds.

Commit after each witness passes. Uncommitted work dies with the cell.
