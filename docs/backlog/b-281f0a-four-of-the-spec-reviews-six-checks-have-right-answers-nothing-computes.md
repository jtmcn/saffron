---
id: b-281f0a
title: Four of the spec review's six checks have right answers, and every spec pays a subagent to work them out by eye
status: partial
tier: 2
filed: 2026-09-19
specs: [SA-0112]
prs: [378, 382]
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
- 2026-09-19: `SA-0112` is queued for the ledger half. It adds
  `driver.py check SA-NNNN`, which applies check 4's four thresholds to the
  rows `history` prints and exits non-zero on a blocker. Two corrections to the
  "Done looks like" above came out of writing it, and the item stays open on
  the second.

  **The `specs:` bookkeeping is already checked**, so that bullet is wrong.
  `check_specs_name_their_items` at `tests/records/check.py:415` reports
  "cites this item and is not listed". It fires for any spec whose `## Context`
  names an item that does not list it back.
  `tests/records/test_records_integrity.py:13-21` runs it over the live tree on
  every `make check`. Nothing is owed there.

  **The parametrised-witness check cannot ride in `SA-0112`'s diff**.
  `tests/test_queued_specs.py` is inside `.saffron/policy.yaml:69`'s
  `test_paths`. A test added there is a new test `revert` re-runs with the
  diff's *source* reverted. That source is `driver.py`, which the new test does
  not read. It would pass reverted, which `revert` blocks
  (`saffron/gates/core/revert.py:171` is the skip for the other case, a diff
  with no source at all). So it is either its own tests-only spec, or by hand
  as item **152** did for the same file and the same reason. In a tests-only
  spec `revert` skips and the anti-theater gate says nothing. `SA-0112` lists
  the file as `forbidden` to keep a cell from reaching for it.
- 2026-09-19: what the by-hand prose half owes, settled by the operator on
  `SA-0112`'s fourth spec review. Two things, both after that cell lands.

  **Reword check 4's concern rule to the worst case among the rows**.
  `.claude/agents/spec-reviewer.md:90-92` asks a reader for "REVIEW and REBUT
  at the rows' usual cost". `check` computes something narrower and sharper:
  the highest `review_usd` plus `rebut_usd` **on one row**. That is the
  worst-case convention the two halves of the `ceilings:` line already use. The
  operator settled the divergence in the computed rule's favour, so the printed
  rule is the one that moves. Until it does, the prompt and the command
  disagree about what a concern means. That is the defect this item was filed
  about, in miniature.

  **Wire `driver.py check` into the loop's step 1b**. The command is called by
  nothing the day `SA-0112` merges, deliberately. Run it by hand, then edit
  `SKILL.md`. That is the order `SA-0092` and item **145** took for the
  `ceilings:` line itself. `.claude/agents/spec-reviewer.md:19` and `:30` also
  name `driver.py history` as the only command a review runs. Whether `check`
  joins that list is a decision about the review rather than about the command.

- 2026-09-19: the ledger-reading half shipped in #382. `driver.py check
  SA-NNNN` judges the `ceilings:` comparison and exits 1 on either of check 4's
  blocker rules, 0 otherwise, with the REVIEW-plus-REBUT shortfall as an
  advisory concern. Run against the live ledger it reproduces the numbers run
  10's spec reviews worked out by hand, and it blocks where they would have:
  `SA-0031` on both rules, `SA-0044` and `SA-0099` on turns. The prompt half is
  still owed, so nothing calls it yet, and `tests/test_queued_specs.py`'s
  parametrised-witness check stays open here too.
- 2026-09-19: `partial`, not done. #382 merged and `SA-0112` retired to
  `done/`, so the ledger-reading half is delivered. Two halves are still owed,
  and neither has a spec. One is check 4's own wording in
  `.claude/agents/spec-reviewer.md`. It still tells a reviewer to apply the
  thresholds by eye, and it does not know `check` exists. The other is the
  parametrised-witness check in `tests/test_queued_specs.py`. `SA-0112` could
  not carry it: `revert` passes a new test there with the diff's source
  reverted, because that source is `driver.py`, which the test does not read.
