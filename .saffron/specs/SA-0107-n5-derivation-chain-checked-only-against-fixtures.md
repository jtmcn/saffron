---
id: SA-0107
title: N5's derivation chain is checked only against hand-authored fixtures, so no merged change was ever its subject
type: feature
priority: 2
touches:
  - saffron/projection.py
  - tests/test_projection.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/report/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/batch.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 20
max_turns: 100
acceptance:
  - claim: >-
      A materialization projects every ended task in the ledger that it does not
      return as left out, from any batch and from any attended cell. It does not
      project only the rows of one batch. It replaces the previous projection rather than
      adding to it. Today no projection is written at all.
    witness: tests/test_projection.py::test_a_materialization_projects_every_ended_task_and_replaces_the_last
  - claim: >-
      A merged task whose stored artifacts match what its own event log recorded
      at extraction reaches Q4's result with every kind the projection states:
      `Spec`, `Plan`, `Diff`, `GateSuite`, `Finding` and `PullRequest`. The
      fixture's task has a gate suite and a finding.
      The query is the committed `ontology/queries/Q4-derivation-chain.rq`, read
      from the tree rather than restated in the test.
    witness: tests/test_projection.py::test_q4_over_the_projection_reaches_a_merged_pull_request
  - claim: >-
      A merged task whose stored plan or diff no longer matches what its own
      event log recorded is among the tasks the materialization kept, and is
      absent from Q4's result. A later task of the same spec overwriting it is
      the case. A sibling merged task that still matches, and shares its pull
      request URL, stays in the same result with every kind the projection
      states.
    witness: tests/test_projection.py::test_an_artifact_a_later_task_overwrote_drops_only_the_earlier_chain
  - claim: >-
      A materialization returns the tasks it kept and every task it left out,
      each with a reason from a closed set. A spec whose `Ceilings` spans match
      its tasks in count but not in time has its tasks returned as
      unattributable, and so does a merged task whose span recorded only one of
      the plan hash and the diff length. None of them is projected. A task that
      never merged and recorded neither line is kept. A merged task whose
      stored file a recorded line points at is missing is left out with its own
      reason, and the call returns normally. A run started in the same whole
      second as its span's `Ceilings` is attributed to that span, on a host
      whose local zone is east of UTC.
    witness: tests/test_projection.py::test_tasks_that_match_their_spans_in_count_but_not_time_are_unattributable
  - claim: >-
      A projection that fails the shapes raises and leaves no projection
      behind, so a reader finds none rather than the last one. The shapes are
      an argument that defaults to the repo's
      `ontology/shapes/factory-shapes.ttl`, and the test passes a stricter shape
      the fixture's graph fails.
    witness: tests/test_projection.py::test_a_projection_that_fails_the_shapes_leaves_none_behind
---

## Context

`DESIGN.md` Appendix T (rev 24) and backlog item b-946f03 reopened the emitter on
`ontology/RATIONALE.md`'s own revisit clause. Read the appendix first. It carries
the decision rule this spec and `SA-0108` make runnable, and it states what the
work does not license. This spec builds the projection. `SA-0108` builds the
comparator and a command that runs it once over the merged history.

