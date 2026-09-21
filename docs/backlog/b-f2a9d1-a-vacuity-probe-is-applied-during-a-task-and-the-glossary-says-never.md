---
id: b-f2a9d1
title: A vacuity probe is applied during a task once SA-0109 lands, and the glossary and §5.5.1 say it never is
status: done
closed: 2026-09-21
tier: 2
by_hand: true
filed: 2026-09-18
specs: [SA-0109]
prs: []
commits: [21488e89]
cites: [§5.5, §5.5.1]
related: [117, 65, 72]
---

## Problem

Found 2026-09-18, writing `SA-0109`.

`CONTEXT.md` defines a *vacuity probe* as applied by the corpus harness only.
Its words are "never by a gate and never during a task".
`DESIGN.md` §5.5.1 says the adequacy lens cannot run anything, so every finding
names an edit "checkable in one command by someone who *can* run one". Neither
says that the host runs that edit.

`SA-0109` makes the host apply every anchored adequacy probe after REVIEW. A
probe's verdict then decides the finding: `survived` becomes a blocker,
`killed` demotes it to a `note`, and `unproven` leaves it as filed. Both documents
are `protected`, and `CONTEXT.md` is generated from `ontology/factory.ttl`, so
the cell cannot change either.

## Done looks like

The *vacuity probe* entry in `ontology/factory.ttl` rewritten, with
`CONTEXT.md` re-rendered by `uv run python -m ontology.render`. The entry says
the host applies the probe after REVIEW, in a Gate-only cell, and that the
verdict decides the finding. `DESIGN.md` §5.5.1 gains a paragraph saying the
same thing and naming the three verdicts. Both land after `SA-0109` merges,
not before.

## Record

- 2026-09-21: the spec loop's run 11 (#403) found a second reader. `SA-0113`'s
  criterion-probe prompt injects the `CONTEXT.md` section holding that entry
  into every probe session.
- 2026-09-21: Done by hand. The **Vacuity probe** entry says the host applies the probe after REVIEW in a Gate-only cell, and that the verdict decides the finding. `DESIGN.md` §5.5.1 gains the paragraph naming the three verdicts.
