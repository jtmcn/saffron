---
id: 169
title: The preflight outcome closed set needs a vocabulary entry no cell can write, because CONTEXT.md is generated from the ontology
status: done
tier: 2
closed: 2026-09-21
filed: 2026-09-17
by_hand: true
specs: []
prs: []
commits: [5dacdf6]
cites: [§4.1, §6]
related: [164, 168, 65, 72]
---

## Problem

Filed with `SA-0099`, per the rule in `docs/agents/issue-tracker.md` that a spec
introducing a term files its vocabulary follow-up when it is written.

`SA-0099` writes `runs.preflight` and gives it a closed set of values, modelled
on `batches.status`. That set is a new term. It cannot land in the same cell:
`ontology/factory.ttl` is editable by a cell, and `CONTEXT.md` is `protected` and
generated from it, so the two halves cannot move together inside one task.

`batches.status` is the precedent for both the shape and the omission. Its five
values are a closed set in `ontology/factory.ttl` as `factory:BatchStopReason`,
they appear in `CONTEXT.md`, and
`tests/ontology/test_vocabulary_agrees_with_code.py` cross-checks them. They are
also one of the three cases items 65 and 72 record, where code reached `main`
using a word the glossary did not have. The four batch stop reasons are named in
item 43's own history for the same reason.

No gate catches this. `CLOSED_SETS` in
`tests/ontology/test_vocabulary_agrees_with_context.py` is a fixed list of six,
and a seventh set does not join it by being written. So the omission is invisible
until somebody reads both files.

## Done looks like

The preflight outcome values are a closed set in `ontology/factory.ttl`, and
`CONTEXT.md` is regenerated from it by `uv run python -m ontology.render`.
`CLOSED_SETS` names the new set, so the cross-check reaches it. The words the
ledger stores are the words the glossary defines. `DESIGN.md` §4.1 names the set
where it describes the column, and §6 says which of its six header fields the
column feeds. Worth doing in one pass with item 168, which is the same
constraint one spec along.

## Record

**Filed 2026-09-17 by hand**, with `SA-0099`. By hand because the change spans
`ontology/factory.ttl`, the `CONTEXT.md` generated from it, and a test list in
`tests/ontology/`. A cell cannot move the generated half with the vocabulary in
one task.

**Closed 2026-09-21 by hand** in `5dacdf6`, with the other two sets that share this constraint.
