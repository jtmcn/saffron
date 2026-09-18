# The appendices as records

Written 2026-09-18. The backlog design named this as a follow-on
(`2026-09-14-backlog-as-records-design.md`, "Appendices as decision records") and
left it as a vocabulary decision to record when it was made. This is that
decision. `DESIGN.md`'s twenty appendices, A to T, become one file each under
`records/`'s second kind, `appendix`. They keep their letters, so no citation
moves. The move is the first step toward recording decisions as their own
records, and it is written down as that intent in a new Appendix U.

## The problem, measured

`DESIGN.md` is 3,057 lines. Lines 1,658 to the end are the appendices, so more
than 45% of the file is revision narrative that no reader wants whole.

The appendices record decisions as a timeline, not one record per decision. Each
is "what rev N found". Finding where one decision stands today means reading
several. The emitter is the plain case: `ontology/RATIONALE.md` closed it,
Appendix O reopened the question around it, Appendix P deferred it, and Appendix
T reopened it. `DESIGN.md` mentions it about twenty times.

Nothing marks a decision as replaced. Appendix P still says the emitter is
"Deferred" (`DESIGN.md:2792`), and no field or test connects that sentence to
Appendix T.

Three sessions asked whether the appendices should be ADRs, and Appendix P
answered no. Its reason was a second address space: a `docs/adr/` tree beside
the appendices, where the first two records to disagree would do it
undetectably (`CONTEXT.md:641`). That reason holds against a *parallel* tree.
It does not hold against moving the appendices themselves into records, which
is one address space with the same letters.

What records give that prose in one file does not, measured by the backlog
move: a record per file, typed frontmatter, and integrity tests that run under
`make check`. `records/kinds.py:137` already has a `KINDS` registry built for
more than one kind.

## Approach

Move each appendix, verbatim, into `docs/appendices/<letter>-<slug>.md`, and
register `appendix` as a second kind. Letters are permanent ids. `DESIGN.md`
keeps §1 to §11 and both indexes, and both indexes render from the records.

Two alternatives were set aside:

- **Keep the appendices in `DESIGN.md` and add status and supersession to
  `factory:RevisionAppendix`.** It fixes the missing supersession link, but
  every check would be built inside the ontology parser, and the file stays
  3,057 lines. The records package already has the checks.
- **A `docs/adr/` tree for new decisions only.** This is the parallel address
  space Appendix P refused, and the refusal is right for it.

## The record

### Location

```
docs/appendices/P-the-vocabulary-covers-the-design-record.md
```

The letter, then a slug cut from the heading's title less any `rev N:`. The pattern is
`^[A-Z]{1,2}-[a-z0-9-]+\.md$`. Two letters because U is the twenty-first and Z
is the twenty-sixth: six appendices remain in one letter. After Z comes AA.
`ontology/design_record.py:36`'s `APPENDIX` reads `[A-Z]` and widens with it.

### Frontmatter

Every field is one the appendix index already states by hand
(`DESIGN.md:1539`), so nothing is invented:

```yaml
---
id: P
title: "rev 20: the vocabulary covers the design record"
revisions: [20]
question: >-
  Should the appendices have been ADRs? No — and the phrase that kept the
  question alive was a summary of two verdicts that nobody decided
---
```

- `title` is the heading after its em dash, verbatim. The headings are not
  uniform (`Appendix A — What changed in rev 2, and why`), so it is not parsed
  further.
- `revisions` is the index's `Rev` column. It is now the only place the list is
  written, so `design_record.py:92`'s check that a heading's rev appears in its
  index row has nothing left to compare and is deleted with the heading.
- `question` is the index's third column.

There is no `status` and no `superseded_by`. An appendix is a permanent record
of what a revision found, and it is never replaced. Supersession belongs to the
decision records that come later. `Identified.status` (`records/kinds.py:57`)
moves onto `BacklogItem`, whose validators are its only readers apart from
`records/check.py:115`, `:248` and `:282`, all three on backlog records.

Principles are not declared in frontmatter. They stay numbered lines in the
body, and `design_record.py` keeps reading them there, so a principle is
written once.

### Body

The appendix's prose, verbatim, without its `## Appendix X —` heading. The
appendices use `###` subheadings (49 of them) and no `##`, so the body has no
`## ` sections. Today the loader's section rules are backlog-only and live in
`records/load.py:23` and `:109`. They move onto `Kind`, and `appendix` declares
none. The backlog design planned this move for when specs join as a kind. It
happens here instead.

