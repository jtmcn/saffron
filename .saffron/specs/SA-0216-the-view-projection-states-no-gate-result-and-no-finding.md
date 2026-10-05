---
id: SA-0216
title: The view projection states no gate result and no finding, so no page can say why an attempt failed
type: feature
priority: 2
depends_on: [SA-0215]
consumes:
  - saffron/view/graph.py:build
estimated_lines: 376
estimate_measured: true
touches:
  - saffron/view/graph.py
  - tests/test_view_graph.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - .saffron/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - saffron/projection.py
  - saffron/ledger.py
  - saffron/cli.py
budget_usd: 20
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      For each attempt of a task `build` states, when the attempt has at
      least one gate result, `build` states one `GateSuite` `data:gatesuite-<attempt_id>`, `prov:wasInformedBy` the
      attempt, and one `Diff` `data:diff-attempt-<attempt_id>` that the
      attempt `prov:generated`. Each of that attempt's gate results is a
      `GateResult` `data:gate-result-<gate_result_id>`, `prov:wasGeneratedBy`
      the suite, with `earl:subject` the diff and `earl:mode
      earl:automatic`. Its `earl:result` node has one `earl:outcome`, by
      `pass` to `earl:passed`, `fail` to `earl:failed`, `error` to
      `earl:cantTell` and `skip` to `earl:inapplicable`. An attempt with no
      gate result states no suite and no diff. A baseline gate result, which
      names a run and no attempt, is not stated. The witness drives all four
      statuses through one attempt. Beside it are an ungated attempt and a
      second gated attempt of the same task, a gated attempt of a second
      task, and a baseline result of the same run. Spare baseline results
      are recorded first, so no gate result id equals its position. It
      checks each result's suite and subject against its own attempt.
    witness: tests/test_view_graph.py::test_each_gate_status_maps_to_its_own_earl_outcome
    wrong_versions:
      - "`error` maps to `earl:failed`, so a gate that broke reads as code that is wrong."
      - "`skip` maps to `earl:passed`."
      - Each gate result gets its own suite node rather than one per attempt.
      - Every attempt states a diff, gated or not.
      - The gate results are read without the attempt filter, so a baseline result is stated too.
      - Results are named by a running counter over the stated results rather than by `gate_result_id`.
      - The suite and the diff are bound once per task, so a later attempt's results name the first gated attempt's suite and diff.
      - The suite and the diff carry over from the previous task, so the second task's results name the first task's.
  - claim: >-
      Each stated gate result carries `factory:failureCount`, an
      `xsd:integer` equal to the number of `failures` rows naming its
      `gate_result_id`, and 0 when there are none. No failure's `file`,
      `code`, `message` or `line`, and no gate result's `summary`, appears
      in the graph's turtle. The witness drives a `fail` result with three
      failures and a `pass` result with none, in one attempt. Each of the
      five fields carries a value found nowhere else in the fixture, and the
      witness asserts that none of the five appears.
    witness: tests/test_view_graph.py::test_a_gate_result_counts_its_failures_and_states_no_line
    wrong_versions:
      - The count is taken over the attempt's failures, so the clean result reads 3.
      - A result with no failures states no `failureCount`.
      - Each failure's message is stated, as an `rdfs:comment` on the result.
      - Each failure's file is stated, as an `rdfs:comment` on the result.
      - Each failure's code is stated.
      - Each failure's line number is stated.
      - The gate result's `summary` is stated.
  - claim: >-
      A gate result is `earl:assertedBy` its gate's node. Each of the nine
      names in `CoreGateShape`'s `sh:in` asserts as `factory:<name>`, the
      vocabulary's own individual. Each of the six names in
      `GateRoleShape`'s `sh:in` asserts as `data:gate-<name>`, typed
      `factory:ContractGate` alone, with `factory:role factory:<name>`. Any
      other name asserts as `data:gate-<name>`, typed
      `factory:RepoDefinedGate` alone, with no role. The witness drives all
      fifteen set members and `structure`, each as one result of one
      attempt.
    witness: tests/test_view_graph.py::test_a_core_gate_is_its_vocabulary_individual_and_a_repo_gate_is_typed_by_role
    wrong_versions:
      - A core gate asserts as `data:gate-<name>` typed `factory:CoreGate`.
      - A role-named gate is typed `factory:RepoDefinedGate` and given its role.
      - A role-named gate is typed both `factory:ContractGate` and `factory:RepoDefinedGate`.
      - "`structure` is given `factory:role factory:structure`."
  - claim: >-
      A task with findings and no gated attempt keeps its own triples and
      its attempts' triples, states none of its findings, and adds one
      `LeftOut` with reason `findings_without_diff` to `left_out`, whatever
      its number of findings. A task SA-0215 already leaves out, by its
      state or by its risk, gets no second entry. No triple names that
      task's attempts, suites, diffs, gate results or findings. The witness
      drives five tasks in this order. They are a task with a gated attempt
      and one finding, a task with an ungated attempt and two findings, a
      task with no attempt and one finding, then three left-out tasks. A
      task in an unknown state has an ungated attempt and one finding. A
      task at an unknown risk has a gated attempt with a failing result and
      one finding. A second task at an unknown risk, in a known state, has
      an ungated attempt and one finding.
    witness: tests/test_view_graph.py::test_findings_without_a_gated_attempt_are_left_out_and_the_task_kept
    wrong_versions:
      - One `LeftOut` is added per finding rather than per task.
      - The whole task is left out with its findings.
      - Only a task that has attempts is checked, so a task with no attempt states a finding with no subject.
      - The last gated diff is not reset between tasks, so a later task's findings attach to an earlier task's diff.
      - A task already left out for its state or its risk also gets a `findings_without_diff` entry.
      - A separate SELECT over `gate_results` outside the kept-task loop states a suite and a diff for a left-out task's gated attempt.
      - Findings are read for every task in the ledger, so a left-out task's finding is stated.
  - claim: >-
      Each finding of a stated task with a gated attempt is a `factory:Finding`
      `data:finding-<finding_id>`. It has its `factory:severity`, and
      `earl:assertedBy` `data:lens-<lens>`, which is typed
      `factory:CriticLens`. Its `earl:subject` is the diff of the task's
      last gated attempt, the one with the highest `attempt_id`. It has
      `earl:mode earl:semiAuto` and its `factory:claim`, plus
      `factory:verdict` when the row's verdict is not null. The witness
      drives all three severities and three lenses. It gives one task two
      gated attempts in one phase, then a gated attempt in a later phase,
      then an ungated one. A second task's finding names that task's own
      diff. One finding has a verdict and one has none.
    witness: tests/test_view_graph.py::test_a_finding_is_asserted_by_its_lens_against_the_last_gated_diff
    wrong_versions:
      - The subject is the task's first gated diff.
      - The subject is the gated attempt with the highest `n`, which picks the second attempt of the first phase.
      - The subject is the last diff of the whole ledger, so the first task's findings name the second task's diff.
      - A finding states `earl:mode earl:automatic`.
      - A null verdict is stated as an empty string.
  - claim: >-
      `build` reads the core gate names and the gate role names from the
      `sh:in` sets of the node shapes in `shapes_path` that target
      `factory:CoreGate` and `factory:GateRole`. It never reads them from a
      literal list, from `DEFAULT_SHAPES` when another file is given, or
      from the vocabulary's typing. The witness builds one ledger twice.
      With the default shapes, `dead` and `prose` are repo-defined gates.
      With a shapes file that adds `factory:dead` to the core set and
      `factory:prose` to the role set, `dead` asserts as `factory:dead` and
      `prose` as a contract gate with role `factory:prose`. There `lint`
      keeps its role and `scope` stays core.
    witness: tests/test_view_graph.py::test_the_gate_sets_are_read_from_the_shapes_it_is_given
    wrong_versions:
      - The core set is a literal list of nine names.
      - The role set is a literal list of six names.
      - Both sets are read from `DEFAULT_SHAPES`, whatever `shapes_path` is.
      - The core set is read from the vocabulary's `a factory:CoreGate` triples.
  - claim: >-
      Each of the five view queries, `V1` to `V5` under
      `ontology/queries/view/`, run over `build`'s turtle loaded into a
      `pyoxigraph` store with the vocabulary, returns the rows the fixture
      implies. `V1` gives the batch with its stop reason and one task. `V2`
      gives that task's spec label and pull request. `V3` gives exactly two
      gate rows, `lint` failed with 2 failures and `scope` passed with 0.
      `V4` gives the one finding, with its task, lens, severity and claim.
      `V5` gives the one task whose run has no batch.
    witness: tests/test_view_graph.py::test_each_view_query_reads_what_build_states
    wrong_versions:
      - The attempt and the diff are swapped on `prov:generated`, so `V4` returns no row.
      - The suite and the attempt are swapped on `prov:wasInformedBy`, so `V3` returns no gate row.
      - "`factory:claim` is not stated, so `V4`'s row has no claim."
