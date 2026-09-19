---
id: SA-0110
title: records/ has no ADR kind, so one decision per file has nowhere to load or be checked
type: feature
priority: 3
depends_on: []
touches:
  - records/kinds.py
  - records/load.py
  - records/check.py
  - records/__main__.py
  - tests/records/**
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - .claude/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/**
budget_usd: 18
max_turns: 100
acceptance:
  - claim: >-
      A file under `docs/adr/` named `0001-<slug>.md` loads as an ADR whose id
      is the integer 1. Its frontmatter is `id`, `title`, `status` (one of
      `accepted`, `superseded` or `deprecated`), `date`, and the lists
      `supersedes`, `superseded_by`, `appendices` and `principles`. An unknown
      key, a `proposed` status, or a filename prefix that is not the id
      zero-padded to four digits is refused, naming the file.
    witness: tests/records/test_records_load.py::test_an_adr_loads_from_a_four_digit_prefix_and_refuses_what_it_does_not_declare
  - claim: >-
      An ADR body is `## Context`, `## Decision`, `## Options considered`,
      `## Principles` and `## Consequences`, in that order. `Options
      considered` may be absent. Any other of the five absent, an unknown
      heading, or the five out of order is refused, naming the file.
    witness: tests/records/test_records_load.py::test_an_adr_body_requires_four_sections_in_order_and_allows_options_to_be_absent
  - claim: >-
      A backlog item missing `## Problem` is still refused.
    witness: tests/records/test_records_load.py::test_a_record_with_no_problem_section_is_refused
    preserves: true
  - claim: >-
      `check_adr_ids` reports ADR ids that do not run from 1 with no gap or
      repeat, and is silent on ids that do.
    witness: tests/records/test_records_check.py::test_adr_ids_run_from_one_with_no_gap_or_repeat
  - claim: >-
      `check_adr_supersession` reports each of these, naming the ADR: an id on
      either side that names no ADR; an id in `supersedes` not lower than the
      ADR naming it; one side without its mirror on the other; a `superseded`
      status with empty `superseded_by`, or a non-empty `superseded_by` without
      it; a `deprecated` ADR with a non-empty `superseded_by`. It is silent on
      the good fixture, where ADR 2 supersedes ADR 1.
    witness: tests/records/test_records_check.py::test_adr_supersession_is_held_equal_on_both_sides
  - claim: >-
      `check_adr_principles`, given the set of principle numbers that exist,
      reports a listed principle not in that set; a `## Principles` section
      whose bullets do not name exactly the listed set, each once; a bullet
      whose verb is not `upholds` or `departs`; and, for an empty list, a
      section that is not one line beginning `Judged against no principle.`
    witness: tests/records/test_records_check.py::test_adr_principles_are_declared_and_each_is_judged
  - claim: >-
      `check_adr_appendices`, given the appendix letters that exist, reports
      an `appendices` entry naming none of them.
    witness: tests/records/test_records_check.py::test_an_adr_cites_only_appendices_that_exist
  - claim: >-
      `records list adr` prints one line per ADR in id order: id, status,
      title. `records show --kind adr 1` prints ADR 1, and a bare
      `records show 1` still prints backlog item 1.
    witness: tests/records/test_records_cli.py::test_list_adr_and_show_by_kind_leave_a_bare_number_to_the_backlog
---

## Context

Backlog item **b-9ff0fd**: decisions have no record of their own. The design is
`docs/superpowers/specs/2026-09-19-adrs-design.md`. Its "The record" and
"Validation against the principles" sections are what this spec implements, and
its "Readers" beyond `records/` land by hand afterwards.

`records/` has two kinds today, `backlog` and `appendix` (`KINDS`,
`records/kinds.py:155-169`). `Kind.sections` names the `## ` headings a body is
allowed, in order (`records/kinds.py:152`), and `_sectioned` refuses an unknown or
out-of-order one (`records/load.py:114-130`). Nothing refuses a *missing*
heading except `_check_sections`, which runs for the backlog only
(`records/load.py:107-108`, `:133-146`). The ADR kind needs a heading to be
required without being backlog-specific.

## Problem

There is no ADR kind, so an ADR under `docs/adr/` has nothing to load it, check
its supersession, or hold its declared principles.

## Out of scope

**`docs/adr/` itself, ADR 1, and wiring the new checks into `check_all`.** They
land by hand after this merges. `CONTEXT.md` and `.saffron/policy.yaml` are
`protected`, and the design orders ADR 1 after them. So `check_all`
(`records/check.py:441-462`) does not call the four new `check_adr_*`
functions. `test_check_all_runs_every_check`
(`tests/records/test_records_check.py:265`) finds every `check_*` in
`records.check` by reflection and fails on one `check_all` does not run. Give it
an exclusion set naming exactly those four, with a one-line comment saying the
by-hand layer removes it with ADR 1.

**The ontology, `DESIGN.md`'s ADR index, and the citation reader for "ADR N".**
They live in `ontology/` and `tests/test_citations.py`, and are by hand.

**Where the principle numbers come from.** `check_adr_principles` and
`check_adr_appendices` take the existing numbers and letters as arguments.
`records/` imports nothing from `ontology/` (its graph library is dev-only), and
the by-hand layer passes them in from `ontology.design_record`.

## Notes for the agent

This change is **new** code, so each criterion declares a witness and no mutant.

**The model.** Add `Adr(Identified)` in `records/kinds.py`: `id` a strict
integer ≥ 1 (`Number`, `records/kinds.py:31`), `title` non-empty, `status` one of
the three, `date` a `dt.date`, and four lists defaulting empty: `supersedes`,
`superseded_by` and `principles` of `Number`, `appendices` of strings matching
`APPENDIX_ID` (`records/kinds.py:129`). `Identified` already forbids extra keys
(`records/kinds.py:52-56`).

**The kind.** Directory `docs/adr`, pattern `^(\d{4})-[a-z0-9-]+\.md$`. `load`
compares the prefix to the id through `as_id` (`records/load.py:164-167` and
`records/kinds.py:41`), which turns `0001` into `1`, so `0001` matches id 1 as
written. The pattern's `\d{4}` refuses a prefix of any other length. The claim's "not the
id zero-padded" case is `0002-x.md` holding `id: 1`. Sorting is by id: `order`
(`records/load.py:173`) already sorts integer ids by value.

**Required headings.** Add a field to `Kind` for the subset of `sections` that
must appear, and have `_sectioned` refuse a missing one, naming it. The backlog
declares `("Problem",)`. Its status-dependent rules stay in `_check_sections`.
Keep the backlog's current behaviour exactly, which criterion 3 holds.

**Witness modules must collect with the source reverted.** `revert` re-runs
every added test with this diff's source reverted. A test module that imports a
name this change adds, at module scope, then fails to collect, and `revert`
reads that as `skip`. So in `tests/records/test_records_check.py` and
`tests/records/test_records_load.py`, reach new names through the module:
`records.check.check_adr_ids`, `KINDS["adr"]` looked up inside the test, and
`records.kinds.Adr` through `import records.kinds` (already importable at base).
Do not add them to a `from … import` line at the top of either file.

**Fixtures.** Add `tests/records/fixtures/good/docs/adr/0001-*.md` (status
`superseded`, `superseded_by: [2]`) and `0002-*.md` (status `accepted`,
`supersedes: [1]`), each with every required section. Give one `principles:
[1]` with a `- **1** upholds.` bullet, and the other an empty list with the
`Judged against no principle.` line. Their `appendices` name letters the
fixture's `docs/appendices/` holds (A and B). Each witness copies the good
fixture to `tmp_path` and breaks one thing, as the existing appendix tests do
(`test_a_skipped_letter_is_a_violation`, `tests/records/test_records_check.py`).

**The four checks return `list[Violation]`**, like every other `check_*` in
`records/check.py`. `check_adr_principles(records, principles: set[int])` and
`check_adr_appendices(records, letters: set[str])` take the existing sets as
arguments. Read a bullet as `- **<n>** <verb>.` at the start of a line inside
`record.sections["Principles"]`.

**The CLI.** In `records/__main__.py`, `list` takes a kind already
(`records/__main__.py:160`), and `cmd_list` branches on `Appendix`
(`:74-92`). Add an ADR branch printing `id  status  title`, refusing `--status`
and `--tier` as the appendix branch does. `show` takes no kind today
(`:169-170`), and `cmd_show` reads a digit id as a backlog item (`:106-114`).
Add `--kind` with choices from `KINDS`, defaulting to today's behaviour, so a
bare `records show 1` is unchanged. `--kind adr` looks the id up among ADRs,
and a missing one prints `no ADR <n>` and exits 1.

**`CITING` and `LIVE_SURFACES` gain `"docs/adr"`** (`records/check.py:18`,
`:247`). A missing directory yields no files through `_walk`
(`records/check.py:198-213`), so the live test is unaffected until ADRs exist.

**The queued-spec smoke test.** Adding this spec changes the live queue that
`tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`
pins. That update is already in this spec's own commit. Do not edit that test.