The rule measures history recorded before backlog item 170. That item moves
artifacts to a store named by content hash, so the overwrite this projection
detects stops arising once it lands. Build against today's ledger and batch
tree, and do not anticipate item 170's interface, which is not designed yet.

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
`gate_results` and `findings` are tables (`saffron/ledger.py`'s `SCHEMA`, from `tasks` at :64). Plan and
diff are files in the batch tree.

The batch tree is keyed by spec, not by task. `task_dir` is `out_dir /
spec.spec_id` (`saffron/cell/session.py:1285`). A later task of the same spec
writes over `plan.json` (`saffron/cell/session.py:1587`) and `patch.diff`
(`saffron/cell/session.py:751`). The earlier task's chain then points at a file
that exists and is not its own.

The event log keeps what each task recorded when the artifact was produced. It
is one log per spec, and each task opens its span with a `Ceilings` event
(`run_task` at `saffron/task.py:270-271`, and `saffron/watch.py:116-132`). The plan's
line carries the first 12 hex digits of its sha256
(`saffron/cell/session.py:1588-1592`). The
diff's line carries its length in characters, though it says bytes: `patch` is a
`str` (`saffron/cell/worktree.py:234`, `saffron/cell/session.py:768`). An edge
stated only when the stored file still matches that record drops the overwritten
chain from Q4's result.

## Out of scope

- **The comparator and the command.** `SA-0108` builds both. Nothing
  materializes at batch end. This spec adds no command and edits no existing file.
- **Nothing here controls execution.** §1.4's bullet stands. No scheduling
  decision reads a triple, and the shapes gate no state transition. The
  projection describes the run record after the fact.
- **No new vocabulary.** Every term Q4 names is already in
  `ontology/factory.ttl`. `ontology/` is forbidden above for the reason
  `docs/agents/issue-tracker.md` gives. A cell that finds a term missing must
  stop and say so rather than invent one. Item b-606ea3 owns the terms this
  spec's code uses and the glossary lacks.
- **The dependency move and four stale sentences are the operator's.**
  `pyproject.toml:21-22`, `ontology/render.py:3-4`,
  `ontology/design_record.py:16-17` and
  `tests/ontology/test_vocabulary_agrees_with_code.py:21-22` each state that
  nothing under `saffron/` imports a graph library. The operator amends all four
  at merge, and moves pyoxigraph, pyshacl and rdflib out of the `dev` group
  (`pyproject.toml:35-37`) with `uv lock`. `uv.lock` is `protected`
  (`.saffron/policy.yaml:61`), so a cell cannot land that move. All three packages
  are installed wherever this code runs today, because the `dev` group is.
- **Recording a full hash for the diff.** Only its length is recorded today.
  Adding a hash means editing `saffron/cell/session.py`, which is forbidden
  here. A diff overwritten by one of the same length goes undetected.
- **Q1, Q2, Q3 and Q5 stay worked examples.** They lost on the analytical case
  and this spec reopens nothing for them.

## Notes for the agent

This spec creates `saffron/projection.py` and its tests, and edits no existing
file. Its criteria declare witnesses and no mutants, so `witness` will report
`skip` for them. `SA-0108` calls this module, so keep the materialization one
call that takes its paths as arguments.

Read `ontology/queries/Q4-derivation-chain.rq` before writing anything. Its
header argues against the emitter and names the one property that argues for
it. Read `tests/ontology/test_queries.py` for the graph shape Q4 expects, and
build the projection to that shape.

**Which rows.** Project a task only in an end state that `TaskShape` lists
(`ontology/shapes/factory-shapes.ttl:12-20`). Leave out every other task and
return it with its reason. `MERGE_TRAIN` is one: `saffron/scheduler.py:67` reads
it, and the vocabulary does not have it. `SpecShape` needs a type and at least
one criterion (`ontology/shapes/factory-shapes.ttl:36-42`). Read both from the
version of the spec whose sha256 equals the task's `spec_sha`. Search every
committed version of `.saffron/specs/` on every ref of the repo's mirror, which
the ledger names in `repos.mirror_path` (`saffron/ledger.py:25`). A task's repo
is reached through its run. A spec
re-runs only once its `spec_sha` changes (`saffron/scheduler.py:59-69`), so an
overwritten task's spec bytes are usually gone from the tree. A task no
committed version matches is left out and returned. So is a task whose matched
version no longer parses or has no criterion. Both default to empty
(`saffron/intake.py:153-154`), and one such task must not fail the shapes for
every other task.

**Which kinds.** State `Spec`, `Plan`, `Diff`, `GateSuite`, `Finding` and
`PullRequest` edges. State no `ScopeProposal`, `TouchesSet` or `Rebuttal`. Their
shapes need a ratifying operator and a stance
(`ontology/shapes/factory-shapes.ttl:170-195`). The ledger records the
critic's verdict and not the implementer's stance, and no ratifier
(the `findings` table, `saffron/ledger.py:133`). Stating one would author the record rather than
derive it.

**Attribution.** Tie a task to a `Ceilings` span of its spec's `events.jsonl`
by time, not by position. The task's `runs.started_at` must fall after the
span's `Ceilings` timestamp and before the next one (`saffron/ledger.py:59`).
The first is UTC text and the second is epoch seconds. Position alone is wrong
in both directions. A span can have no task, because `Ceilings` is written
(`saffron/task.py:270`) before the task's run row exists
(`ledger.create_run`, `saffron/cell/session.py:1335`). A task can have no span: `saffron/replay.py:54`
writes none, and nor did any task before `Ceilings` existed. A task no single
span holds is unattributable, and so is every task in a span that holds more
than one. Leave each such task out and return it with that reason.

**Where the two lines are.** The plan hash is the `detail` of a `PhaseStart`
with phase `IMPLEMENT` and label `PLAN`, reading `accepted, sha256 <12 hex>`.
The diff length is the `detail` of a `Teardown` with step `exported`, reading
`exported <N> bytes to …`. An older log worded differently has neither. Read each log with
`saffron.events.read_log`, and have the fixture builder write through
`EventLog`, so the fixture and the parser cannot agree on a wrong key.

**A missing line counts only where the artifact exists.** A merged task
produced both a plan and a diff. A span of a merged task lacking either line
makes it unattributable. A `pushed_sha` is no proof, because
`push_unpackaged_work` pushes tasks that never became ready. `EventLog.append`
never raises (`saffron/events.py:390`), so a lost line is possible and silent.
A task that never merged can end without a plan or a diff. `PREFLIGHT_FAILED`,
`PLAN_REJECTED` and a `NOT_IMPLEMENTED` with no commits are the cases. Its
missing line states no edge and leaves it projected.

**A merged task missing a stored file a recorded line points at is left out
with its own reason,** and the call never raises. An old merged task can lack
one, and `SA-0108` runs this over all of them. A merged task that lacks both a
line and a file is returned as missing a line. A task that never merged is not
held to this rule, so a `PREFLIGHT_FAILED` task with no `plan.json` stays
projected.

**Mint one `PullRequest` node per task.** Never mint it from `pr_url`. A re-queued task
at the same `spec_sha` inherits the first one's pull request
(`saffron/scheduler.py:647-650`), so two tasks share a `pr_url`. One node for
both would hide an overwritten chain behind its whole sibling in Q4's result. `SA-0108` keys its comparison by task through this IRI.

**Compare times at whole seconds.** `runs.started_at` has whole-second
resolution and `Ceilings.timestamp` is `time.time()` (`saffron/task.py:271`).
Compare the run's start with the floor of the timestamp, or a run started in the
same second as its `Ceilings` reads as earlier. `runs.started_at` is SQLite's
`datetime('now')`, UTC with no offset. Parse it as UTC, never as local time. The
fourth criterion's test sets `TZ` east of UTC, because the cell runs in UTC and
a naive parse passes there.

**What it returns.** Each kept task's id maps to its `PullRequest` IRI. Each
left-out task comes with a reason from a closed set that names `unattributable`
apart from the rest. `SA-0108` reads both rather than deciding them again, and
keys its comparison by that IRI. The third criterion's test reads both tasks'
IRIs from this value, never from a string it spells.

**Where things are.** Take the ledger, the `out_dir` each `task_dir` is built from (`saffron/cli.py:152`,
`~/.saffron/batches/v0` by default) and the output path
as arguments. Never spell `~/.saffron` inside the module. Read Q4 and the shapes
from Saffron's own source tree, never from a target repo. `pyproject.toml:44-45`
packages only `saffron/`, and another repo has no `ontology/`. Validate with
`ontology/factory.ttl` loaded into the data graph, as
`tests/ontology/test_shapes.py:43-46` does. The shapes check class membership
through its subclass axioms.

**Compare lengths in characters.** The diff's recorded number is `len` of a
`str`. Compare it with the length of the stored file read as text, never with
its size on disk. Read it with `open(path, newline="", encoding="utf-8")`, since Python 3.12's
`read_text` takes no `newline`. Hash `plan.json` from its bytes, as
`hash_artifact` hashes the encoded text. Put a non-ASCII
character in every fixture diff, since this
repo's diffs carry them and an ASCII fixture passes either way.

Distinguish `error` from `fail`. A projection that fails the shapes is an error
in this module's own sense. It aborts the materialization and removes the
previous projection.

**Import anything new inside the test body.** Module scope does not work. A
module-scope import of a name this change adds turns `revert`'s reverted run
into a collection error. `revert` reads that error as `skip`, and the
anti-theater gate then checks nothing.

Write each test against the unfixed code before trusting it. The third
criterion matters most. Build its fixture from two merged tasks of one spec,
the second overwriting the first's stored file. Give the overwritten task and
its whole sibling the same `pr_url`, so an IRI minted from it fails. Assert the
overwritten task's id is in the kept set. A left-out reason there would empty
`SA-0108`'s count. Drive the plan case and the diff case in the one test.

The fourth criterion's test drives these cases:
- spans misaligned in time.
- a merged task's span with no plan-hash line, and one with no diff-length line.
- a task that never merged and recorded neither line, which is kept.
- a merged task's `patch.diff` deleted, with a missing-file reason returned by a
  call that returns normally.
- a run in second N whose `Ceilings.timestamp` is N+0.7, under `TZ=JST-9`
  with `time.tzset()`. A POSIX zone string needs no zone data, as
  `tests/test_events.py:1323` shows, and `round()` of N+0.5 is N for an even N. Restore `TZ` and call `time.tzset()`
  again in a `finally`.

**Keep the fixtures compact.** Write one builder in the test file for all five
tests. It takes a list of tasks, each with its spec version, state,
merged or not, run start, `pr_url`, plan text and diff text. It writes the ledger rows, the
`events.jsonl` spans, the committed spec versions and the batch-tree files. The
feature ceiling is 600 changed lines, and five hand-built fixtures would pass
it.
