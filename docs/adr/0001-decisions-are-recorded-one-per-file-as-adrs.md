---
id: 1
title: "Decisions are recorded one per file as ADRs"
status: accepted
date: 2026-09-21
supersedes: []
superseded_by: []
appendices: [P, U]
principles: [62]
---

## Context

Appendix P records three sessions that asked for ADRs and were refused.
`CONTEXT.md` §11 gave the reason. A
`docs/adr/` tree beside the appendices would be a second address space, and
two records that disagreed would do it undetectably.

Appendix U found that the reason reached only a parallel tree. It moved the
appendices into records under `docs/appendices/`, in the one address space
their letters name. U still said that "ADR" means prior art's records, and that
Saffron keeps no `docs/adr/`.

An appendix records what one revision found, and it is never edited. A
decision that several revisions touched is spread across their appendices, and
nothing marks one replaced. The emitter spans `ontology/RATIONALE.md` and
Appendices O, P and T.

## Decision

Saffron records each decision as one ADR under `docs/adr/`, cited by number,
as in "ADR 1". An ADR holds one decision as it stands today and names the
appendices that argued it. An appendix still records what a revision found,
and principles are still numbered there.

A new ADR that replaces older ones lists them in `supersedes`. Each replaced
ADR lists it in `superseded_by`, in the same pull request, and `records/`
holds the two sides equal.

Prior art's records keep their dashed form, as in `ADR-0019`, which Appendix D
cites. Saffron's are cited without the dash.

This ADR replaces the first sentence of Appendix U's "What did not change"
paragraph. U itself is not edited.

## Principles

- **62** upholds. "No ADRs" was argued against a parallel tree. These ADRs
  live in one address space, cited by number, and a test resolves every
  citation of one.

## Consequences

`CONTEXT.md` §11 defines Saffron's ADR and keeps the dashed form for prior art.
`docs/agents/domain.md` and `CLAUDE.md` name `docs/adr/`. `DESIGN.md` renders
an index of ADRs from the records.

An ADR is `protected`, so no cell writes one. `adr-reviewer` reads each one
against the principles and the accepted ADRs before its pull request merges.

Two branches can claim the same next number. The records check refuses the
duplicate before either merges.
