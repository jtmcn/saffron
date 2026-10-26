---
id: b-8e14fb
title: "`ontology/factory.ttl` is authoritative for protected `CONTEXT.md` spans, and a cell can edit any part of it no span renders"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.6]
related: [72]
---

## Problem

`CONTEXT.md` is in `protected`, and its closed sets render from
`ontology/factory.ttl`. The vocabulary sits in neither `protected` nor
`gate_config` in `.saffron/policy.yaml`. `ontology/shapes/**` and
`ontology/*.py` are in `gate_config`, and the vocabulary they read is not.

Item 72 measured this and argued it acceptable. An edit that changes a
rendered span is not complete until `ontology.render` rewrites `CONTEXT.md`,
and a cell cannot. An edit that changes no rendered span passes outright, such
as a class, a property or a comment.

ADR 5 keeps the ontology out of execution, so such an edit changes no
behaviour. It changes the record a shape and the view read.

24 of the file's 28 commits at `2e1efa2b` also touched `CONTEXT.md`, so few
cell edits would change route.

## Done looks like

`ontology/factory.ttl` joins `protected` or `gate_config`, with its reason
stated beside it. Or a Record line says why item 72's argument still holds for
edits no span renders. `.saffron/policy.yaml` is protected, so a
change there is host-side.

## Record

- 2026-10-24: filed from a review of the controlled vocabulary.
