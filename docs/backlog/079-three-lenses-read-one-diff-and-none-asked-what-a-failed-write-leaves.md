---
id: 79
title: Three lenses read one diff and none asked what a failed write leaves behind
status: open
tier: 1
filed: 2026-09-06
specs: [SA-0062]
prs: [154]
commits: []
cites: [§5.4, §5.5, §9]
related: [69, 78, 88]
---

## Problem

**Still owed by this item:** the independent review itself is not kept beside
the fixture. `recorded-findings.json` holds REVIEW's *production* output, which
is what `calibrate` needs; the independent grading survives only as declared
phrases and severities in `fixture.toml`, sourced from item 78. "With the
independent review beside it" is not yet literally true.

Found 2026-09-06, comparing REVIEW's output on PR #154 against an independent
review of the same `base..head`. REVIEW filed **0 blockers and 3 concerns** and
the task reached `READY_FOR_REVIEW` at $8.70. The independent pass over the same
range found the two defects in item **78**, both of which destroy or poison the
worktree while reporting something else, and graded both critical. Two of
REVIEW's three concerns match findings the independent pass graded *below* those
two. Neither of the two was filed at any severity.

The fact that makes this a remit gap rather than bad luck: **both were findable
by reading.** Each is named in a comment already in the tree —
`gates/core/revert.py:174` states the refusal and its reason,
`gates/core/witness.py:79` names the `__enter__` shape and says the obligation
binds every implementation. Neither needed a mutation run to surface. This is
therefore not item **69**, which is the adequacy lens reaching for an answer only
running can give. Here the answer was in the repository, and no lens was looking
for it.

§5.5's three lenses are correctness & data semantics, contract & schema, and
test adequacy, **disjoint by construction** — which is the property that makes
any single blocker route to REBUT without a vote. The cost of that choice is
that the lenses do not backstop each other, so a question no lens owns is not
covered thinly, it is invisible. *What does the failure path leave behind* is
such a question. It is not correctness of the happy path, not schema, and not
test adequacy.

Worth recording alongside it, because it is cheaper to fix and may be the same
cause: the adequacy concern that *was* filed describes `witness_gate` reporting a
false `pass` where §5.4 requires `error`, which contradicts an acceptance
criterion the same PR body renders as satisfied. §5.5 already holds that a lens
filing everything as `concern` is as much a prompting defect as one that
hallucinates; a finding contradicting a checked criterion is a candidate for
`blocker`, and nothing currently says so.

## Done looks like

PR #154's range kept as a known-bad diff with its two graded
defects and the independent review beside it — the way Appendix L measured the
critic against one — and REVIEW re-run against it after any lens change, scored
on how many of the two it raises. The fix is a remit rather than machinery:
either widened on an existing lens or given to a fourth, and measured against
that diff rather than argued. Cheap to try, and it is the item that decides
whether §9's "merge half of what it produces" is read off a number that means
anything.

## Record

**Status: measured 2026-09-07, and the diagnosis below is wrong on one point.**
The known-bad diff this item asks for exists — `docs/evidence/fixtures/SA-0062/`,
scored by `harness/lens_scoring.py` and re-runnable after any lens change. First
pass, three runs, $5.70: `docs/evidence/2026-09-07-lens-scoring-first-pass.md`.

Both defects **are** raised. The truncating write was filed 3/3, by the
**contract** lens, reached through `witness.Mutated`'s own written contract; the
undo-over-uncommitted-work 2/3 by correctness. So *what does the failure path
leave behind* is not a question no lens owns — the run this item was written
from is the one where the correctness lens spent itself on a UTF-8 concern
instead, and a single sample read as a remit gap. What is real is the variance
in *which* defect a run raises and at what grade: run 1 missed the undo, run 3
filed the truncating write as a concern, run 2 filed both as blockers. The fix is
therefore aimed at that spread, not at widening a remit or adding a fourth lens,
neither of which would have changed run 1. The paragraph below proposing the
fourth lens is superseded; everything else in the item stands, including the
`blocker`-for-a-contradicted-criterion suggestion at the end, which is untested.

**Corrected 2026-09-08.** This block first read "run 1 of three would still have
shipped this pull request green", which the pass's own data contradicts: anchored
blockers per run are 1, 2, 1 — run 1's contract lens filed the truncating write
as a blocker at `worktree.py:418` — and §5.5 routes any single anchored blocker
to REBUT. All three runs would have blocked, against zero on the production run
of the same range. The number came from `dirty-restore`'s 2/3, a per-defect score
applied to a per-pull-request claim. The gap it hides is the interesting one and
is now open as item 88: 3/3 here against 0/1 in production is larger than lens
variance explains, and the frozen `gates.txt` reading `no tool reported` on all
14 lines is the leading candidate.

**Track A is delivered, 2026-09-09.** The scored corpus exists and has a kept
baseline: `docs/evidence/2026-09-09-lens-corpus-baseline.md`, eight fixtures,
twelve declared defects, `3/12` graded. The exit criterion in
`docs/superpowers/plans/2026-09-07-trusting-the-queue.md` is rewritten off this
item's one fixture onto that corpus. **This item is not thereby closed**: it asks
whether a lens owns the failure-path question, and a corpus that grades 3 of 12
is a measurement of that gap rather than a closing of it.
