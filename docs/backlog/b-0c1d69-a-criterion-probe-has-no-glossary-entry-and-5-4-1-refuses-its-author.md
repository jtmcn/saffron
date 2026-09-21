---
id: b-0c1d69
title: A criterion probe has no glossary entry, and §5.4.1 reads as a refusal of the session that names one
status: done
closed: 2026-09-21
tier: 2
by_hand: true
filed: 2026-09-20
specs: [SA-0113]
prs: []
commits: [21488e89]
cites: [§5.4.1, §5.5]
related: [b-2750d5, b-f2a9d1, 117, 80]
---

## Problem

Found 2026-09-20, writing `SA-0113`.

`SA-0113` has the host ask a fresh session, one acceptance claim at a time, for
the smallest edit that would make that claim false. The witness node id is
withheld from that session. The child spec applies the edit and runs the
criterion's witness over it. A surviving edit is a witness hole.

The edit is neither of the two `CONTEXT.md` already names. A *Mutant* is
"declared by a criterion" and its author is the spec's
(`CONTEXT.md:335-343`). A *Vacuity probe* is "named by a lens" to show what the
tests would miss (`CONTEXT.md:345-352`). Its `_Avoid_` line refuses the word
mutant for one. This edit is named by a session that is not a lens. It is aimed
at the claim rather than at the tests, and it must die under the witness.
`SA-0113` calls it a *criterion probe* and coins the term in code alone.

`DESIGN.md:972` reads the other way on the author. Its heading is "Why the spec
declares the mutant rather than an agent generating it". The reason it gives is
that "a mutant it authored is a mutant chosen to be killed". That holds for the
implementer, which wrote the code and the tests. It does not hold for a session
that wrote neither and never sees the witness. The section says nothing about
that case today.

`CONTEXT.md` is `protected` and is generated from `ontology/factory.ttl`.
`DESIGN.md` is `protected`. So a cell can land neither half, and `SA-0113`
leaves both here.

## Done looks like

A *criterion probe* entry in `ontology/factory.ttl`, with `CONTEXT.md`
re-rendered by `uv run python -m ontology.render`. The entry names who authors
the edit. It says the witness is withheld from that author, and that a probe
surviving its own criterion's witness is the finding. Its `_Avoid_` line keeps
it apart from a mutant and from a vacuity probe.

`DESIGN.md` §5.4.1 gains a paragraph beside the one at `:972`. It says the host
asks a fresh session for the edit a spec could not declare. It names the
withholding as the reason that edit is evidence, and points at the criterion
probe entry. Both halves land after `SA-0113` merges, not before.

## Record

- 2026-09-21: `SA-0113`'s cell shipped the criterion-probe prompt (#403). The
  in-cell `contract` lens raised this item's tension as a concern, and the review
  left it here, since the spec sanctions the design.
- 2026-09-21: Done by hand. `CONTEXT.md` §4 gains **Criterion probe**, with an `_Avoid_` line against mutant and vacuity probe. `DESIGN.md` §5.4.1 gains the paragraph beside the mutant's. Both say no gate applies one yet, which is b-2750d5's open half.
