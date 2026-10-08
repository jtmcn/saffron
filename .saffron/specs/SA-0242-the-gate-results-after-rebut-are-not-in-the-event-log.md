---
id: SA-0242
title: The gate results after REBUT are not in the event log, so a red rebuttal names no gate
type: bug
priority: 2
depends_on: [SA-0235]
estimated_lines: 176
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/events.py
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
  - images/**
  - records/**
  - hooks/**
  - saffron/ledger.py
  - saffron/record/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/watch.py
  - saffron/view/**
  - saffron/projection.py
  - saffron/cli.py
  - saffron/task.py
  - saffron/batch.py
  - tests/test_events.py
  - tests/fixtures/**
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 21
max_attempts: 4
max_turns: 120
acceptance:
  - claim: >-
      A green re-run after REBUT writes one `GateResult` event to
      `events.jsonl` for each gate in its suite, each with `against` set to
      `rebuttal`. Each carries the number the REBUT `Attempt` line carries,
      and no `attempt` event carries that number. Each count follows the repair loop's rule. A blocking gate that did not
      skip carries its count of new failures, so a passing one carries zero.
      A blocking gate failing identically at base also carries zero. An
      advisory gate and a skipped gate carry none. Every such event sits
      after the loop's last GATE `Attempt` and before the REBUT `Attempt`. The
      REBUT line still reads `gates: 0 new failures after the rebuttal` and
      names no gate.
    witness: tests/test_session.py::test_a_green_rebuttal_re_run_logs_each_gate_result_against_the_rebuttal
    wrong_versions:
      - The rebuttal's events carry `against` set to `attempt`.
      - The re-run writes its set twice, once under `attempt` and once under `rebuttal`.
      - The rebuttal's events carry no attempt number, or the loop's last number rather than the REBUT line's.
      - A passing blocking gate carries no count rather than a measured zero.
      - A gate's count is its raw failure count, so a gate failing identically at base carries 1.
      - An advisory or skipped gate carries a count of zero.
      - The events are emitted after the REBUT `Attempt` line.
      - The green line gains a trailing separator or an empty list of names.
  - claim: >-
      A red re-run after REBUT names, on its own REBUT `Attempt` line, each
      gate that contributed a new failure, once. It names no gate that
      contributed none. The line is the event's own `describe` text read back
      from `events.jsonl`, which is what `saffron watch` prints. The witness
      drives a re-run with one new-failing gate and one with two. Each run
      also carries a gate failing identically at base and a passing gate.
      Each failing gate's own `GateResult` event carries `against` set to
      `rebuttal`, the status `fail` and its own count.
    witness: tests/test_session.py::test_a_red_rebuttal_line_names_each_gate_that_failed_anew
    wrong_versions:
      - The names go out on a separate line, or into REBUT's `PhaseStart` text, and the `Attempt` event carries none.
      - The names come from every gate whose status is `fail`, so a gate failing identically at base is named.
      - Only the first new failure's gate is named, so the second of two is missing.
      - A gate with two new failures is named twice.
      - The line names the gates but the count before them is dropped.
      - Each failing gate's event carries the count of the whole suite rather than its own.
  - claim: >-
      A re-run after REBUT whose suite aborted, or drifted, still writes one
      `GateResult` event per gate with `against` set to `rebuttal`. An
      errored gate keeps the status `error`, never `fail`. No gate in either
      suite carries a count, and the task ends `GATE_ERROR`. The drifted
      suite's events name exactly the gates in the head's results, a gate
      the baseline lacks included.
    witness: tests/test_session.py::test_an_errored_or_drifted_rebuttal_re_run_logs_each_gate_with_no_count
    wrong_versions:
      - The count is withheld only from the errored gate, so the failing gate in the aborted suite carries a count.
      - An errored gate is written with the status `fail`.
      - An aborted or drifted re-run writes no `GateResult` events at all.
      - The drifted re-run's events are taken from the baseline's gates, so a gate only the head ran is missing.
  - claim: >-
      The repair loop's own suites still emit `GateResult` events with
      `against` set to `attempt`, each set with its own number and count.
    witness: tests/test_session.py::test_each_attempts_gate_results_carry_their_own_attempt_number
    preserves: true
  - claim: >-
      The repair loop's `gates: attempt N, K new failures -> decision` line
      reads exactly as it did for the decisions `green`, `repair` and
      `no-progress`, with a failing gate named on no GATE line.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
---

## Context

Backlog item b-66e82d, from the spec loop's run 13. `SA-0118`'s log read
`gates: 1 new failures after the rebuttal` and then `EXHAUSTED`. No event in
`events.jsonl` named the failing gate. Finding it (`revert`, item b-4a63b7)
took re-running every gate by hand. The same gap recurred in runs 15, 18
and 19.

§5.6 says the rebuttal diff and the failing gate "are both kept for you to
read". The ledger keeps the gate. The event log does not.

**Where the re-run is judged.** `_rebut_gates` (`saffron/cell/session.py:3027-3044`)
calls `_judge()` with no argument at `:3031`. It then emits one `Attempt` through
`attempt_event` at `:3034-3041`, with `phase="REBUT"` and the number
`attempts + 1`.

**When the re-run happens.** `run_rebut` calls `rerun_gates()` after the rebuttal
and its extraction turn, and before any verdict (`saffron/phases/rebut.py:716`).
The cap's `EXHAUSTED` is decided only after `run_rebut` returns. So under
`SA-0231`, a cap cut after HEAD moved still logs green rebuttal events before
`EXHAUSTED`.

**Why that call emits no gate events.** `_judge` (`saffron/cell/session.py:2529`)
writes every gate result to the ledger. It emits per-gate events only inside
`if attempt is not None:` at `:2557`. The comment at `:2555-2556` gives the reason.
It says `_rebut_gates` calls `_judge()` bare, because the rebuttal value of
`against` has no owner yet (item 160). Only `repair_loop` passes a number, as
`judge(attempt)` at `:762`.

**The value already exists.** `GateResult.against` in `saffron/events.py:252` is
`Literal["baseline", "attempt", "rebuttal"]`. `tests/test_events.py:496-512`
round-trips all three. Nothing emits the third. It is a type literal, not a
vocabulary closed set: `tests/ontology/test_vocabulary_agrees_with_context.py:22-34`
lists the closed sets, and no `against` set is among them.

**The number is CONTEXT.md's.** "Attempt" in `CONTEXT.md:241-245` says the suite
re-run after REBUT continues the repair loop's count. After a loop that reached 2,
that re-run is attempt 3, labelled REBUT. So a rebuttal event carrying that number
borrows nothing.

**What the REBUT line says now.** `describe` renders an `Attempt` with a count and
no decision as `new failures after the rebuttal`, after the count
(`saffron/events.py:779-792`). The `Attempt` kind (`:205-235`) carries a count and
no gate name. `attempt_event` (`saffron/cell/session.py:687-730`) builds it from
`len(comparison.new_failures)`.

**What the GATE line says now.** The same branch renders a counted `Attempt` with
a decision as `gates: attempt N, K new failures -> decision` (`saffron/events.py:779-790`).
The golden fixture pins it with a failing lint gate.
`tests/fixtures/watch-golden.txt:62` reads `gates: attempt 1, 1 new failures -> repair`.
`tests/fixtures/watch-golden.txt:70` reads `gates: attempt 2, 1 new failures -> no-progress`.

## Problem

- **A red rebuttal names no gate.** The `EXHAUSTED` it causes is the most
  informative failure §5.6 describes, and the log gives a count only.
- **The repair loop's suites are logged gate by gate, and REBUT's is not.** The
  per-gate events `SA-0102` added stop at the loop.
- **`saffron watch` inherits the gap.** It prints `describe(event)` for every
  event it does not drop as noise (`saffron/watch.py:115`).

## Out of scope

**Item 160, the ledger row.** `_judge` keeps calling `record_gate_result` for the
re-run under the rebuttal's extraction turn (`saffron/cell/session.py:2537-2554`). No ledger
schema changes, and `saffron/ledger.py` is forbidden. This spec changes events only.
Item 160's record says the post-rebuttal suite emits no `GateResult`. The operator
updates that record and closes b-66e82d after merge, since `docs/**` is forbidden.

**The GATE line.** It keeps its exact text. Criterion 5 holds it. The per-gate
events with counts already say which gate failed in an attempt.

**`describe`'s `GateResult` branch.** It renders `gates: {gate}={status}` whatever
`against` holds (`saffron/events.py:797-800`). Only position tells a rebuttal's
from an attempt's, which criterion 1 pins. Its two-line comment names only the
baseline and attempt suites, so update that comment. Leave the rendered text alone.

**No new event kind and no new vocabulary.** `CONTEXT.md` and `ontology/` need no
edit.

## Notes for the agent

**This change is new behaviour on an existing path.** Criteria 1 to 3 declare a
witness and no mutant. Their spelling at head is yours, so expect `witness` to
report `skip` for them. Criteria 4 and 5 are `preserves`, and both tests exist.

**Parallel specs edit `saffron/cell/session.py` near here.** Keep this diff inside
`attempt_event`, `_judge`, the body of `_rebut_gates`, and the `judge=` argument
of the `repair_loop` call. Leave the REBUT cap code alone: the
`cap = _RebutCap(...)` line and the `if cap is not None:` block after
`run_rebut` returns. Leave `_over_budget` alone too.

**Pass the re-run's number and `against` explicitly.** Thread both from
`_rebut_gates` into `_judge`. Make `against` a required keyword on `_judge`, with
no default, for the reason `GateResult.against` gives at `saffron/events.py:250-252`.
Hand `repair_loop` `functools.partial(_judge, against="attempt")`, since it calls
`judge(attempt)` with one argument (`saffron/cell/session.py:762`). The count rule
is the one at `saffron/cell/session.py:2558-2571`, and the re-run reuses it rather
than copying it. Rewrite the comment at `:2555-2556`, which becomes false.

**Add no `FAMILIES` row.** `tests/test_events.py:1241-1242` pins
`len(FAMILIES) == 70`, and that file is forbidden. If the red REBUT line's shape
changes, edit the existing row at `saffron/events.py:946` in place.

**The gate names travel on the REBUT `Attempt` event itself.** `describe` reads one
event. A name list printed elsewhere never reaches a reader of the line, and
criterion 2's witness reads the event back from `events.jsonl`. A new field on
`Attempt` needs a default, so an older log still parses (`_parse_line`,
`saffron/events.py:504-544`). Derive the names from `comparison.new_failures`,
never from statuses. Render them on the REBUT branch only. The green REBUT line
stays byte-identical, and so does every GATE line.

**`tests/test_events.py` is forbidden.** Its describe table already pins the green
REBUT line (`:1028-1039`). A new row there constructs a field the change adds at
module scope. `revert` then reads a collection error as `skip`.

**Drive each witness through a whole cell, with `use_default_emit=True`.** That
path writes a real `events.jsonl` under `tmp_path / "out" / "SY-1"`. Read it with
`read_log`, imported inside the test body, as `_task_outcome` does (`tests/test_session.py:5800`).
`_rebuttable` and `_through_rebut` set up REBUT, as
`test_the_gate_check_after_the_rebuttal_continues_the_gate_count` does at `:5106`.
Use `rebut_commits=1` and a `fixed` rebuttal, or the re-run never happens. Share
one `_`-prefixed helper across the three, and prefix every other helper too. A new
test that passes with the source reverted fails `revert`.

**Keep the shared helpers' signatures.** The forbidden `tests/test_events.py:49-60`
imports `_drive`, `_results`, `_spec`, `_stub_the_runtime`, `_turn` and `_block`
from `tests/test_session.py`. Change none of their signatures.

**Criterion 3's drifted drive gains a gate.** Its events come from the head's
results (`saffron/cell/session.py:2565`). `suite_drift` skips a gate only the
head ran (`saffron/gates/baseline.py:67-89`). So add one passing gate to the
head's suite that the baseline lacks, and assert it is among the events.

**Gate names in the witnesses.** `_results` builds only `lint`. Build the others as
`GateResult` values directly. For criterion 2, a `prose` failing identically at base
and at the re-run reproduces run 19's case. Use two new-failing gates whose names
appear nowhere else in the line, such as `lint` with two failures and `dead` with one.

**Criterion 1's position check.** Index the read-back log. Every `rebuttal` event's
index lies after the last `Attempt` with phase `GATE` and before the one with phase
`REBUT`.

**Criterion 4's witness never reaches the re-run.** Its docstring says the
post-rebuttal re-run "emits nothing" (`tests/test_session.py:5180-5184`). On the
prototype below, a re-run emitting under `attempt` still passed it. Its turn
script at `:5191-5200` scripts three lens turns. REVIEW runs four, as
`_through_rebut` at `:3935` scripts them. Criterion 1's witness is the one that
holds the `attempt` set to the loop's own numbers. Correct that one docstring
sentence, and leave criterion 4's assertions alone. `census` compares test names,
so rename nothing.

**Measured on a prototype.** A diff built to this spec at base measured 701
changed tokens on `size_gate`, against the `bug` ceiling of 1300. It added 160
lines and removed 35. The three new witnesses failed with the source reverted.
Every wrong version listed under criteria 1 to 3 ran against its witness, and each
failed it. So did a GATE line that names its gates, against criterion 5's.

**`error` is not `fail`.** Carry each gate's contract status through unchanged.

Commit after each coherent step. Uncommitted work dies with the cell.
