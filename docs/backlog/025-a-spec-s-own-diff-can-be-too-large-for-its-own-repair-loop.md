---
id: 25
title: A spec's own diff can be too large for its own repair loop
status: done
tier: null
specs: [SA-0009, SA-0014, SA-0015, SA-0016, SA-0017]
prs: [56]
commits: []
cites: [§4.2.1]
related: [18, 56]
---

## Problem

**Status:** **done** — the resplit landed. `SA-0014` (PR #56), `SA-0015`
(#59), `SA-0016` (#60) and `SA-0017` (#64) are all `MERGED`, so the too-wide
`SA-0009` was recut into four pieces that each fit inside one repair loop.
The "still open" paragraph at the end of the body is now **item 56**: nothing
weighs a spec's own shape against its `type`'s size ceiling before a cell
starts. That is a separate control from the recut, and the recut did not build
it.

Resplit as `SA-0014`–`SA-0017`. Found by running `SA-0009` (task 11).

`SA-0009` was §4.2.1's read-only half — discovery, the re-queue filter, the
six refusals, `saffron queue` — as one spec. It never converged: two `IMPLEMENTING`
attempts landed 990 changed lines across seven files, `size` reported `fail` in
every gate result after, at the 600-line `feature` ceiling
(`gate_result_id` 113/124/135), and
two `REPAIRING` attempts each burned a full `max_turns=100` trying to cut the
diff down without ever getting `committed` clean again — $31.60 against an $18
budget, terminal state `EXHAUSTED`, zero lines merged.

**The size was foreseeable before a single turn ran.** The diffstat splits
cleanly along the spec's own acceptance criteria: `tests/test_scheduler.py`
alone was 433 of the 990 lines, because it was carrying tests for two
unrelated mechanisms — the `spec_sha` re-queue filter and the five refusals —
each demanding its own fixture per the spec text. A spec whose acceptance
criteria describe more than one mechanism is a spec whose diff is the sum of
both, and nothing checked the sum against the ceiling before the cell started.

**Done looks like** the same work recut so each piece fits inside one repair
loop: `SA-0014` (intake's parser fix and directory discovery), `SA-0015`
(the ledger reads and the re-queue filter), `SA-0016` (the four refusals that
need `touches`, criteria, or GitHub state), `SA-0017` (`saffron queue`'s CLI
wiring) — chained by `depends_on`, ~150–420 lines apiece by the same diffstat.
`SA-0009` itself is left as written: its `spec_sha` is pinned to the
`EXHAUSTED` task above, and editing it would only mint a fresh `spec_sha` for
a monolith nothing intends to run again.

**Split out as item 56:** nothing yet checks a spec's own shape — how many
acceptance criteria, how many files in `touches` — against its `type`'s size
ceiling before a cell starts. That would have caught this one for the price of
a `gh`-free scan, the same argument item 18 made for turn ceilings.
