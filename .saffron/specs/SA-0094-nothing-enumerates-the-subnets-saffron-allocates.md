---
id: SA-0094
title: three subnets are declared in three files, nothing lists them, and the gate cell's pre-clean is by name while the collision it prevents is by value
type: bug
priority: 2
depends_on: [SA-0093]
touches:
  - saffron/cell/runtime.py
  - saffron/cell/proxy.py
  - saffron/cell/session.py
  - tests/test_runtime.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - ontology/**
  - docs/**
  - images/**
  - harness/**
  - saffron/cell/worktree.py
  - saffron/gates/**
  - saffron/agents/**
  - saffron/report/**
  - saffron/repos/**
  - saffron/phases/**
  - saffron/task.py
  - saffron/cli.py
  - saffron/batch.py
  - saffron/replay.py
budget_usd: 18
max_attempts: 3
max_turns: 100
risk: elevated
acceptance:
  - claim: >-
      `saffron/cell/runtime.py` declares every subnet Saffron allocates in one
      place, and each allocation draws its own from there rather than spelling
      a literal in its own module. Today the task network's is in `runtime.py`,
      the proxy's is a second literal in `proxy.py` and the gate cell's is a
      third in `session.py`, and no name lists them.
    witness: tests/test_runtime.py::test_every_subnet_saffron_allocates_is_declared_in_one_place
  - claim: >-
      A test reads that declaration and fails if any two of the subnets in it
      overlap. Today nothing compares them, and the first report of an overlap
      is a `CellRuntimeError` raised at REVIEW.
    witness: tests/test_runtime.py::test_no_two_declared_subnets_overlap
  - claim: >-
      Before the gate cell creates its network, the pre-clean removes whatever
      network is holding that subnet, whatever that network is called — not
      only the one bearing the name this task would use. A leftover from a
      SIGKILLed run of a *different* spec no longer aborts REVIEW.
    witness: tests/test_session.py::test_the_gate_cells_pre_clean_removes_the_holder_of_its_subnet_whatever_its_name
  - claim: >-
      The gate cell still holds no credential and is gone before the first lens
      turn, and the lenses are still shown a gate table computed outside the
      implementer's cell.
    witness: tests/test_session.py::test_the_lens_gate_cell_holds_no_credential_and_is_gone_before_any_lens_runs
    preserves: true
  - claim: >-
      An overlapping `create_network` still raises `CellRuntimeError` naming
      the network already holding the subnet.
    witness: tests/test_runtime.py::test_an_overlapping_network_names_the_one_already_holding_the_subnet
    preserves: true
  - claim: >-
      The task network's prefix and gateway are still derived from its subnet
      and written nowhere a second time.
    witness: tests/test_runtime.py::test_the_subnet_is_the_only_place_the_network_is_written
    preserves: true
---

## Context

Backlog item **143**, found reviewing `SA-0089` (PR #282). Three subnets are
declared in three files — `runtime.DEFAULT_SUBNET` for the task's own
`saffron-cells` network, `proxy.EGRESS_SUBNET` for `saffron-egress`, and
`SA-0089`'s new one in `session.py` for the gate cell. Nothing lists them, and
`runtime.create_network` raises `CellRuntimeError` on overlap — **at REVIEW,
after IMPLEMENT is paid for**, landing in `_drive_cell`'s `except
BaseException` as `ABORTED`/`ORPHANED`, exit 2, charged to nobody.

The spec review caught the first half before `SA-0089`'s cell ran, and it cost
a spec amendment: the spec's notes named only the `saffron-cells` holder and
told the agent to "choose a non-overlapping subnet", and the obvious next pick
after reading the task's own is the proxy's. The amendment named both holders
and dictated the third by hand. The next spec that adds a subnet has to redo
that audit from prose, and the suite cannot see the collision at all because
`_stub_the_runtime` stubs `create_network` to a no-op.

The second half is unfixed and is the defect proper. The gate cell pre-cleans
by **name**, keyed on the spec id, but the collision is by **value**. A
SIGKILLed run of a different spec leaves that run's gate network holding the
subnet, and the next task's REVIEW aborts exactly the way the pre-clean exists
to prevent — one name over.

`runtime.networks_on_subnet` already exists and already answers this question:
`create_network` calls it to name the holder in the error it raises.

## Problem

Saffron cannot enumerate the subnets it allocates, and the guard against a
leftover holder looks it up by the wrong key.

## Out of scope

**Allocating subnets dynamically**, or reading what the runtime has free.
Every subnet stays declared in source. `SAFFRON_CELL_RUNTIME` is declared and
never detected, and so is this: the change is that the declarations live in one
place, not that they stop being declarations.

**`cell_up`'s and the proxy's own pre-cleans.** Only the gate cell's is wrong,
because only it creates a network under a name that is stable across runs of
one spec and different across specs. Do not add a by-value pre-clean to the
other two.

**Which cell gets which subnet.** Keep today's three values. This spec moves
where they are written, not what they are.

**The `cell`-marked isolation tests.** The property that a gate cell has no
route out is item **131**'s live probe. This spec's witnesses run against the
stubs like the rest of `tests/test_session.py`.

## Notes for the agent

**Criteria 1–3 carry witnesses and no mutants.** The declaration, the overlap
test and the by-value pre-clean are all new code, so no text exists at base
that a mutant could pin honestly, and `witness` will report `skip` for all
three. That is expected; `SA-0089` and `SA-0092` have the same shape. Criteria
4 and 5 are `preserves` and name tests that exist at base — `git grep` them.

**Criterion 1's witness must observe the second literal is gone, not merely
that a tuple exists.** A tuple in `runtime.py` that nothing draws from
satisfies "declares every subnet" and leaves the defect exactly where it was.
Assert that the proxy's and the gate cell's subnets *are* members of the
declaration — compare the values the two allocation sites actually pass
against the declared set — so a module that keeps its own literal fails.

**Criterion 2's witness is the comparison, and it must read the declaration
rather than a list of its own.** A test that spells the three subnets again
and compares those passes forever, including the day a fourth is added to
`runtime.py` and not to the test. Iterate over the declared names.
`ipaddress.ip_network(...).overlaps(...)` is the comparison `networks_on_subnet`
already uses, and it is overlap and not equality for the reason its docstring
gives.

**Criterion 3's witness needs `networks_on_subnet` stubbed, because the real
one shells out.** `_stub_the_runtime` does not stub it today. Add it there,
returning a name the test chooses, and assert `remove_network` was called with
that name before the create — `_stub_the_runtime` already records every removal
as a `(kind, name)` pair in `cell.removed` and appends to the shared
`cell.order` timeline, so "before" is assertable rather than merely "both
happened". The name the test returns must differ from the one this task would
use, or the witness cannot tell the new pre-clean from the old one.

**`exclude=` exists for a reason and the pre-clean should not pass it.**
`create_network` passes `exclude=name` because it is explaining an error about
a network it was itself trying to create. A pre-clean that excludes its own
name would skip the one leftover the by-name removal already handles; passing
nothing is right, and removing a network that is not there is tolerated.

**Removing a holder is not always possible, and a failure there is not this
task's failure.** A network with a live container on it will not go. Let
`create_network`'s own `CellRuntimeError` be what reports that, with the
holders it already names — do not swallow a failed removal and do not raise a
new error type for it.

**Both new `tests/test_runtime.py` witnesses must fail with the source
reverted.** Reverted, there is no declaration to read, so an honest test of
either fails. Import nothing new at module scope: a module-scope import of a
name you add turns the reverted run into a collection error, which `revert`
reads as `skip` and the anti-theater gate then checks nothing.

**`SUBNET_PREFIX` and `GATEWAY` are derived from `DEFAULT_SUBNET` and must
stay derived.** The comment above them says why — a second literal is a probe
that silently covers nothing the day the subnet moves. Whatever the declaration
looks like, `DEFAULT_SUBNET` keeps naming the task network's own, and
`container_ip`'s default argument keeps working.

**`proxy.py` is in `touches` for one line.** `EGRESS_SUBNET` is used at
`proxy.py:36` as well as declared at `:21`; the declaration is what moves.
Nothing else in that file is this spec's business.

**This spec builds on `SA-0093`**, which unifies the critic and gate cell
lifecycles into one function. The pre-clean this criterion 3 changes is the
one in that unified lifecycle's create-its-own-network branch. Read it as it
is at your base, not as item 143 describes it.

**The `size` gate counts tests.** A `bug` gets 300 changed lines, tests
included. Five `touches` is the widest part of this change; each file's share
is small.
