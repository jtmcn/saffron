---
id: 28
title: A spec whose `touches` are protected paths dies at the plan checkpoint with no exit
status: done
tier: null
closed: 2026-08-31
specs: [SA-0016, SA-0021, SA-0023]
prs: []
commits: []
cites: []
related: [13, 15, 18, 27]
---

## Problem

`SA-0021` — the spec that closes item 27 — declared `DESIGN.md` and `CONTEXT.md`
in `touches`, which is the only honest declaration it could make. Run as a cell on
2026-08-30 (ledger task 18) it ended `PLAN_REJECTED` in 2m44s having spent $0.82:

```
PLAN: rejected, $0.82 spent — DESIGN.md is a protected path
```

`.saffron/policy.yaml` lists `DESIGN.md`, `CONTEXT.md`, `.saffron/**` and `uv.lock`
under `protected:`, and `validate_plan` (`saffron/agents/artifacts.py`) rejects any
plan naming a protected path — checked after `touches` and `forbidden`, with no
exemption for a path the spec itself declares. The protection is right: those two
documents are authoritative, and a cell rewriting the definition of its own
constraints is exactly what a global deny list is for. What is missing is an exit.

The scope-proposal door does not cover this. That door is for "the declared
`touches` cannot satisfy the criteria"; here they can — it is policy, not scope,
that bars them. So the implementer correctly wrote a plan, and the plan was
correctly rejected, and the task is terminal at a state that means "your spec needs
work" when the spec is as good as it can be. Every future attempt spends the same
$0.82 to reach the same wall. This is item 18's shape — a declaration with no
reader — inverted: a rejection with no route.

**One tension to meet deliberately rather than at implementation time.** Such a
proposal names only paths *inside* the declared `touches`, which is precisely what
`validate_scope_proposal` refuses — "every proposed path is already inside touches".
Generated host-side it would bypass that validator, and `SCOPE_REVIEW` would then
carry two meanings: a scope to ratify, and "this one is yours to do by hand".
`CONTEXT.md` defines **Ratify** as what the operator does to a *proposed `touches`
set*, so the second meaning needs either a different state or a deliberate widening
of that definition — not a quiet reuse.

## Done looks like

a plan naming a protected path inside the spec's own declared
`touches` ending at `SCOPE_REVIEW` rather than `PLAN_REJECTED`, carrying the
protected paths as the proposal and the rejection reason as the root cause, so the
work reaches the operator as a one-click "do this by hand" rather than as a dead
task. A plan naming a protected path *outside* `touches` stays a rejection: that is
an agent reaching for something it was never given, which is the case the check was
written for. Until then, a docs spec over protected paths must be run by hand and
say so in its own notes.

## Record

**Status:** **done** — `SA-0023`, 2026-08-31.

**Closed differently from this item's own "Done looks like."** Not a second
`SCOPE_REVIEW` producer — the tension two paragraphs up is why: that state already
means "ratify a proposed `touches` set", and this collision is not one. Instead,
`SA-0023` added a refusal beside `SA-0016`'s: `scheduler.protected_touch_refusal`
compares a spec's declared `touches` against `policy.yaml`'s `protected` list with
the same glob matcher every other `touches` comparison uses, deciding only literal
`protected` entries — an entry that is itself a glob (`.saffron/**`) is left to
`validate_plan`'s own rejection, unmoved, still the backstop. Read at both places
this repo's specs actually run: the scan (`build_queue`'s new `protected`
parameter) and the attended single-spec run (`cli._run_cell`, before a cell
exists), both from the same `base_sha` export `build_queue`'s specs already come
from — never the working copy (items 13 and 15). What it cost to learn: one task,
$0.82, and a spec that had to be run by hand with nothing on the way in saying so.
