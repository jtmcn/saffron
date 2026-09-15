---
id: 65
title: The batch's four stop reasons are a closed set that lives only in SQL
status: done
tier: 3
closed: 2026-09-05
specs: []
prs: []
commits: [2a293b5]
cites: [§6]
related: []
---

## Problem

**Status: done** — `factory:BatchStopReason` in the vocabulary, `CONTEXT.md`
regenerated, and `factory:BatchShape` closing the set with `sh:in`.

Four readers now have to agree, and a test fails on each direction of drift:
the vocabulary, `CONTEXT.md`'s **Batch stop reason** entry (generated, not
hand-copied), `batch.StopReason`, and the `CHECK` on `batches.status` — the
last parsed out of `SCHEMA` rather than restated, because a copy of the four in
a test drifts exactly the way the constraint drifted from the vocabulary. That
is the specific hole this item named: a fifth reason added in SQL alone.

The shape carries one axiom the `CHECK` cannot state. `minCount 0`: a batch
with no stop reason is legal *precisely while it is in flight*, which is the
NULL-means-running distinction §6's morning queue reads. A constraint can say
which strings are legal; it cannot say that absence means something.

Worth recording because it is the confusion the class exists to prevent: the
shape rejects `EXHAUSTED` and `ORPHANED` as stop reasons. They are *task* end
states, they share a column type and a naming style with these four, and
`saffron batch` maps three of the four to exit `0` — so reading one set as the
other misreports a night.

**Tier 3.** Found reviewing `SA-0045` (PR #115), and again reviewing `SA-0049`.

`DRAINED`, `BUDGET`, `UNTIL` and `INFRASTRUCTURE` are a closed set — a `CHECK`
constraint on `batches.status` refuses anything else, and `batch.StopReason` is
a `Literal` of the same four. They appear in neither `ontology/factory.ttl` nor
`CONTEXT.md`.

Every other closed set in this repo is generated from the vocabulary and
cross-checked by `tests/ontology/test_vocabulary_agrees_with_context.py`, which
is the mechanism CLAUDE.md names as authoritative. This is the sixth, and the
first with no vocabulary entry: nothing stops a fifth reason being added in SQL
alone, and nothing tells a reader of `CONTEXT.md` that the four exist.

Deferring was correct in the layer that found it — `ontology/` and `CONTEXT.md`
were both `forbidden` to `SA-0045` and to every spec above it — but the
deferral has no owner now.

## Done looks like

a `factory:BatchStopReason` class in the vocabulary with the
four individuals, `uv run python -m ontology.render` re-run, and the closed-set
test naming it alongside the other five. The `CHECK` constraint stays: the
vocabulary is authoritative for the words, and the constraint is what enforces
them at the one place a bad value could be written.
