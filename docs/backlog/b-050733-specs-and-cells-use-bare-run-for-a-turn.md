---
id: b-050733
title: "Specs and cells use bare \"run\" for one turn or one agent call, and nothing catches it"
status: open
tier: 3
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

Found in stage 2 of the delegate-loop plan, by a Standards seat on #689.

`CONTEXT.md:205` defines "Run" as one task's pin. `CONTEXT.md:354` puts bare
"run" on an _Avoid_ line. `SA-0205`'s spec prose said "Each run starts with
no model seen" and "five runs through `main`". Its cell copied both into
comments and test labels. The Standards seat caught it, and the review commit
on #689 fixed the code.

`SA-0207`'s title says "one run of the suite". The `terms` gate's `AVOIDED`
map in `.saffron/gates/prose.py` holds no "run" entry
(`.saffron/gates/prose.py:147`).

## Done looks like

The spec writer and spec reviewer prompts name the rule. Or a `terms` entry
catches bare "run" as a noun, scoped so that the verb, the defined term and
command names raise no false hit.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
