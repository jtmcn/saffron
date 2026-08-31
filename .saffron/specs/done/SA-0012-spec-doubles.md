---
id: SA-0012
title: Two SimpleNamespace fakes stand in for Spec and drift silently
type: test
priority: 1
depends_on: []
touches:
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  # Tests-only, and the forbid is load-bearing rather than tidy: the tempting
  # wrong fix is `getattr(spec, "acceptance", [])` in `pr_body`, which puts a
  # default in production code to accommodate a test fake and makes a missing
  # field indistinguishable from an empty one — §5.4's `tool` defect again.
  - saffron/**
budget_usd: 6
max_attempts: 3
max_turns: 60
risk: standard
acceptance:
  - claim: "both `package()` call sites are handed a real `Spec`, so the next
      field `Spec` gains is an error where the spec is constructed rather than
      an `AttributeError` in a suite about pushes and conflicts"
    witness: tests/test_package.py::test_the_package_fixtures_build_a_real_spec
  - claim: "the conflict path — the site at `:679` — still persists
      `MERGE_FAILED` and pushes nothing"
    witness: tests/test_package.py::test_a_conflict_persists_merge_failed_and_pushes_nothing
    preserves: true
  - claim: "the green-cell path through the `packageable` fixture — the site at
      `:783`, which feeds most of this module — still becomes a branch, a draft
      PR and a queue line"
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
---

## Context

`tests/test_package.py:679` and `:783` build a `Spec` out of `SimpleNamespace`,
carrying whatever attributes `package()` happened to read the day they were
written. They are not typed, so nothing checks them against the model. They do
not fail when `Spec` gains a field — they fail later, when some renderer finally
*reads* that field, in tests that are nominally about something else.

`package()`'s parameters are unannotated (`saffron/phases/package.py:500`), so
the type checker cannot see the substitution either; and `.saffron/gates/types`
is a `skip` stub, so no gate would read the annotation if one were added. There
is no mechanical reader of this invariant anywhere today.

That is exactly how it went. `SA-0011` added `Spec.acceptance` and nothing
noticed for three tasks; the moment `pr_body._criteria` read it, fourteen
PACKAGE tests died on `AttributeError: 'types.SimpleNamespace' object has no
attribute 'acceptance'` — none of them about acceptance criteria, all of them
about pushes, conflicts and queue lines. The two `acceptance=[]` lines now
standing at `:685` and `:778` are that patch. They are the shape of the defect,
not the fix: the next field wants a third such line, from whoever happens to
break next.

## Problem

The cost is not the `AttributeError`, which a human reads in seconds. It is the
`touches` interaction, and it is what makes this worth its own spec.

A spec's `touches` is written by reasoning about which files the change *should*
need, and nobody knows these fakes exist until the code runs. So a cell that
adds a field to `Spec` hits a wall with no way over it: editing
`tests/test_package.py` fails `scope`, leaving it fails `tests`. Both burn the
attempt, on every attempt, until the budget is gone — and the agent cannot widen
its own `touches`, which is the point of `touches`. `SA-0011` only got past it
because a human was watching and amended the spec mid-flight. An unattended
night would have spent the whole budget discovering a test fake.

This spec is drivable precisely because it names the file in `touches` up front.
That is the exemption the trap does not grant to anything else.

## The shape

One construction point, in the test module, going through the real parser:

```python
def _spec(*, touches=(), criteria=()):
    return parse_spec("---\n...\n---\n\n## Acceptance criteria\n...")


# :679  spec = _spec()
# :783  spec = _spec(touches=["f.txt"], criteria=["it works"])
```

`tests/test_report.py:21` and `:1240` are the prior art and the shape to copy: a
string literal parsed by `parse_spec`, not a hand-built model instance. Going
through intake rather than `Spec(...)` keeps the fixture honest about what a
real spec file can actually say, and both call sites then diverge only in the
two fields they actually differ in.

The blast radius was measured, not assumed: these two are the only structural
`Spec` doubles in the repo. `tests/test_session.py:86` builds a real `CellSpec`,
`tests/test_report.py` goes through `parse_spec`, and `saffron/replay.py:51`
uses a real `Spec` from `load_spec`.

## Out of scope

**Annotating `package()`.** `spec: Spec` on its signature is one word and gives
pyright teeth in an editor, but `outcome`, `ledger` and `watch` sit bare beside
it, `types` is a skip stub, and no gate would read any of them. Annotating one
parameter of four, checked by nothing in the loop, is the appearance of a
control — Appendix I's founding defect. The `types` gate is the item that
unlocks it, and it is not this one.

**`_cell_outcome` at `:609`.** A third `SimpleNamespace`, standing in for
`CellOutcome` with the same drift shape. It is out of scope because it has not
cost anything yet and the backlog item was measured against `Spec`; when it
does, it wants the same fix and this helper is the model. Left deliberately, so
that the next field `CellOutcome` gains lands as an ordinary failure in this
module rather than as a spec that cannot be widened.

**Dropping `tests/test_package.py` from `SA-0011`'s `touches`.** It is declared
there only because of this defect, and the line is dead once this ships — but
`SA-0011` is merged, its spec file is the record of what was actually driven,
and `.saffron/**` is `forbidden` here as in every spec since `SA-0001`. If it
comes out, an operator takes it out.

**Any production behaviour change.** `saffron/**` is forbidden. If a test cannot
be made to pass without touching it, that is a finding to raise, not a diff.

## Notes for the agent

**Preserve the two fields the sites differ in.** `:679` passes `touches=[]` and
`acceptance_criteria=[]`; `:783` passes `touches=["f.txt"]` and
`acceptance_criteria=["it works"]`. `parse_spec` derives `acceptance_criteria`
from the markdown `## Acceptance criteria` section, not from frontmatter, so the
helper writes that section — the frontmatter `acceptance:` key is a different
list and declaring both raises `SpecError` at intake.

**`id: SA-0005` is load-bearing in both fakes.** The surrounding ledger rows,
branch names and task ids are built from that string; the fixture spec's id has
to keep matching them or the tests fail for a reason that has nothing to do with
this change.

**The witness for the first criterion is a new test and must actually assert the
invariant.** `isinstance(spec, Spec)` over what the helper returns is the whole
claim — the property that was violated, checked at the point of construction.
Do not reach for a test that asserts the helper's string literal parses; that is
a test of `parse_spec`, which already has one.

**Roughly twenty lines.** If the diff is materially larger, something has been
misread — the two call sites and one helper are the entire change, plus the
witness test.
