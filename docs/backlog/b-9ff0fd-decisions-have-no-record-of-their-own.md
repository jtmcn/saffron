---
id: b-9ff0fd
title: Decisions have no record of their own, so where one stands today is spread across appendices
status: done
closed: 2026-09-19
tier: null
filed: 2026-09-18
by_hand: true
specs: [SA-0110]
prs: [377]
commits: []
cites: []
related: [b-61127f]
---

## Problem

The appendices are records now, one per revision, and a revision records
several decisions. Where one decision stands today still means reading every
appendix that touched it: the emitter spans `ontology/RATIONALE.md` and
Appendices O, P and T. Nothing marks a decision replaced.

## Done looks like

A record kind holding one decision per file, designed and landed. The design
answers four things:

- **Numbering.** Principles are one sequence each appendix claims a block of:
  per-decision files written in parallel were refused (`DESIGN.md`,
  "Appendices — an index"). The backlog's answer, random ids after item 177
  (`records/kinds.py:34`), is the one to try first.
- **Supersession.** `BacklogItem.superseded_by` holds one id. A decision
  split into several, or replaced by several, needs a list.
- **The name.** "ADR" is on `CONTEXT.md`'s _Avoid_ list because every
  `ADR-NNNN` the design record cites is prior art's, now in
  `docs/appendices/D-lessons-from-prior-art.md`. "Decision record" collides
  too: `CONTEXT.md:639` uses it for prior art's records, and §11's own title
  is "Design record". The name is chosen when the kind is designed, and it
  goes into `ontology/factory.ttl` then.
- **The first record.** The reversal U records, migrated out of U. It is
  short, self-contained and states its own reason, so it tests the kind and
  the migration path on the smallest case.

## Record

- 2026-09-19: `records/` gained the ADR kind by #377. That is the model, the
  loader's required-headings rule, `records list adr`, and three of the four
  checks. What is by hand or later has its own item, b-61127f: `docs/adr/`
  itself and ADR 1, wiring the checks into `check_all`, `records show --kind`,
  `check_adr_principles`, the ontology entry, and `CONTEXT.md` §11's rewrite.
