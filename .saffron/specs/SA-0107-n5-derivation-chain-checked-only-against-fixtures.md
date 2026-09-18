---
id: SA-0107
title: N5's derivation chain is checked only against hand-authored fixtures, so no merged change was ever its subject
type: feature
priority: 2
depends_on: [SA-0106]
touches:
  - saffron/projection.py
  - saffron/batch.py
  - tests/test_projection.py
  - pyproject.toml
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
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
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/task.py
  - saffron/cli.py
  - saffron/replay.py
  - saffron/events.py
budget_usd: 20
max_turns: 100
acceptance:
  - claim: >-
      A batch that ended materializes a projection of its own rows as RDF, in
      the vocabulary `ontology/factory.ttl` declares. The projection is built
      from the ledger and the batch tree on every materialization, and a second
      materialization replaces the first rather than adding to it. Today no
      projection is written at all.
    witness: tests/test_projection.py::test_a_second_materialization_replaces_the_projection_rather_than_adding
  - claim: >-
      A merged task reaches the projection with its derivation edges stated as
      triples, and Q4 run over the projection returns that task's pull request
      with every step of its chain. The query is the committed
      `ontology/queries/Q4-derivation-chain.rq`, read from the tree rather than
      restated in the test.
    witness: tests/test_projection.py::test_q4_over_the_projection_reaches_a_merged_pull_request
  - claim: >-
      A merged task whose plan or diff is absent from the batch tree is absent
      from Q4's result. It does not reach the result with an empty step, and it
      does not raise. This is the property the file-path walk cannot hold, and
      the reason the projection states edges rather than deriving them from a
      path template.
    witness: tests/test_projection.py::test_a_merged_task_with_no_stored_diff_is_absent_from_q4
  - claim: >-
      A projection that fails the shapes is reported as an error and is not
      written. A caller reading the projection therefore never reads a graph
      that the shapes reject, and a failed materialization is charged to nobody.
    witness: tests/test_projection.py::test_a_projection_that_fails_the_shapes_is_not_written
---

## Context

`DESIGN.md` Appendix T (rev 24) reopened the emitter on `ontology/RATIONALE.md`'s
own revisit clause. Read it first. It carries the decision rule this spec exists
to make runnable, and it states what the work does not license.

N5 is a numbered requirement in §1. Any merged change must be reconstructible
from stored artifacts alone, expressed as a derivation-chain query so it is
checkable rather than asserted. Q4 is that query. Every input Q4 ever ran against
was Turtle text written by hand in `tests/ontology/test_queries.py`. So Q4 proves
the query is well formed, and proves nothing about any change this repository
merged. That is principle 61.

`SA-0001`'s verdict stands and this spec does not touch it. The five queries were
the analytical case and SQL won all five. This is the operational case for one
query, which the RATIONALE never tested (principle 56).

## Problem

Q4 walks spec to scope to plan to diff to pull request, plus gate suites,
findings and rebuttals. The ledger holds the ends of that chain and not its
middle. `tasks`, `attempts`, `gate_results` and `findings` are rows, and
`findings.rebuttal` is a column. Scope, plan and diff are file paths under the
batch tree, which is what Q4's own header calls the awkward part.

A path that resolves to nothing reads exactly like an artifact that was never
produced. That is the `tool` field one level up. A chain that never linked is
indistinguishable from one that did, and §4.6's audit trail is where that
ambiguity costs the most.

Stating the edges as triples collapses it. A broken chain drops out of Q4's
result instead of rendering as a missing file.

## Out of scope

- **Nothing here controls execution.** §1.4's bullet stands. No scheduling
  decision reads a triple, and the shapes gate no state transition. The
  projection describes the run record after the fact.
- **No new vocabulary.** Every term Q4 names is already in
  `ontology/factory.ttl`. `ontology/` is forbidden above for the reason
  `docs/agents/issue-tracker.md` gives. A cell that finds a term missing must
  stop and say so rather than invent one.
- **Two docstrings the operator amends by hand.** `ontology/render.py` and
  `ontology/design_record.py` each state that nothing under `saffron/` imports a
  graph library. This spec falsifies that sentence. Both files are forbidden
  here, so the operator amends them in the commit that merges this work.
- **Q1, Q2, Q3 and Q5 stay worked examples.** They lost on the analytical case
  and this spec reopens nothing for them.

## Notes for the agent

Read `ontology/queries/Q4-derivation-chain.rq` before writing anything. Its
header argues against the emitter and names the one property that argues for it.
Read `tests/ontology/test_queries.py` for the shape the fixtures assert, because
the projection must satisfy the same query.

Build the projection from two sources. The ledger supplies tasks, attempts, gate
results and findings. The batch tree under `~/.saffron/batches/` supplies the
control artifacts, which §5 extracts and hashes when they are produced. Read the
stored artifact. Never read `/work`.

The store is pyoxigraph and the shapes check is pyshacl, both currently declared
in the `dev` group of `pyproject.toml`. This spec moves what `saffron/` imports
into the runtime dependencies. Move only what the new module imports, and leave
the rest of the group alone.

Materialize at the end of a batch, from `saffron/batch.py`. A materialization
that raises must not end the batch differently. The batch already ended, and its
five stop reasons are a closed set.

This spec stacks on `SA-0106`, which rewrites the same file's scan loop. Read
what that task landed before editing `batch.py`. The materialization runs once
per batch, after the loop, and not once per rescan.

Distinguish `error` from `fail`. A projection that fails the shapes is an error
in this module's own sense. It aborts the materialization and writes nothing.

Write each test against the unfixed code before trusting it. The third criterion
is the one that matters most. Build its fixture by deleting one stored diff from
a batch tree that is otherwise whole.
