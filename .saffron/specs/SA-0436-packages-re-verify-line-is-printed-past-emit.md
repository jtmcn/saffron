---
id: SA-0436
title: "PACKAGE's `re-verify:` line is printed past `emit`, so no caller can redirect it and `events.jsonl` never carries it"
type: bug
priority: 3
estimated_lines: 79
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/phases/package.py
  - tests/test_events.py
  - tests/test_package.py
  - tests/test_package_cell.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - tests/test_spec_loop_driver.py
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/cli.py
  - saffron/regate.py
  - saffron/task.py
  - saffron/finish.py
  - saffron/ledger.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/parent_versions.py
  - saffron/intake.py
  - tests/test_cli.py
  - tests/test_regate.py
  - tests/test_session.py
  - tests/test_task.py
  - tests/test_finish.py
  - tests/test_adopt_stack_layer.py
  - tests/test_ledger_fold_task.py
  - tests/test_witness_gate.py
  - tests/test_suite.py
  - tests/test_parent_versions.py
  - tests/test_report.py
  - tests/test_record_refs.py
  - tests/test_record_routed.py
  - tests/test_record_migrate.py
  - tests/test_stack_view.py
  - tests/test_intake.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 36
max_attempts: 3
max_turns: 150
renames:
  "tests/test_package.py::test_only_the_line_no_kind_carries_writes_to_a_stream_outside_emit": "tests/test_package.py::test_package_writes_to_a_stream_only_inside_an_emit"
