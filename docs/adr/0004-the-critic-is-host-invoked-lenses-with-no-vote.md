---
id: 4
title: "The critic is host-invoked lenses, and any one blocker goes to REBUT"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [A, K, L, Q]
principles: [4, 9, 15, 16, 17, 27, 28, 29, 30, 34, 36, 42, 48, 50, 51, 55, 57, 58]
---

## Context

Appendix A replaced a majority of lenses with any single blocker, because a
vote over disjoint lenses never votes. In Appendix K three tasks went green,
and the one reviewed was broken in ways only an adversary found. So the critic
is the component that makes the loop's output mean anything.

Appendix L built the critic and measured it against a diff whose defects were
written down first. It found the worst one as a `blocker`, and four true
defects the prior review had not. It invented none. L also found two lenses
filing one finding, so the lenses are less disjoint than §5.5 assumed.

Appendix Q moved every lens out of the implementer's container. Until rev 21
each lens was a new conversation in the implementer's own cell.

The decision is spread across §3.3, §5.5, §5.5.1, §5.6, §11 and
`saffron/cell/session.py`, which holds one rule no section states.

## Decision

REVIEW is a set of lenses. Each lens is a fresh, read-only session with its own
remit. Its prompt asks for the reason not to merge the change, and forbids
inventing one. The three lenses are correctness, contract and adequacy. ADR 3
records what adequacy is.

The host starts every lens itself. A lens is never a subagent, because the
model decides when to spawn a subagent. A lens that runs only when the model
thinks it relevant is a suggestion. Every declared lens runs on every
reviewed diff, at every risk tier. A lens that errors stops the task at
`REVIEWING`, so an unrun lens never reads as a clean review.

Each lens runs in a critic cell. The cell is a new container whose tree is the
base with the exported patch applied, so a lens reads the patch that ships.
The gate table a lens is shown comes from a gate-only cell on the same tree. A
patch that does not apply ends the task `EXHAUSTED`, so a forged export is no
free way past the critic. A binary change is the one exception. Its stub
applies to no base, and it ends `GATE_ERROR`, charged to nobody. Nothing ships
from it, so it is no way past the critic either.

A finding is a claim. The host counts it only if it anchors, either inside a
diff hunk or on a line that names an identifier the diff changed. A dropped
finding is recorded with `anchored = false`, never deleted. The host also
files blockers. A vacuity probe that survives promotes its finding, and a
criterion probe that survives becomes an adequacy finding (ADR 3).

Severity has three levels. A `blocker` goes to REBUT. A `concern` reaches the
operator. A `note` appears in the pull request and is counted nowhere.

There is no vote. Any one anchored blocker goes to REBUT, unless the task is
already over its budget. No ceiling check stops REVIEW. REBUT checks the spend
ceiling before the rebuttal turn, and a task over it ends `EXHAUSTED` with its
findings written.

Otherwise the implementer gets one attempt to fix each blocker or argue against
it. A rebuttal that neither moved HEAD nor argued halts at `REBUTTING`, and the
gates do not run. Otherwise the gates run again, and a red re-run ends the task
`EXHAUSTED`. Then each lens with a blocker confirms or withdraws it, in a fresh
session in a critic cell rebuilt from the post-rebuttal patch. The adequacy
session answers the host's blockers too. Each session also reads the diff
REVIEW saw, because a blocker's line number was filed against that tree. A
verdict set that leaves a blocker unanswered is an error, never a withdrawal. A
verdict session that errors halts the task at `REBUTTING`.

Three outcomes reach `READY_FOR_REVIEW`. Every blocker was withdrawn, or a fix
committed and stayed green, or the implementer argued against a confirmed
blocker. A person adjudicates the last one in the pull request.

## Principles

- **4** upholds. No lens runs in the container the implementer had root in.
  The gate re-run after a rebuttal still does, and Appendix Q accepts it as
  feedback because PACKAGE re-verifies.
