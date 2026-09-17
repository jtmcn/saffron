---
id: 165
title: The eleventh event kind needs a vocabulary entry no cell can write, because CONTEXT.md is generated from the ontology
status: open
filed: 2026-09-17
by_hand: true
specs: []
prs: []
commits: []
cites: [§4.1]
related: [43, 36, 37, 38, 65, 72]
---

## Problem

Filed with `SA-0101`, per the rule in `docs/agents/issue-tracker.md` that a spec
introducing a term files its vocabulary follow-up when it is written.

`SA-0101` adds an eleventh event kind, for the task's own terminal announcement
and the rate-limit rejection. Both are `events.FINDINGS[0]` today, and both stay
bare prints until that spec lands.

The entry cannot go in the same cell. `ontology/factory.ttl` is editable by a
cell, and `CONTEXT.md` is `protected` and generated from it, so the two halves
cannot move together inside one task. Intake refuses the attempt. That is the
same trap items 65 and 72 record: `witness`, `mutant` and the four batch stop
reasons each reached `main` with the code using a word the glossary did not have.

Two comments about this kind already disagree on its number, which is what an
unowned term looks like before it has an entry. `saffron/cell/session.py:2268`
calls it "a tenth kind". `events.FINDINGS[0]` calls it "a eleventh kind". `Event`
unions ten kinds and `_KINDS` maps ten names, so eleventh is right and the
`session.py` comment counts from a draft that had nine.

Three neighbouring items are the rest of this surface, all tier 2. Item 36 says
the event schema wants its own `DESIGN.md` §4 subsection and nothing can write
one. Item 37 says `events.Terminal` and `CONTEXT.md`'s "terminal state" are two
different things. Item 38 says `events.Phase` splits `GATE` and `REPAIR` where
`CONTEXT.md` does not.

## Done looks like

The eleventh kind has a name in `ontology/factory.ttl`, and `CONTEXT.md` is
regenerated from it by `uv run python -m ontology.render`. The name the code uses
is the name the glossary defines. The stale count in
`saffron/cell/session.py` is gone rather than corrected to a number that will
drift again. Worth doing in one pass with items 36, 37 and 38, which are the same
surface and the same by-hand constraint.

## Record

**Filed 2026-09-17 by hand**, with `SA-0101`. By hand because the change spans
`ontology/factory.ttl` and the `CONTEXT.md` generated from it. A cell cannot move
the generated half with the vocabulary in one task.
