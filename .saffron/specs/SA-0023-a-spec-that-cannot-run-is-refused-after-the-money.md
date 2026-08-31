---
id: SA-0023
title: a spec whose touches are protected paths is refused after the cell, the turn and the money
type: feature
priority: 1
depends_on:
  - SA-0020
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
  - saffron/agents/**
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/reconcile.py
  - saffron/report/**
budget_usd: 10
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
Measured on this machine, 2026-08-30. `SA-0021`'s job was to correct `DESIGN.md`
and `CONTEXT.md`, so its `touches` declared both — the only honest declaration it
could make. Run as a cell (ledger task 18) it ended `PLAN_REJECTED` in 2m44s
having spent $0.82:

```
PLAN: rejected, $0.82 spent — DESIGN.md is a protected path
```

`.saffron/policy.yaml` lists `DESIGN.md`, `CONTEXT.md`, `.saffron/**` and
`uv.lock` under `protected:`, and `validate_plan` rejects any plan naming one —
checked after `touches` and `forbidden`, with no exemption for a path the spec
itself declares. **The protection is right.** Those documents define what the
system does and what its words mean; a cell rewriting them is exactly what a
global deny list is for. `SA-0021` was done by hand instead, and that was the
correct outcome.

What is wrong is when the system says so. §4.2.1's refusal gate already refuses
**"a spec whose acceptance criteria name a path that no `touches` pattern
matches"** — a spec-quality check that costs nothing and reaches the operator as
one line in the morning queue. A spec whose `touches` collide with `protected` is
the same shape and the same fault class, and it is discovered five layers later.

The policy is already on disk when the scan runs. `_queue` exports the whole
`.saffron/` at `base_sha` — `export_saffron_dir`'s docstring says why it is the
whole directory rather than `gates/` alone — and then hands only
`.saffron/specs` to `build_queue`. `policy.yaml` sits beside it, unread, and
`build_queue`'s signature has nowhere to put it.

## Problem
- **The check runs after the money.** A mirror fetch, a policy load, an image
  build, a network, a proxy, a preflight suite and one model turn all happen
  before `validate_plan` sees a path the operator declared in the spec file
  itself. Nothing between intake and the plan checkpoint reads `touches` against
  `protected`, and both are known before a container starts.
- **The state it produces is wrong about whose fault it is.** `PLAN_REJECTED`
  reaches the operator meaning *"your spec needs work"* (§3.3). Here the spec is
  as good as it can be, and the collision is between two operator declarations —
  the spec's `touches` and the repo's `policy.yaml`. Neither the agent nor the
  spec author did anything wrong, and the state says one of them did.
- **It is terminal, so the cost repeats.** `PLAN_REJECTED` is in
  `scheduler.DONE_STATES`; a re-run at the same `spec_sha` learns the same thing
  for the same money, and an operator who has not read the log has no way to know
  the task never had a route.
- **A refusal that lives only in the scan misses the path this repo uses.**
  `cli._run_cell` never calls `build_queue` — every spec in this repository has
  shipped attended, `SA-0021` included. A gate-0-only fix would not have caught
  the one case that produced this spec.

## Acceptance criteria
- [ ] A spec whose declared `touches` match a literal path the repo's policy
      marks protected is refused before any cell exists, and the reason names
      both the path and the fact that it is the repo's global deny list rather
      than the spec's own `forbidden` — a reason an operator can act on without
      reading the policy file
- [ ] The refusal reaches the operator on **both** paths: the scan, as one line
      beside the other refusals, and the attended single-spec run, which exits
      without creating a cell, without a model call, and without leaving a task
      in an in-flight state
- [ ] Matching is the same glob matcher every other `touches` comparison uses,
      not a string compare — the mistake `SA-0016`'s fifth refusal already
      records, where a criterion naming a nested file string-compares to no match
      against a `**` pattern that plainly covers it
- [ ] A protected entry that is itself a glob is **not** decided here, and the
      spec says so where the code does: deciding whether two glob patterns can
      ever intersect needs the file list at `base_sha`, which the scan does not
      have. The literal entries are the ones that bit — this repo's own policy
      marks three of its four protected entries as literal paths
- [ ] The plan checkpoint's own protected-path rejection stays exactly as it is.
      This spec adds an earlier, cheaper reader of the same fact; it does not
      move the boundary, and a test asserts the checkpoint still rejects when a
      plan reaches a protected path the refusal did not catch
- [ ] The witness is a spec declaring a protected path driven through the real
      scan and the real attended path against a real `policy.yaml` — not a
      refusal reason handed to an assertion
- [ ] `docs/BACKLOG.md`'s item on this defect is marked done and cites what it
      cost to learn: one task, $0.82, and a spec that had to be run by hand with
      nothing saying so in advance
- [ ] Every new test runs with no network and no cell

## Out of scope
**Making a protected path reachable.** Nothing here lets a cell edit a protected
file, propose one, or negotiate the list. The outcome for such a spec is still
"a human does this"; the change is that the system says so for nothing, before a
container exists, instead of for $0.82 after one.

**The mid-attempt scope proposal.** §5.3.1's door is at the plan checkpoint and
its ceiling is named there — an insufficiency discovered mid-diff still burns to
a ceiling. That is a separate spec and it touches `saffron/agents/**` and
`saffron/cell/**`, both forbidden here.

**A new state.** A refusal already has a shape, a reason and one line in the
morning queue (§4.2.1, §6). Adding a state for this would be a state with one
producer and one consumer, which item 18 counts six of.

**The `depends_on` gate itself.** `SA-0020` owns `scheduler.py`'s refusal list
and lands first — this spec adds a refusal beside its, and depends on it to avoid
two tasks editing one file.

## Notes for the agent
**`build_queue` has no policy and that is the whole plumbing job.** Its caller
already holds the export that contains `policy.yaml`; `load_policy` exists and
needs no edit. Thread the answer in, do not re-export, and do not reach past the
export to the working copy — item 13 and item 15 are both that mistake.

**A false refusal is more expensive than the bug.** §4.2.1 says it of the fifth
refusal and it holds here: a spec wrongly refused costs a whole night with no
cell started and nothing to notice until morning. When the two patterns cannot be
decided, admit and let the plan checkpoint catch it — the backstop is still
there, which is why a criterion above keeps it.

**Mark the ceiling with a `ponytail:`.** The glob-versus-glob case is a
deliberate simplification with a named limit, which is exactly what that marker
is for.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Drive both witnesses through the real entry points against a real
policy file, not by calling the refusal helper with a hand-built candidate.

Commit after each coherent step. Uncommitted work dies with the cell.