acceptance:
  - claim: >-
      `reverify` takes an optional `emit`. Handed one, it hands each suite's
      line to that `emit` as a `PhaseStart` with phase `PACKAGE`, label
      `re-verify` and the spec's id, and prints nothing. Handed none, it
      prints each line, on every call. Each line reads `re-verify: baseline
      suite at <new_base_sha cut to 12>`, then `re-verify: head suite at
      <packaged_sha cut to 12>`, as at your base. The witness drives one call
      with an `emit` and two calls without one, with distinct shas, and
      compares every line whole.
    witness: tests/test_package.py::test_reverify_says_each_suites_line_through_emit_or_print
    positive_case: >-
      The two calls without an `emit` see both lines on stdout through the
      same `capsys` read, so the empty stdout after the call with an `emit`
      reads an instrument that does see the lines.
    wrong_versions:
      - "The `print` stays beside the new `emit` call, so a caller's `emit` gets the line and stdout gets it too."
      - "The event's label is `PACKAGE` and its detail starts `re-verify: `, so it renders as `PACKAGE: re-verify: ...`."
      - "The detail carries the whole sha rather than its first twelve characters."
      - "Both suites' lines name `packaged_sha`, so the baseline line names the head."
      - "The event's phase is `GATE`."
      - "Handed no `emit`, `reverify` emits nowhere, so `regate` and the finishing suite print nothing."
      - "Handed no `emit`, `reverify` prints the event's detail alone, without the `re-verify: ` label."
      - "The default `emit` is built once at import and prints only the first event it is handed."
    covers:
      - set: the suites `reverify` judges
        members:
          - member: the baseline suite at `new_base_sha`
            driven_by: "Both suites' lines name `packaged_sha`, so the baseline line names the head."
          - member: the head suite at `packaged_sha`
            driven_by: "The detail carries the whole sha rather than its first twelve characters."
      - set: the forms of a `reverify` call
        members:
          - member: handed an `emit`
            driven_by: "The `print` stays beside the new `emit` call, so a caller's `emit` gets the line and stdout gets it too."
          - member: handed none
            driven_by: "Handed no `emit`, `reverify` emits nowhere, so `regate` and the finishing suite print nothing."
      - set: the calls handed no `emit`
        members:
          - member: the first
            driven_by: "Handed no `emit`, `reverify` prints the event's detail alone, without the `re-verify: ` label."
          - member: a second, on the same input
            driven_by: "The default `emit` is built once at import and prints only the first event it is handed."
      - set: the fields of the event
        members:
          - member: "`phase`"
            driven_by: "The event's phase is `GATE`."
          - member: "`label`"
            driven_by: "The event's label is `PACKAGE` and its detail starts `re-verify: `, so it renders as `PACKAGE: re-verify: ...`."
          - member: "`spec_id`"
            driven_by: tests/test_package.py::test_reverify_says_each_suites_line_through_emit_or_print
  - claim: >-
      `package()` hands its `emit` to `reverify`. Driven with the real
      `reverify` behind it and an `emit` of the test's own, both suites'
      lines reach that `emit`. They name the fixture's base and the pushed
      head, each cut to 12.
    witness: tests/test_package.py::test_package_hands_its_emit_to_reverify
    wrong_versions:
      - "`package()` passes no `emit` to `reverify`, so both lines print and the caller's `emit` never sees them."
      - "`package()` hands `reverify` a print-only `emit` of its own."
      - "`package()` hands `reverify` its `emit` for the baseline suite alone."
    covers:
      - set: the suites `package()` re-verifies
        members:
          - member: the baseline suite at the fixture's base
            driven_by: "`package()` passes no `emit` to `reverify`, so both lines print and the caller's `emit` never sees them."
          - member: the head suite at the pushed head
            driven_by: "`package()` hands `reverify` its `emit` for the baseline suite alone."
  - claim: >-
      Handed no `emit`, `package()`'s own default carries both suites'
      lines into the task's `events.jsonl`, and prints each exactly once.
    witness: tests/test_package.py::test_package_with_no_emit_logs_and_prints_each_re_verify_line_once
    positive_case: >-
      The stdout read that counts each line once is the read that sees both
      lines, so the count is never taken over an empty capture.
    wrong_versions:
      - "`package()` passes no `emit` to `reverify`, so the lines print and the log never holds them."
      - "`package()` hands `reverify` a print-only `emit`, so the log never holds the lines."
      - "`reverify` prints beside the `emit` it is handed, so each line prints twice."
      - "`package()` hands `reverify` its `emit` for the baseline suite alone, so the head line never reaches the log."
    covers:
      - set: the suites `package()` re-verifies
        members:
          - member: the baseline suite at the fixture's base
            driven_by: "`package()` passes no `emit` to `reverify`, so the lines print and the log never holds them."
          - member: the head suite at the pushed head
            driven_by: "`package()` hands `reverify` its `emit` for the baseline suite alone, so the head line never reaches the log."
      - set: where the default sends each line
        members:
          - member: "`events.jsonl`"
            driven_by: "`package()` hands `reverify` a print-only `emit`, so the log never holds the lines."
          - member: stdout, once
            driven_by: "`reverify` prints beside the `emit` it is handed, so each line prints twice."
  - claim: >-
      The stream-write scan over `saffron/phases/package.py` exempts a
      function named `emit`, and no longer exempts `reverify`.
      It still finds no write.
    witness: tests/test_package.py::test_package_writes_to_a_stream_only_inside_an_emit
    positive_case: >-
      The witness first scans a four-line snippet whose `print` sits one
      function out from an `emit`, and sees that line reported. So the
      empty answer over `package.py` comes from a scan that finds prints.
    wrong_versions:
      - "`reverify` keeps its direct `print` of the line."
      - "`reverify`'s default sink is a nested function under another name that prints."
    covers:
      - set: the functions in `package.py` that may print
        members:
          - member: a function named `emit`
            driven_by: "`reverify`'s default sink is a nested function under another name that prints."
          - member: "`reverify`"
            driven_by: "`reverify` keeps its direct `print` of the line."
  - claim: >-
      `re-verify` is a `LineLabel` member. `FAMILIES` holds one row for the
      line, citing `reverify` in `saffron/phases/package.py` and the kind
      `PhaseStart`, and `FINDINGS` is empty.
    witness: tests/test_events.py::test_the_re_verify_line_is_a_typed_row_and_no_finding_is_left
    wrong_versions:
      - "`FINDINGS` keeps its `re-verify` entry beside the new row."
      - "The row cites `package` in that file rather than `reverify`."
      - "The label is spelled `RE_VERIFY` and `describe` gains a branch that lowers it."
    covers:
      - set: the tables that name the line
        members:
          - member: "`LineLabel`"
            driven_by: "The label is spelled `RE_VERIFY` and `describe` gains a branch that lowers it."
          - member: "`FAMILIES`"
            driven_by: "The row cites `package` in that file rather than `reverify`."
          - member: "`FINDINGS`"
            driven_by: "`FINDINGS` keeps its `re-verify` entry beside the new row."
