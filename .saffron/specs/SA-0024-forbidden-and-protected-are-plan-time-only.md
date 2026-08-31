---
id: SA-0024
title: forbidden and protected are checked against the plan and never against the diff
type: feature
priority: 1
depends_on: []
touches:
  - saffron/gates/core/scope.py
  - saffron/cell/session.py
  - tests/test_scope.py
  - tests/test_session.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/scheduler.py
  - saffron/cli.py
  - saffron/reconcile.py
  - saffron/agents/**
  - saffron/phases/**
  - saffron/report/**
budget_usd: 12
max_attempts: 4
max_turns: 100
risk: elevated
---

## Context
`forbidden` is a spec's own deny list and `protected` is the repo's global one
(`CONTEXT.md` §3 defines both). Measured 2026-08-31, `grep -rn forbidden
saffron/`: they are read in exactly two places. `agents/context.py` puts them in
the prompt, which §5.3 says is never a boundary. `agents/artifacts.py`'s
`validate_plan` rejects a plan whose `files_to_change` names one.

**Nothing reads either against the diff.** `gates/core/scope.py` checks one
thing — changed files are a subset of `touches` — and `integrity` checks test
deletion, suppression tokens and gate-config edits. So a path both lists deny is
a path no gate refuses; it is only a path a *plan* may not declare.

The reachable case, measured on the branch that found it:

```
touches:   ['docs/**']
forbidden: ['docs/DESIGN.md']
protected: ['docs/DESIGN.md']

gate 0 refusal:  None      (SA-0023 exempts what `forbidden` bars)
plan checkpoint: ACCEPTED  (the plan names only tests/test_x.py)
scope on a diff containing docs/DESIGN.md: pass — within touches
```

An agent that declares one plan and commits another is not a hypothetical: the
extraction turn exists (§5.3) because "the agent wrote prose around the JSON"
was measured, and **control artifacts are extracted and hashed the moment they
are produced** precisely because a validated plan the implementer then edits
leaves no trace in the diff. The same asymmetry applies one layer out: a
validated plan and the diff that follows it are different objects, and only one
of them is checked against the deny lists.

## Problem
- **The gate that answers "may this file change" reads one of the three lists.**
  `touches`, `forbidden` and `protected` are the same question asked three ways,
  and `scope` is where the diff meets a path list. Two of the three arrive there
  and are dropped.
- **`SA-0023` is the first thing to lean on plan-time rejection as a backstop.**
  Its refusal exempts a `protected` path the spec's own `forbidden` bars, on the
  ground that `validate_plan` will reject it — true of the plan, not of the diff.
  That exemption carries a `ponytail:` naming this ceiling; this spec is what
  closes it.
- **It is scope discipline, not containment, and the spec must not overstate.**
  §2's controls are structural — no credentials, no route, mirror-only remote —
  and an unwanted edit lands in a diff a human reads before merge. What is at
  stake is a reviewable PR quietly containing a change the spec forbade, which
  costs a review rather than a breach.

## Acceptance criteria
- [ ] `scope_gate` takes the spec's `forbidden` and the repo's `protected` and
      fails on a changed file matching either, with the same glob matcher it
      already uses for `touches` — one function, one meaning of "declared"
- [ ] Both new parameters default to empty, so every existing caller and every
      existing test is unchanged, and a test asserts that a call passing neither
      behaves exactly as before
- [ ] A file **outside** `touches` still reports today's `out-of-scope` code and
      message, unchanged. The new codes are for a file *inside* `touches` that a
      deny list nonetheless refuses — a file can be both, and the existing
      failure is not renamed underneath the baseline
- [ ] The two new failures carry distinct codes, and the failure line names
      which list denied the path: a spec's own `forbidden` and the repo's
      `protected` are different facts and §5.4 keys baseline subtraction and
      no-progress detection on `(gate, file, code)`
- [ ] The status is `fail`, never `error`: the repo's code is wrong, the gate is
      not broken
- [ ] The wiring passes the spec's `forbidden` and the policy's `protected` from
      the same place `scope` is already called, and a test drives a real cell
      suite rather than calling the gate directly
- [ ] A spec with empty `touches` still reports `skip`, unchanged — that is the
      documented shape for a bug awaiting DIAGNOSE, and the ceiling is stated
      where the code is: such a diff is not checked against either deny list
      until its scope is ratified
- [ ] `docs/BACKLOG.md` records that `CONTEXT.md`'s one-line definition of the
      `scope` gate — a subset check against `touches` — no longer describes what
      the gate does, that the correction is by hand because that file is
      `protected`, and that this is the second instance of the drift item 30
      names
- [ ] Every new test runs with no network and no cell

## Out of scope
**A new gate name.** `scope` is where the diff meets a path list, and a second
core gate would need a reserved name, a vocabulary entry and a `DESIGN.md`
section — all in files this spec cannot touch. Widening the gate that already
asks the question costs one clause of documentation instead of three.

**Editing the documents that define the gate.** `CONTEXT.md` and `DESIGN.md` are
`protected`; `SA-0023` now refuses at gate 0 any spec whose `touches` names them.
The correction is a by-hand follow-up and a backlog entry says so — the shape
`SA-0018` and `SA-0021` already established.

**Enforcing the deny lists anywhere else.** The prompt keeps its advisory copy
(§5.3, a prompt is not a boundary) and `validate_plan` keeps its plan-time
rejection. This adds a reader against the diff; it removes none.

**The `PreToolUse` path check.** §5.3 already declines a hook as a control: it
runs inside the cell, on the untrusted side, and its value is fewer wasted turns
rather than safety. That argument is unchanged.

## Notes for the agent
**`scope_gate` already has both halves.** It holds `changed_files` and `matches`,
and its `error` branch for unreadable diff prefixes stays exactly as it is — a
gate that cannot read its input reports `error`, and that is a different thing
from the code being wrong.

**Do not fold the new failures into `out-of-scope`.** Three mechanisms key on
`(gate, file, code)` — baseline subtraction, no-progress detection and the
flywheel's sole-failure question (§4.1) — so a collapsed code makes a denied path
cancel against an out-of-scope one at baseline.

**The failure line is the whole channel to the agent (§5.4).** `scope`'s existing
message names the declared `touches` because frontmatter never reaches the spec
body. The new ones have the same problem and the same fix.

**A test that constructs the value it then asserts on proves nothing about the
caller.** Drive the wiring through the suite that runs `scope`, not by calling
`scope_gate` with a hand-built list, and build the diff from a real `git diff`
rather than a string that looks like one.

Commit after each coherent step. Uncommitted work dies with the cell.
