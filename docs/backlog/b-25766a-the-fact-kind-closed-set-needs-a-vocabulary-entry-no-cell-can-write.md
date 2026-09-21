---
id: b-25766a
title: The fact kind closed set needs a vocabulary entry no cell can write, because CONTEXT.md is generated from the ontology
status: done
tier: 2
closed: 2026-09-21
by_hand: true
filed: 2026-09-20
specs: []
prs: [393]
commits: [5dacdf6]
cites: [§4.1, §11]
related: [168, 169, 170, 65, 72, b-d5d290]
---

## Problem

`saffron/record/contract.py` declares `KINDS`, the eighteen values a fact
takes. Its own comment calls the set closed: a kind not there cannot be
appended, so the fold never meets one it cannot place. That set is a new
term, and no vocabulary entry defines it.

This is the third instance of one pattern. Item 168 is the eleventh event kind
and item 169 the preflight outcome set, both filed for the same reason and both
tier 2. The constraint is the same one. `ontology/factory.ttl` is editable by
a cell, and `CONTEXT.md` is `protected` and generated from it. The two halves
cannot move together inside one task.

No gate catches it. `CLOSED_SETS` in
`tests/ontology/test_vocabulary_agrees_with_context.py` is a fixed list, and a
new set does not join it by being written. PR 393 wrote `KINDS` and left
`uv run python -m ontology.render` deliberately unrun. `DESIGN.md` and
`CONTEXT.md` are `protected`, and their amendments are that branch's second
plan.

Seven of the eighteen kinds are appended by nothing today (`run_created`,
`run_finished`, `run_preflight`, `batch_created`, `batch_closed`,
`repo_upserted`, `decision`). The set is declared ahead of the batch and run
folds that use it. So the vocabulary entry has to say the set is the
record's whole alphabet, not what the fold reaches.

## Done looks like

The fact kinds are a closed set in `ontology/factory.ttl`, and `CONTEXT.md` is
regenerated from it by `uv run python -m ontology.render`. `CLOSED_SETS` names
the new set, so the cross-check reaches it. The entry says a **fact** is the
record's entry and an **event** is `events.jsonl`'s. §11 of the record design
specifies that already, and no glossary line carries it. Worth one pass with
items 168 and 169, the same constraint on two other sets.

## Record

**Filed 2026-09-20 by hand**, reviewing PR 393. By hand because the change
spans three places: `ontology/factory.ttl`, the `CONTEXT.md` generated from
it, and a test list in `tests/ontology/`. A cell cannot move the generated
half with the vocabulary in one task.

**Closed 2026-09-21 by hand** in `5dacdf6`, with the other two sets that share this constraint.