---

## Context

Backlog item **43**, tier 2, partial. The item cites no section.
`saffron/events.py` names `DESIGN.md` §4.1, the log is §4.7's, and the
line is §5.7's re-verification. Every line below was read at `42107252`.

**The line.** `reverify` stands up a gate-only cell per suite in
`_gate_cell`. Each prints `re-verify: {label} suite at {sha[:12]}` with a
bare `print` (`saffron/phases/package.py:605`). The comment above it says
no `PhaseStart` label fits without widening `LineLabel`, and that
`events.py` was forbidden to the spec that wrote it
(`saffron/phases/package.py:599-604`). `reverify` takes no `emit`
(`saffron/phases/package.py:526-536`).

**The callers.** Three call `reverify`. `package()` holds an `emit`
(`saffron/phases/package.py:663`) and defaults it to a log that also
prints (`:687-694`). The call inside `package()` hands it nothing
(`saffron/phases/package.py:879-888`). `regate`
calls it with no `emit` (`saffron/regate.py:230-239`), and so does
`cli.py`'s finishing suite (`saffron/cli.py:1161-1169`). Both are
forbidden here, and both keep the printed line.

**The vocabulary.** `LineLabel` lists nine upper-case prefixes
(`saffron/events.py:88-98`). `describe` renders any `PhaseStart` as
`f"{label}: {detail}"` (`saffron/events.py:918-919`), so a `re-verify`
label renders today's line unchanged. `_shape_ok` checks a `Literal`
field's type and never its membership (`saffron/events.py:596-602`).
`FAMILIES` ends with the eight `PACKAGE:` rows
(`saffron/events.py:1140-1147`). `FINDINGS` holds one entry, this line
(`saffron/events.py:1153-1163`). `tests/test_events.py` pins 74 rows
(`:1535-1536`) and one finding (`:2093-2098`).

**The watcher.** `test_every_progress_line_the_cli_prints_reaches_the_watcher`
asserts the spec loop's watch pattern matches each `LineLabel` member
(`tests/test_spec_loop_driver.py:473-484`). At `42107252`,
`WATCH_PREFIXES` lacks `re-verify`
(`.claude/skills/run-saffron-spec-loop/driver.py:64-92`). A cell's file
tools refuse every path under `.claude` (`saffron/scheduler.py:25-28`). So this spec's own commit adds
`re-verify` to `WATCH_PREFIXES` by hand, and your base holds it. That
test stays green with the label added, and you edit neither file.
`cell-watch` reads `events.jsonl` and renders a `PhaseStart` as
`label: detail` (`.claude/skills/cell-watch/hooks/progress.ts:110-112`).
It gives a `Preflight` a fixed `preflight:` prefix (`:87-89`), which is
one reason this line is a `PhaseStart`.

**The scan.** `test_only_the_line_no_kind_carries_writes_to_a_stream_outside_emit`
allows stream writes inside `reverify` and inside any function named
`emit` (`tests/test_package.py:1658-1691`). Its docstring cites
`events.FINDINGS[1]`. So does the docstring of
`test_reverification_runs_the_suite_inside_a_cell`
(`tests/test_package_cell.py:24-34`).

## Problem

A caller that hands `package()` an `emit` still gets two lines it cannot
capture or silence, and the task's `events.jsonl` never holds them. Make
these changes.

