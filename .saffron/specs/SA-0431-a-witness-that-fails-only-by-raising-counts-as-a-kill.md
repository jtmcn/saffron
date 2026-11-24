---
id: SA-0431
title: "A witness that fails only by raising counts as a kill, in the `witness` gate and in REVIEW's edits"
type: bug
priority: 2
risk: elevated
estimated_lines: 132
estimate_measured: true
pending_symbols:
  - saffron/repos/policy.py::assertion
touches:
  - saffron/gates/core/witness.py
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/cell/session.py
  - saffron/phases/review.py
  - saffron/parent_versions.py
  - saffron/regate.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_session.py
  - tests/test_parent_versions.py
  - tests/test_regate.py
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
  - saffron/repos/**
  - saffron/gates/contract.py
  - saffron/gates/baseline.py
  - saffron/probe.py
  - saffron/qualify.py
  - saffron/cell/worktree.py
  - saffron/agents/**
  - saffron/report/**
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/task.py
  - tests/test_policy.py
  - tests/test_setup_saffron.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
  - tests/test_refusal_count.py
  - tests/test_cli.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
budget_usd: 64
max_attempts: 3
max_turns: 290
acceptance:
  - claim: >-
      `witness_gate` takes a keyword `assertion`, a pattern or `None`. A
      witness whose `tests` result under its edit is `fail` raised when the
      pattern is declared, the result holds at least one failure, and every
      failure's `detail` is non-empty and unmatched by `re.match` with the
      pattern. A raised witness is neither died nor survived. It moves no
      status: a gate whose only verdicts are raises reports `pass`, and
      raises add no failure to any result. The summary names each raised
      witness with its first failure's detail, after the died or survived
      count, and the died count leaves raised witnesses out. A matched
      detail, an empty detail beside an unmatched one, one matched detail
      among unmatched ones, a `fail` with no failure and an undeclared
      pattern each read as died, as at base. A derived criterion is judged
      the same way as a declared one. The witness drives `witness_gate`
      directly with a stub mutator. A lone `KeyError` detail reads `pass`
      with no failure and the raised clause. Five kills and an undeclared
      pattern read the base summary. A detail that holds the matched word
      later in its text, beside a second unmatched detail, names its first
      detail. A kill beside a raise reads `pass` and counts one of two died.
      A survivor beside a raise reads `fail` with only the survivor's
      failure and both clauses. A derived criterion that raises is named.
    witness: tests/test_witness_gate.py::test_a_witness_that_fails_only_by_raising_reads_as_raised_and_moves_no_status
    positive_case: >-
      The survivor beside a raise reads `fail` with one `survived-mutant`
      failure through the same `status` and `failures` the lone raise is read
      by, so the raise's `pass` and empty failures are read where a verdict
      does change both.
    wrong_versions:
      - "A raised witness is counted among the died, so the summary carries no raised clause, as at your base."
      - "The pattern is searched anywhere in the detail with `re.search`, so a detail naming the word later reads as an assertion."
      - "One unmatched detail is enough, so a witness with one assertion failure beside a raise reads as raised."
      - "An empty detail reads as unmatched, so a failure with no reason counts toward a raise."
      - "A `fail` with no failures reads as raised, since every failure of none is unmatched."
      - "With no pattern declared every non-empty detail reads as raised."
      - "A raised witness is filed as a `survived-mutant` failure, so the gate reports `fail`."
      - "A gate whose only verdicts are raises reports `skip`, since nothing died."
      - "A raised witness adds a failure of its own to a passing result."
      - "The raised clause is left out of a failing gate's summary."
      - "Only declared criteria are judged for a raise, so a derived criterion that raises reads as died."
      - "The raised clause names the last failure's detail rather than the first."
      - "The pattern is matched against each failure's `message` rather than its `detail`."
      - "A detail reads as an assertion only when it starts with `AssertionError`, whatever the pattern says."
    covers:
      - set: the details a failing witness can show
        members:
          - member: one unmatched detail
            driven_by: "A raised witness is counted among the died, so the summary carries no raised clause, as at your base."
          - member: a detail matched at its start by a bare assert's reason
            driven_by: "A detail reads as an assertion only when it starts with `AssertionError`, whatever the pattern says."
          - member: a detail matched at its start by an AssertionError reason
            driven_by: "The pattern is matched against each failure's `message` rather than its `detail`."
          - member: an unmatched detail beside a matched one
            driven_by: "One unmatched detail is enough, so a witness with one assertion failure beside a raise reads as raised."
          - member: an unmatched detail beside an empty one
            driven_by: "An empty detail reads as unmatched, so a failure with no reason counts toward a raise."
          - member: a `fail` with no failure
            driven_by: "A `fail` with no failures reads as raised, since every failure of none is unmatched."
          - member: a detail holding the matched word after its start
            driven_by: "The pattern is searched anywhere in the detail with `re.search`, so a detail naming the word later reads as an assertion."
          - member: an unmatched detail with no pattern declared
            driven_by: "With no pattern declared every non-empty detail reads as raised."
      - set: the verdicts a raise can sit beside
        members:
          - member: a raise alone
            driven_by: "A gate whose only verdicts are raises reports `skip`, since nothing died."
          - member: a raise beside a kill
            driven_by: "A raised witness adds a failure of its own to a passing result."
          - member: a raise beside a survivor
            driven_by: "The raised clause is left out of a failing gate's summary."
          - member: a raise of a derived criterion
            driven_by: "Only declared criteria are judged for a raise, so a derived criterion that raises reads as died."
      - set: the details a summary can name for one raised witness
        members:
          - member: its first failure's detail, out of two
            driven_by: "The raised clause names the last failure's detail rather than the first."
  - claim: >-
      `runner.run_suite` and `runner.run_witness` take the same keyword and
      pass it on, and `GateSuite` passes `policy.witness.assertion`. So a
      task's `witness` gate judges raises under the repo's declared pattern
      and under no other. A raise there adds no new failure to the
      comparison. The witness drives `GateSuite.against` three times over
      one `preserves` criterion with a mutant, against a tree whose killing
      `tests` result carries one failure's detail. Under a policy declaring
      `^assert\b`, a `KeyError` detail reads `pass`, no new failure and the
      raised clause. An `assert` detail reads `pass` and the base summary.
      Under a policy declaring no pattern, the `KeyError` detail reads the
      base summary too.
    witness: tests/test_suite.py::test_the_suite_hands_witness_its_policys_assertion_and_a_raise_blocks_nothing
    positive_case: >-
      The `assert` detail reads the died count through the same `witness`
      result's summary, so the raised clause is read where the suite does
      reach the gate.
    wrong_versions:
      - "`GateSuite` passes no pattern, so the policy's assertion never reaches the gate."
      - "`run_suite` takes the keyword and does not hand it to `run_witness`."
      - "`run_witness` takes the keyword and does not hand it to `witness_gate`."
      - "`GateSuite` passes a fixed pattern rather than the policy's own, so an undeclared pattern still judges raises."
    covers:
      - set: the hops from the policy to the gate
        members:
          - member: "`GateSuite` to `run_suite`"
            driven_by: "`GateSuite` passes no pattern, so the policy's assertion never reaches the gate."
          - member: "`run_suite` to `run_witness`"
            driven_by: "`run_suite` takes the keyword and does not hand it to `run_witness`."
          - member: "`run_witness` to `witness_gate`"
            driven_by: "`run_witness` takes the keyword and does not hand it to `witness_gate`."
          - member: a policy declaring no pattern
            driven_by: "`GateSuite` passes a fixed pattern rather than the policy's own, so an undeclared pattern still judges raises."
  - claim: >-
      `_apply_criterion_probes` takes a required keyword `assertion` and
      hands it to `witness_gate`. A pair whose witness raised under that
      pattern reads `raised`, never `killed`, for a criterion probe, a wrong
      version and a parent's version alike. Its summary is the gate's own.
      Its line is read as a survivor's is, and it files one `adequacy`
      concern through `review.raised_finding`, anchored as a survivor's
      finding is, with no probe. It gets no second ask, and it is never a
      blocker. A line read that returns `None`, or text without the edit's
      `find`, reads `error` with the summary "the raised edit's line could
      not be read". A read that stops the cell reads `error` and asks the
      same pair again in a fresh cell. With no pattern the same raise reads
      `killed`. The witness drives `_run_apply_criterion_probes` over eight
      pairs in two cells: a criterion probe, a wrong version and a parent's
      version that raise, a wrong version killed by an assertion, a survivor,
      two raises whose read returns `None` and lacks the `find`, and a raise
      whose read stops the first cell. It asserts every outcome and each
      raised summary. It asserts the four concerns' claims, lens, line,
      anchor and probe. It asserts that only the survivor reaches
      `check_probe` and `anchored_blockers`, and five findings in all. It
      then drives one raise under no pattern.
    witness: tests/test_session.py::test_a_witness_that_only_raises_under_an_edit_reads_raised_and_files_a_concern
    positive_case: >-
      The survivor reaches `check_probe` and `anchored_blockers` through the
      same spy and the same call, so the raises' absence from both is read
      where a pair does reach them.
    wrong_versions:
      - "A raise reads `killed` and files nothing, as at your base."
      - "A raise reads `survived` and files the survivor's blocker."
      - "A raise files its finding as a blocker, so REBUT is asked to answer it."
      - "A raise is asked a second time of the whole `tests` gate, as a survivor is."
      - "Only wrong versions are judged for a raise, so a criterion probe that raises reads `killed`."
      - "A parent's version that raises names the spec rather than its parent in the concern."
      - "A raise whose line cannot be read keeps `raised` and files nothing."
      - "A raise whose read stops the cell is not asked again."
      - "The concern carries the edit as its probe."
      - "The concern is appended unanchored, without passing through `anchor`."
      - "With no pattern the raise still reads `raised`."
    covers:
      - set: the kinds of pair a raise can come from
        members:
          - member: a criterion probe
            driven_by: "Only wrong versions are judged for a raise, so a criterion probe that raises reads `killed`."
          - member: a wrong version
            driven_by: "A raise reads `killed` and files nothing, as at your base."
          - member: a parent's version
            driven_by: "A parent's version that raises names the spec rather than its parent in the concern."
      - set: the line reads a raise can meet
        members:
          - member: a read that returns the text with the `find`
            driven_by: "The concern is appended unanchored, without passing through `anchor`."
          - member: a read that returns `None`
            driven_by: "A raise whose line cannot be read keeps `raised` and files nothing."
          - member: a read whose text lacks the `find`
            driven_by: "A raise whose line cannot be read keeps `raised` and files nothing."
          - member: a read that stops the cell
            driven_by: "A raise whose read stops the cell is not asked again."
      - set: what a raise must never reach
        members:
          - member: the survivor's blocker
            driven_by: "A raise reads `survived` and files the survivor's blocker."
          - member: a blocker of its own
            driven_by: "A raise files its finding as a blocker, so REBUT is asked to answer it."
          - member: the second ask
            driven_by: "A raise is asked a second time of the whole `tests` gate, as a survivor is."
          - member: a probe on its finding
            driven_by: "The concern carries the edit as its probe."
      - set: the pattern's two states
        members:
          - member: a declared pattern
            driven_by: "A raise reads `killed` and files nothing, as at your base."
          - member: no pattern
            driven_by: "With no pattern the raise still reads `raised`."
  - claim: >-
      `_drive_cell` passes `policy.witness.assertion` to
      `_apply_criterion_probes`. The witness drives one cell through REVIEW
      under a policy declaring `^assert\b`, with two wrong versions on one
      criterion. Its witness fails the first with an `assert` detail and the
      second with a `KeyError` detail. The task ends `READY_FOR_REVIEW`.
      `wrong-versions.json` records `killed` then `raised`, and
      `findings.json`'s `adequacy` entry holds one concern, at the raised
      edit's line, naming that version.
    witness: tests/test_session.py::test_a_drive_hands_review_its_policys_assertion_for_each_wrong_version
    positive_case: >-
      The first version reads `killed` through the same `wrong-versions.json`
      record, so the second's `raised` is read where the drive does record an
      outcome.
    wrong_versions:
      - "`_drive_cell` passes `None`, so both versions read `killed`."
      - "`_drive_cell` passes a pattern that matches nothing, so both versions read `raised`."
    covers:
      - set: the details the drive's witness fails with
        members:
          - member: an `assert` detail
            driven_by: "`_drive_cell` passes a pattern that matches nothing, so both versions read `raised`."
          - member: a `KeyError` detail
            driven_by: "`_drive_cell` passes `None`, so both versions read `killed`."
  - claim: >-
      A recorded `raised` version is asked again as a `killed` one is, by
      `parent_version_pairs` and by `own_version_pairs`. A `survived`,
      `error` or `unproven` one is not. `describe_parent_versions` counts a
      `raised` entry only as chosen. The witness writes one parent record
      holding a version of each of those five outcomes, and reads it as a
      parent and as the task's own. Both read `killed` then `raised`. It
      then describes one `raised` and one `killed` entry.
    witness: tests/test_parent_versions.py::test_a_raised_version_is_asked_again_beside_each_killed_one
    positive_case: >-
      The `killed` version is paired through the same two calls, so the
      `survived`, `error` and `unproven` versions' absence is read where a
      version is paired.
    wrong_versions:
      - "Only `killed` versions are paired, as at your base."
      - "Only `raised` versions are paired, so a `killed` one is never asked again."
      - "Every version but `survived` is paired."
      - "Every recorded version is paired, whatever its outcome."
      - "`describe_parent_versions` counts a `raised` entry as survived."
      - "Only `parent_version_pairs` pairs a raised version, and the task's own record does not."
    covers:
      - set: the recorded outcomes
        members:
          - member: "`killed`"
            driven_by: "Only `raised` versions are paired, so a `killed` one is never asked again."
          - member: "`raised`"
            driven_by: "Only `killed` versions are paired, as at your base."
          - member: "`survived`"
            driven_by: "Every recorded version is paired, whatever its outcome."
          - member: "`error`"
            driven_by: "Every version but `survived` is paired."
          - member: "`unproven`"
            driven_by: "Every version but `survived` is paired."
      - set: the readers of a record
        members:
          - member: "`parent_version_pairs`"
            driven_by: "Only `killed` versions are paired, as at your base."
          - member: "`own_version_pairs`"
            driven_by: "Only `parent_version_pairs` pairs a raised version, and the task's own record does not."
          - member: "`describe_parent_versions`"
            driven_by: "`describe_parent_versions` counts a `raised` entry as survived."
  - claim: >-
      `saffron regate` passes the assertion pattern of the policy it exported
      at the task's base to `_apply_criterion_probes`. A revived version
      that raised prints its own line, `regate: <spec> wrong version raised:
      <version> (<summary>)`, and adds no new failure. The witness builds
      the wrong-version fixture with `^assert` declared at the task's base
      and `^KeyError` at `main`. It calls `regate` with the task's own first
      version failed by a `KeyError` detail. The first two pair lines read
      `raised: v1` then `survived: v2`, and the last line counts three new
      failures. A second `regate` with an `assert` detail prints no raised
      line.
    witness: tests/test_regate.py::test_regate_prints_a_version_that_only_raised_and_counts_it_nowhere
    positive_case: >-
      The second `regate` prints `survived: v2` through the same output, so
      the missing raised line is read where pair lines do print.
    wrong_versions:
      - "`regate` passes `None`, so the version reads `killed` and prints nothing."
      - "`regate` reads the pattern from the checkout's policy at `main`, so `KeyError` reads as an assertion."
      - "`regate` counts a raised version as a new failure."
    covers:
      - set: the policies `regate` could read
        members:
          - member: the policy exported at the task's base
            driven_by: "`regate` passes `None`, so the version reads `killed` and prints nothing."
          - member: the checkout's policy at `main`
            driven_by: "`regate` reads the pattern from the checkout's policy at `main`, so `KeyError` reads as an assertion."
      - set: what a raised version adds to the count
        members:
          - member: no new failure
            driven_by: "`regate` counts a raised version as a new failure."
---

## Context

Backlog item **b-c2f264**, filed from the spec loop's run 81 reviewing
#1281 (`SA-0418`). It cites `DESIGN.md` §5.4.1. Three `SA-0418` witnesses
looked a task up in a dict before they asserted. Fifteen wrong versions
removed that task, and each died by `KeyError`. Every one counted as
caught, though no assertion judged it, and the cell's REVIEW passed all
fifteen.

**Where a kill is read today**. `witness_gate` reads any `fail` from the
repo's `tests` gate as a kill (`saffron/gates/core/witness.py:298-299`).
It reports `pass` when something died and nothing survived
(`saffron/gates/core/witness.py:353`). `runner.run_witness` calls it
(`saffron/gates/runner.py:298`), and `runner.run_suite` calls that
(`saffron/gates/runner.py:339`). `GateSuite` calls `run_suite` with the
policy it holds (`saffron/gates/suite.py:205-212`). REVIEW's criterion
probes, wrong versions and parents' versions go through
`_apply_criterion_probes` (`saffron/cell/session.py:2089`). Its
`_ask_pairs` calls `witness_gate` once per pair and maps the status
through `review.criterion_probe_outcome`, where `pass` reads `killed`
(`saffron/cell/session.py:2239`, `saffron/phases/review.py:883-886`). Only
a `survived` pair reads its line and files a finding
(`saffron/cell/session.py:2243-2291`). `_drive_cell` and `saffron regate`
are its two callers (`saffron/cell/session.py:3608`,
`saffron/regate.py:285`).

**What the gate result already carries**. `SA-0426` gave `Failure` a
`detail` field that `identity` never reads
(`saffron/gates/contract.py:59`). This repo's `tests` gate puts each
`FAILED` or `ERROR` line's reason there (`.saffron/gates/tests.py:170-171`).
A test that could not be collected carries no detail
(`.saffron/gates/tests.py:126`, `:194`).

**What the loop's driver already reads**. `driver.py probe` prints
"killed only by errors, not by an assertion" when every failed line's
reason names an error other than `AssertionError`
(`.claude/skills/run-saffron-spec-loop/driver.py:1880`, `:1926-1928`).

**Measured pytest reasons**. With this host's pytest 9.1.1 at
`COLUMNS=400`, a bare `assert 1 == 2` prints the reason `assert 1 == 2`.
An assert with a message prints `AssertionError: boom`. `pytest.fail` and
an unraised `pytest.raises` print `Failed: nope` and `Failed: DID NOT
RAISE ValueError`. A dict lookup prints `KeyError: 'x'`, and a fixture
that raises prints its own exception under an `ERROR` line. An edit that
breaks the witness module's import reads `fail` with the one failure
"could not be collected" and no detail.

**What this pull request lands by hand**. `WitnessPatterns` refuses an
unknown key (`saffron/repos/policy.py:130`), and the setup template must
name each of its fields (`tests/test_setup_saffron.py:166`). The template
sits under `.claude/`, and `.saffron/policy.yaml` is `protected`. So these
are already in the tree a cell for this spec starts from:

- `saffron/repos/policy.py`'s `WitnessPatterns` holds `assertion: str |
  None`, `None` by default, with a validator that refuses a pattern that
  does not compile.
- `tests/test_policy.py` holds
  `test_a_witness_assertion_is_checked_and_this_repos_reads_each_measured_reason`.
  It loads this repo's own pattern and checks it against each measured
  reason above.
- The setup template declares `assertion: null` in its `witness:` block,
  and the setup skill's step D names the field.
- `.saffron/policy.yaml`'s `witness:` block declares
  `'^(?:assert\b|AssertionError\b|Failed\b)'`.

## Problem

**In `saffron/gates/core/witness.py`**, add `raised_detail(result:
GateResult, assertion: str | None) -> str | None`. It needs a declared
`assertion`, a `fail` status and at least one failure. Every failure's
`detail` must then be non-empty and unmatched by `re.match(assertion,
detail)`. It then returns the first failure's `detail`, and `None`
otherwise. Give `witness_gate` a keyword `assertion: str | None = None`.
Where it reads a `fail` today, a witness `raised_detail` names goes to a
new raised list, as `"<witness> (<detail>)"`, and every other `fail` dies
as before. Add the clause `"; <n> witness(es) failed only by raising, not
by an assertion: <entries joined by ', '>"` to the summary, ahead of the
"not proven" note, whatever the status. Report `pass` when anything died
or raised and nothing survived or miscounted. A raise never becomes a
`Failure`, because `subtract_baseline` counts every failure of every
result whatever its status (`saffron/gates/baseline.py:72`).

**In `saffron/gates/runner.py` and `saffron/gates/suite.py`**, give
`run_witness` and `run_suite` the same keyword with the same default, and
pass it down. `GateSuite._run` passes `policy.witness.assertion`. Three
`run_suite` fakes in `tests/test_session.py` spell their keywords out
(`:13419`, `:13485`, `:13598`), so each takes `assertion` too.

**In `saffron/phases/review.py`**, add `raised_finding(criterion, edit,
content, detail, *, version=None, parent=None) -> Finding` beside
`survivor_finding`. Its line is found as that function finds one. It
files lens `adequacy`, severity `concern`, the edit's file and no probe.
Its claim reads, with `{edit}` as below:

> `{HOST_FILED}{witness} failed with {edit} applied to {file} only by
> raising {detail!r}, and no assertion failed. The claim was {claim!r}.`

`{edit}` is "the criterion's own edit" with no `version`, and otherwise
"`{parent or 'the spec'}`'s wrong version `{version!r}`".

**In `saffron/cell/session.py`**, give `_apply_criterion_probes` a
required keyword `assertion: str | None` and pass it to `witness_gate`.
Keep the last `tests` result `_run_tests` returned for the pair. A pair
read `killed` whose last result `raised_detail` names reads `raised`. A
`raised` pair reads its line as a survivor does. Where the survivor's text
says "the survivor's line could not be read", it says "the raised edit's
line could not be read". A `CellRuntimeError` there returns
the same index, as a survivor's does. It anchors `raised_finding` through
`anchor` as a survivor's finding is anchored, appends it to the `adequacy`
review and asks nothing more. `_drive_cell` passes
`policy.witness.assertion`. Add `assertion=None` to
`_run_apply_criterion_probes`'s keywords in `tests/test_session.py`
(`:16249`, `:16341`), and pass it through.

**In `saffron/parent_versions.py`**, pair a `raised` version as a
`killed` one (`saffron/parent_versions.py:105`). Name `raised` beside
`killed` in `describe_parent_versions`'s docstring
(`saffron/parent_versions.py:187`).

**In `saffron/regate.py`**, pass `policy.witness.assertion`
(`saffron/regate.py:285`). Its pair loop already prints every outcome
but `killed` and counts only `survived` (`saffron/regate.py:303-311`).
In `tests/test_regate.py`, `_write_wv_policy` (`:2208`) declares
`witness: assertion:` as `^assert` in the base policy and `^KeyError` in
the moved one.

## Out of scope

- **Blocker severity**. The operator chose a concern now. A later spec can
  make a raise block once the concern's rate is known.
- **A collection error**. An edit that breaks the witness module's import
  reads `fail` with no detail, so it still reads as a kill. Giving that
  failure a detail is `.saffron/gates/tests.py`'s work, which is
  `protected`.
- **A lens's vacuity probe, the second ask and the probes after REBUT**.
  `probe.check_probe` reads a kill from the whole `tests` gate. The
  blockers asked again after REBUT go through `probe_findings`, which
  calls it (`saffron/cell/session.py:1894-2051`). None of them reads `detail`
  here.
- **REVIEW's three lines**. `describe_criterion_probes` and
  `describe_wrong_versions` count no outcome, and
  `describe_parent_versions` counts `raised` only as chosen. None gains a
  raised count.
- **A stacked layer's qualifying**. `qualify._in_cell_concerns` rebuilds
  each in-cell concern with no probe, and `_decide` files an `adequacy`
  one `unverified` because "its REVIEW probe did not survive"
  (`saffron/qualify.py:95`, `:282`). A raised edit did not survive its
  witness, so that sentence holds for it.
- **The vocabulary**. `raised` is a new outcome word. Backlog item
  **b-84cf18** files its `CONTEXT.md` and `DESIGN.md` §5.4.1 entries,
  `outside_cell: true`.
- **A `retired_first`**. The change adds no refusal, so it refuses no
  queued spec.

## Notes for the agent

**Every behaviour is new code inside existing functions.** Each criterion
declares a witness and no mutant. So `witness` reports `skip` here.

**At base each witness fails in its body**, and its module still
collects. `WitnessPatterns(assertion=...)` and `policy.witness.assertion`
exist at base, landed by hand. Import `raised_detail` and
`raised_finding` inside a test body, never at module scope, or `revert`'s
`revert` reads a collection error.

**The gate witness** follows `tests/test_witness_gate.py`'s `_criterion`.
A stub mutator that yields `None` is enough, since no file changes. Build
each `tests` result with `Failure(..., detail=...)`. Give it a pattern
with no leading `^`. Only then does a search tell the rows apart from a
match at the start.

**The suite witness** extends `_WitnessTree` in `tests/test_suite.py` with
a tree whose killing result carries one failure with a `detail`. Mark the
criterion `preserves: true`, so `criteria` does not flag the witness green
at base. Read the `witness` result from `comparison.run.results`.

**The REVIEW witness** drives `_run_apply_criterion_probes`. The harness's
`read_at_head` stub receives the container name, so the stopping read can
raise `runtime.CellRuntimeError` in `gate-1` alone. Spy on
`saffron.probe.check_probe` with `monkeypatch.setattr`, wrapping the real
function. Script ten `tests` results: one per pair, one more for the
survivor's second ask and one for the pair asked again.

**The drive witness** follows
`test_a_wrong_version_its_witness_survives_is_rebutted_as_a_blocker`.
Append a `witness:` block to `_PROBE_POLICY`. No rebuttal turn is needed,
since nothing blocks.

**The regate witness** reuses `_build_wrong_version_fixture`,
`_seed_wv_records` and `_prepare_wrong_version_run`. The first `tests`
result is the task's own `v1`. Replace it in `_wv_full_results()`.

**The `prose` gate** counts each new comment and docstring.
`_apply_criterion_probes`'s docstring is at ten lines already, so reword it
inside the lines it holds.

**Size**. A prototype changed 132 lines outside `tests/` by `git diff
--numstat`, and `size` counted 465 tokens there. Its tests changed 424
lines, 1739 tokens that `size` leaves out.
