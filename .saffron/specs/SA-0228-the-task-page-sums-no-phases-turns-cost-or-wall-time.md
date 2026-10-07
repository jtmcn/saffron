---
id: SA-0228
title: The task page sums no phase's turns, cost or wall time
type: feature
priority: 3
depends_on: [SA-0225]
estimated_lines: 137
estimate_measured: true
touches:
  - saffron/view/server.py
  - tests/test_view_server.py
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
  - records/**
  - hooks/**
  - images/**
  - saffron/view/graph.py
  - saffron/projection.py
  - saffron/ledger.py
  - saffron/cli.py
  - saffron/report/**
  - saffron/record/**
  - saffron/gates/**
  - tests/test_view_graph.py
  - tests/test_cli.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A task page with attempts has a `<table id="phase-totals">` right after
      `<table id="attempts">`. Its columns are `phase`, `attempts`, `turns`,
      `cost` and `wall time`. It has one row per phase, in the order of each
      phase's first attempt in `V3`, and then one last row whose phase cell
      is `all phases` and which sums every attempt of the task. Each attempt
      is counted once however many gate results it has, and only the page's
      own task's attempts are counted. `turns` sums `numTurns`. `cost` sums
      `costUsdEst` exactly, then rounds half up to cents. `wall time` sums
      each attempt's end minus its start, as hours, then two-digit minutes
      and seconds, joined by colons. A total over which no attempt lacks the
      value shows that sum. A total over which some attempts lack it shows
      the sum of the rest, then ` + `, the number lacking it and
      ` unknown`. A total over which every attempt lacks it shows only that
      number and ` unknown`. The witness drives one task with four phases.
      `SPEC_WRITING` has two attempts with every value, one over 24 hours,
      and its second attempt starts after every other phase's.
      `SPEC_REVIEW` has two such attempts, each costing `0.005`, and one
      lacking all three values. `IMPLEMENTING` has three attempts, each
      lacking one value, end, turns or cost, and the first carries three
      gate results. `REVIEWING` has two attempts lacking all three values.
      A decoy task has a `SPEC_REVIEW` attempt of its own.
    witness: tests/test_view_server.py::test_a_task_page_totals_each_phase_and_the_task_with_unknowns_never_zero
    wrong_versions:
      - An attempt with several gate results is counted once per gate result.
      - The attempts are read from `V3` unbound, so the decoy task's attempt is summed too.
      - A missing turns value is summed as 0 and no unknown is shown.
      - A missing cost is summed as 0 and no unknown is shown.
      - A missing end is summed as no time and no unknown is shown.
      - A missing end is measured to the current time.
      - One unknown count serves all three columns, counting attempts that lack any value.
      - An attempt lacking any value is left out of every total, its count included.
      - A total that every attempt lacks shows `0 + 2 unknown`.
      - A total that some attempt lacks shows `unknown` alone.
      - Each attempt's cost is rounded to cents before the sum.
      - Wall time is rendered by `str` of a `timedelta`, so a total past a day reads `1 day, ...`.
      - Wall time is rendered as a whole number of seconds.
      - The phase rows are sorted by phase name.
      - The phase rows follow each phase's last attempt, not its first.
      - The `all phases` row comes first.
      - The `all phases` row counts the phases with an unknown, not the attempts.
      - The totals table sits after `<table id="gate-results">`.
  - claim: >-
      A task page with no attempts still shows no table, the totals table
      included.
    witness: tests/test_view_server.py::test_a_task_with_no_attempts_shows_its_summary_and_no_table
    preserves: true
    wrong_versions:
      - The totals table is rendered for a task with no attempts, holding only its `all phases` row.
---

## Context

Backlog item **b-98a3be**, whose first point asks for tokens and wall time
for every writer, reviewer and delegate step. `DESIGN.md` §3.4's paragraph
"Cost and time come from the attempts" says each session is a
`SPEC_WRITING` or `SPEC_REVIEW` attempt with turns, cost and times (§4.1).
It says nothing new records them, and what is new is a reader that sums
them. §3.4 and the item landed in `d7a9ec6e`, the base this spec was read
at. Line numbers below are at that commit.

**What the graph already states.** The graph states every attempt's start,
since `attempts.started_at` is `NOT NULL` (`saffron/ledger.py:159`,
`saffron/view/graph.py:247`). It states turns, cost and end only where the
column is not null (`saffron/view/graph.py:248`, `:256` and `:258`). A
phase node is named from the task id and the phase text
(`saffron/view/graph.py:230`). `V3` returns them all, one row per gate
result, ordered by `?task ?started ?n ?gate`
(`ontology/queries/view/V3-task-timeline.rq:1`, `:8` and `:25`).

**What the page does with them now.** `_attempt_solutions` keeps one `V3`
row per attempt, bound on `?task` (`saffron/view/server.py:488`).
`_task_cost` sums the costs it finds and skips a missing one
(`saffron/view/server.py:506`). The summary shows that as `cost`
(`saffron/view/server.py:661`). `_render_task` writes `no attempts` and no
table for a task with no attempts (`saffron/view/server.py:666`). Otherwise
it writes the attempts table, then the gate results table
(`saffron/view/server.py:669` and `:673`). No row sums a phase, and no
wall time appears anywhere.

**The parent.** `SA-0225` adds a last `model` column to the attempts table
and a spec section under the summary. It edits `_render_task` and
`tests/test_view_server.py`, so this spec waits for it. This spec reads the
attempts table and the summary only for their position.

## Problem

1. **The totals.** Add a `<table id="phase-totals">` to a task page, right
   after the attempts table, inside the branch that renders it. Build its
   rows from `_attempt_solutions`, grouped by `?phase`, in the order each
   phase first appears there. Add the `all phases` row last.
2. **Unknown, never zero.** Keep, per row and per column, the number of
   attempts lacking that value. Render each total by the three forms the
   first criterion names.
3. **The pinned table list.** One existing test pins the task page's table
   ids and their headers. Add the new table to it.

## Out of scope

- The summary's `cost` term. It sums the known costs and shows `0.00` for a
  task with none, as `SA-0219` specified. The `all phases` row says what it
  leaves out.
- A per-spec reader across tasks. A `saffron draft` task carries one spec's
  whole chain (`SA-0227`), so its page is that spec's sum. A stack batch
  opens its spec review attempt on the task it mints for that spec
  (`saffron/batch.py:532` and `:588`).
- Tokens. The attempts table keeps no token count
  (`saffron/ledger.py:152`), and no ledger change is in scope.
- An end before its start. No criterion fixes how one renders.
- Escaping a phase name holding markup. The graph builder raises on one,
  since the name is part of the phase IRI (`saffron/view/graph.py:230`).
  Escape the cell as every other cell is escaped.
- A CLI command, and any change to the graph, the queries or the ledger.

## Notes for the agent

**This change adds code whose spelling no spec can know.** The totals
table is new. So criterion 1 declares a witness and no mutant, and the
`witness` gate reports `skip` for it. Criterion 2 is `preserves`. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**Reading the times.** `V3`'s `?started` and `?ended` read as
`2026-01-02T03:00:00Z` (`tests/test_view_server.py:112`).
`datetime.fromisoformat` parses that on Python 3.12, the floor in
`pyproject.toml`. Subtract, then sum whole seconds.

**Reuse.** Group the rows `_attempt_solutions` returns, and round with
`_round_cents` (`saffron/view/server.py:484`). Sum costs as `Decimal`, as
`_task_cost` does.

**The fixture.** Use `_ledger`, `_set_task`, `_set_attempt` and `_gate`
from the test module. `open_attempt(task_id, phase)` numbers `n` within the
phase. Set each attempt's times with `_set_attempt`. Never call
`close_attempt`, since it stamps the end from the clock. Use second-level
times, such as an attempt of five minutes and thirty seconds, so the
seconds field is driven. Assert the whole `phase-totals` table by `==`,
rows and cells in order.

**The test that changes, by name kept.** The `census` gate fails a removed
or renamed test.
`test_every_table_on_every_page_has_a_header_row_naming_its_columns`
(`tests/test_view_server.py:1540`) pins the task page's table ids
(`:1618`) and each table's header (`:1627`). Add `phase-totals` after
`attempts` in both.

**Measured on a prototype over `d7a9ec6e`.** All 46 tests in the two view
test files passed. The witness failed against the base source. Each of the
19 wrong versions above, applied as an edit, failed its own witness. The
diff was 547 changed tokens by the `size` gate's counter, against the
`feature` ceiling of 3000. `ruff`, `ty`, the `dead` scan and the `prose`
counter passed on both files.

**Not this task's work.** `DESIGN.md` is forbidden here. The operator
edits it by hand in the pull request that adds this spec. §6.2 gains a
sentence. A task page totals its attempts per phase and for the whole task, with the
count, turns, cost and wall time. A value an attempt lacks shows as
unknown, never as zero. The last sentence of §3.4's paragraph "Cost and
time come from the attempts" then names the task page as that reader.
`CONTEXT.md` gains no term.
