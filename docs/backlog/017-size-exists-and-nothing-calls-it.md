---
id: 17
title: '`size` exists and nothing calls it'
status: done
tier: null
closed: 2026-08-25
specs: [SA-0002, SA-0005, SA-0006, SA-0007]
prs: []
commits: [2f7c6d9]
cites: [§5.6]
related: [6, 18]
---

## Problem

**Status:** **done** — `SA-0005` (`2f7c6d9`). `size_gate` is called at
`session.py:1017`, advisory unless the effective risk tier is elevated
(`session.py:950`).

`SA-0002` built the gate (#15) and its spec put the consumer out of scope, on
the correct reasoning that the risk tier has none until v1. So the module is
present, unit-tested, adversarially reviewed — and unreachable: `session.py`'s
`_suite` builds its core-gate list from `scope`, `integrity`, `committed` and
`census`, and `size` is not in it.

**This is a spec-writing lesson before it is a task.** A spec whose output has
no consumer produces a module, not a capability, and the gate loop cannot be
handed one without a change it does not have: every `fail` today means repair,
while §5.6 makes `size` **advisory at `standard` and blocking only at
`elevated`**. There is no advisory result the repair loop honours.

**Corrected 2026-08-25, writing `SA-0005`:** the sentence here said
`policy.elevate_on` "does not exist either", and it does — `Policy.elevate_on`
(`saffron/repos/policy.py:51`), parsed, validated, tested, and already carrying
three patterns in this repo's own `.saffron/policy.yaml`. So does
`GateDeclaration.blocking` (`:29`), which is the advisory switch for *declared*
gates. Both have **no reader anywhere downstream**. That makes this task
smaller than the item claimed and its failure mode worse: a declaration a repo
can set, that validates, and that changes nothing is indistinguishable from one
that works until someone checks.

**Done looks like:** an advisory status the repair loop does not act on,
`policy.elevate_on` matched against the diff, `risk` reaching `run_one_cell`,
and `size` in `_suite`. Two things it must carry, both found reviewing #15:

- **Call it host-side, never declare it.** `size` leaves `tool` unset, which is
  right for a gate that executes nothing — and `runner.run_gate` turns a
  declared gate's `pass`/`fail` with no `tool` into `error`. Declaring it in a
  `policy.yaml` errors every task.
- **Close the binary hole with what this spec has.** A block git renders as
  `Binary files ... differ` has no `@@`, so it counts 0 and a `-diff`
  gitattribute zeroes the gate on a rewrite of any size — at `elevated`, the one
  tier where it blocks. It carries a `ponytail:` comment rather than a fix
  because the honest response is `error` only when the unreadable file is inside
  `touches`, and `size_gate` is handed neither `touches` nor a `--numstat`
  cross-check. This spec is handed both.

The same wiring is what item 6's third lens needs, and the two should be built
together or in that order.

**Done, 2026-08-25**, across three specs rather than one — which is the part
worth carrying forward. `SA-0005` (#21) wired the tier and the advisory set,
`SA-0007` (#23) closed the two call sites `SA-0005`'s `touches` could not reach,
and `SA-0006` (#24) closed the binary hole. All four clauses of *done looks
like* hold: `effective_risk(spec.risk, changed, policy.elevate_on)` matches the
diff per attempt (`session.py:663`), `cli.py:176` passes `risk=spec.risk` into
`CellSpec`, `advisory_gates` plus `_blocking` give the repair loop a status it
does not act on, and `size` is in `_suite` (`session.py:691`).

**The advisory switch is two rules, not one, and they are not the same rule.**
`size` is advisory unless the tier is elevated; a declared gate the repo marked
`blocking: false` is advisory at *every* tier, because that is what the
declaration means rather than a tier-dependent switch. They sit in adjacent
lines and reading them as one is the mistake available here.

**And `size` still needs `blocking` even though it is host-side.** Refusing an
unreadable diff ends the attempt through `aborted_gates`, which no advisory
filter downstream can soften — so a gate that stops nothing at this tier must
not spend that refusal. That is why the fix `SA-0006` shipped is a `blocking`
argument and not an `error` return.

**What this item taught, beyond the gate.** Item 18 files the general pattern —
a declaration that parses, validates, and changes nothing. This is the instance
that produced it, and the sequence is the evidence: `SA-0005` could not close
its own gap because its `touches` did not reach `cli.py` and `package.py`, so a
second spec existed only to finish the first. A spec whose acceptance criteria
reach outside its own `touches` is unsatisfiable by construction.