1. **`events.py`.** Add `re-verify` to `LineLabel`, spelled as the line
   prints it. Add one `FAMILIES` row for the line, citing
   `phases/package.py:reverify` and `PhaseStart`. Empty `FINDINGS`, and
   keep the name. Reword the module docstring and `describe`'s docstring
   where they say one shape resists typing. `PhaseStart`'s docstring names
   the labels that differ from their phase (`saffron/events.py:200-203`).
   Add `re-verify:` to that list.
2. **`reverify`.** Give it an optional keyword `emit`, defaulting to
   `None`. Handed none, it builds a nested function named `emit` that
   prints `describe(event)`. Replace the `print` with one `emit` of a
   `PhaseStart`: phase `PACKAGE`, label `re-verify`, the spec's id, and
   the detail `f"{label} suite at {sha[:12]}"`. Drop the comment that
   explained the `print`.
3. **`package()`.** Pass its `emit` to `reverify`.
4. **The tests.** In `tests/test_events.py`, move the row count to 75 and
   say `SA-0436` moved it, and assert `FINDINGS` is empty. Rename the
   scan test to `test_package_writes_to_a_stream_only_inside_an_emit`, as
   `renames:` declares. Allow only `emit`, and drop the `FINDINGS[1]`
   paragraph from its docstring. Reword the `FINDINGS[1]` sentence in
   `tests/test_package_cell.py`'s docstring.

## Out of scope

- `regate` and the finishing suite in `cli.py` still print the line
  through `reverify`'s default. Neither holds a task's log. Both files are
  forbidden here.
- **Protected.** `.saffron/deadcode-allow.py` keeps `_.FINDINGS` with a
  comment naming `SA-0101` and `SA-0102` as open. That comment is stale
  and the entry stays needed. `CONTEXT.md` and `DESIGN.md` need no edit,
  since no event kind is added.
- Any other line in `package.py` or elsewhere.

## Notes for the agent

**Edit or new.** Every claim edits existing code, but the spelling of the
new `emit` call and its default is yours. No `find` written now pins it,
so no mutant is on the ref, and `witness` reports `skip` for each claim.

**Why a label and not a kind.** `PhaseStart` already carries a phase and
a free detail, and `describe` already renders `label: detail`. One
`Literal` member is the smallest widening. A new kind would cost a
dataclass, the union, `_KINDS` and a `describe` branch.
The `FINDINGS` note judged a lower-case label to carry no more than a free
string (`saffron/events.py:1157-1161`). Two things reverse it. `PLAN`,
`SALVAGE` and `SCOPE` already name no phase (`saffron/events.py:80-87`),
so only the casing sets `re-verify` apart. And the label carries the line
through `emit` into `events.jsonl` with its phase, which the free print
never did.

**The lambda exemption.** `_stream_writes` also shields any lambda, and
`package.py` holds no lambda at your base. The fourth claim leaves that
rule as your base tests it.

**Drive the real `reverify`.** `_stub_package_cells` stubs both gate
cells (`tests/test_package.py:228-264`). For the `package()` witnesses,
put the real `reverify` back over the `packageable` fixture's stub, as
`test_package_re_verifies_with_the_cells_revert_exemption` does
(`tests/test_package.py:1120-1144`). Drop `emit` from the fixture's
`kwargs` and pass your own or none. The pushed head is the remote's
`refs/heads/saffron/SA-0005`. The target branch's head is the fixture's
`base`. Replace `GateSuite.against` with one that returns a clean
comparison, as that test does. Measured on a prototype: left real, the
head suite's core gates shell out to the cell runtime, and the test
harness refuses the call. Both lines precede the suites, so the stub
hides neither.

**`regate` and the finishing suite.** Their lines carry phase `PACKAGE`
too, and only ever print. Neither caller is in scope.

**The scan's other spellings.** `_stream_writes` also flags `write`,
`writelines` and an attribute `print` (`tests/test_package.py:1629-1639`).
The fourth claim drives only the dropped exemption. The other spellings
stay as your base tests them.

**`capsys` before each call.** Read it empty first, so lines from the
fixture's own setup never count.

**No `retired_first`.** Nothing here adds or widens a refusal.
