---
id: b-8e14fb
title: "`ontology/factory.ttl` is authoritative for protected `CONTEXT.md` spans, and a cell can edit it"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.6]
related: []
---

## Problem

`CONTEXT.md` is in `protected`, and its closed sets render from
`ontology/factory.ttl`. The vocabulary sits in neither `protected` nor
`gate_config` in `.saffron/policy.yaml`. `ontology/shapes/**` and
`ontology/*.py` are in `gate_config`, and the vocabulary they read is not.

A cell's edit to `factory.ttl` fails today only because
`test_generated_surfaces_are_current` sees `CONTEXT.md` disagree, and the cell
cannot edit the protected file to follow. The protection rests on a downstream
test rather than on the source.

24 of the file's 28 commits at `2e1efa2b` also touched `CONTEXT.md`, so few
cell edits would change route.

## Done looks like

`ontology/factory.ttl` is in `protected`, or in `gate_config` with the reason
stated beside it. `.saffron/policy.yaml` is protected, so this is a host-side
edit.

## Record

- 2026-10-24: filed from a review of the controlled vocabulary.
