---
id: SA-0052
title: the overlap refusal walks one hop, so a stack three deep refuses its own grandchild
type: bug
priority: 1
depends_on: []
touches:
  - saffron/scheduler.py
  - tests/test_scheduler.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/cli.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/report/**
  - saffron/gates/**
  - saffron/ledger.py
  - saffron/reconcile.py
  - saffron/preflight.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
acceptance:
  - claim: >-
      A candidate three deep in a stack is admitted when the open pull request
      it overlaps belongs to its own grandparent. That parent's changes are
      already in this candidate's base, because a stacked child is cut from its
      parent's branch head — there is nothing to conflict with.
    witness: tests/test_scheduler.py::test_a_grandparents_open_pull_request_does_not_refuse_its_grandchild
  - claim: >-
      Two unrelated tasks touching one file are still refused, naming the pull
      request and the overlapping paths. This is what the gate was built for
      and the fix must not widen past the ancestor case.
    witness: tests/test_scheduler.py::test_an_unrelated_open_pull_request_still_refuses_on_overlap
  - claim: >-
      Only the first dependency is treated as an ancestor. K=1 fixes the first
      entry as the sole stacking candidate, so a second entry is a dependency
      rather than a base: its changes are not in this candidate's tree and an
      overlap with its pull request is a real conflict, still refused.
    witness: tests/test_scheduler.py::test_a_second_dependency_is_not_an_ancestor_and_still_refuses
  - claim: >-
      A dependency cycle terminates the walk instead of hanging the scan.
      Nothing validates the graph for cycles at parse time, so this is
      reachable from a hand-written pair, and unattended a hang costs the whole
      night rather than one task.
    witness: tests/test_scheduler.py::test_a_dependency_cycle_does_not_hang_the_ancestor_walk
  - claim: >-
      A parent the scan cannot see ends the walk quietly rather than raising —
      a retired parent is not in the scanned set, and a dangling id is already
      the dependency gate's refusal to make with its own reason.
    witness: tests/test_scheduler.py::test_an_unscanned_parent_ends_the_walk_without_raising
---

## Context

Backlog item 59, measured on this repo's own queue 2026-09-04 by the first
stack three deep.

`saffron/scheduler.py`'s open-pull-request overlap refusal exempts the
candidate's own branch and one parent, taken from `depends_on[0]`. A stack is
transitive. `SA-0049` → `SA-0048` → `SA-0046` → `SA-0045`: the exemption covers
`SA-0048` and not `SA-0046`, whose pull request is open and whose changed files
include `saffron/ledger.py`, which `SA-0049` touches. The scan refuses it:

```
SA-0049: touches overlaps open pull request #116's changed files:
         saffron/ledger.py, tests/test_ledger.py
```

**The refusal is a false positive, and stacking is the reason.** A stacked
child is cut from its parent's branch head, so a linear stack's grandparent
changes are already in the child's own base by construction. There is nothing
to conflict with — that is what `SA-0022`, `SA-0025` and `SA-0026` were built
to make true. The gate refuses the case the machinery exists to admit, which
is the correction §4.2.1 already had to make once for the dependency gate.

## Problem

- **The chain is walked one link and stacks are longer than that.** Two deep is
  fine; three deep refuses.
- **Nothing sees it today, which is why it is worth fixing now.** `saffron
  cell` never consults `build_queue` — only `saffron queue` does — so an
  operator driving specs by hand watches every one succeed while the scan is
  refusing one of them. It costs nothing until a batch reads it, and then it
  costs a task a night on exactly the deep queues stacking exists for.
- **The refusal reads as correct.** It names a real open pull request and a
  real overlapping file. Nothing about the line says the overlap is with the
  candidate's own ancestor.

## Out of scope

**Widening the refusal.** The gate is right about two unrelated tasks touching
one file — that is what it was built for and it must keep doing it. Only the
ancestor case is wrong.

**`depends_on` entries after the first.** §4.2 fixes K=1: *"only the first
`depends_on` entry is a stacking candidate."* A second entry is a dependency,
not a base, so its changes are **not** in this candidate's tree and an overlap
with its pull request is a genuine conflict. The walk follows slot zero only.

**The dependency gate.** A different refusal with a different rule; it already
admits what it should.

**Whether every ancestor is *really* a base.** A child is only cut from its
parent's branch when that parent has a task in a waiting state; a parent that
already merged leaves the child cut from the default branch instead, so an
exemption for it is an over-approximation. It is narrow — a stack merges bottom
up, so reaching it needs an out-of-order merge — and the one-hop code being
fixed makes exactly the same unconditional assumption today. Widening it from
one link to all does not make that assumption worse, and narrowing it is a
separate question about consulting ledger state inside a refusal that currently
needs none.

**Anything outside `saffron/scheduler.py`.** The whole fix lives there —
`build_queue` already has the discovered specs in scope where it calls
`_refuse`, so no new lookup and no new caller.

## Notes for the agent

**The internal shape is yours; the file is not.** Whether the ancestor set is
computed in `build_queue` and passed to `_refuse` as one more keyword, or
derived inside `_refuse` from a map handed to it, is a judgement call — both
live entirely inside the one module `touches` permits, which is why this spec
declares that module rather than leaving `touches` empty for a proposal.
What is fixed is that the exemption must cover every ancestor rather than one.

**The specs are already in hand.** `build_queue` binds `specs` from
`discover_specs` before it loops, and calls `_refuse` inside that loop. The
`spec_id` → `depends_on[0]` map comes from there. `_branch` turns an id into a
branch name and is two lines.

**The walk must terminate, and nothing today guarantees the graph is acyclic.**
Nothing validates `depends_on` for cycles at parse time, so a spec pair that
depends on each other would hang the scan — a worse failure than the one being
fixed, and unattended it is the whole night. Carry a visited set.

**A parent that is not in the scan stops the walk, and that is correct rather
than an error.** A retired parent is in `specs/done/` and not in `specs`; a
parent that never existed is a dangling reference the dependency gate already
refuses with its own reason. Either way there is no branch to exempt and no
pull request of theirs to collide with, so the walk ends quietly.

**Do not exempt by spec id.** The comparison is against `headRefName` on the
open pull request. Two things could name a branch and the refusal already
built its own with `_branch`; reuse it rather than reconstructing the string.

**Three of the five witnesses are regression guards and pass before the fix as
well as after — that is intended, not a mistake to correct.** Only the
grandparent case and the cycle are red at head today. An unrelated pull request
already refuses, a second `depends_on` entry already refuses, and no walk exists
yet so nothing raises on an unscanned parent. Do not spend turns trying to make
those three fail first; they exist so the fix cannot pass by widening the gate
into uselessness. Every witness is a new node id, so none can be green at
`base_sha` in the sense `criteria` refuses — that check reads the *base* tree's
own collected names.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked test is never collected at head. Nothing
here needs a container: `build_queue` takes an injected `gh` callable and every
existing refusal test uses it.

**Two tests here are anchored to this repo's real spec files, and neither is
affected by this fix.** One promotes ids out of `specs/done/` and passes no
`repo_slug` at all; the other copies the live spec directory and passes an
empty `gh`. Both leave `open_prs` empty, so the overlap refusal never executes
in either — which is why the ancestor walk cannot move them, and why the
synthetic fixtures beside them are where this behaviour gets pinned.

If either does move, that is a finding worth reporting rather than a green to
chase: it would mean the walk reached a path the fix was not supposed to touch.

**`build_queue`'s own signature is not yours.** `saffron/cli.py` and the
`run-saffron-spec-loop` skill's driver both call it and neither is in
`touches`, so a new *required* parameter breaks a caller this spec cannot
legally repair. `_refuse` is private and free to change.