---

## Context

Backlog item **b-a1d649**, which cites `DESIGN.md` §6 and §6.2, with ADR 9
(`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md`).
The design is `docs/superpowers/specs/2026-10-05-run-record-view-design.md`,
and its "Settled while planning" section (`:43-58`) fixes the choices below.
The plan's Task 3 (`docs/superpowers/plans/2026-10-05-run-record-view.md:568-660`)
was measured at 678 lines and split in two. `SA-0215` is the parent and
builds `saffron/view/graph.py`. This spec is the child. It adds the gate
results and the findings to the graph that `SA-0215`'s `build` returns.

Line numbers below were read at `c1a04c8c`.

**What `SA-0215` gives this spec.** Its `saffron/view/graph.py` has the
frozen dataclasses `LeftOut(task_id, spec_id, reason)` and
`ViewGraph(turtle, left_out)`, the exception `ViewGraphError`,
`open_read_only(path)` and `build(db, *, shapes_path=DEFAULT_SHAPES)`. Its
`build` states batches, runs, tasks, phases and attempts. Each attempt is
`data:attempt-<attempt_id>`. A task whose state or risk is outside the
shapes' sets is left out with reason `unknown_state` or `unknown_risk`, and
nothing of it is stated. `build` validates the whole graph with `pyshacl`
against the shapes and the vocabulary, and raises `ViewGraphError` on a
failure. Read the merged file before you edit it. Keep every name and every
reason it has.

