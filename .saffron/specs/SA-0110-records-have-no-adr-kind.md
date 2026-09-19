---
id: SA-0110
title: records/ has no ADR kind, so one decision per file has nowhere to load or be checked
type: feature
priority: 3
depends_on: []
touches:
  - records/kinds.py
  - records/load.py
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
pending_symbols:
  - records/kinds.py::supersedes
budget_usd: 23
max_turns: 135
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
`records/kinds.py:154-169`). `Kind.sections` names the `## ` headings a body is
allowed, in order (`records/kinds.py:151`), and `_sectioned` refuses an unknown or
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
(`tests/records/check.py:445-466`) does not call the four new `check_adr_*`
functions. `test_check_all_runs_every_check`
(`tests/records/test_records_check.py:265`) finds every `check_*` in
`tests.records.check` by reflection and fails on one `check_all` does not run. Give it
an exclusion set naming exactly those four, with a one-line comment saying the
by-hand layer removes it with ADR 1.

**The ontology, `DESIGN.md`'s ADR index, and the citation reader for "ADR N".**
They live in `ontology/` and `tests/test_citations.py`, and are by hand.

**Where the principle numbers come from.** `check_adr_principles` and
`check_adr_appendices` take the existing numbers and letters as arguments.
A fixture passes its own small set, and the by-hand layer passes the live one
in from `ontology.design_record`.

## Notes for the agent

This change is **new** code, so each criterion declares a witness and no mutant.

**This diff runs ahead of `CONTEXT.md` §11 on purpose.** §11 still says "ADR"
means prior art's records and that Saffron keeps no `docs/adr/`
(`CONTEXT.md:639-645`). The design reverses that, and `CONTEXT.md` is
`protected`, so its entry is rewritten by hand after this merges. Saffron's own
ADR kind here is that design's first step, not a use of a word the glossary
refuses.

**Each witness plants every case its claim lists**, one broken copy of the
fixture per case, and asserts each is reported. Criterion 1's witness also
asserts `1-x.md` and `00001-x.md` holding `id: 1` are refused, so a pattern of
`\d+` fails it. Criterion 2's plants each of the four required headings
missing in turn, an unknown heading, and two headings swapped. Criterion 5's
plants all six supersession defects, and criterion 6's all four principle
defects. A witness that plants one case passes an implementation that checks
only that one.

**The model.** Add `Adr(Identified)` in `records/kinds.py`: `id` a strict
integer ≥ 1 (`Number`, `records/kinds.py:31`), `title` non-empty, `status` one of
the three, `date` a `dt.date`, and four lists defaulting empty: `supersedes`,
`superseded_by` and `principles` of `Number`, `appendices` of strings matching
`APPENDIX_ID` (`records/kinds.py:128`). `Identified` already forbids extra keys
(`records/kinds.py:51-56`).

**The kind.** Directory `docs/adr`, pattern `^(\d{4})-[a-z0-9-]+\.md$`. `load`
compares the prefix to the id through `as_id` (`records/load.py:165-168` and
`records/kinds.py:40`), which turns `0001` into `1`, so `0001` matches id 1 as
written. The pattern's `\d{4}` refuses a prefix of any other length. The claim's "not the
id zero-padded" case is `0002-x.md` holding `id: 1`. Sorting is by id: `order`
(`records/load.py:173`) already sorts integer ids by value.

**Required headings.** Add a field to `Kind` for the subset of `sections` that
must appear, and have `_sectioned` refuse a missing one, naming it. The backlog
declares `("Problem",)`. The comment on `sections` (`records/kinds.py:150`) says
its headings are required. Once the new field exists they are only allowed, so
correct it. Its status-dependent rules stay in `_check_sections`.
Keep the backlog's current behaviour exactly, which criterion 3 holds.

`_sectioned`'s existing parameter is already called `required`
(`records/load.py:114-116`) and holds the *allowed* set, which is what its
`unknown` and `order` checks read (`:122`, `:126`). The design calls the new
`Kind` field `required`. Rename that parameter to `allowed` in the same edit,
or the two senses meet inside one nine-line function.

**Witness modules must collect with the source reverted.** `revert` re-runs
every added test with this diff's source reverted. A test module that imports a
name this change adds, at module scope, then fails to collect, and `revert`
reads that as `skip`. So in `tests/records/test_records_check.py` and
`tests/records/test_records_load.py`, reach new names through the module:
`tests.records.check.check_adr_ids` (the module is imported whole at the top
of `tests/records/test_records_check.py`), `KINDS["adr"]` looked up inside the test, and
`records.kinds.Adr` through `import records.kinds` (already importable at base).
Do not add them to a `from … import` line at the top of either file.

`tests/records/check.py` is the third module this governs, and it is the one
that needs `Adr` to narrow `r.model`, as it narrows `BacklogItem` at `_backlog`
(`tests/records/check.py:53-58`). It is a test path
(`.saffron/policy.yaml:69`), so `revert` leaves it at head
(`saffron/gates/core/revert.py:165-168`) while `records/kinds.py` goes back.
A new name on its `from records.kinds import …` line at `:14` therefore breaks
collection of every module importing it. `revert` reads that as `skip` for the
whole subset. Reach `Adr` there through `import records.kinds` too.

**Fixtures.** Add `tests/records/fixtures/good/docs/adr/0001-*.md` (status
`superseded`, `superseded_by: [2]`) and `0002-*.md` (status `accepted`,
`supersedes: [1]`), each with every required section and no title line: prose
before the first `## ` heading is refused (`records/load.py:118-120`). Give one `principles:
[1]` with a `- **1** upholds.` bullet, and the other an empty list with the
`Judged against no principle.` line. Their `appendices` name letters the
fixture's `docs/appendices/` holds (A and B). Two readers scan the fixture
prose. `tests/test_citations.py` resolves every appendix letter and `§`
citation in it against the real repo. Once `CITING` gains `docs/adr`,
`check_all(FIXTURE, …)` also reads the fixture ADRs for backlog item citations,
which the fixture must hold (`tests/records/test_records_check.py:261`). Keep the fixture
ADRs' prose free of any citation. Each witness copies the good
fixture to `tmp_path` and breaks one thing, as the existing appendix tests do
(`test_a_skipped_letter_is_a_violation`, `tests/records/test_records_check.py`).

**The four checks return `list[Violation]`**, like every other `check_*` in
`tests/records/check.py`, where they go. `check_adr_principles(records, principles: set[int])` and
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

**`CITING` and `LIVE_SURFACES` gain `"docs/adr"`** (`tests/records/check.py:22`,
`:251`). A missing directory yields no files through `_walk`
(`tests/records/check.py:202-217`), so the live test is unaffected until ADRs exist.

**The queued-spec smoke test.** Adding this spec changes the live queue that
`tests/test_scheduler.py::test_saffron_queue_smoke_reproduces_this_repos_measured_queue`
pins. That update is already in this spec's own commit. Do not edit that test.
