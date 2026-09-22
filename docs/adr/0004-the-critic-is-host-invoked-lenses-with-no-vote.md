---
id: 4
title: "The critic is host-invoked lenses, and any one blocker goes to REBUT"
status: accepted
date: 2026-09-22
supersedes: []
superseded_by: []
appendices: [A, K, L, Q]
principles: [4, 9, 15, 28, 48, 50, 51, 57, 58]
---

## Context

Appendix A replaced a majority of lenses with any single blocker, because a
vote over disjoint lenses never votes. Appendix K found that three green tasks
produced plausible, verified, broken code, and that only an adversary found it.
So the critic is the component that makes the loop's output mean anything.

Appendix L built the critic and measured it against a diff whose defects were
written down first. It found the worst one as a `blocker`, and two true defects
the prior review had not. It invented none. L also found two lenses filing one
finding, so the lenses are less disjoint than §5.5 assumed.

Appendix Q moved every lens out of the implementer's container. Until rev 21
each lens was a new conversation in the implementer's own cell.

The decision is spread across §5.5, §5.5.1, §5.6 and §11.

## Decision

REVIEW is a set of lenses. Each lens is a fresh, read-only session with its own
remit. Its prompt asks for the reason not to merge the change, and forbids
inventing one. The three lenses are correctness, contract and adequacy. ADR 3
records what adequacy is.

The host starts every lens itself. A lens is never a subagent, because the
model decides when to spawn a subagent. A lens that runs only when the model
thinks it relevant is a suggestion. Every declared lens runs on every
reviewed diff, at every risk tier.

Each lens runs in a critic cell. The cell is a new container whose tree is the
base with the exported patch applied, so a lens reads the patch that ships.
The gate table a lens is shown comes from a gate-only cell on the same tree.

A finding is a claim. The host keeps it only if it anchors, either inside a
diff hunk or on a line that names an identifier the diff changed. A dropped
finding is recorded with `anchored = false`, and the drop rate measures the
lens's prompt.

Severity has three levels. A `blocker` goes to REBUT. A `concern` reaches the
operator. A `note` appears in the pull request and is counted nowhere.

There is no vote. Any one anchored blocker goes to REBUT. The implementer gets
one attempt to fix it or argue against it, and the gates run again. A red
re-run ends the task `EXHAUSTED`. Then each lens that raised a blocker confirms
or withdraws it, in a fresh session in a critic cell rebuilt from the
post-rebuttal patch. A confirmed blocker the implementer argued against still
reaches `READY_FOR_REVIEW`, because a person adjudicates it in the pull request.

## Principles

- **4** upholds. No lens runs in the container the implementer had root in.
- **9** upholds. Any one blocker routes to REBUT, since disjoint lenses never
  form a majority.
- **15** upholds. A finding counts only once the host anchors it against the
  diff.
- **28** upholds. The hunk rule was tuned for lenses #1 and #2, and it drops
  most of what lens #3 cites. The second anchoring target exists for that.
- **48** upholds. The lenses look for what the gates did not check, which is
  why the critic runs after the gates pass.
- **50** upholds. The critic does not replace the operator. A person merges,
  and a person adjudicates an argued blocker.
- **51** departs. The no-vote rule rests on disjoint lenses, and Appendix L
  measured two lenses filing one finding. The overlap is a prompt defect, and
  nothing checks for it. §5.5.1 records a class the other way round. Every
  prompt still routes callers and downstream findings to the retired blast
  radius lens, so no lens owns them.
- **57** upholds. This ADR condenses §5.5, §5.5.1, §5.6 and §11, and adds
  nothing they do not state.
- **58** upholds. A lens in the implementer's cell was a fresh conversation on
  a tree the implementer controlled. The critic cell does not rely on the
  implementer having been honest.

## Consequences

Each lens is a paid session on every reviewed diff, and REBUT adds one verdict
session per lens that raised a blocker. REVIEW is not gated on the spend
ceiling, so a lens cannot fail a task for money.

Whether a lens earns its cost is to be measured, not argued. §11 asks for the
count of blockers per lens that the operator agrees with, and cuts a lens whose
count trends toward zero. `harness/lens_scoring.py` scores the lenses against a
fixture whose defects are declared (backlog item 79).

A risk tier adds no lens. Whether a tier gates one is still open (backlog
item 6).