**The ledger rows.** A `gate_results` row names an attempt or a run and
never both, by the `CHECK` at `saffron/ledger.py:182`. A row naming a run is a
baseline result, and this spec states none. `failures` (`:192-199`)
carries `file`, `code`, `message` and `line` per `gate_result_id`.
`findings` (`:207-219`) carries `task_id`, `lens`, `severity`, `claim` and
a nullable `verdict`, and names no attempt.

**The shapes.** `GateResultShape` (`ontology/shapes/factory-shapes.ttl:211-220`)
requires one `earl:assertedBy` of class `factory:Gate` and an
`earl:subject` of class `earl:TestSubject`. It also requires `earl:mode
earl:automatic`, one outcome among the four EARL ones, and a non-negative
integer `failureCount`. `FindingShape` (`:196-206`) requires one severity
among three, one `earl:assertedBy` of class `factory:CriticLens`, an
`earl:subject` and one `earl:mode`. `GateShape` (`:95-99`) makes a gate
exactly one of core, contract and repo-defined. `ContractGateShape`
(`:150-153`) requires one `factory:role` of class `factory:GateRole`.
`factory:Diff` is an `earl:TestSubject` (`ontology/factory.ttl:44`).

**The two gate sets.** `CoreGateShape`
(`ontology/shapes/factory-shapes.ttl:112-116`) and `GateRoleShape` (`:118-121`) close their sets with a node-level `sh:in`,
on the shape that targets the class. `projection._sh_in`
(`saffron/projection.py:255-267`) finds shapes by `sh:path`, so it cannot
read either set. The vocabulary types each member too, nine core gates at
`ontology/factory.ttl:85-93` and six roles at `:97-99`. The shapes file is
the set `build` reads, because `shapes_path` is the caller's to choose.

