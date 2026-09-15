---
id: 53
title: Three closed sets live only in the shapes, where nothing cross-checks them
status: open
tier: 3
specs: []
prs: []
commits: []
cites: [§4]
related: [56]
---

## Problem

The item says the reason matters more than the choice, so: the test is **who
has to know the term.** `SpecType` appears in every spec's frontmatter and,
since item 56, selects the size ceiling that can end a run `EXHAUSTED`.
`BlockingLevel` is written by repo authors in `policy.yaml`, which is the exact
surface v2's afternoon-long onboarding is measured against. The rebuttal roles
render into pull request bodies read at review time. None of the three is
internal to the shapes.

§4's precedent for leaving repo-defined gate *names* out does not extend to
these: gate names are open by design, and a set that is closed by `sh:in` and
enforced by a blocking gate is a controlled vocabulary whether or not it is
written down as one.

`SpecType` (`feature`/`bug`/`refactor`), `BlockingLevel`
(`alwaysBlocking`/`blockingWhenElevated`/`advisory`) and the rebuttal roles
(`disputes`/`concedes`, `confirms`/`withdraws`) are closed by `sh:in` in
`ontology/shapes/factory-shapes.ttl` and enforced by the blocking `shacl` gate.
None is among the generated sets, because `CONTEXT.md` does not enumerate any of
them — so `test_vocabulary_agrees_with_context` cannot see them and
`ontology/render.py` does not write them.

They are therefore in exactly the state the generated sets were in before Phase
A: a closed set with one hand-maintained copy per file, and no check that the
copies agree. The difference is that the second copy has not been written yet,
so nothing has drifted. This is a deferred decision, not a live defect.

## Done looks like

a decision, in writing: either `CONTEXT.md` enumerates them
and they join `CLOSED_SETS`, `SETS` and `SHAPE_SETS` — three lines and a
regenerate — or a stated reason why they are shape-internal and not vocabulary,
of the kind §4 already gives for repo-defined gate names. The reason matters more
than the choice; `test_the_generator_and_the_cross_check_name_the_same_sets`
will hold whichever way it goes.

## Record

**Decided 2026-09-04: they are vocabulary. Enumerate all three** in
`CONTEXT.md`, joining `CLOSED_SETS`, `SETS` and `SHAPE_SETS` — three lines and
a regenerate. **Tier 3.**