- **9** upholds. Any one blocker routes to REBUT. Disjoint lenses never form a
  majority, and overlapping ones agree for reasons that are not evidence
  (principle 51).
- **15** departs. At REVIEW a finding counts only once the host anchors it. At
  REBUT the adequacy session can withdraw a probe the host ran and saw
  survive, so a reading overrules a measurement. ADR 3 records the same step.
- **16** upholds. The budget exit keeps the work. The findings are written, and
  the branch is pushed unpackaged.
- **17** departs. A lens runs on a $2 floor after the budget is gone, so REVIEW
  spends past the ceiling. REBUT upholds it, and refuses before the rebuttal
  turn.
- **27** upholds. The verdict session reads each blocker against the diff it
  was filed on, since the rebuttal moves its line.
- **28** departs. `LensReview.drop_rate` excludes a host-filed survivor, and the
  ledger's drop rate in §4.1 counts it against the lens (backlog item
  b-b431c1). A survivor that fails to anchor never reaches REBUT, and no item
  owns that half.
- **29** departs. "Any one blocker goes to REBUT" has an exception. REBUT's
  budget check sends a task over its ceiling to `EXHAUSTED` with no rebuttal.
  Only a comment in `saffron/cell/session.py` states it, and no section does.
- **30** departs. Three sentences still call the lenses disjoint: §5.5, §7's
  plausible-but-wrong row, and `CONTEXT.md`'s entry for a lens. L measured an
  overlap. No backlog item owns them.
- **34** upholds. A lens that errors stops the task, so an absent review never
  reads as a clean one.
- **36** upholds. A verdict set missing a blocker is an error, not a partial
  result read as withdrawals.
- **42** upholds. The budget exit ends a reviewed diff with no pull request,
  and the pushed branch keeps it readable.
- **48** upholds. The lenses look for what the gates did not check, which is
  why the critic runs after the gates pass.
- **50** upholds. The critic does not replace the operator. A person merges,
  and a person adjudicates an argued blocker.
- **51** departs. The no-vote rule rests on disjoint lenses, and L measured two
  lenses filing one finding. No production check reads overlap. The scoring
  harness keeps one finding per defect per run, so it shows overlap only across
  runs. Item 6 records that the overlap did not recur. §5.5.1 records a class
  owned by nobody. Every prompt still routes callers and downstream findings to
  the retired blast radius lens.
- **55** upholds. Three outcomes share `READY_FOR_REVIEW`, and `rebuttal.json`
  and the sustained blockers tell them apart. Three routes also share
  `EXHAUSTED` at REBUT. Only the budget exit writes no `rebuttal.json`, and it
  emits a `Budget` event. §3.3 draws only the red re-run.
- **57** upholds. This ADR condenses §3.3, §5.5, §5.5.1, §5.6 and §11. It adds
  two rules no section states. The budget exception is in
  `saffron/cell/session.py`. The adequacy session answering host blockers is a
  stopgap that backlog item b-9ed36d holds open.
- **58** upholds. A lens in the implementer's cell was a fresh conversation on
  a tree the implementer controlled. The critic cell does not rely on the
  implementer having been honest.

## Consequences

Every lens and every criterion-probe session is a paid session on every
reviewed diff. Each is capped at what is left of the budget, with a $2 floor,
and the cap is not reduced between sessions. REBUT adds the rebuttal turn and
one verdict session per lens with a blocker. REBUT's budget is inherited as a
remainder, not decided, and backlog item 120 holds that open.

Whether the critic earns its cost is to be measured, not argued. §11 asks for
the count of blockers the operator agrees with. It names cutting a lens whose
count trends toward zero as an option, not a rule. `harness/lens_scoring.py`
scores the lenses against a fixture whose defects are declared (backlog
item 79).

A risk tier adds no lens. Whether a tier gates one is open. Item 6 closed
without settling it, and no open record holds the question.