**The readers.** `V3` (`ontology/queries/view/V3-task-timeline.rq:17-23`)
walks from an attempt to its suite by `prov:wasInformedBy`, then to each
result by `prov:wasGeneratedBy`. `V4`
(`ontology/queries/view/V4-task-findings.rq:9-12`) walks
from a finding's subject back to the attempt that `prov:generated` it. The
expected results beside them were written by hand in PR #688 against a
fixture graph. No Python produces these triples yet.

## Problem

1. **One suite and one diff per gated attempt.** Inside the loop over the
   tasks `build` keeps, read each attempt's gate results with
   `attempt_id = ?`. A left-out task's attempts are never read. When there is at least one, state the
   suite and the diff as criterion 1 says. Baseline rows never match
   that filter.
2. **One `GateResult` per row.** State the triples criterion 1 names, and
   `failureCount` from a `COUNT(*)` over `failures` for that
   `gate_result_id`. The outcome is a blank node. The status-to-outcome map
   is the design's
   (`docs/superpowers/specs/2026-10-05-run-record-view-design.md:47-49`). It keeps `error`
   and `fail` apart, as `CLAUDE.md`'s invariant asks.
3. **The gate node.** A name in the core set is `factory:<name>`, and
   `build` adds nothing about it, since the vocabulary types it. Any other
   name is `data:gate-<name>`, typed and given a role as criterion 3 says.
4. **Read the two sets from `shapes_path`.** Collect the `sh:in` list of
   each node shape whose `sh:targetClass` is `factory:CoreGate`. Do the
   same for `factory:GateRole`. `SA-0215` adds a helper that matches on
   `sh:targetClass` for its in-flight states. Use it.
5. **Findings.** For each task `build` keeps, read its findings. With a
   gated attempt, state each as criterion 5 says, and type each lens node
   `factory:CriticLens`. Without one, state none and append
   `LeftOut(task_id, spec_id, "findings_without_diff")` once.
6. **Failure text stays out.** Nothing from `failures` but the count enters
   the graph, and nothing from `gate_results.summary`. ADR 9
   (`docs/adr/0009-a-read-only-view-renders-the-run-record-from-the-graph.md:29-30`) keeps failure lines in the ledger, where a page reads them by
   gate result id.

## Out of scope

- Baseline gate results. They name a run, the view has no page for them,
  and the next spec decides whether it needs one.
- Batches, runs, tasks, phases and attempts. `SA-0215` states them. Change
  none of their triples and none of the parent's tests.
- `saffron serve` and the pages. A later spec reads `build`'s output.
- A finding's `file`, `line`, `anchored`, `rebuttal` and `adjudication`.
  No view query reads them, and the vocabulary has no term for most.
- A status or severity outside the closed sets. `GateStatus`
  (`saffron/gates/contract.py:17`) and `Severity`
  (`saffron/agents/findings.py:23`) are literals, and the shapes reject
  anything else. So `build` raises `ViewGraphError` there, and leaves no
  such row out. A value outside those sets is a broken invariant, not a
  task to hide. The known consequence is that one such row stops
  `saffron serve` from starting until it is repaired. The operator's
  session measured the real ledger at base. Its attempt-bound gate results
  hold exactly the statuses `pass` (3941), `fail` (573), `skip` (295) and
  `error` (1). Its findings hold exactly `blocker` (84), `concern` (131)
  and `note` (46). The first writer's prototype of both halves built that
  ledger read-only in 3.4 s, with no task left out.
- `ontology/**`, the shapes and the view queries. They are forbidden.

## Notes for the agent

