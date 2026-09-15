---
id: 107
title: The runtime seam is one file, and widening it cannot be done from a cell
status: done
tier: 3
closed: 2026-09-11
specs: []
prs: []
commits: [572819a]
by_hand: true
cites: [§4.6, §10]
related: [65, 72, 101, 108]
---

## Problem

Two things worth keeping from doing it. The rule was re-proved rather than
assumed: with the exemption moved, a `container` argv planted in `runtime.py`
turns the gate red where it was previously exempt, so the invariant moved
instead of being disarmed. And the first version of the new dialect test read
`exec_workdir_flag` and compared it to itself — it passed against a nonsense
value, and the mutant is what said so. A dialect's members are claims about a
product, so they are pinned as literals; a second runtime pins its own.

**Tier 3.** Appendix G wrote the seam on purpose and it held: `saffron/cell/runtime.py`
is 441 lines and the only module that names the cell runtime, kept there by
`.saffron/rules/container-runtime-is-runtime-only.yml`. What no one checked is
whether the factory can widen its own seam. It cannot, and the reason is
structural rather than incidental.

Splitting the module — a `CellRuntime` protocol and the selector in
`runtime.py`, the `apple/container` argv-building in `saffron/cell/runtimes/apple.py` —
moves the guarded code out from under the rule's exemption, which names the old
path exactly. So the rule must change in the same commit, and it cannot:

- `.saffron/**` is `protected` in this repository's own `policy.yaml`, and
  `validate_plan` rejects a plan naming a concrete path under it. A cell is
  refused at the plan checkpoint.
- The exemption cannot be widened *ahead* of the move either.
  `test_every_rules_path_scope_still_reaches_a_file` asserts that every
  `ignores:` glob reaches a file that exists, so an exemption for a module that
  has not been written yet fails before the spec is ever driven.
- `test_a_rules_exemptions_are_the_named_files` pins all four exemptions by
  value, and its own docstring says they "are not supposed to move without a
  person saying so". That test is working exactly as designed. This item is the
  person saying so.

**`ontology/factory.ttl` needs nothing.** It is a projection of the run record
(§4.6) and the cell runtime is not in it — no class, no property, no closed set.
A term whose only reader would be a comment is what `test_no_dead_terms` deletes,
so the runtime earns an entry when a query or a shape reads it, which would mean
recording per task which runtime ran it. That is worth doing and is a ledger
change, not a vocabulary one; it is named in **108**.

## Done looks like

a by-hand commit on the host, in the shape item **101**
describes: the protocol and the move, the rule's exemption and its asserting
test, and `tests/test_runtime.py` following the code, all together, with the
suite green either side and no behaviour change for a host that has
`apple/container`. Two things ride with it and neither can be deferred to the
runtime that arrives second:

- **The vocabulary follow-up.** `CONTEXT.md`'s **Cell runtime** entry says the
  seam "stays the only module that names the product", which the move falsifies
  — it becomes one module per product, and `runtime.py` becomes the selector
  that names none. The entry's own closing clause, *a decision made by spike can
  be remade by spike*, already anticipates a second answer, so the term survives
  and one clause changes. `CONTEXT.md` is `protected` and is generated from
  `ontology/factory.ttl` for its closed sets only; this is prose outside any of
  them, so it is a hand edit that `ontology.render` leaves alone. Filed here
  rather than on the spec because a cell cannot land the two halves together —
  the defect `docs/agents/issue-tracker.md` records as items **65** and **72**.
- **A paired rule for the second backend.** With the exemption moved, nothing
  stops the next runtime's name being spelled anywhere under `saffron/`. The
  rule ships with the mutant that proves it fires, and it cannot be written
  before the module it guards exists, for the reach reason above. It belongs to
  item **108**, not here, and is named here so the gap between the two commits
  is a decision rather than an oversight.

## Record

**Status:** **done**, by hand on the host, 2026-09-11 — for the reason below: a
cell is refused at the plan checkpoint. `saffron/cell/runtime.py` names no
product, `saffron/cell/runtimes/apple.py` is the only module that does, and
`runtimes/__init__.py` carries the `Dialect` — every spelling member a
difference **measured** between two runtimes rather than anticipated. The rule's
exemption, its asserting test, `CONTEXT.md`'s **Cell runtime** entry and
§10's layout moved with it. `SA-0077` is the cell-landable piece that came out
of it: a missing runtime reporting as absent rather than as twenty-one failures.
