---
id: SA-0107
title: N5's derivation chain is checked only against hand-authored fixtures, so no merged change was ever its subject
type: feature
priority: 2
depends_on: [SA-0106]
touches:
  - saffron/projection.py
  - saffron/cli.py
  - tests/test_projection.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/batch.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 25
max_turns: 120
acceptance:
  - claim: >-
      A materialization projects every task in the ledger that reached an end
      state, from any batch and from any attended cell. It does not project only
      the rows of the batch that just ended. It replaces the previous projection
      rather than adding to it. Today no projection is written at all.
    witness: tests/test_projection.py::test_a_materialization_projects_every_ended_task_and_replaces_the_last
  - claim: >-
      A merged task whose stored artifacts match what its own event log recorded
      at extraction reaches Q4's result with every kind in its chain. The query
      is the committed `ontology/queries/Q4-derivation-chain.rq`, read from the
      tree rather than restated in the test.
    witness: tests/test_projection.py::test_q4_over_the_projection_reaches_a_merged_pull_request
  - claim: >-
      A merged task whose stored plan or diff no longer matches what its own
      event log recorded is absent from Q4's result. A later task of the same
      spec overwriting it is the case. A sibling merged task that still matches
      stays in the same result with every kind.
    witness: tests/test_projection.py::test_an_artifact_a_later_task_overwrote_drops_only_the_earlier_chain
  - claim: >-
      The command that materializes the projection also reports every merged pull
      request Q4 drops while the checked walk calls its chain whole. A task it
      cannot attribute to its own events is counted apart and never reported as
      a break.
    witness: tests/test_projection.py::test_the_report_names_a_break_the_checked_walk_calls_whole
  - claim: >-
      A projection that fails the shapes is reported as an error and leaves no
      projection behind, so a reader finds none rather than the last one.
    witness: tests/test_projection.py::test_a_projection_that_fails_the_shapes_leaves_none_behind
  - claim: >-
      `saffron batch` materializes once, after its loop returns. A
      materialization that raises leaves the batch's exit code as the loop
      decided it.
    witness: tests/test_projection.py::test_a_batch_materializes_once_and_a_raise_leaves_its_exit_code
---

## Context

`DESIGN.md` Appendix T (rev 24) and backlog item b-946f03 reopened the emitter on
`ontology/RATIONALE.md`'s own revisit clause. Read the appendix first. It carries
the decision rule this spec makes runnable, and it states what the work does not
license.

N5 is a numbered requirement in §1. Any merged change must be reconstructible
from stored artifacts alone, expressed as a derivation-chain query so it is
checkable rather than asserted. Q4 is that query. Every input Q4 ever ran against
was a graph written by hand: `tests/ontology/fixtures/lifecycle.ttl`, loaded by
`tests/ontology/conftest.py:12-17`, and variants of it. So Q4 proves the query
is well formed, and proves nothing about any change this repository merged.
That is principle 61.

`SA-0001`'s verdict stands and this spec does not touch it. The five queries were
the analytical case and SQL won all five. This is the operational case for one
query, which the RATIONALE never tested (principle 56).

## Problem

Q4 walks spec to scope to plan to diff to pull request, plus gate suites,
findings and rebuttals (`ontology/queries/Q4-derivation-chain.rq:25-62`). The
ledger holds the ends of that chain and not its middle. `tasks`, `attempts`,
`gate_results` and `findings` are tables (`saffron/ledger.py:58-139`). Plan and
diff are files in the batch tree.

The batch tree is keyed by spec, not by task. `task_dir` is `out_dir /
spec.spec_id` (`saffron/cell/session.py:1285`). A later task of the same spec
writes over `plan.json` (`saffron/cell/session.py:1582`) and `patch.diff`
(`saffron/cell/session.py:751`). The earlier task's chain then points at a file
that exists and is not its own. A walk over §4.1's foreign keys that checks each
file exists calls that chain whole.

