---
id: b-a4df62
title: Nothing in Saffron reviews a spec before its cell, so the loop's delegate does it by hand for every spec of every run
status: open
tier: 1
filed: 2026-09-20
specs: []
prs: []
commits: []
cites: ["§4.2", "§5.5"]
related: [130, 124, 125, 56, 159, b-281f0a, b-865399]
---

## Problem

Filed 2026-09-20 from the spec loop's runs 8 to 10. Step 1b is the read-only
`spec-reviewer` agent reviewing each spec before its first cell. It is the
delegate's largest manual step, and Saffron does none of it. Run 8 ranked it
A4 and recorded that no item covered it. This is that item.

What the step cost, per run:

- Run 8, five specs (#350): a first review of each, then re-reviews on spec
  branches and at parent branches. Three verified blockers, and every spec
  needed an edit.
- Run 9, two specs (#374): three rounds on `SA-0109` and two on `SA-0110`.
  Every blocker after round 1 sat in text the delegate wrote to answer an
  earlier finding. One reviewer blocker was false.
- Run 10, two specs (#380): five rounds. Three of the nine findings came from
  the delegate's own edits. Each was true about the paragraph it touched and
  false about one it left alone.

The step never converges. Run 7's stop rule was a review with no blocker and
no concern. No run reached one. The operator's standing rule is to fix every
finding, then re-review only a spec whose child forbids its module.

One promotion attempt already failed.
`docs/evidence/2026-09-14-spec-reviewer-backtest.md` ends FAIL, at K = 5 false
blockers against a bar of 2, with recall 18/34 against a bar of 17. The review
stayed advisory in the skill instead of becoming a phase. Items 123 to 125
carry what a second backtest needs, and 124 and 125 are open. Two neighbours
bound how much of the step belongs in prose. b-281f0a computes four of the six
checks the reviewer works out by eye, and b-865399 turned a fifth into a
measurement.

## Done looks like

A host-side phase runs a fresh session over a spec before the scheduler admits
it. The reviewer's own defects are fixed (124), and each review leaves a report
to score (130). A blocker holds the spec out of the queue with a reason in the
morning queue, the way a refusal does (§4.2). It does not stop a cell that is
already paid for. The phase runs unattended only after it clears the bar its
first attempt failed. That bar is recall at or above 17/34, with at most 2
false blockers, pre-registered again, over controls reviewed at their real
bases (125). Until then step 1b stays in the skill, and the delegate keeps
running it.

## Record

- 2026-09-20: filed. Run 8 ranked a spec phase A4 and recorded that nothing
  tracked it (`docs/evidence/2026-09-19-spec-loop-skill-feedback-run-8.md`).
  Runs 9 and 10 repeated the pattern, with the same two causes: the delegate's
  own edits, and a stop rule that never converges. No spec exists. A second
  promotion attempt waits on 124, 125 and 130.
