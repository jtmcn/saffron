---
id: SA-0426
title: "A gate failure has no field for its reason outside its identity, so a failed test reaches a writer and a repair turn as its node id alone"
type: bug
priority: 2
estimated_lines: 35
estimate_measured: true
touches:
  - saffron/gates/contract.py
  - saffron/gates/baseline.py
  - saffron/record/migrate.py
  - saffron/report/pr_body.py
  - tests/test_contract.py
  - tests/test_baseline.py
  - tests/test_saffron_gates.py
  - tests/test_record_migrate.py
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
  - saffron/gates/core/**
  - saffron/gates/runner.py
  - saffron/gates/suite.py
  - saffron/record/fold.py
  - saffron/record/contract.py
  - saffron/record/refs.py
  - saffron/record/memory.py
  - saffron/record/routed.py
  - saffron/view/**
  - saffron/ledger.py
  - saffron/finish.py
  - saffron/task.py
  - saffron/events.py
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - tests/test_cli.py
  - tests/test_task.py
  - tests/test_events.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_finish.py
  - tests/test_implement.py
  - tests/test_ledger.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 64
max_attempts: 3
max_turns: 290
acceptance:
  - claim: >-
      A gate failure carries an optional `detail` string. `parse_gate_json`
      reads it from a failure that names one, and a failure that omits it
      reads as the empty string. A failure's JSON dump carries a non-empty
      `detail` and leaves the key out when it is empty, alone and inside its
      `GateResult`'s dump. The witness parses one failure with a detail and
      one without, and reads each one's attribute, its own dump and the
      result's dump.
    witness: tests/test_contract.py::test_a_failures_detail_parses_and_defaults_to_empty
    positive_case: >-
      The failure that names a detail dumps it under `detail`, through the
      same `model_dump(mode="json")` call that shows the other failure's
      dump without the key.
    wrong_versions:
      - "`Failure` declares `detail` but a hook after validation sets it back to empty."
      - "`detail` is typed `str | None` with a `None` default, so an omitted detail reads as `None`."
      - "`detail` is a plain field, so every failure's dump gains a `detail` key."
      - "`detail` is excluded from every dump, so a failure's dump never carries it."
      - "`Failure` overrides `model_dump` to drop an empty detail, so a `GateResult`'s dump still carries `\"detail\": \"\"`."
    covers:
      - set: a failure's JSON as a gate emits it
        members:
          - member: naming a `detail`
            driven_by: "`Failure` declares `detail` but a hook after validation sets it back to empty."
          - member: omitting `detail`
            driven_by: "`detail` is typed `str | None` with a `None` default, so an omitted detail reads as `None`."
      - set: where the parsed detail is read
        members:
          - member: the failure's attribute
            driven_by: tests/test_contract.py::test_a_failures_detail_parses_and_defaults_to_empty
          - member: the failure's JSON dump, non-empty
            driven_by: "`detail` is excluded from every dump, so a failure's dump never carries it."
          - member: the failure's JSON dump, empty
            driven_by: "`detail` is a plain field, so every failure's dump gains a `detail` key."
          - member: the failure inside its `GateResult`'s JSON dump
            driven_by: "`Failure` overrides `model_dump` to drop an empty detail, so a `GateResult`'s dump still carries `\"detail\": \"\"`."
  - claim: >-
      `identity` never reads `detail`. Two failures alike but for their
      detail share one identity. `subtract_baseline` cancels a head failure
      against a baseline failure that differs only in detail, and
      `is_no_progress` reads two such new-failure lists as no progress.
      The witness gives the two a detail each with no digits, so
      `normalize_message` cannot make them equal. The one failure that
      survives the subtraction keeps its own detail.
    witness: tests/test_baseline.py::test_failures_differing_only_in_detail_share_one_identity
    positive_case: >-
      A head failure with its own file and code is not cancelled, and the
      same `subtract_baseline` call returns it with its detail.
    wrong_versions:
      - "`identity` adds the normalized detail to the normalized message."
      - "`subtract_baseline` cancels a head failure only when its detail matches the baseline failure's."
      - "`is_no_progress` counts each new failure by its identity and its detail."
    covers:
      - set: the readers of a failure's identity in `baseline.py` and `contract.py`
        members:
          - member: "`identity`"
            driven_by: "`identity` adds the normalized detail to the normalized message."
          - member: "`subtract_baseline`"
            driven_by: "`subtract_baseline` cancels a head failure only when its detail matches the baseline failure's."
          - member: "`is_no_progress`"
            driven_by: "`is_no_progress` counts each new failure by its identity and its detail."
  - claim: >-
      `render` appends ` - ` and the detail to the line it renders, on that
      same line, when the detail is non-empty. An empty detail renders the
      line exactly as your base does. The witness compares whole strings for
      each of the three location forms `render` prints: a file and a line, a
      file with no line, and no file. It does so once with a detail and once
      without.
    witness: tests/test_baseline.py::test_render_ends_a_failures_line_with_its_detail
    positive_case: >-
      Each location form with a non-empty detail renders with ` - ` and the
      detail at its end, through the same `render` call that renders the
      empty case unchanged.
    wrong_versions:
      - "`render` renders the failure as your base does and drops the detail."
      - "`render` puts the detail on a following line."
      - "`render` always appends ` - `, so an empty detail ends the line with the separator."
      - "`render` appends the detail only for a failure that names a file."
    covers:
      - set: the location forms `render` prints
        members:
          - member: a file and a line
            driven_by: tests/test_baseline.py::test_render_ends_a_failures_line_with_its_detail
          - member: a file with no line
            driven_by: tests/test_baseline.py::test_render_ends_a_failures_line_with_its_detail
          - member: no file
            driven_by: "`render` appends the detail only for a failure that names a file."
      - set: the detail
        members:
          - member: non-empty
            driven_by: "`render` renders the failure as your base does and drops the detail."
          - member: empty
            driven_by: "`render` always appends ` - `, so an empty detail ends the line with the separator."
  - claim: >-
      A `tests` gate failure parsed from a `FAILED` line, or from an `ERROR`
      line naming a node id, carries pytest's reason as `detail`, as pytest
      prints it at 400 columns. Its `message` is that line with no ` - `
      reason. The witness calls the gate with
      `COLUMNS=80` in its environment over three tests in one file. One
      fails with a node id too long for its reason to fit 80 columns, one
      fails with a short node id, and one errors in its fixture's setup.
    witness: tests/test_saffron_gates.py::test_the_tests_gate_carries_pytests_reason_as_a_failures_detail
    positive_case: >-
      Each of the three failures carries its reason in `detail`, read from
      the same parsed failure whose `message` ends at the node id.
    wrong_versions:
      - "`Failure` declares `detail` but a hook after validation sets it back to empty."
    covers:
      - set: the summary lines the gate parses
        members:
          - member: a `FAILED` line
            driven_by: tests/test_saffron_gates.py::test_the_tests_gate_carries_pytests_reason_as_a_failures_detail
          - member: an `ERROR` line for a node id
            driven_by: tests/test_saffron_gates.py::test_the_tests_gate_carries_pytests_reason_as_a_failures_detail
      - set: the reason's fit at 80 columns
        members:
          - member: it fits
            driven_by: tests/test_saffron_gates.py::test_the_tests_gate_carries_pytests_reason_as_a_failures_detail
          - member: it does not fit
            driven_by: tests/test_saffron_gates.py::test_the_tests_gate_carries_pytests_reason_as_a_failures_detail
  - claim: >-
      A finish still writes each new failure's dump into its suite
      comparison with exactly the keys it has at your base, for a failure
      whose detail is empty.
    witness: tests/test_cli.py::test_a_finish_writes_its_suite_comparison_beside_its_findings
    preserves: true
  - claim: >-
      `saffron migrate`'s top-up sets aside each failure's `detail` in a
      `gate_result` fact, since no ledger row stores it. The witness records a
      failing gate result through a `Ledger` writing to a live record. One
      failure carries a detail and one does not, and the held fact keeps the
      first's detail. `migrate` over that record migrates the task, refuses
      nothing and appends nothing. The same `migrate` still refuses a held
      fact whose failure's message differs from its row.
    witness: tests/test_record_migrate.py::test_a_live_gate_results_failure_detail_is_set_aside
    positive_case: >-
      A held fact whose failure carries a differing message is refused,
      through the same `migrate` call and the same `the record holds N
      fact(s) that disagree` reason.
    wrong_versions:
      - "`_normalized` compares a `gate_result` fact's failures as your base does."
      - "`_normalized` drops a failure's `detail` only when it is empty."
      - "`detail` joins the four top-level `gate_result` keys set aside, which no failure's own key reaches."
      - "`_normalized` sets aside every key of every failure, so a differing message agrees."
    covers:
      - set: the held fact's failures
        members:
          - member: a failure carrying a detail
            driven_by: "`_normalized` drops a failure's `detail` only when it is empty."
          - member: a failure carrying none
            driven_by: tests/test_record_migrate.py::test_a_live_gate_results_failure_detail_is_set_aside
      - set: what the top-up decides
        members:
          - member: agrees and gains nothing
            driven_by: "`detail` joins the four top-level `gate_result` keys set aside, which no failure's own key reaches."
          - member: disagrees and is refused
            driven_by: "`_normalized` sets aside every key of every failure, so a differing message agrees."
  - claim: >-
      A pull request body's new-failure tables end each row's message with
      ` - ` and the failure's detail when it is non-empty. The detail is
      escaped as the message is, and an empty detail leaves the row as your
      base renders it. The witness renders one body with a blocking failure
      whose detail holds a pipe, a blocking failure with no detail, and an
      advisory failure with a detail, and compares each row whole.
    witness: tests/test_report.py::test_a_new_failures_row_ends_its_message_with_its_detail
    positive_case: >-
      The blocking and the advisory rows with a detail end with ` - ` and
      their detail, in the same body whose row with no detail ends at its
      message.
    wrong_versions:
      - "`_failure_rows` renders each row as your base does and drops the detail."
      - "`_failure_rows` appends the detail outside `_cell`, so its pipe splits the row."
      - "`_new_failures` hands the advisory table its failures with the detail cleared."
      - "`_failure_rows` always appends ` - `, so a row with no detail ends with the separator."
    covers:
      - set: the tables `_failure_rows` builds
        members:
          - member: the blocking new-failure table
            driven_by: "`_failure_rows` renders each row as your base does and drops the detail."
          - member: the advisory new-failure table
            driven_by: "`_new_failures` hands the advisory table its failures with the detail cleared."
      - set: the detail
        members:
          - member: non-empty, holding a pipe
            driven_by: "`_failure_rows` appends the detail outside `_cell`, so its pipe splits the row."
          - member: empty
            driven_by: "`_failure_rows` always appends ` - `, so a row with no detail ends with the separator."
---

## Context

Backlog item **b-18fa39**, filed from the spec loop's finish 103. It cites
`DESIGN.md` §5.4. Every line below was read at `a55e55ce`. Your base adds
only the two hand edits the notes describe, outside every file cited here.

**The failure model.** `Failure` holds `file`, `line`, `code` and `message`
(`saffron/gates/contract.py:45-58`). It sets no `extra` policy, so pydantic
ignores a key it does not declare. `parse_gate_json` validates a gate's
stdout into a `GateResult` (`saffron/gates/contract.py:145-147`).

**The identity.** `identity` returns the gate, the file, the code and the
normalized message (`saffron/gates/contract.py:131-142`). `normalize_message`
collapses each span of digits to `N` and each span of whitespace to one space
(`saffron/gates/contract.py:122-128`). `subtract_baseline` counts identities
through `_cancelling` (`saffron/gates/baseline.py:46-52`, `:55-75`).
`is_no_progress` compares the two lists' identity counts
(`saffron/gates/baseline.py:122-134`).

**The render.** `render` prints `[gate] file:line code: message`. It prints
`?` for a missing line and no location for a failure with no file
(`saffron/gates/baseline.py:25-33`). Each of its six callers puts one
rendered failure on one line.

- `implement.py` writes each into a repair turn as one `- ` bullet
  (`saffron/phases/implement.py:200`).
- `finish.judge_draft` returns them to the follow-up writer
  (`saffron/finish.py:294`).
- `finish.publish_finish` prints each through `events._clean`
  (`saffron/finish.py:519-521`).
- `package.py` prints each on a line of its own
  (`saffron/phases/package.py:901-902`).
- `session.py` puts each into an event, twice
  (`saffron/cell/session.py:847`, `:3140-3144`). `_with_failures` prints an
  event's failures one per line through `_clean`
  (`saffron/events.py:597-601`).

`_clean` maps every control character to a space
(`saffron/events.py:751-762`). A newline inside a rendered failure would
read as a space there, and would split a repair turn's bullet.

**What dumps a failure.** `finish.write_verify_comparison` writes each new
failure's `model_dump(mode="json")` (`saffron/finish.py:471-474`).
`tests/test_cli.py:14851-14854` pins that list with exactly the keys
`gate`, `file`, `line`, `code` and `message`. `Ledger` writes a gate
result's dump into its `gate_result` fact (`saffron/ledger.py:2411-2416`).
The fold reads each failure's keys by name and ignores the rest
(`saffron/ledger.py:978-984`).

**The top-up.** `saffron migrate` derives each `gate_result` fact from
ledger rows. `_failure_payload` writes `file`, `line`, `code` and `message`
and no `detail` (`saffron/record/migrate.py:332-338`). The top-up compares a
held fact with its derived twin through `_agrees`
(`saffron/record/migrate.py:104-113`). `_normalized` sets aside
only four top-level keys of a `gate_result` (`saffron/record/migrate.py:83-101`).
A held fact whose failure carries a detail therefore disagrees, and the task
is refused (`saffron/record/migrate.py:224-228`).

**The pull request body.** `_failure_rows` builds the
`gate | where | code | message` rows, and its message cell is
`failure.message` alone (`saffron/report/pr_body.py:256-273`). `_new_failures`
calls it for the blocking table and the advisory one
(`saffron/report/pr_body.py:292`, `:306`). `_cell` escapes a pipe, turns a
newline into a space and defangs a mention (`saffron/report/pr_body.py:153-164`).

## Problem

A failed test reaches a writer, a repair turn and a finish's log as its node
id alone. The `tests` gate now sends each failure's reason in a `detail`
key, as the notes describe, and `Failure` drops it. Make these changes.

1. **`Failure` declares `detail`.** A string, defaulting to empty. Leave it
   out of a dump when it is empty, so a failure without one dumps the keys it
   dumps at your base. Pydantic 2.13's `Field` takes `exclude_if`.
2. **`identity` stays as it is.** It never reads `detail`, so assertion
   text that varies between base and head still cancels.
3. **`render` appends the detail.** A non-empty detail follows the message
   after ` - `, on the same line. An empty detail adds nothing. One line,
   because each reader above puts one rendered failure on one line. The
   ` - ` separator is pytest's own.
4. **The top-up sets the detail aside.** `_normalized` drops `detail` from
   each failure of a `gate_result` payload, on both sides of the compare.
   `_failure_payload` stays as it is. Keep `_normalized`'s docstring naming
   the four top-level keys, since
   `test_the_normalized_docstring_counts_every_set_aside_gate_result_key`
   reads that count.
5. **The body's tables show the detail.** `_failure_rows` joins a non-empty
   detail to the message after ` - `. The join sits inside the one `_cell`
   call, so the detail is escaped as the message is. The same separator as `render`, so a
   reader sees one shape in a log and in a body.

## Out of scope

- **Storing the detail in the ledger.** The `failures` table has no column
  for it (`saffron/ledger.py:983`), and both readers build a `Failure`
  without it (`saffron/ledger.py:2478-2486`, `saffron/record/migrate.py:266-275`).
  Every `render` caller above, and `_failure_rows`, reads a suite's own
  comparison, parsed from the gate's stdout. A `gate_result` fact does
  carry a non-empty `detail` in its dump, and the fold ignores it.
- **The view's failure table.** `saffron serve` reads failures from the
  ledger's own rows (`saffron/view/server.py:706-714`), and the fold drops
  the detail. Its table keeps showing the message alone.
- **`DESIGN.md` §5.4's gate contract example.** It shows four failure keys
  and already leaves out `collected`, `uncollected` and `locations`.
- **Every other gate.** None sends a `detail`, so each failure keeps its
  render and its dump.

## Notes for the agent

**The `tests` gate is amended by hand at your base.** `.saffron/**` is
forbidden here, and the operator edited `.saffron/gates/tests.py` in this
spec's pull request. Its test-session `subprocess.run` call now sets
`COLUMNS` to 400 in pytest's environment. Its `failures` comprehension now
splits each `FAILED` or `ERROR` line at the first ` - `. The part before is
`message` and the part after is `detail`. Your base's `Failure` ignores the
new key, so that edit is safe before yours lands. Criterion 4's witness
calls the amended gate as a subprocess. Do not edit the gate.

**`GATES.md` is amended by hand at your base too.** `.claude/**` is
forbidden here. The operator added a contract bullet to
`.claude/skills/setup-saffron/GATES.md`, saying `detail` is optional and the
baseline never matches on it.
`tests/test_setup_saffron.py::test_gates_md_names_every_contract_field`
requires that file to name every `Failure` field, so it passes at your base
and stays green once `detail` exists.

**Why `COLUMNS`.** pytest fits each `FAILED` line in its short summary to
the terminal width, 80 under captured output. A node id that leaves no room
drops the ` - ` reason, and a shorter one keeps it, cut to fit. Measured on
the host with pytest 9.1.1 on 2026-11-22. At 400 columns the line kept its
reason whole. The cell image's pytest is not measured, and the witness
calls whichever pytest the gate finds.

**What criterion 4 leaves out.** No witness drives three other failures
the gate emits. A file's `ERROR` line, kept only under a handed subset,
splits the same way. A handed name that could not be collected, and the
`KeyboardInterrupt` failure, each carry a fixed message and no detail.

**What `message` holds.** Before the hand edit, `message` was the whole
summary line. A short node id's line carried its reason, and a long one's
did not. Now `message` is always the line with no reason, so every
identity the gate reports drops the assertion text. A pull request body's
table showed a short node id's reason through `message`. Step 5 brings it
back through `detail`. Base and head each call
the same amended gate inside one task, so a baseline still cancels.

**Edit or new.** Each criterion edits existing code. Five mutants on the
ref pin text that exists at your base and survives the change, in
`contract.py`, `baseline.py`, `migrate.py` and `pr_body.py`. Criterion 4's
witness shares criterion 1's mutant. The `preserves` witness exists at your
base and passes there.

**The witnesses.**

- Criterion 2: give the two details no digits, since `normalize_message`
  collapses each span of digits, so two details of digits alone would match.
  Keep the assertion that the surviving failure holds its own detail. At
  your base `Failure` ignores `detail`, so the identity and subtraction
  halves pass there unchanged. That assertion is what fails at your base,
  as `criteria` requires. It also catches a subtraction that hands back the
  baseline's failure, or a copy without its detail.
- Criterion 4: copy the shape of
  `test_a_warning_a_failing_test_prints_leaves_every_failure_keyed_on_its_node_id`
  (`tests/test_saffron_gates.py:323-355`). Pass `COLUMNS=80` in the
  subprocess's environment, so a gate that left the width alone would lose
  the long node id's reason. Compare each failure's `message` and `detail`
  whole, keyed by its code.
- Criterion 6: build the `Ledger` over a `MemoryRecord`, as
  `test_a_live_ref_whose_rebut_reached_no_verdict_and_no_rebuttal_tops_up`
  does (`tests/test_record_migrate.py:2881-2884`). Read the held facts from
  that record. Seed a fresh `MemoryRecord` with them for each half, through
  `_assert_agrees_and_gains_nothing` and `_assert_disagrees`
  (`tests/test_record_migrate.py:2203-2230`).
- Criterion 7: render through `render_pr_body` with `advisory_failures`, as
  `test_the_new_failures_section_names_advisory_new_failures_apart_from_blocking_ones`
  does (`tests/test_report.py:298-330`).
- Criteria 1, 2 and 4 read `detail` from a parsed or built `Failure`.
  Criterion 6 reads it from a fact a `Failure` dumped. So each fails at
  your base. Criteria 3
  and 7 fail there because `render` and `_failure_rows` leave the detail
  out.

**Size.** A prototype on your base held all five changes and the six new
witnesses. `size_gate` measured 139 changed tokens outside the test paths,
and `estimated_lines` is that over four. `ty check` was clean, and each new
witness failed with the source reverted. Every wrong version listed above
failed its witness there.
