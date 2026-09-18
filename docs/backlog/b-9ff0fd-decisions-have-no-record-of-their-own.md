---
id: b-9ff0fd
title: Decisions have no record of their own, so where one stands today is spread across appendices
status: open
tier: null
filed: 2026-09-18
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: []
---

## Problem

The appendices are records now, one per revision, and a revision records
several decisions. Where one decision stands today still means reading every
appendix that touched it: the emitter spans `ontology/RATIONALE.md` and
Appendices O, P and T. Nothing marks a decision replaced.

## Done looks like

A record kind holding one decision per file, designed and landed, with the
reversal the new appendix, U, records migrated into it first. The design
answers four things:

- Numbering. Principles are one sequence each appendix claims a block of, which
  is why per-decision files written in parallel were refused. The backlog's
  answer, random ids after item 177, is the one to try first.
- Supersession. `superseded_by` holds one id, and a decision can be replaced
  by several.
- The name. "ADR" is on `CONTEXT.md`'s _Avoid_ list, and "decision record"
  already means prior art's records there. It goes into `ontology/factory.ttl`
  when chosen.
- Which decisions migrate, and whether an appendix then cites them.
