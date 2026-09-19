---
id: b-281f0a
title: Four of the spec review's six checks have right answers, and every spec pays a subagent to work them out by eye
status: open
tier: 2
filed: 2026-09-19
specs: []
prs: []
commits: []
cites: []
related: [123, 124, 145, 152, 153]
---

## Problem

Found 2026-09-19, measuring a `spec-writer` agent against a plain prompt on
backlog item 97. Four specs were written for the same item and each was read by
one `spec-reviewer`. Three of the four drew a blocker. **Two of those three
blockers were the same arithmetic**: a diff estimated at 635 to 930 changed
lines against a `size` ceiling of 600 that blocks at `elevated`. Both reviewers
reached it the same way. They counted the lines of comparable
modules and test files, then read the `size:` summaries the loop's `history`
prints. That is a computation, and a person paid a subagent for it twice.

`tests/test_queued_specs.py` already owns the mechanical half of check 3, and
it owns it well. It checks that every queued spec parses (`:48`) and that no
two share an id
(`:58`). It checks that no spec is refused on its own text (`:67`). It checks that every `preserves` witness names a test the suite collects
(`:103`). It checks that no other witness already exists at the commit that
last changed the spec (`:179`), which item 152 built.

Nothing covers the rest of what a review computes:

- **The ceilings comparison.** `driver.py history` prints a `ceilings:` line
  that already does the work, and reading it is the review's check 4. Whether a
  spec's declared ceilings clear that line is decided by a person quoting it.
  Item 123 promoted the check because a review made the same comparison by eye
  and got it wrong in both directions.
- **A parametrised witness.** `criteria` matches a bare node id by exact
  string, so an id carrying a `[` can never be collected. Nothing refuses one
  at intake.
- **The bookkeeping `issue-tracker.md` asks of the commit that adds a spec.**
  The origin item's `specs:` entry is checked by nothing. The queue smoke test
  catches the candidate list, and only because it is pinned by hand.

Checks 1, 2 and 6 stay human, and check 5's estimate is a forecast rather than
a measurement. That is the point of the split. A review's attention is worth paying for
where the answer is a judgement, and both real blockers here were of that
kind.

## Done looks like

The computable checks run before a spec review is dispatched, so the review
spends itself on judgement.

Two homes, because the checks divide by what they need to read:

- **The tree alone** goes in `tests/test_queued_specs.py`, which a cell can
  land: the witness id with no bracket, and the origin item's `specs:` entry.
- **The ledger** stays host-side, in the spec loop's `driver.py`, because
  `~/.saffron/ledger.db` is mounted into no cell and reaches no CI runner. A
  `driver.py check SA-NNNN` would hold the ceilings comparison, and the loop's
  step 1b would run it before dispatching the review.

A repo gate under `.saffron/gates/` is the wrong home. Gates judge a cell's
diff, and no cell adds a spec, so the gate would never fire on the commit that
matters.

## Record

- 2026-09-19: filed by hand from the writer measurement above. The four specs
  and their reviews are this record's evidence and are not kept. The agent is
  `.claude/agents/spec-writer.md`.
