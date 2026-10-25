---
id: b-541e9a
title: "Four texts still describe one `_Avoid_` list and who reads it, which ADR 11 splits in two"
status: open
tier: 3
filed: 2026-10-24
specs: []
prs: [963]
commits: []
cites: [§5.3, §5.5]
related: [162, b-8220e6]
---

## Problem

ADR 11 gives each kind of avoided phrase its own reader. The `terms` gate
reports banned phrases, and the conventions lens judges confusable ones. Four
texts still say otherwise:

- `docs/agents/domain.md`, "Keeping the model in sync", said §5.3's injection
  enforces the lists, while `saffron/agents/context.py` strips them (item 162).
  #963 corrected that sentence. It still describes the seven-phrase gate.
- `DESIGN.md` §5.5 says the conventions lens reads the `_Avoid_` lists.
- The `CONTEXT.md` preamble calls the `_Avoid_` lists "the load-bearing part".
- The comment on `terms` in `.saffron/policy.yaml` calls its list "curated".

## Done looks like

Each text names the three mechanisms: `terms` for banned phrases, the
conventions lens for confusable ones, and the `retired-vocabulary` hook for a
term a settled naming decision retired. It lands with b-8220e6, or after it.

`DESIGN.md`, `CONTEXT.md` and `.saffron/` are protected, so these edits are
host-side.

## Record

- 2026-10-24: filed with ADR 11 (#963).
