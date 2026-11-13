---
id: SA-0386
title: "REVIEW's reviewed-diff line is spelled once in `session.py` and again in `qualify.py`, so a wording change to either unbinds every record"
type: refactor
priority: 3
estimated_lines: 87
estimate_measured: true
touches:
  - saffron/cell/session.py
  - saffron/qualify.py
  - tests/test_session.py
  - tests/test_qualify.py
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
  - saffron/agents/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/record/**
  - saffron/view/**
  - saffron/cell/runtime.py
  - saffron/cell/runtimes/**
  - saffron/cell/proxy.py
  - saffron/cell/worktree.py
  - saffron/events.py
  - saffron/finish.py
  - saffron/end_review.py
  - saffron/task.py
  - saffron/cli.py
  - tests/fixtures/**
  - tests/test_events.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 22
max_attempts: 3
max_turns: 180
risk: elevated
acceptance:
  - claim: >-
      `saffron/cell/session.py` declares a module-scope `str` constant
      `REVIEWED_DIFF_DETAIL` whose value is `reviewed diff recorded, sha256 `,
      the text before the hash with its trailing space. REVIEW's line after
      `reviewed-diff.json` is written is that constant followed directly by
      the recorded hash, read from the module global when the line is built.
      The witness drives a clean REVIEW twice through `_drive`'s `capture`.
      Driven as shipped, exactly one REVIEW `PhaseStart` detail equals
      today's full text with the recorded hash. Driven with
      `session.REVIEWED_DIFF_DETAIL` replaced by a sentinel, exactly one
      equals the sentinel with that hash, and no REVIEW detail contains
      `reviewed diff recorded`.
    witness: tests/test_session.py::test_review_spells_its_reviewed_diff_line_from_the_shared_constant
    wrong_versions:
      - "`session.py` declares the constant but keeps its f-string literal at the `_phase_start` call."
      - "The constant drops its trailing space, and both sides join it to the hash with a space of their own."
      - "The constant's wording changes, for example to `sha-256`, on both sides at once."
      - "`_write_review_log` builds its line from the constant, and the constant's wording changes."
  - claim: >-
      `qualify._binds_task` matches a REVIEW detail only when it equals the
      value `session.REVIEWED_DIFF_DETAIL` holds at the moment of the call,
      followed by the hash it was handed. A replacement of the constant
      reaches it. The witness writes four `events.jsonl` logs, each a REVIEW
      `PhaseStart` followed by one `RecordAppend`. Two carry today's text
      and two a sentinel, each with the hash asked about or another hash.
      As shipped, the log carrying today's text and the asked hash binds,
      and the one with the other hash does not. With
      `session.REVIEWED_DIFF_DETAIL` replaced by the sentinel, the log with
      today's text no longer binds. The sentinel log with the asked hash
      binds, and the sentinel log with the other hash does not.
    witness: tests/test_qualify.py::test_binds_task_reads_the_reviewed_diff_line_from_the_shared_constant
    wrong_versions:
      - "`qualify.py` keeps its own f-string literal in `_binds_task`."
      - "`qualify.py` imports the constant by name with `from saffron.cell.session import REVIEWED_DIFF_DETAIL`, so its copy is bound at import."
      - "`qualify.py` copies `session.REVIEWED_DIFF_DETAIL` into a module-scope name of its own and matches against that."
      - "`_binds_task` matches any REVIEW detail that contains the hash."
      - "`_binds_task` matches any REVIEW detail that ends with the hash."
      - "`_binds_task` matches the constant as a prefix and ignores the hash."
      - "`_write_review_log` builds its line from the constant, and the constant's wording changes."
  - claim: >-
      A layer whose `events.jsonl` carries today's full line, followed by its
      own task's `RecordAppend`, still has its record bound. Its in-cell
      concerns are still read against the tree its critic read.
    witness: tests/test_qualify.py::test_an_in_cell_concern_is_dropped_when_its_line_changed_since_the_tree_its_critic_read
    preserves: true
    wrong_versions:
      - "The constant's wording changes, for example to `sha-256`."
      - "`_binds_task` matches a label other than `REVIEW`."
---

## Context

Backlog item b-19f43a. REVIEW records the diff its lenses read in
`reviewed-diff.json`, then writes one line naming its hash
(`saffron/cell/session.py:3391-3395`):

```
_phase_start("REVIEW", "REVIEW", f"reviewed diff recorded, sha256 {reviewed_diff_sha256}")
```

`_phase_start` emits a `PhaseStart` with that `detail`
(`saffron/cell/session.py:2301-2310`). A later finish reads the record back
only when that line binds it to the task. `qualify._binds_task` spells the
same text again (`saffron/qualify.py:122`) and compares each REVIEW
`PhaseStart`'s detail to it for equality (`saffron/qualify.py:130-135`).
When it is false, `_reviewed_tree` returns no tree, with the cause `no REVIEW
line binds it to this task` (`saffron/qualify.py:201-202`). Its caller then
checks the layer's in-cell concerns from the packaged head and calls `note`
(`saffron/qualify.py:246-256`). Nothing shares the two spellings.

If either side's wording changes, no record binds. Every in-cell concern then
falls back to the packaged head's check with a `note`. No gate or test that
reads both sides notices. `SA-0378` could not share them, because its
`forbidden` held `saffron/cell/**`.

`qualify.py` already imports `session` (`saffron/qualify.py:40`) and reads
`session.CellSpec` and `session.probe_findings` through it
(`saffron/qualify.py:266`, `:277`). `session.py` imports nothing from
`qualify`. So the constant lives in `session.py`, the module that writes the
line, with no import cycle.

## Problem

1. Declare `REVIEWED_DIFF_DETAIL` at module scope in `session.py`, beside the
   other module constants, with the value criterion 1 names.
2. Build the REVIEW line at `saffron/cell/session.py:3394` from the constant
   and the hash.
3. Build `_binds_task`'s target at `saffron/qualify.py:122` from
   `session.REVIEWED_DIFF_DETAIL` and the hash. Read the constant on each
   call. An attribute read through `session` does that, the way
   `qualify.py` reads that module's other names. A module-scope import of
   the name binds a copy at import, so a test that replaces the constant no
   longer reaches `qualify`.
4. Add criterion 1's witness to `tests/test_session.py` and criterion 2's to
   `tests/test_qualify.py`.

The line's text does not change. No other module reads it: `git grep`
finds the text in `saffron/` at these two lines alone.

## Out of scope

- The literal text in the tests and fixtures. `tests/test_qualify.py:1596`
  and `:1906` write today's full line by hand. So does `tests/test_events.py:2284`,
  and `tests/fixtures/watch-golden.txt:27` carries it rendered. Leave each
  literal. A test that builds the line from the constant passes whatever the
  constant says, and these literals are what pin the text.
- Any other detail text `session.py` writes.

## Notes for the agent

**This is a refactor.** The line's text and the binding do not change, so
criterion 3 is `preserves`. Criteria 1 and 2 are new witnesses that fail at
base, since `session` has no `REVIEWED_DIFF_DETAIL` there. Their subject is
a constant that does not exist at base. So they declare no mutant, and
`witness` reports `skip` for them. The wrong versions under each criterion
are what its witness must kill. Do not run them yourself.

**Criterion 3 declares no mutant.** `refs/saffron/mutants` does not exist
on origin at this base, so no spec carries one. The operator can add one
with `saffron mutant`. The candidate is `saffron/qualify.py`'s
`event.label == "REVIEW"`, replaced with `"PLAN"`.

**Two hand-written lines stay as written.** `_write_review_log` writes
today's full line as a literal (`tests/test_qualify.py:1596`), and so does
the unbound case of
`test_a_layer_whose_record_cannot_be_used_keeps_the_packaged_heads_check`
(`tests/test_qualify.py:1906`). Criterion 3's witness writes its logs
through `_write_review_log`. Built from the constant, that line moves with
any wording change, and criterion 3 would pass it. Criteria 1 and 2 pin
the wording through their own literals.

**Criterion 1's witness.** Drive a clean REVIEW the way
`test_a_task_whose_lenses_are_handed_no_diff_records_none` drives its clean
case: `_stub_the_runtime`, then `_drive` with a plan turn and one implement
turn, under its own `tmp_path` subdirectory. Pass a `capture` list. Read the
hash from that task's `reviewed-diff.json` and the details from the REVIEW
`PhaseStart` events in `capture`. Assert the constant's value as a literal.
Then assert the shipped line as a literal too, so the text stays pinned. For
the second drive, replace the constant with `monkeypatch.setattr(session,
"REVIEWED_DIFF_DETAIL", <sentinel>)` and drive again under a second
subdirectory. Pick a sentinel that does not contain `reviewed diff recorded`,
so the claim's last half can see a literal left behind.

**Criterion 2's witness.** Import `_binds_task` inside the test. Write each
log with `events.EventLog`, as `_write_review_log` does
(`tests/test_qualify.py:1573`), but with the detail as a parameter. Ask
every log about the same hash. Assert the shipped log binds before you
replace the constant. That positive case,
through the same call, is what makes the later "no longer binds" assertion
mean something.

**Docstrings and comments.** The `prose` gate reads each new docstring and
comment, so keep them in house style.
