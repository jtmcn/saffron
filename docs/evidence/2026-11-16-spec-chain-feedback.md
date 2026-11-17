# Spec chain feedback, 2026-11-16

Continues `docs/evidence/2026-11-15-spec-chain-feedback.md`. Check numbers
carry on from its 61. The chain took b-d9a027 after spec loop run 75
merged, from `d72d0733`.

## The split (b-d9a027)

The first writer stopped at step 1 and wrote no file. The whole item
priced at 2916 tokens by hand and 3328 measured, past the 2400-token line.
It split three ways. `SA-0403` chooses the versions a review commit puts
back in play. `SA-0404` has `saffron regate` ask them. `SA-0405` keeps
REBUT from withdrawing a parent survivor's blocker. The split report also
named three design calls, which the caller settled in the next briefs.

## SA-0405 (REBUT guard)

**Review 1: 1 blocker, 1 concern, 2 notes.** The writer revised. No
blocker had the green phrase twice in its claim, so a parse that cut at the
last one passed. Criterion 2 overlapped criterion 1 on one shape.

**Review 2: 1 blocker, 3 notes.** Applied by hand. A check running the
`preserves` rule first passed, because the one parent survivor on the
`preserves` witness took the exception case. On the prototype the
reviewer's mutant passed the old witness and failed the new one. Check 62
names the class.

## SA-0403 (regate, chooses)

**Review 1: 0 blockers, 2 concerns, 6 notes.** The writer revised.
`--literal-pathspecs` sat after `diff`, where git exits 129. Two criteria
shared one bare-path witness, which made the asserted pairs unreachable.

**Review 2: 0 blockers, 2 concerns, 4 notes.** Applied by hand. Two
claims named the wrong criterion's head. A stray commit's fork point was
left open, and one fork makes a wrong version pass.

## SA-0404 (regate, asks)

**Review 1: 0 blockers, 6 concerns.** The writer revised. Passing the
task's `base_sha` or the checkout to `review_commit_diff` passed every
witness, and the writer measured both. The survivor exit was driven only
beside a gate failure. `adopt` was said to read a failed re-gate, but it
records the head first. `estimated_lines` held tokens over four.

**Review 2: 0 blockers, 3 concerns, 3 notes.** The writer applied them on
its prototype, since only it held the harness. No third review ran. The
baseline equalled the base branch's tip, so either name passed. No witness
read the cell's `repo`. The clone's branch was unpinned. All seven new
wrong versions die on the prototype, and its full suite passed.

## What the reviews keep finding

Every blocker and most concerns were one class: a fixture in which two
names a cell could confuse hold the same value. Check 63 names it. A
witness cannot tell `baseline_sha` from `base_head` when they are equal.

## Checks to build

62. A rule that overrides another drives the overriding member under each
    case where the overridden rule would answer differently.
63. For every pair of in-scope names a call could take in place of each
    other, the fixture makes their values differ.
