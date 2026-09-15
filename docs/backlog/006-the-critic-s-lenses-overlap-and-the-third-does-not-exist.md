---
id: 6
title: The critic's lenses overlap, and the third does not exist
status: done
tier: null
specs: [SA-0002, SA-0043]
prs: [105]
commits: [80a7a3e]
cites: [§3, §5, §5.5, §5.5.1, §5.6, §7]
related: [2]
---

## Problem

**Status:** **done** — `SA-0043`, PR #105 (`80a7a3e`). The third lens exists
as `saffron/agents/prompts/review-adequacy.md`, wired at `phases/review.py:39`.
The remit question this item raised was settled separately by #34, and
`review.py:41` records the reasoning: the third lens is adequacy, not blast
radius.

Measured on the critic's first live run (Appendix L): **both lenses filed the
same `touches` finding.** §5.5's no-voting rule rests on lenses being disjoint by
construction — *"the schema critic will never independently corroborate the
correctness critic's timezone finding"* — so an overlap is a prompt defect, not a
duplicate to deduplicate. Principle 51: two lenses reaching one finding is a fact
about the prompts, and it reads as corroboration, which is what makes it
dangerous.

Lens 3 (blast radius) is not built because no risk tier is wired into
`run_one_cell`. It is the lens that would have caught item 2 — the review found
the `srcPrefix` escape and the critic did not, because it lives in `session.py`
rather than in the diff.

**Done looks like:** remits that do not overlap, a risk tier on the task, and the
third lens at `elevated`.

**Amended 2026-08-25 by `SA-0002`, and the amendment changes what lens 3 should
be.** The overlap did not recur: correctness filed the counting blocker,
contract filed a `tool` concern, disjoint by construction on a second live diff.
One run is not proof the prompts are fixed, but it is evidence the remits hold.

The sharper finding is what *both* lenses missed. A later review of the same
97-line diff found two mediums neither lens raised. One was a `-diff`
gitattribute zeroing the count — the escape route item 2 leaves open, arriving
in a new gate. The other was that the multi-file header reset had **no test**:
deleting the line left all sixteen tests passing while a two-file diff
overcounted by two lines per file. That second one is the same class as the
blocker correctness *did* catch — a header-collision bug in `_changed_lines` —
found one level up, in whether the suite would notice a regression.

So the gap the third lens should close is not blast radius. **No lens asks
whether the tests would catch the code being wrong**, and a critic that reads
the diff without mutating it cannot: the implementer's own tests passed, the
gates were green, and the line was invisible to every one of them.

**Corrected 2026-08-25 by #33: the line is not uncovered, and the word mattered.**
Measured twice independently — `saffron/gates/core/size.py` reports **100%
statement and 100% branch coverage** from its own tests, and the reset line is
executed by every one of them. The defect is an *executed line whose effect
nothing observes*, which is the one class coverage cannot report by
construction. The wrong word had a cost: it made diff-scoped coverage look like
a cheap answer to this remit, and #33 was written to price an option that was
never available. See `docs/evidence/2026-08-25-mutation-testing-vs-a-lens.md`.

**And `DESIGN.md` §5.5 says the opposite of this item, which is #34's to
settle.** `DESIGN.md:782`: *"lens #3 in a naive design would be 'test quality' —
but the `revert` gate now answers that mechanically and for free."* Neither
document cites the other. The displacement is also incomplete (reasoned, not
measured): `revert` stashes the source hunks and requires the new tests to fail,
but `SA-0002` landed source and tests together, so stashing the source fails all
sixteen and `revert` reports green without ever asking whether the reset line
specifically is tested. `revert` asks whether the new tests test *anything*;
this remit asks whether they test *each thing*.
§5.5's disjointness argument still holds — this is a third remit, not a second
opinion on the first two.

**Half done, 2026-09-02, by #34 — the remit half, not the risk-tier half.**
This item's own "done looks like" named two things: remits that do not
overlap, and the third lens at `elevated`. Only the first shipped. The third
lens is `adequacy` (`saffron/agents/prompts/review-adequacy.md`), a prompted
critic with no mutation tool and no coverage gate — both were priced again
against this item's own evidence and both lost again, for the reasons already
recorded above. It reads the diff and asks whether the tests in it would
actually notice the code being wrong: an assertion on a value the exercised
code never reads, a test that constructs the value it then asserts, a
structural check over source text a rename defeats, a witness whose setup is
the only input the new code is correct for. Holding no tool that can run
anything, it cannot mutate a line and watch a test fail the way a person
would — so every finding names the edit that would keep the suite green
instead, checkable in one command by whoever can run one. The correctness
lens's own `Evidence` bullet — the one BACKLOG item 6 first flagged as
misfiled test-adequacy language sitting under a data-semantics remit — moved
into this lens rather than being copied, and all three prompts now name all
three boundaries in their `Not yours` lists.

**The risk-tier half is deliberately still open, not silently dropped.**
Nothing in v0.5 or since carries a risk tier that could gate this lens the way
this item originally specified, and building one was out of scope for #34:
measured against this repo's own specs, 28 of 34 declare `elevated`, so
gating on tier would exclude six specs while costing an edit to the
supervisor — which #34 could not touch — for a saving of one lens session
($0.76–$0.91 on the two specs it was priced against). The lens runs at every
tier instead, and REVIEW is not gated on the host budget ceiling, so this
does not fail a task for money. Closing this item for real still means
wiring a risk tier into `run_one_cell` and deciding whether `adequacy` is the
lens that tier gates or whether, having shipped ungated, it stays that way.

**And `DESIGN.md` §5.5 still says the opposite of the shipped code — #34 did
not settle it after all.** The spec put `DESIGN.md` and `CONTEXT.md` in
`forbidden`, so the cell structurally could not touch either; the sentence
above assigning that half to #34 stands unanswered rather than resolved, and
this paragraph exists so the trail is not lost with the work. §5.5 still lists
lens #3 as blast radius at `elevated` (`:889`, `:893`), still asserts `revert`
displaces a test-quality lens (`:903`), and §5.6 still says the tier *adds*
the third lens (`:915`); §7's cost table still prices `Review × 2 lenses`
(`:1124`) and the roadmap still files the third lens under v2 (`:1217`).

`CONTEXT.md` is worse than stale, because it is a runtime input rather than a
record: §5's `Lens` entry names the three remits as correctness, contract and
blast radius, and `context.SECTIONS_BY_PHASE["REVIEW"]` injects §5 verbatim
into every lens's system prompt under a heading reading *"These terms have
exactly one meaning here."* The adequacy lens is therefore handed a vocabulary
block that does not contain its own lens and does contain one that will never
file anything, and §3's *"Elevated adds the third lens"* is now false at every
tier. No gate compares either document against `review.LENSES`, so both are
invisible to the suite.

**Retiring blast radius leaves its remit owned by nobody, at three seats.** All
three prompts still name "the blast-radius lens" in their `Not yours` lists, so
callers-and-downstream findings are actively routed away from every lens that
could file one — worse than uncovered, because each lens is told someone else
has it. Left deliberately (`DESIGN.md` §5.5.1): releasing the remit by editing
three `Not yours` lists scatters it across three lenses, which is the overlap
this item was opened about. Reviving it is a new decision with its own
evidence, and it wants the same risk tier the half above is waiting on.

*(Added 2026-09-13.)* The spec loop's Spec seat
(`.claude/skills/run-saffron-spec-loop/REVIEW-PROMPT.md`) asks for "call sites
the fix should also cover", which leaves it, host-side, the one place this
remit is still reviewed. What it finds that no lens raised goes into
`.saffron/rejections.md`: the evidence this decision is waiting on.
