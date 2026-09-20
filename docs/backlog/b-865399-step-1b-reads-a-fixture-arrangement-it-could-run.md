---
id: b-865399
title: Step 1b judges a criterion's fixture arrangement by reading, when the helper it will be judged by can be run against it
status: done
tier: 2
by_hand: true
filed: 2026-09-19
closed: 2026-09-19
specs: []
prs: [387]
commits: [f03a6afb]
cites: []
related: [123, 124, b-2750d5, b-281f0a]
---

## Problem

Found in the spec loop's run 10, 2026-09-19, on `SA-0112`.

Step 1b's check 3 is witness and mutant discipline, and the reviewer answers it
by reading, because its Bash is limited to git and `driver.py history`. A
criterion can pin a *selection*, meaning which rows a command judges. Reading
one took three rounds, and found a different hole each time:

- round 1: every same-type row in the fixture the spec named is identical in
  `touches` and `criteria`. The closeness sort is a tie, so a `check` skipping
  it passes.
- round 2, on the delegate's fix: the arrangement contradicted the paragraph
  above it, and "placed first" survived the date sort only by an unstated
  property of `_cell`'s defaults.
- round 3, on that fix: the other-type row carries the target's own shape and
  sits after the twelve. The cut drops it either way, so the type filter goes
  unwatched.

Round 4 was not dispatched. The fourteen rows were built against
`_history_lines` at `origin/main` and the selection printed, which took about
two minutes and answered all three arms at once. The correct selection prints
the twelve low-peak rows. A `check` skipping the sort, the cut or the type
filter each keeps a row that blocks. The cell then delivered exactly that
arrangement and the Spec seat's probes killed all three wrong implementations
separately.

Run 9 recorded the same shape for a gate question (a `dead`-gate blocker
overturned by running the gate over a mutated worktree). This is the same move
against a witness-adequacy question, and it is the cheaper half of `b-2750d5`:
that item mutates the *implementation* inside the cell, where this runs the
*fixture* before one starts.

## Done looks like

The skill's step 1b measures a criterion that pins a selection, an ordering or
a cut. It runs the helper that performs it, before the spec's cell starts. The
measurement then ends the round in place of a further review.
Optional: the driver grows the command, so the arrangement is built and printed
rather than hand-scripted each time.

## Record

- 2026-09-19: filed from the spec loop's run 10 (`SA-0112`, #382). Three
  reviews at roughly six minutes each preceded a two-minute measurement that
  settled what they were circling.

- 2026-09-19: done, by hand, in the two prose files the move needs. Check 3 of
  `.claude/agents/spec-reviewer.md` stops arguing a wrong implementation that
  turns on the arrangement, and hands it to step 1b instead. The reviewer lists
  the wrong implementations the arrangement must exclude, names the helper, and
  reports the arrangement `unmeasured`. That list is the measurement's input,
  which is why the two edits are one change. Step 1b of the loop's `SKILL.md`
  builds the arrangement against the helper at `base` and prints what each
  named wrong implementation would select.

  **The delegate performs it, not the reviewer.** Step 1b dispatches its
  reviewers in parallel into the checkout the loop drives. Most specs pin no
  selection, so arming every reviewer spends turns on nothing. This also
  cuts against run 9's observation A, restated at
  `docs/evidence/2026-09-19-spec-loop-skill-feedback-run-10.md:82`: the
  delegate's spec edit is the loop's one artifact with no gate and no second
  reader. What the delegate adds here is printed output rather than prose.

  **The measurement simulates, and does not mutate the helper.** A first draft
  had step 1b probe the helper's source once per wrong implementation. Two
  reviews of that draft rejected it, correctly. It is the technique this item's
  Problem fences off as **b-2750d5**'s half. It costs a probe cycle per arm,
  where run 10's measurement cost one run for all three. And `probe` classifies
  a pytest run rather than a print, so two of its four verdicts are unreachable
  here. Mutating the real code stays where it already works, on the delivered
  diff, in the pull request's Spec seat.

  **The optional driver command is declined.** An arrangement is spec-specific,
  and a command that builds rows would serve `history`-shaped specs alone.

  Nothing enforces either rule. The evidence that they fire is the next run's
  feedback record. The shape to look for is a check 3 line reading `unmeasured`
  and a round that ended on output instead of on a review.