**This change is new code.** Each criterion declares a witness and no
mutant, so the `witness` gate reports `skip` for all seven. The wrong
versions under each criterion are what its witness must kill. Do not run
them yourself.

**Commit as each witness passes.** Seven witnesses, seven commits at
least. A turn cut by a bound then loses one witness's work.

**Every witness must fail without this change.** Import
`saffron.view.graph` inside each test body, never at module scope, for the
reason `tests/test_projection.py:3-6` gives. Each witness then fails on an
assertion against the parent's `build`, which states no gate result and no
finding.

**Fixtures.** Build each ledger with `Ledger(tmp_path / "ledger.db")`, close
it, then call `build(open_read_only(...))`. Reuse `SA-0215`'s helpers in
`tests/test_view_graph.py` where they fit. Record gate results with
`record_gate_result` and `attempt_id=`, or `run_id=` for the baseline
row (`saffron/ledger.py:1828-1834`). Record findings with
`Ledger.record_findings(task_id, findings)` (`:1773`), which returns their
ids in order. `Ledger.open_attempt(task_id, phase)` (`:1333`) numbers `n`
within a phase, so two attempts in one phase get `n` 1 and 2. Set one
finding's verdict with a raw `UPDATE`, or with `record_rebuttal`.

**Criterion 1.** Read each result's owning attempt back from
`gate_results`, then assert its `prov:wasGeneratedBy` and `earl:subject`
name that attempt's suite and diff. One shared suite or diff then fails.

**Criterion 2.** Give each failure's `file`, `code`, `message` and `line`,
and the result's `summary`, a value found nowhere else in the fixture.
Assert that none of the five appears in `ViewGraph.turtle`.

**Criterion 4.** Compare `left_out` as a sorted list of
`(task_id, spec_id, reason)` tuples, so a duplicate entry fails. Put the
task with a gated attempt first, so a diff carried over from it would show
on the tasks after it. Take each of the three left-out tasks. Assert that no
triple names its attempt, suite, diff, gate result or finding, as subject
or as object. `SA-0215` checks the state before the risk, so give both
unknown-risk tasks a known state. The two ungated left-out tasks are what
a second `findings_without_diff` entry would show on, one per reason.

**Criterion 6.** Write the edited shapes under `tmp_path`, from
`DEFAULT_SHAPES`'s text. `factory:dead` and `factory:prose` are typed
nothing in the vocabulary, so the edit also drops `sh:class factory:Gate`
from `GateResultShape`'s `earl:assertedBy` and `sh:class factory:GateRole`
from `ContractGateShape`'s `factory:role`. Assert each text you replace
occurs once. The witness can only add members. A shapes file that drops
one fails validation, because the vocabulary still types it. So a build
that unions a literal list with the shapes' set passes this witness, and
the review is where that is caught.

**Criterion 7.** Load the turtle and `projection.VOCABULARY` into one
`pyoxigraph.Store`, and read each query's text from its file. The fixture
needs one batch with one run and one task, with a `pr_url` set. Its
attempt has a `lint` fail with two failures and a `scope` pass. That task
has one finding. A second task sits on a run with no batch.

**Offset the ids.** A fresh ledger numbers each table from 1, so a node
named by a running counter reads right by accident. Before each fixture's
own rows, record spare baseline gate results on a spare run, and spare
findings on a spare task. Delete the spare findings and the spare task
before `build`. Their ids stay used, so no gate result or finding id
equals its position. Build every expected IRI from the ids the ledger
returned.

**Measured on a prototype at `c1a04c8c`.** A prototype of this half passed
all seven witnesses, and each failed against `SA-0215`'s half alone. Each
of the 38 wrong versions above was applied to it as an edit. Each failed
its own criterion's witness.

**The IRI forms are a contract.** `SA-0217` parses a gate result's id
from `data:gate-result-<gate_result_id>`, and a gate's name from
`factory:<name>` or `data:gate-<name>`. Spell them exactly as the claims
do.

**Annotate what you add.** The `types` gate checks the whole tree, and
an unannotated helper hides its values' types.
