---
id: SA-0020
title: the dependency gate refuses every dependency instead of scheduling it
type: feature
priority: 2
depends_on:
  - SA-0019
touches:
  - saffron/scheduler.py
  - saffron/cli.py
  - tests/test_scheduler.py
  - tests/test_cli.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/reconcile.py
  - saffron/cell/**
  - saffron/gates/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 16
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`SA-0016` shipped four of §4.2.1's six refusals. Three of them decide something.
The fourth does not:

```python
if candidate.spec.depends_on:
    return f"depends_on is not scheduled: {', '.join(candidate.spec.depends_on)}"
```

`saffron/scheduler.py`, in `_refusal`. It never looks the dependency up. Any spec
with a non-empty `depends_on` is refused, whatever state its parent is in, and
`tests/test_scheduler.py::test_a_non_empty_depends_on_refuses` pins exactly that.

§4.2 states the rule the gate is standing in for: **all `depends_on` tasks have
reached `READY_FOR_REVIEW`** — not `MERGED` — and *"a dependent task branches off
its parent's branch rather than `base_sha` — stacked branches."* The reasoning is
in the same paragraph: requiring `MERGED` means a dependency can never be
satisfied inside a batch, so a 3-node DAG takes three nights with two cells idle
each night.

Measured, 2026-08-30: `saffron queue --repo .` refuses three specs this way —
`SA-0006` and `SA-0007` behind `SA-0005`, and `SA-0018` behind `SA-0016`. `SA-0016`
had reached `READY_FOR_REVIEW` and in fact merged as #60; under §4.2's rule its
dependent was schedulable and the scan said otherwise. The message compounds it:
*"depends_on is not scheduled: SA-0016"* names a spec whose state was never read,
and reads as a verdict about `SA-0016`.

## Problem
- **A batch cannot run a dependency chain at all.** Every dependent spec on disk
  is refused, so the DAG §4.2 designed the stacking rule for has never had a
  second node scheduled. Three of this repo's own specs sit behind it.
- **The message describes a check that did not happen.** An operator reading
  "is not scheduled: SA-0016" investigates `SA-0016`. There is nothing there to
  find.
- **Admitting the dependent without stacking it is the other wrong fix.** A
  dependent branched from `base_sha` runs against a default branch missing every
  commit its parent made — it is built on sand by a different route than the one
  §4.2 names, and its gates would judge a tree that never existed. §4.2 pairs the
  gate and the stacking in one sentence, so they ship together or not at all.
  **This spec therefore admits only a parent that is already in `base_sha`** —
  `MERGED`, nothing earlier. That needs no stacking, because there is no gap
  between the parent's commits and the tree the child is cut from; the sand is
  gone rather than shored up. §4.2's actual rule is `READY_FOR_REVIEW`, and
  `SA-0022` restores it together with the stacking it requires. Until then a
  dependency costs a night, which §4.2.1's own argument tolerates at this depth:
  *"at this depth there is none to arbitrate."*

## Acceptance criteria
- [ ] A spec whose every `depends_on` id has a `MERGED` task is a candidate,
      not a refusal — `MERGED` and nothing earlier, because a merged parent is
      in the default branch the child is cut from and needs no stacking. A
      parent at `READY_FOR_REVIEW`, `APPROVED` or `MERGE_TRAIN` is refused here
      with a reason that says it is waiting to merge, not that it is unrun
- [ ] A spec whose dependency has no task, or only a task that never reached
      `READY_FOR_REVIEW`, is still refused — and the refusal names the state it
      actually read, so no reason claims a check it did not perform
- [ ] A spec with a dependency at `REJECTED` or `EXHAUSTED` is refused with a
      reason distinct from "not started yet": a parent that will not merge and a
      parent not yet run are different facts about the night
- [ ] The dependency lookup is keyed on spec id across every `spec_sha`, not on
      the pair: a parent is satisfied by the task that merged, whatever sha it
      ran at. But a *dead* state under a superseded `spec_sha` does not speak for
      a parent that has since been edited and re-run — measured on the first
      attempt (2026-08-30), `any(state in DEAD)` over every row reports "will not
      reach `READY_FOR_REVIEW`" about a parent whose fresh task is in flight
- [ ] Re-anchored 2026-08-31, after `SA-0006` and `SA-0007` were retired as
      shipped and `SA-0018`'s own task merged, which filters it out before any
      refusal runs: the live witness is **this spec**. `SA-0020`'s parent
      `SA-0019` is `MERGED` in this machine's ledger, so `SA-0020` is a
      candidate rather than a refusal when the scan runs against this
      repository's own specs and ledger — while `SA-0022` and `SA-0023`, whose
      parent is `SA-0020`, are refused with a reason naming what it actually
      read: no task at `SA-0020`'s current `spec_sha`, because the spec was
      edited after its only run. A witness a later retirement can invalidate is
      one that has to be re-measured, not deleted
- [ ] Every new test runs with no network and no cell

## Out of scope
**Keeping the states this gate reads current.** That is `SA-0019`, which is why
this spec depends on it; `saffron/reconcile.py` is forbidden. This gate reads
`tasks.state` and trusts it.

**Stacking, and admitting a parent that has not merged.** `SA-0022`, split
out of this spec on 2026-08-30 after the first attempt measured why they cannot
ship together here: a stacked worktree makes the child's exported patch — the
task's only durable product — contain the parent's diff as well, because
`export_patch` is computed from `base_sha`. `saffron/phases/package.py` then
applies that combined patch to the current default branch, and re-verification
re-applies the parent's hunks once the parent has merged separately. Fixing that
needs PACKAGE, which is forbidden here and forbidden in the first attempt too —
the criteria could not be satisfied inside the files the spec declared.
`saffron/cell/**` joins the deny list so the boundary is a rule rather than an
intention.

**The merge train, and what happens when a stacked parent is rejected.** §4.2
names that risk and assigns it to §6.1 — *"exactly the risk the merge train
exists to catch, and it costs one wasted task rather than three wasted nights."*
`saffron/phases/**` is forbidden. A child stacked on a parent that later gets
rejected is a wasted task by design, not a defect this spec prevents.

**Multi-node DAG ordering within one batch.** One cell runs at a time (K=1), so
the scan only has to answer whether a dependent is admissible now. Ordering
several ready dependents against each other is the batch runner's, and it does
not exist yet.

**Cross-repo dependencies.** §11 lists them as not supported.

## Notes for the agent
**This spec cannot be scheduled by the gate it fixes.** Its own `depends_on:
[SA-0019]` is refused by the very refusal it replaces, so it runs attended:

```
uv run saffron cell .saffron/specs/SA-0020-the-dependency-gate-refuses-every-dependency.md --repo .
```

`SA-0017` and `SA-0018` both shipped this way — `cli.py`'s `_run_cell` never calls
`build_queue`, so the attended path has always ignored the scan. Do not "fix"
that by exempting this spec inside the scan.

**The state list is not `DONE_STATES`.** They overlap and they mean different
things: `DONE_STATES` asks whether running the spec again would learn anything,
and includes `EXHAUSTED`, `NOT_IMPLEMENTED` and `REJECTED` — none of which
satisfies a dependency. Deriving one list from the other is the mistake this
note exists to prevent. Note the admitting state here is narrower than §4.2's
own rule for a reason stated in **Problem**, and narrower still than
`DONE_STATES`: `MERGED` alone.

**`tasks_by_spec` is keyed `(spec_id, spec_sha)`** and returns a list per key,
so a lookup across shas is a scan of its keys — no new query needed, and the
existential rule (`any`, not last-row-wins) is already the one the filter above
it uses for the same reason.

**`Candidate`'s docstring still says the `ORPHANED` stamp "belongs to the half of
`SA-0009` that runs a cell".** `SA-0019` ended that deferral and could not correct
the sentence — `scheduler.py` was forbidden to it. Correct it here.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Drive the gate through `build_queue` against real spec files and real
ledger rows, not by handing `_refusal` a hand-built `Candidate`.

**What the first attempt already established, so it is not re-derived.** It ran
2026-08-30, passed every gate on attempt 1, and died only because its rebuttal
edited code and REBUT has no repair loop (`EXHAUSTED`, $14.43). Its patch is at
`~/.saffron/batches/v0/SA-0020/patch.diff`. The gate half of that diff is sound
work; the stacking half is what opened the hole above. Read it before starting.

Commit after each coherent step. Uncommitted work dies with the cell.
