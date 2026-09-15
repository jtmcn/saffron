---
id: 84
title: '`revert` judges a witness whose subject the spec forbids'
status: done
tier: 1
specs: [SA-0063, SA-0064]
prs: []
commits: []
cites: []
related: [74, 83]
---

## Problem

**Status: done, 2026-09-08 (#166), against `source` rather than the
`touches` this item's *Done looks like* names.** `revert` sets aside a
criterion whose `mutant.file` is not among the source files the diff changed,
and says which in the summary. The divergence is deliberate: `touches` is what
a spec was *permitted* to change, and a spec permitted to change a file it then
left alone leaves the gate equally unable to answer, so `source` — the set
about to be reverted — is what the question is actually made of. `SA-0064`, the
case that filed this, is set aside under either rule.

**One narrowing the first implementation lacked, added in review.** `source`
excludes the repo's declared test paths wholesale, so a subject inside them is
outside `source` for every diff there will ever be: exempting it would have
given any criterion whose `mutant.file` names a test file a standing pass from
the anti-theater gate, bought with one line of frontmatter — `_argv_safe`'s
buyable-`skip` shape from the other side. A test subject says nothing about
whether the witness leans on the source being reverted, so it stays judged.

Received 2026-09-07 through the notes channel item **74** asked for — the first
finding this repo has been handed by an implementer rather than by a lens or a
person. `SA-0063` built the channel, `SA-0064` wired it, and this arrived in
`SA-0064`'s own run, in its own words:

> `revert` ran anyway, found that
> `tests/test_session.py::test_a_protected_path_alone_asks_for_notes` depended
> on none of this diff's own source files … and correctly flagged it as
> theater. … it's a workaround for what reads like a gap in `revert_gate`: it
> has no way to recognize "this witness's mutant is declared against a file
> this spec forbids me from editing" and skip itself accordingly.

`revert_gate` folds every declared acceptance witness into one question — does
this test still pass with the diff's own source reverted — and a spec can make
that question unanswerable. `SA-0064`'s criterion 2 was a deliberate coverage
backfill for a predicate in `saffron/cell/session.py`, a file that spec
`forbids`; only `saffron/phases/package.py` was in `touches`. The new test
therefore depended on none of the diff's source, which is what `revert` calls
theater, and here was the point.

**The workaround shipped.** The test now also drives a real `package.package()`
against a real git remote so that it depends on both, which satisfies the gate
and leaves a test of one boolean predicate standing up a git remote to check it.
That cost is in #160's diff and is the honest reason to fix this rather than
argue it.

The implementer bounds it itself: *"I don't think this generalizes beyond specs
that split a claim's verifier (mutant) from its enforcement site (`touches`) the
way this one does."* Narrow, then — but this is the second gate in two days to
answer `fail`/`error` where the spec's own scope made the question unanswerable,
and item **83** is the first. Same class: a gate that cannot say *unproven*
says something worse.

**Done looks like** `revert` skipping a witness whose subject lies outside the
spec's `touches`, with a summary saying so. "This diff could not have made that
test pass, because the spec did not let it near the code" is unproven, not
theater, and `skip` is the status that already means it.
