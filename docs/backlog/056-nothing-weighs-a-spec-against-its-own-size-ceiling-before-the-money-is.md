---
id: 56
title: Nothing weighs a spec against its own size ceiling before the money is spent
status: superseded
tier: 3
closed: 2026-11-07
specs: [SA-0129]
prs: [502]
commits: []
cites: [§4.2.1]
related: [18, 23, 25]
superseded_by: b-db95e1
---

## Problem

Split out of item 25, which the `SA-0014`–`SA-0017` recut closed by hand. The
recut fixed one spec; **the check that would have caught it before a cell
started was never built**, and every spec written since has been sized by
whoever wrote it.

`SA-0009` is the measurement. Two `IMPLEMENTING` attempts landed 990 changed
lines across seven files, `size` reported `fail` in every gate result after, at
the 600-line `feature` ceiling (`gate_result_id` 113/124/135), and two
`REPAIRING` attempts
each burned a full `max_turns=100` trying to cut the diff back down without
ever getting `committed` clean again. **$31.60 against an $18 budget,
`EXHAUSTED`, zero lines merged.** The overrun was not bad luck: the diffstat
split cleanly along the spec's own acceptance criteria, and
`tests/test_scheduler.py` alone was 433 of the 990 lines because it was
carrying fixtures for two unrelated mechanisms the spec text asked for
separately.

**Everything the check needs is already parsed and host-side.** `Spec` carries
`type`, `touches` and `acceptance_criteria`; `saffron/gates/core/size.py`
carries `_CEILINGS` (`bug` 300, `feature` 600, `refactor` 1000) and
`_DEFAULT_CEILING`. The scan runs before a container starts and costs no
`gh` call, which is what makes this cheap in the way item 18's turn-ceiling
argument was cheap: the ceiling already exists and is enforced far too late,
against a diff somebody has already paid for.

**The hard part is the predicate, not the plumbing, and it should not be
guessed.** Criteria count times files in `touches` is a number with no
measurement behind it, and a refusal gate that fires on a good spec is worse
than no gate — `saffron queue` refuses before a cell runs, so a false positive
costs a spec that never gets written rather than a diff that never lands.
Twenty specs carry a `MERGED` row in `~/.saffron/ledger.db` with a real
diffstat behind them, each pinned to its own `spec_sha`, so the honest first
move is to fit the predicate against that corpus and see whether it separates
`SA-0009` from the twenty that converged.

## Done looks like

one of: a warning line on `saffron queue` naming a spec
whose shape predicts an over-ceiling diff, fitted against the merged corpus
rather than reasoned; or a written finding that the corpus does not separate
them, which retires the idea. **The refusal gate is the wrong home either
way** — §4.2.1's refusals are all facts (a parent did not merge, a path is
protected), and this is a forecast. A forecast that blocks is the shape item
23 is about.

## Record

- 2026-11-07: superseded in grooming by item b-db95e1, done on 2026-09-23.
  `SA-0129` (#502) gave a spec an `estimated_lines` field, and `driver.py check`
  now weighs it against the `size` ceiling of the spec's type before a cell
  runs. The estimate is multiplied by the median overrun over landed specs that
  declared one, so the predicate is fitted rather than reasoned. At 80% of the
  ceiling it is a blocker where `size` blocks and a concern elsewhere. Its home is
  the spec loop's pre-flight, not `saffron queue` and not the refusal gate. The
  problem this item names is closed there. How well that estimate predicts a
  landed diff is item b-fbd181.
