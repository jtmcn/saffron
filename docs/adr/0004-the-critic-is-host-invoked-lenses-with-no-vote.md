---
id: 4
title: "The critic is host-invoked lenses, and any one blocker goes to REBUT"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [A, K, L, Q]
principles: [4, 9, 15, 27, 28, 29, 30, 34, 36, 48, 50, 51, 55, 57, 58]
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

The decision is spread across §5.5, §5.5.1, §5.6, §11 and
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
free way past the critic.

A finding is a claim. The host keeps it only if it anchors, either inside a
diff hunk or on a line that names an identifier the diff changed. A dropped
finding is recorded with `anchored = false`, and the drop rate measures the
lens's prompt. The host also files blockers. A vacuity probe that survives
promotes its finding, and a criterion probe that survives becomes an adequacy
finding (ADR 3).

Severity has three levels. A `blocker` goes to REBUT. A `concern` reaches the
operator. A `note` appears in the pull request and is counted nowhere.

There is no vote. Any one anchored blocker goes to REBUT, unless the task is
already over its budget. REVIEW itself never stops for money. REBUT checks the
spend ceiling before the rebuttal turn, and a task over it ends `EXHAUSTED`
with its findings written.

Otherwise the implementer gets one attempt to fix each blocker or argue against
it, and the gates run again. A red re-run ends the task `EXHAUSTED`. Then each
lens with a blocker confirms or withdraws it, in a fresh session in a critic
cell rebuilt from the post-rebuttal patch. The adequacy session answers the
host's blockers too. Each session also reads the diff REVIEW saw, because a
blocker's line number was filed against that tree. A verdict set that leaves a
blocker unanswered is an error, never a withdrawal.

Three outcomes reach `READY_FOR_REVIEW`. Every blocker was withdrawn, or a fix
committed and stayed green, or the implementer argued against a confirmed
blocker. A person adjudicates the last one in the pull request.

## Principles

- **4** upholds. No lens runs in the container the implementer had root in.
- **9** upholds. Any one blocker routes to REBUT, since disjoint lenses never
  form a majority.
- **15** departs. At REVIEW a finding counts only once the host anchors it. At
  REBUT the adequacy session can withdraw a probe the host ran and saw
  survive, so a reading overrules a measurement. ADR 3 records the same step.
- **27** upholds. The verdict session reads each blocker against the diff it
  was filed on, since the rebuttal moves its line.
- **28** departs. Anchoring was checked against three lens producers. The
  host's criterion-probe survivor passes the same filter, and `drop_rate`
  excludes it. A survivor that fails to anchor never reaches REBUT, and nothing
  counts it. No backlog item owns this.
- **29** departs. "Any one blocker goes to REBUT" has an exception. REBUT's
  budget check sends a task over its ceiling to `EXHAUSTED` with no rebuttal.
  Only a comment in `saffron/cell/session.py` states it, and no section does.
- **30** departs. §5.5 and `CONTEXT.md`'s entry for a lens still call the
  lenses disjoint by construction, where L measured an overlap. No backlog item
  owns the pair.
- **34** upholds. A lens that errors stops the task, so an absent review never
  reads as a clean one.
- **36** upholds. A verdict set missing a blocker is an error, not a partial
  result read as withdrawals.
- **48** upholds. The lenses look for what the gates did not check, which is
  why the critic runs after the gates pass.
- **50** upholds. The critic does not replace the operator. A person merges,
  and a person adjudicates an argued blocker.
- **51** departs. The no-vote rule rests on disjoint lenses, and L measured two
  lenses filing one finding. No production check reads overlap. Scoring runs
  show it, and item 6 records that it did not recur. §5.5.1 records a class
  owned by nobody. Every prompt still routes callers and downstream findings to
  the retired blast radius lens.
- **55** upholds. Three outcomes share `READY_FOR_REVIEW`, so the record tells
  them apart. `rebuttal.json` and the sustained blockers carry which one it
  was.
- **57** upholds. This ADR condenses §5.5, §5.5.1, §5.6 and §11. It adds the
  budget exception, and names its only source.
- **58** upholds. A lens in the implementer's cell was a fresh conversation on
  a tree the implementer controlled. The critic cell does not rely on the
  implementer having been honest.

## Consequences

Each lens is a paid session on every reviewed diff, and REBUT adds one verdict
session per lens with a blocker. Each lens is capped at what is left of the
budget, with a floor of $2, so a lens always has room to run.

Whether a lens earns its cost is to be measured, not argued. §11 asks for the
count of blockers per lens that the operator agrees with. It names cutting a
lens whose count trends toward zero as an option, not a rule. `harness/lens_scoring.py` scores the
lenses against a fixture whose defects are declared (backlog item 79).

A risk tier adds no lens. Whether a tier gates one is open. Item 6 closed
without settling it, and no open record holds the question.
