---
id: 1
title: "Decisions are recorded one per file as ADRs"
status: accepted
date: 2026-09-21
supersedes: []
superseded_by: []
appendices: [P, U]
principles: [30, 56, 57, 62]
---

## Context

Appendix P records three sessions that asked to make the appendices ADRs, and
each was refused. `CONTEXT.md` §11 gave the reason. A `docs/adr/`
tree beside the appendices would be a second address space, and two records
that disagreed would do it undetectably.

Appendix U found that the reason reached only a parallel tree. It moved the
appendices into records under `docs/appendices/`, in the one address space
their letters name. U still said that "ADR" means prior art's records, and that
Saffron keeps no `docs/adr/`.

An appendix records what one revision found, and it is never edited. A
decision that several revisions touched is spread across their appendices, and
nothing marks one replaced. The emitter spans `ontology/RATIONALE.md` and
Appendices O, P and T.

`DESIGN.md`'s appendix index names a second refusal. Per-decision documents
written in parallel would each claim numbers from the same sequence. Backlog
item b-9ff0fd proposed random ids as the answer to try first.

## Decision

Saffron records each decision as one ADR under `docs/adr/`, cited by number,
as in "ADR 1". An ADR holds one decision as it stands today and names the
appendices that argued it. An appendix still records what a revision found,
and principles are still numbered there.

Ids are sequential, not random. An ADR is `protected`, so only a person writes
one, and parallel ADRs are rare. A collision is renumbered before merge, while
nothing cites the new ADR. A random id would give up the short citation, "ADR 1".

A new ADR that replaces older ones lists them in `supersedes`. Each replaced
ADR lists it in `superseded_by`, in the same pull request, and `records/`
holds the two sides equal.

Prior art's records keep their dashed form, as in `ADR-0019`, which Appendix D
cites. Saffron's are cited without the dash.

This ADR replaces the first sentence of Appendix U's "What did not change"
paragraph. U itself is not edited.

## Principles

- **30** departs. Appendix U keeps the sentence this ADR replaces, because an
  appendix is never edited. A reader learns of the reversal from `CONTEXT.md`
  §11, naming decision 4 and `DESIGN.md`'s ADR index.
- **56** upholds. Appendix P refused to make the appendices ADRs. This ADR
  answers a different question, whether one decision gets a record of its own.
- **57** upholds. An ADR summarises its appendices and can widen what they
  decided. Each ADR names its appendices, and `adr-reviewer` reads its Context
  against them before merge.
- **62** upholds. "No ADRs" was argued against a parallel tree. These ADRs are
  cited by number, and a test resolves every citation of one. The records check
  holds a declared supersession on both sides. An undeclared conflict, with an
  ADR or an appendix, is caught only by `adr-reviewer`, by hand.

## Consequences

`CONTEXT.md` §11 defines Saffron's ADR and keeps the dashed form for prior art.
`docs/agents/domain.md` and `CLAUDE.md` name `docs/adr/`. `DESIGN.md` renders
an index of ADRs from the records.

An ADR is `protected`, so no cell writes one. `adr-reviewer` reads each one
against the principles and the accepted ADRs before its pull request merges.

Two branches can claim the same next number. The records check reads one tree,
so each branch passes alone. The duplicate fails on the second branch once it
is rebased on main, or on main after both merge.
