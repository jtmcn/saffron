---
id: SA-0013
title: The Spec fixture's arguments reach nothing that checks them
type: test
priority: 1
depends_on:
  - SA-0012
touches:
  - tests/test_package.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  # Tests-only for the same reason SA-0012 was: the fixture is wrong, not the
  # parser it calls. A change under `saffron/` here would be `parse_spec`
  # bending to accommodate a test.
  - saffron/**
budget_usd: 4
max_attempts: 2
max_turns: 40
risk: standard
acceptance:
  - claim: "the values `_spec()` is called with reach the parsed `Spec`, so the
      fixture cannot drift in value the way the two fakes it replaced drifted
      in shape"
    witness: tests/test_package.py::test_the_spec_fixtures_arguments_reach_the_parsed_spec
  - claim: "the conflict path still persists `MERGE_FAILED` and pushes nothing"
    witness: tests/test_package.py::test_a_conflict_persists_merge_failed_and_pushes_nothing
    preserves: true
  - claim: "the green-cell path through the `packageable` fixture still becomes
      a branch, a draft PR and a queue line"
    witness: tests/test_package.py::test_a_green_cell_becomes_a_branch_a_draft_pr_and_a_queue_line
    preserves: true
---

## Context

`SA-0012` replaced two `SimpleNamespace` fakes with `_spec()`, which builds a
real `Spec` by putting a string literal through `parse_spec`. That was the right
shape and it shipped correctly. Review of the diff then found the defect had not
died — it had moved one level down, from attribute *shape* to attribute *value*.

`_spec()` assembles frontmatter and a `## Acceptance criteria` section by string
concatenation. Nothing asserts that what goes in comes out.

## Problem

Measured, not reasoned. Two mutations of the helper, each run against the whole
module:

- break the section header so `_CRITERIA_SECTION` misses and
  `acceptance_criteria` parses to `[]` — **97 passed**
- corrupt the `touches` line so it yields `["ZZZf.txt"]` — **97 passed**

`["f.txt"]` and `["it works"]` appear in `tests/test_package.py` only as
arguments to `_spec()`. No assertion mentions either. So the `packageable`
fixture, which feeds most of this module, can silently start handing `package()`
a spec with no criteria and a scope that matches nothing, and every test stays
green while exercising less than its name claims.

That is `SA-0012`'s own thesis — a fixture whose contents nothing checks — one
level down. `parse_spec` changing its criteria regex is enough to trigger it, and
that regex has no test tying it to this fixture.

## The shape

A new test beside the existing one, asserting *which* `Spec` the helper builds
rather than only that it built one:

```python
def test_the_spec_fixtures_arguments_reach_the_parsed_spec():
    spec = _spec(touches=["f.txt"], criteria=["it works"])
    assert spec.touches == ["f.txt"]
    assert spec.acceptance_criteria == ["it works"]
```

Two assertions over one construction. The file is in `touches`, so this is in
scope in a way it was not when `SA-0012` was written.

## Out of scope

**Anchoring the witness to the two call sites.** `SA-0012`'s first criterion
claimed *"both `package()` call sites are handed a real `Spec`"*, and its witness
checks the helper, not the sites — reintroduce a `SimpleNamespace` at either call
site tomorrow and it stays green. That is a real gap, it is not this one, and
it wants a different shape than an assertion (there is no cheap test that reads
how a fixture was constructed). Left deliberately.

**`_cell_outcome`.** Still a `SimpleNamespace` standing in for `CellOutcome`,
still out of scope for the reason `SA-0012` gave: it has not cost anything yet,
and `_spec` is the model when it does.

**Asserting more of `parse_spec`.** `id`, `title`, `type` and `risk` are literals
in the helper's string with no keyword behind them; asserting them tests the
parser, which `tests/test_intake.py` already does. Only the two arguments need
constraining, because only they vary.

**Amending `SA-0012`'s spec file.** It is the record of what was driven.
`.saffron/**` is `forbidden` here as everywhere.

## Notes for the agent

**The assertion must fail under the mutation that motivated it.** This is the
whole point of the task, and `SA-0012` is the counter-example: it prescribed
`isinstance(spec, Spec)` over a helper calling a function already annotated
`-> Spec`, which cannot fail. Before you finish, break the helper's `touches`
line, confirm the witness goes red, and put it back. A witness that passes
against a broken helper is not a witness — §5.4's `tool` defect, in a test.

**A new test, not an extension of the existing witness.** Folding these
assertions into `test_the_package_fixtures_build_a_real_spec` is the tidier
diff and it fails the `criteria` gate: a criterion that does not declare
`preserves` must name a witness that was *not* green at `base_sha`, or it
proves nothing about this change (`saffron/gates/core/criteria.py:100`). The
existing witness is green at base. Leave it exactly as it is.

**`_spec()`'s signature does not change.** `touches=()` and `criteria=()`
defaults stay, and both `_spec()` call sites stay exactly as they are. The diff
adds one test function and changes nothing else.

**Two assertions, plus a docstring** — the body shown above, nothing further.
Materially larger means something has been misread.

**`depends_on: SA-0012` is documentation, not a control** — nothing in the
orchestrator reads it (`saffron/intake.py:62` declares the field and no caller
uses it). This spec is undrivable until `#49` merges, because `_spec` does not
exist on `main` before then. An operator sequences it.