The event log keeps what each task recorded when the artifact was produced. It
is one log per spec, and each task opens its span with a `Ceilings` event
(`saffron/task.py:259-260`, `saffron/watch.py:116-132`). The plan's line carries
the first 12 hex digits of its sha256 (`saffron/cell/session.py:1583-1587`). The
diff's line carries its length in bytes (`saffron/cell/session.py:768`). An edge
stated only when the stored file still matches that record drops the overwritten
chain from Q4's result, which the checked walk cannot do.

## Out of scope

- **Nothing here controls execution.** §1.4's bullet stands. No scheduling
  decision reads a triple, and the shapes gate no state transition. The
  projection describes the run record after the fact.
- **No new vocabulary.** Every term Q4 names is already in
  `ontology/factory.ttl`. `ontology/` is forbidden above for the reason
  `docs/agents/issue-tracker.md` gives. A cell that finds a term missing must
  stop and say so rather than invent one. Item b-606ea3 owns the terms this
  spec's code uses and the glossary lacks.
- **The dependency move and three stale sentences are the operator's.**
  `pyproject.toml:21-22`, `ontology/render.py:3-4` and
  `ontology/design_record.py:16-17` each state that nothing under `saffron/`
  imports a graph library. The operator amends all three at merge, and moves
  pyoxigraph and pyshacl out of the `dev` group (`pyproject.toml:35-36`) with
  `uv lock`. `uv.lock` is `protected` (`.saffron/policy.yaml:59`), so a cell
  cannot land that move. Both packages are installed wherever this code runs
  today, because the `dev` group is.
- **Recording a full hash for the diff.** Only its byte count is recorded
  today. Adding a hash means editing `saffron/cell/session.py`, which is
  forbidden here. A diff overwritten by one of the same length goes undetected,
  and the report says so rather than hiding it.
- **Q1, Q2, Q3 and Q5 stay worked examples.** They lost on the analytical case
  and this spec reopens nothing for them.

## Notes for the agent

This spec creates `saffron/projection.py` and its tests, and edits
`saffron/cli.py`. The new module's criteria declare witnesses and no mutants,
so `witness` will report `skip` for them.

Read `ontology/queries/Q4-derivation-chain.rq` before writing anything. Its
header argues against the emitter and names the one property that argues for
it. Read `tests/ontology/test_queries.py` for the graph shape Q4 expects, and
build the projection to that shape.

**Which rows.** Project a task only in an end state that `TaskShape` lists
(`ontology/shapes/factory-shapes.ttl:12-20`). Omit every other task, and count
the omissions in the report. `MERGE_TRAIN` is one: `saffron/scheduler.py:67`
reads it, and the vocabulary does not have it. `SpecShape` needs a type and at
least one criterion (`ontology/shapes/factory-shapes.ttl:36-42`). Read both
from the spec file in the repo whose sha256 equals the task's `spec_sha`,
searching `.saffron/specs/` and `.saffron/specs/done/`. A task whose spec file
no longer has those bytes is omitted and counted.

**Attribution.** A spec's tasks, ordered by `task_id`, map in order onto the
`Ceilings` spans of that spec's `events.jsonl`. A spec whose count of spans
differs from its count of tasks is unattributable. Omit its tasks and count
them apart. Never report one of them as a break.

**The checked walk** is the comparator Appendix T names. It follows §4.1's
foreign keys for a merged task and asks only whether each stored file exists.
Build it beside the projection, from the same rows, so the report compares like
with like.

**Where the batch tree is.** `saffron/cli.py:152` resolves it from `--home`.
Pass that path in, and never spell `~/.saffron` inside the new module.

**Materialize from `saffron/cli.py`,** after `run_batch` returns
(`saffron/cli.py:776`), and not from `saffron/batch.py`. The loop's stop
reasons are a closed set (`saffron/batch.py:36`), and a materialization that
raises must not become one. `SA-0106` edits the same command's scan, so read
what it landed first. Materialization runs once per batch and not once per
rescan.

Distinguish `error` from `fail`. A projection that fails the shapes is an error
in this module's own sense. It aborts the materialization and removes the
previous projection.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Write each test against the unfixed code before trusting it. The third
criterion matters most. Build its fixture from two merged tasks of one spec,
the second overwriting the first's stored file. Drive the plan case and the
diff case in the one test.
