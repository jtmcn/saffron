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
      today's text and the asked hash no longer binds. The sentinel log with the asked hash
      binds, and the sentinel log with the other hash does not.
    witness: tests/test_qualify.py::test_binds_task_reads_the_reviewed_diff_line_from_the_shared_constant
    wrong_versions:
      - "`qualify.py` keeps its own f-string literal in `_binds_task`."
      - "`qualify.py` imports the constant by name with `from saffron.cell.session import REVIEWED_DIFF_DETAIL`, so its copy is bound at import."
      - "`qualify.py` copies `session.REVIEWED_DIFF_DETAIL` into a module-scope name of its own and matches against that."
      - "`_binds_task` matches any REVIEW detail that contains the hash."
      - "`_binds_task` matches any REVIEW detail that ends with the hash."
      - "`_binds_task` matches the constant as a prefix and ignores the hash."
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

## Before this cell starts

Criterion 3 is `preserves`, so `witness` only re-runs its existing test.
It cannot apply a mutant to it unless one sits on `refs/saffron/mutants` at
this spec's id. That ref does not exist on origin at this base
(`git rev-parse --verify --quiet refs/saffron/mutants` against origin
fails). No spec here carries a mutant yet. Decide now, before dispatch,
rather than discover it mid-cell:

- **Seed one first**, so `witness` machine-checks that criterion 3's
  `wrong_versions` fail the test. Run `saffron mutant SA-0386 --from
  <file>`. Give `<file>` a mapping keyed by
  `tests/test_qualify.py::test_an_in_cell_concern_is_dropped_when_its_line_changed_since_the_tree_its_critic_read`.
  Name `file: saffron/qualify.py`. Name a `find` that is the sole line in
  the tree comparing the event's label to the review phase's name
  (`saffron/qualify.py:132`). Name a `replace` that swaps that phase's
  name for the planning phase's name. Name a `case` describing a REVIEW
  `PhaseStart` whose detail matches today's line, still binding a
  planning-labeled record to the task. The case explains that
  `_binds_task` stopped checking the label.

  Write that `find` and `replace` only in `<file>`, never in this spec.
  `saffron/intake.py:397`'s `refuse_disclosed_mutants` runs again against
  the filled-in spec. `saffron/mutants.py`'s `attach_mutants` calls it
  once the ref supplies the mutant. It raises `DisclosedMutantError`, a
  `SpecError`, when a criterion's `find` sits inside this spec's own body,
  claims, wrong versions, or cases. Every caller of `attach_mutants_at`
  catches `SpecError` and returns `Refused`. `saffron/task.py`'s dispatch
  paths are among those callers. A disclosed `find` refuses the whole
  task the next time it is dispatched, not criterion 3's witness alone.
  That is why the target above is named by file, line, and effect, with
  neither side of the comparison spelled out as source text here.

- **Or accept the gap this round.** With no mutant attached, `witness`
  reports `skip` for criterion 3, not `fail`: the cell runs and the gate
  passes either way. Criterion 3's regression guard then stays asserted
  only in its `wrong_versions` prose, unverified by any gate. That stays
  true until a later spec or a seeded mutant checks it.

Either choice is compatible with the rest of this spec, provided a seeded
mutant's `find` is never quoted in this file. Nothing below depends on
which one is made.

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
- Seeding criterion 3's mutant. "Before this cell starts" names the
  candidate for whoever decides to seed it. This spec's cell neither runs
  `saffron mutant` nor edits anything on `refs/saffron/mutants`.

## Notes for the agent

**This is a refactor.** The line's text and the binding do not change, so
criterion 3 is `preserves`. Criteria 1 and 2 are new witnesses that fail at
base, since `session` has no `REVIEWED_DIFF_DETAIL` there. Their subject is
a constant that does not exist at base. So they declare no mutant, and
`witness` reports `skip` for them. The wrong versions under each criterion
are what its witness must kill. Do not run them yourself.

**Criterion 3's mutant, if any, is seeded outside this cell.** See "Before
this cell starts". Whether or not one lands on `refs/saffron/mutants`
before the cell runs changes nothing this cell does: build the refactor,
keep criterion 3's existing test passing unmodified, and leave
`saffron mutant` alone.

**`_write_review_log` stays a literal.** It writes today's full line as a
literal (`tests/test_qualify.py:1596`), and so does the unbound case of
`test_a_layer_whose_record_cannot_be_used_keeps_the_packaged_heads_check`
(`tests/test_qualify.py:1906`). Criterion 3's witness writes its logs
through `_write_review_log`, and that helper's detail must stay a literal.
Built from the constant instead, the line would move with any wording
change. Criterion 3's own "wording changes" mutant would then pass silently
rather than being caught. Do not route `_write_review_log` through the
constant. Criteria 1 and 2 never call `_write_review_log`. Each pins the
wording through its own literal, as the Notes below describe.

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
log with `events.EventLog`, directly, not through `_write_review_log`. Pass
the detail as a literal parameter of the test itself, rather than reading
it from the constant. Write today's text as a literal, never from the
constant. Ask every log about the same hash. Assert the shipped log binds
before you replace the constant. That positive case, through the same
call, is what makes the later "no longer binds" assertion mean something.

**Docstrings and comments.** The `prose` gate reads each new docstring and
comment, so keep them in house style.
