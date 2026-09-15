---
id: 86
title: The notes channel's two rendering-side safety properties are unwitnessed
status: done
tier: 3
closed: 2026-09-12
specs: [SA-0063, SA-0064]
prs: []
commits: [0631855]
cites: []
related: [82]
---

## Problem

**Status: the two assertions are done, 2026-09-12, by hand** —
`test_a_mention_and_a_closing_reference_are_defanged_inside_the_notes` and
`test_notes_with_nothing_in_them_render_no_heading` in `tests/test_report.py`,
each run red against the mutant this item describes (the `neutralize` call
dropped; `_notes`'s own empty `return ""` dropped, matched uniquely rather than
by first occurrence). Whether `preserves` should name what would falsify it
stays open here, beside item **82**.

**Still unwritten, 2026-09-09, and the corpus now says so with a number.** Both
properties are `SA-0063`'s declared defects, and the baseline pass graded
**neither** — every finding that fixture produced anchored in
`saffron/cell/session.py` and `saffron/phases/package.py`, none in
`saffron/report/pr_body.py` or `tests/test_report.py`. So no lens reached them,
which is a measured miss rather than the assumed one. The two assertions are
still owed.

Found reviewing `SA-0064` (#160), 2026-09-07, by mutation rather than by
reading. Both are gaps in what the suite *proves*, not live defects — I
confirmed each behaviour holds today by hand. Both live in
`tests/test_report.py`, which `SA-0063` and `SA-0064` each had outside their
`touches`, so neither run could have closed them.

**Neutralization on the notes path is asserted nowhere.** `_notes` does defang
an `@mention` and a `Fixes #12` — measured: `_notes("ping @maintainer and Fixes
#12")` comes back with zero-width joiners in both. But
`test_notes_cannot_move_a_status_or_a_gate_result` feeds exactly that string in
and then asserts only that the *head* of the body is unchanged. It never looks
inside the notes section, so deleting the `neutralize` call on this path leaves
the suite green. This is the one place a cell's output causes an effect outside
the boundary without executing (`pr_body.neutralize`'s own docstring), and the
notes are a new way into it.

**`SA-0064`'s criterion 4 does not witness its own claim.** It reads *"a task
that recorded nothing packages the body it packages today"* and names
`test_the_pr_body_reports_the_effective_tier_not_the_specs_declared_one` as the
witness, with `preserves: true`. Measured at `0631855`: make `_notes` render
a heading over
empty notes and that test stays green — the only test that turns red is
`test_notes_cannot_move_a_status_or_a_gate_result`, and it catches it
incidentally, through an exact-prefix comparison aimed at something else.

Watch the mutation itself: `        return ""` appears seven times in
`pr_body.py` and only line 390 is `_notes`'s, so a first-occurrence replace
lands in an unrelated function and reports a green suite that means nothing.
It did, on the first attempt at this measurement — the number was right and
the thing measured was not. A
`preserves` witness is a keep-this-green contract rather than a real witness, so
this is defensible as written; the property is nonetheless guarded by accident.

That second half is a spec-authoring fault, not an implementer's, and it
generalises: a `preserves` witness is only as good as the operator's judgement
that the named test would actually notice, and nothing checks that judgement.
`criteria` confirms the test passed at both ends, which it would whether or not
it has anything to do with the claim.

**Done looks like** two assertions in `tests/test_report.py` — that a mention
and an issue-closing reference are defanged *inside* the rendered notes section,
and that empty notes render no heading — plus, separately worth deciding,
whether `preserves` should require the operator to name what would falsify it
the way `mutant` does for the other direction. The first is half an hour; the
second is a design question and probably belongs beside item **82**.
