---
id: SA-0112
title: the ceilings comparison is computed, printed, and then judged by a paid reader, so every spec review spends a subagent applying check 4's thresholds by eye
type: feature
priority: 3
depends_on: []
touches:
  - .claude/skills/run-saffron-spec-loop/driver.py
  - tests/test_spec_loop_driver.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - tests/test_queued_specs.py
  - docs/**
  - images/**
  - harness/**
  - pyproject.toml
  - uv.lock
  - saffron/**
  - records/**
  - .claude/agents/**
  - .claude/skills/run-saffron-spec-loop/SKILL.md
budget_usd: 23
max_turns: 130
max_attempts: 3
acceptance:
  - claim: >-
      `driver.py check SA-NNNN` reports as a blocker a `max_turns` at or below
      the highest peak among the rows it judged — the equality case included —
      and a `budget_usd` strictly below the highest pre-REVIEW total among
      them. The two thresholds differ by exactly that, and the command keeps
      them apart: a `budget_usd` level with that total is not a blocker, where
      a `max_turns` level with that peak is. It exits 1 when it reports either
      — 1 and not 2, which is reserved for infrastructure — and 0 whenever it
      reports neither. The usage failures `cmd_history` already spells, a spec
      no file declares and a repo with no ledger row, are not verdicts: they
      keep the 1 they return today, and the command reaches no comparison to
      report. Today nothing judges that comparison: `_ceilings_line` renders it
      and `cmd_history` prints it, and the reader applies the thresholds.
    witness: tests/test_spec_loop_driver.py::test_check_blocks_the_ceilings_check_4_calls_blockers_and_no_others
  - claim: >-
      The rows `check` judges are the rows `history` prints for the same spec:
      the target's own type, closest in shape first, and the same limit. A past
      cell of another type, or one past that limit, changes no verdict.
    witness: tests/test_spec_loop_driver.py::test_check_judges_the_rows_history_prints_and_no_others
  - claim: >-
      `check` reports as a concern, and does not fail on, a budget whose
      remainder after that pre-REVIEW total cannot cover the highest REVIEW plus
      REBUT total among the same rows. A remainder that covers it draws no
      concern. Either way the exit status is 0, so a concern is the operator's
      judgement and never the command's.
    witness: tests/test_spec_loop_driver.py::test_check_reports_a_review_and_rebut_shortfall_as_a_concern
  - claim: >-
      A spec with no rows to compare against is never reported as checked:
      `check` says the comparison had no evidence, and whatever sentence it
      prints when a real comparison found no blocker is absent there. It exits
      0 all the same — no evidence is not a failure, and step 1b must not read
      a spec of a new shape as one.
    witness: tests/test_spec_loop_driver.py::test_check_with_nothing_to_compare_against_claims_no_pass
  - claim: >-
      The `ceilings:` line `history` prints stays the comparison it is today:
      the target's ceilings against the rows `history` selected, and against no
      cell it filtered out by type or cut past the limit. Sharing that
      selection with `check` does not move it.
    witness: tests/test_spec_loop_driver.py::test_history_compares_the_targets_ceilings_with_the_rows_it_printed
    preserves: true
  - claim: >-
      The block above that line is unchanged too: `history`'s header, which
      rows of the target's own type it prints, and their order, closest in
      shape first.
    witness: tests/test_spec_loop_driver.py::test_history_lists_only_the_same_type_most_similar_shape_first
    preserves: true
---

## Context

Backlog item b-281f0a is
`docs/backlog/b-281f0a-four-of-the-spec-reviews-six-checks-have-right-answers-nothing-computes.md`,
tier 2. It was filed on 2026-09-19 from a measurement of four specs. Each was
written for the same backlog item and read by one spec review. Three of the
four reviews drew a blocker. Two of those three blockers were the same
arithmetic: a diff estimated against a `size` ceiling, and ceilings against
`history`. This spec is the ledger-reading half of that item. Its other half is
out of scope below.

Every sentence here about current code was read at `90f2e5c` on 2026-09-19.

**The comparison exists and is judged by nobody**. `_ceilings_line` at
`.claude/skills/run-saffron-spec-loop/driver.py:1568-1602` computes the
target's `max_turns` against the highest `peak_turns` among the rows. It
compares `budget_usd` against the highest plan-plus-implement-plus-repair total
among them, summed by `_pre_review_total` at `:1562-1565`. `_history_lines` at
`:1605-1622` appends that line under the rows it selected. `cmd_history` at
`:1625-1659` prints the block and returns 0. Nothing in the file reads the line
back.

**The thresholds it is read against are prose**.
`.claude/agents/spec-reviewer.md:86-99` holds four rules for check 4. A blocker
when the turns half says `below by` or `level with it`. A blocker when the
budget half says `below by`. A concern when what remains after the pre-REVIEW
total cannot cover REVIEW and REBUT "at the rows' usual cost". A note, not a
pass and not a blocker, for `ceilings: no past cells of this shape to compare
against`. The first two are a subtraction against a threshold. The third is a
second subtraction the same rules say the line does not compute, at `:91-92`:
"Read those from the rows themselves — the line does not compute it".

**Which is why `SA-0092` stopped where it did**. It shipped `_ceilings_line`
and left check 4's own wording out of scope, because that half is a prompt and
no test can watch one. The spec says so itself at
`.saffron/specs/done/SA-0092-history-compares-the-ceilings-itself.md:70-72`.
Item 145 then carried the prompt half and closed. Between them they moved the
*arithmetic* into code and left the *verdict* in a reader. This spec moves the
verdict.

**`history` selects rows and `check` must select the same ones**.
`_history_lines` at `:1616-1621` keeps only cells whose `spec_type` equals the
target's. It sorts by closeness in `touches` and criteria count, with the newer
of a tie first, and cuts the list at `limit`. `cmd_history`'s parser defaults
that limit to 12 (`:1746`). `_ceilings_line` is then called with `rows`, the
cut list, and not with every cell the ledger holds.
`tests/test_spec_loop_driver.py:1197-1223` is the existing guard on exactly
that: a high-peak row of another type and one past the limit, each asserted
absent from the line.

**A subcommand that fails is already the file's shape**. `cmd_size` at
`:1345-1365` ends `return 0 if result.status == "pass" else 1`. `_fail` at
`:75-78` documents why the failing status is 1: "`saffron/cli.py` reserves 2
for infrastructure".

**The loop has the place to run it**. `SKILL.md:59` is "## 1b. Review each spec
before its first cell". Wiring the command into that step is prose and is out
of scope below.

**Two files hold every caller of these helpers**. A `git grep` for
`_history_lines` and `_ceilings_line` at this base returns
`.claude/skills/run-saffron-spec-loop/driver.py` and
`tests/test_spec_loop_driver.py`, whose fourteen hits run from `:1151` to
`:1349`. Both are in `touches`. The same grep matches two further files, and
neither calls anything. `docs/superpowers/plans/2026-09-14-spec-reviewer.md`
(`:51`, `:82`, `:194`, `:228`, `:341`, `:370`) is the plan that built the line.
`.saffron/specs/done/SA-0092-history-compares-the-ceilings-itself.md` (`:38`,
`:112`, `:120`) is the spec that shipped it. Both are records of work already
done, both are `forbidden`, and the change reaches no third file.

## Problem

- **The line is computed once and reasoned over every time**. Each spec review
  reads the rendered sentence, recovers the two subtractions from it, and
  applies four thresholds that live in another file. That is a computation. The
  item was filed because a person paid a subagent for it twice in one
  measurement.
- **The concern half is not computed at all**. Check 4's third rule needs a
  third number, what a REVIEW and a REBUT cost on those same rows. The rows
  carry `review_usd` and `rebut_usd` already
  (`.claude/skills/run-saffron-spec-loop/driver.py:1399-1400`). Nothing sums
  them.
- **Nothing gives the loop a verdict it can act on before a cell**. Step 1b
  dispatches a review. No command's exit status says that a spec's ceilings sit
  under what cells of its shape needed.
- **An absent comparison reads like a passing one**. The no-rows sentence is
  the same shape of output as a comparison that found nothing wrong, and only
  the prompt says the two differ.

## Out of scope

**The tree-only checks of the same item**. Item b-281f0a's "Done looks like"
puts a parametrised-witness check in `tests/test_queued_specs.py`. It cannot
ride in this diff. That file is inside `.saffron/policy.yaml:69`'s
`test_paths`. A new test there is a new test the `revert` gate re-runs with
this diff's *source* reverted. That source is `driver.py`, which the new test
does not read. It would pass reverted, and `revert` blocks a new test that
passes without its source. `tests/test_queued_specs.py` is `forbidden` here for
that reason. The item stays open on it.

**The `specs:` bookkeeping check of the same item**. It is already built, and
the item's own bullet is wrong about it. `check_specs_name_their_items` at
`tests/records/check.py:415` on `origin/main` reports "cites this item and is
not listed".
It fires for any spec whose `## Context` names an item that does not list it
back. `tests/records/test_records_integrity.py:13-21` runs the whole check set
over the live tree. Add nothing for it.

**Check 4's wording, and step 1b's**. `.claude/agents/spec-reviewer.md` and
`.claude/skills/run-saffron-spec-loop/SKILL.md` are both `forbidden`. What the
review says about a command's output, and where the loop runs it, is prose with
no witness. That is the same split `SA-0092` made and item 145 then closed by
hand. Item b-281f0a carries it. The operator settled the order: this cell runs
first, and the prose is wired to it afterwards. `SA-0092` shipped the
`ceilings:` line the same way, before any prompt knew it existed. So the
command this spec adds is called by nothing once the cell ends, and that is the
expected state rather than an omission. Two lines of that prose are the ones to
leave alone rather than the ones to fix.
`.claude/agents/spec-reviewer.md:19` names `driver.py history <SPEC-ID>` as
what a review runs. `:30` limits its Bash to "those git commands and
`driver.py history` only". `check` is for the delegate driving step 1b, before
a review is dispatched. Adding it to a reviewer's Bash is a decision about the
review, not about this command.

**The floor caveat**. A peak the line marks "a floor — cut off at its own
ceiling" makes an `above by` narrower than it looks
(`.claude/agents/spec-reviewer.md:95-97`). That is a reading rather than a
threshold, because there is no number it crosses. `check` prints the line,
which carries the words, and adds no judgement of its own about them.

**`--before`**. `cmd_history` takes it for a blind backtest
(`.claude/skills/run-saffron-spec-loop/driver.py:1633-1639`). `check` is for
live use before a cell, so it takes the spec id and nothing else. Do not add
`--limit` either. 12 is what `history` prints. A `check` judging a different
number of rows than the line the reviewer quotes is the defect this spec is
about.

**Checks 1, 2, 3, 5 and 6**. Criteria against invariants, scope, witness
discipline, size against the ceiling, and claims about current code stay with
the review. Item b-281f0a says why: a review's attention is worth paying for
where the answer is a judgement.

**The rows, their order, and the line's own words**. `_ceilings_line`,
`_cell_line` and `_history_lines` keep the output they produce today.
`tests/test_spec_loop_driver.py:1160-1162`, `:1174-1175`, `:1217-1232`,
`:1310-1318` and `:1337-1350` read that output exactly, and criteria 5 and 6
are that standing still declared. This change adds a reader for those numbers,
not a second rendering of them.

## Notes for the agent

**Six criteria, four new witnesses and no mutants, plus two `preserves`**. The
command is new code, so no text at base pins a mutant honestly. The subcommand,
its verdicts and the sentence each prints do not exist, and nothing in the tree
determines their spelling. Expect the `witness` gate to report `skip`, with a
summary saying the spec declares no mutants. The names of the subcommand's
helpers, and the exact wording of every line it prints, are yours.

**Criteria 5 and 6 are the other kind**, and between them they cover what the
lift below could move. Criterion 5 names
`test_history_compares_the_targets_ceilings_with_the_rows_it_printed`
(`tests/test_spec_loop_driver.py:1178`). That test reads
`_history_lines(...)[-1]` and asserts the filtered-out and cut rows are absent
from it, which is the type filter and the limit. Criterion 6 names
`test_history_lists_only_the_same_type_most_similar_shape_first` (`:1150`).
That test reads the header and the row lines between it and the `ceilings:`
line, which is the closeness sort the other one never sees. Both exist at base,
and both must be green at base and at head. `SA-0092` declared a `preserves`
criterion of the same shape
(`.saffron/specs/done/SA-0092-history-compares-the-ceilings-itself.md:39-42`),
though over a different function. Its witness pins the fields `_cell_line`
renders for one row, not `_history_lines`'s block.

Both tests are inside `touches`, so you can edit the file they live in. You
cannot edit them: `preserves` is a promise about `history`'s output, and the
lift must leave both passing unedited. `revert` excludes a `preserves` witness
from the subset it re-runs. These two are the declared tests here that are not
asked to fail without their source.

**`blocker` and `concern` here are the spec review's words, and this spec coins
none**. They are defined for a spec review at
`.claude/agents/spec-reviewer.md:48-50`: "A **blocker** is a defect that, built
exactly as the spec says, gets a cell wrong. A **concern** needs the operator's
judgement". Check 4's four rules at `:86-99` are stated in them. They are not a
finding's `Severity`, which `CONTEXT.md:406-411` defines for a lens against a
diff and whose `blocker` "routes the task to REBUT". Nothing this command
prints routes anything, because it runs before a task exists. No term is new,
so no vocabulary follow-up is owed and `ontology/` stays `forbidden`.

**`check` is the subcommand name, and `SA-NNNN` its only argument**.
`uv run .claude/skills/run-saffron-spec-loop/driver.py check SA-0112`. Register
it beside `history` in `main` (`:1743-1747`). Load the target and the rows the
way `cmd_history` does at `:1631-1657`: `_known_specs()`, then
`_ledger_and_repo()`, then `_past_cells(...)` in a `try/finally` that closes
the ledger. `_fail` for a spec no file declares and for a repo with no ledger
row, exactly as `cmd_history` does at `:1644` and `:1648`.

**Judge the numbers, not the sentence**. Compute each verdict from the same
`(target, rows)` pair `_ceilings_line` renders from. Parsing the rendered line
back into numbers makes the words load-bearing twice. A later edit to the
line's prose would then move the verdict silently. That wording is fixed by the
assertions listed under "Out of scope".

**The row selection is shared, not copied**. `_history_lines` at `:1616-1621`
is where the same-type filter, the closeness sort and the `limit` cut live
today. Criterion 2 is that `check` judges that same list. Lift those lines into
one helper both call. A second copy is the reasoning `CLAUDE.md` gives for "One
module drives a task", in its small form: two selections that must agree and
nothing making them.

**What the concern needs**. The remainder is `budget_usd` minus the same
highest pre-REVIEW total the budget half of the line names, not minus some
other row's. It is compared against the highest `review_usd` plus `rebut_usd`
among those same rows. That is the worst case, the same convention both halves
of `_ceilings_line` already use (`:1576`, `:1593`). A row whose REBUT never ran
contributes its REVIEW cost alone. Say so in a comment of no more than two
lines, because a reader will otherwise read the maximum as a mean. A remainder
exactly equal to that cost *covers* it and draws no concern, and strictly less
is what "cannot cover" means. No criterion pins that edge, deliberately: a
concern costs an advisory line and never an exit status, so it does not earn a
sixth case in criterion 1's witness. Spell it in the code, so the next reader
does not have to derive it.

**The four new witnesses each drive the command**. Criteria 1, 3 and 4 are all
partly about the exit status. A helper returning a list of verdicts leaves
"`cmd_check` ignores what it was handed and returns 0" alive as a plausible
wrong implementation. So each witness calls `cmd_check` and asserts its return
value, and through `capsys` what it printed. The shape is
`driver.cmd_check(argparse.Namespace(spec_id=...))`, which
`tests/test_spec_loop_driver.py:805` and `:834` already use for `cmd_record`.

Hand it rows without a ledger. `monkeypatch.setattr` on `driver._past_cells`
returns a list built by `_cell(...)` at
`tests/test_spec_loop_driver.py:1121-1147`. The same on
`driver._ledger_and_repo` returns a three-tuple: a stub with a `close()`, a
repo id that is **not** `None`, and a url. `cmd_history` unpacks exactly those
three at `:1645` and `_fail`s on a `None` repo id at `:1647-1648`, which the
note above tells `check` to copy. A one-element stub raises. A `None` second
element makes every witness assert against "this repo has no ledger row yet"
instead of against a verdict. The target spec comes from `_spec(...)` at
`:1043-1052` through a monkeypatched `_known_specs`, or from a `SPECS_DIR` in
`tmp_path` the way `:1055-1065` does. Either is fine, and the ledger is not
what any of these four criteria is about. None of them asserts a status for a
spec no file declares or a repo with no ledger row. Those are `_fail`'s 1, and
they sit outside criterion 1's sentence. A witness asserting 0 for either would
contradict the `cmd_history` copy the note above asks for.

**Criterion 1's witness drives five ceilings against one set of rows**. Both
ceilings above, asserting 0 and no blocker. `max_turns` below the highest peak.
`max_turns` exactly equal to it. `budget_usd` below the highest pre-REVIEW
total. `budget_usd` exactly equal to that total, which is 0 and no blocker
again. Assert each blocker names which ceiling it is about, so a run that
blocks for the wrong reason is not read as the right answer.

**The two equality cases go opposite ways, and that is the whole of this
criterion**. `max_turns` level with the peak is a blocker. `budget_usd` level
with the total is not. `_ceilings_line` already renders the asymmetry, and its
comment at `:1578-1581` states it: "check 4's blocker is `max_turns` 'at or
below' the peak but `budget_usd` only 'below'". That is why the turns half is
three-way at `:1582-1585`. The budget half at `:1596` is
`"above" if budget_diff >= 0 else "below"`, printing "above by $0.00" on an
exact match. `.claude/agents/spec-reviewer.md:86-89` is the rule both follow.
Without the fifth case a `<=` on the budget half passes the other four. It then
reports a false blocker on any spec whose budget lands exactly on the
worst-case total. Without the third case a `<` on the turns half passes them as
easily, and `tests/test_spec_loop_driver.py:1297-1318` exists because that
threshold was read wrong once already.

**Build that row's spends in whole dollars**. The budget-equality case asks
whether `budget_usd` minus a *sum of floats* is exactly zero. Only then does
`:1596`'s `budget_diff >= 0` read as "above". This was measured on CPython
3.14.7, the host interpreter here. `_cell`'s own defaults happen to be safe:
`1.82 + 2.5 + 0.0` is exactly `4.32`, so a target at `4.32` reads "above by
$0.00". The neighbouring shapes are not safe. `1.1 + 2.2` is
`3.3000000000000003`, so a target at `3.3` reads *below* by `$0.00`. The case
then inverts into a false blocker the printed line cannot even show, because
both sides format to `$0.00`. Give that row `plan`, `implement` and `repair`
costs that are whole dollars, and set `budget_usd` to their sum. No other case
needs it. An equality is the only comparison a representation error can flip,
which is why criterion 3's remainders below can sit between dollars.

**Build the rows so the maxima are not the first of them**. At least three
rows. The highest peak sits on one and the highest pre-REVIEW total on another,
and neither of those two is first in the list. A `rows[0]` where the claim says
"the highest" passes all five cases otherwise. Criterion 2's witness cannot
kill it either, because its target clears every printed row, so `rows[0]` gives
the right answer there too.

One plain `def` for all five cases. `criteria` matches a bare node id against
the names the suite collected, by exact string. A `pytest.mark.parametrize`
test collects under a name no criterion can name (backlog item 159).

**Criterion 2's witness needs rows that would change the verdict if they were
judged**. Build the shape `tests/test_spec_loop_driver.py:1197-1214` already
builds. A cell of another type carries a peak far above the target's
`max_turns`. Fourteen same-type rows stand against the limit of twelve, and the
last of them, which the cut drops, carries such a peak too. Give the target
ceilings that clear every *printed* row, and `check` returns 0 and names no
blocker. Judging the unfiltered list is the wrong implementation this kills. It
is also the natural one to write, because `_past_cells` hands back every cell
in the ledger.

**Criterion 3's witness drives both directions too**. A remainder that cannot
cover the highest REVIEW-plus-REBUT among the rows draws the concern and still
returns 0. A remainder that covers it draws none. Without the second half, a
check that reports the concern unconditionally passes. `_cell` at `:1137-1143`
builds `budget_usd=6.0`, `review_usd=0.8` and `rebut_usd=0.0`. Set the fields
you need on the rows you build, as the ceilings tests at `:1186-1195` do.

**And its rows have to tell the three readings apart**. The quantity is the
highest `review_usd` *plus* `rebut_usd` on **one** row. It is not the highest
`review_usd` added to the highest `rebut_usd`, and not a mean of the sums. So
the row carrying the highest sum must be neither the row with the highest
`review_usd` nor the row with the highest `rebut_usd`. Three rows do it:
`$5.00` of REVIEW and no REBUT, no REVIEW and `$4.00` of REBUT, and `$3.00` of
each. The right answer is then `$6.00`, adding the two maxima gives `$9.00`,
and the mean of the three sums gives `$5.00`. Pick the two remainders so that
each direction also kills one wrong reading. About `$7.00` for the case that
covers it draws no concern under `$6.00` and a concern under `$9.00`. About
`$5.50` for the case that does not is a concern under `$6.00` and none under
`$5.00`. Criterion 1's rows are pinned two notes above for the same reason.
This criterion needs it more: its exit status is 0 in every case, so nothing
else here would notice.

**Criterion 4's witness is about what is *not* printed**. With no rows,
`_ceilings_line` at `:1573-1574` already returns "no past cells of this shape
to compare against". A `check` that prints it and returns 0 is not yet enough.
A reader who sees only an exit status reads it as a pass. So whatever sentence
`check` prints when a real comparison found no blocker must be absent here. The
witness asserts three things: the no-evidence line present, that sentence
absent, and the return value 0. Pick a clean-verdict sentence that is not a
substring of the no-rows line, or the second assertion cannot be written. The
status is 0 because `.claude/agents/spec-reviewer.md:98-99` calls this case "a
note, not a pass and not a blocker". A 1 here would make step 1b read every
spec of a shape no cell ran yet as a failing one. That is most of them after a
new gate or a new module lands.

**The shape is about 220 changed lines, and nothing here raises the tier**.
Neither file in `touches` is under `.saffron/policy.yaml:34-58`'s `elevate_on`.
So this task runs at `risk: standard`, where `size` is advisory against the
`feature` ceiling of 600 (`saffron/gates/core/size.py:25`). The `history` rows
for this shape read 155 to 515 changed lines for a comparable cell. The one
that exceeded the ceiling is `SA-0107` at 1049, a much larger change than this
one. One subcommand, one verdict helper, one lifted row selection and four new
tests is the whole of it. Do not go looking for more to do.

**Nothing under `.claude/` is scanned by `dead`**. Its roots are
`.saffron/gates/dead.py:21-29`, and none of them is this file, so a helper only
the new tests call is not reported. That is not licence to leave one, and
`check` is what calls the helpers this spec asks for.

**The prose gate counts comment runs and docstrings per file**. It blocks
(`.saffron/policy.yaml:25`), and it subtracts the base's failures, so a file
that gains a hit fails the attempt. Keep every comment to one or two lines, and
every docstring under ten, including `cmd_check`'s and the test module's.

**Load nothing new at module scope in the test file**.
`tests/test_spec_loop_driver.py:19-26` execs `driver.py` through
`importlib.util` at import time. That keeps working with `driver.py` reverted,
and a reverted run then fails on the missing attribute, which is what `revert`
needs to see. A module-scope `from ... import` of a name this change adds would
turn that run into a collection error. `revert` reads that error as `skip`, and
the anti-theater gate would then check nothing.

**Rename no existing test**. `census` compares collected names between base and
head and reads a rename as a removal. The four new tests belong beside the
ceilings tests at `tests/test_spec_loop_driver.py:1178-1352`.

Commit after each coherent step. Uncommitted work dies with the cell.