## What reads the records

- **`ontology/design_record.py`** parses principles and appendices from the
  records instead of from `DESIGN.md`. `render_principles` still writes the
  principle index into `DESIGN.md`, and the direction is unchanged: the
  appendices are authoritative and the index is their render.
- **The appendix index** (`DESIGN.md:1533`) becomes a render too. It is
  hand-written today and held by
  `tests/test_citations.py:341`'s test that it lists every appendix. Rendered
  from `id`, `revisions`, `question` and the principle numbers, it cannot be
  a row short, so that test is replaced by the currency test the principle
  index already has (`tests/ontology/test_design_record.py:86`).
- **`tests/test_citations.py`** takes `APPENDICES` from the records directory,
  not from `APPENDIX` over `DESIGN.md` (`tests/test_citations.py:36`, `:179`).
  Every `Appendix X` citation still has to resolve.

## Validation

In `tests/records/`, against the live directory, beside the backlog's:

- Ids unique, the filename prefix equals `id`, and the letters run
  contiguously from A to the last one.
- Every `Appendix X` citation resolves, as above.
- The principle tests in `tests/ontology/test_design_record.py` keep running
  unchanged against the new source: one global sequence, each appendix a
  contiguous block, every appendix reached.

## Migration

**Pass 1, mechanical.** A throwaway script splits `DESIGN.md` from line 1,658
on `^## Appendix ([A-Z]) — (.*)$`. `id` and `title` come from the heading, and
`revisions` and `question` from the index row with the same letter. The body is
everything up to the next heading. Done when the twenty bodies, rejoined with
their headings, are byte-identical to the removed range.

**Pass 2, Appendix U.** Written by hand as `rev 25`. It records three things:
that Appendix P's no is reversed for the appendices themselves, and why the
parallel-tree reason does not reach this move; that naming decision 4 in
`CONTEXT.md` is amended; and the intent to record decisions as their own
records and migrate them out of the appendices. It contributes a principle only
if writing it finds one. `DESIGN.md`'s status line gains rev 25.

**Pass 3, the surfaces that say otherwise.**

- `CONTEXT.md` §11: **Revision appendix** is a record under `docs/appendices/`,
  and the **ADR** entry keeps its point about prior art's `ADR-NNNN` but drops
  "Saffron keeps no ADRs" for what this decision says. Naming decision 4
  gains the reversal.
- `docs/agents/domain.md:11`, and its tree at `:21`.
- `CLAUDE.md`'s sentence on the principle index, which names where a new
  principle is written.
- `DESIGN.md:1571`'s paragraph on why an appendix is coarse stays. It states
  the constraint the decision kind has to meet.

**Prose scope, in its own commit.** `.saffron/gates/prose.py:36` covers
`DESIGN.md` but not `docs/appendices/`. `hooks/prose_limit.py` compares a new
file against zero hits, so adding the directory to `INCLUDED_DIRS` in the
same commit as the move would fail the hook on text that moved and did not
change. The move lands first, and the scope change follows with no appendix
file staged, so the moved prose is the baseline.

## Delivery

A two-pull-request stack with `gh stack`, as the backlog was:

1. **`records/`**: the `appendix` kind, section rules onto `Kind`, `status`
   onto `BacklogItem`, loader tests on a fixture directory.
2. **The move**: passes 1 to 3, the readers switched to the records, the prose
   scope commit, and the backlog item below.

Both are by hand. `DESIGN.md`, `CONTEXT.md` and `.saffron/**` are `protected`
(`.saffron/policy.yaml:57`), so no cell can run this.

## Follow-on, filed with the move

A `by_hand: true` backlog item for the decision record kind. What it has to
answer, stated now so it is not rediscovered:

- **Numbering.** Principles are one sequence that each appendix claims a block
  of when it is written, which is why per-decision documents written in
  parallel were refused (`DESIGN.md:1571`). The backlog met the same problem
  with random ids after item 177 (`records/kinds.py:34`), and that answer is
  the one to try first.
- **Supersession.** `BacklogItem.superseded_by` holds one id. A decision split
  into several, or replaced by several, needs a list.
- **The name.** "ADR" is on `CONTEXT.md`'s _Avoid_ list because every
  `ADR-NNNN` in `DESIGN.md` cites prior art. "Decision record" does not collide.
- **The first record.** Appendix U's reversal, migrated out of U. It is short,
  self-contained and states its own reason, so it tests the kind and the
  migration path on the smallest case.
