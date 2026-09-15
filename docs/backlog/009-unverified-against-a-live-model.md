---
id: 9
title: Unverified against a live model
status: partial
tier: 3
specs: [SA-0002, SA-0031, SA-0040]
prs: [16]
commits: []
cites: [§4.3]
related: [10, 42, 45]
---

## Problem

**Status:** **partly met, and the standing claim in it is now false.** Two of
the three "expensive" paths this item was waiting on have since fired in
production, both recorded elsewhere in this file rather than here:

- **A critic confirming a plausible-but-wrong finding** — item 42, measured on
  `SA-0040` 2026-09-01. The critic wrote `confirmed: The implementer offered no
  argument and made no visible change` about a finding that was false, and the
  operator inherited a pull request body asserting it.
- **`GATE ⇄ REPAIR` firing at all** — item 45, measured on `SA-0031`: six
  commits, 39 new gate failures and an `EXHAUSTED` terminal. The bullet below
  claiming it "did not fire, for the fourth time" describes 2026-08-25 and has
  not held since.

**Still unmet:** a rebuttal that claims a fix and does neither — §4.3's doneness
rule at the point an agent has the strongest incentive to lie. That one still
needs a task chosen to fail rather than a fifth hope.

Everything here is built and unit-tested and has never met a real session. On
this project's evidence that is exactly where the next defect is.

- **GATE ⇄ REPAIR has never fired.** Three live tasks, three greens on attempt
  one, because a capable agent with `Bash` runs every gate it can reach before
  committing (principle 49). Repair's real domain is only the core gates.
- **A critic confirming** rather than withdrawing. The one live REBUT saw a
  blatantly false blocker withdrawn; a plausible-but-wrong finding is untested,
  and that is the kind that costs mornings.
- **A rebuttal that fixes and commits**, with `head_moved` true.
- **The gate re-run after a rebuttal**, and `EXHAUSTED` when it is red.
- **A rebuttal that claims a fix and does neither** — §4.3's doneness rule at the
  point an agent has the strongest incentive to claim it is done.

**Half met, 2026-08-25**, by `SA-0002` — the first task to run the whole
pipeline, spec to pull request (#15), $2.38 against an $8 budget, green on
attempt one.

**Two of the five fired, and the pair that fired is the pair that matters
most.** The correctness lens filed a true blocker: `_changed_lines` dropped any
hunk line *starting with* `---`/`+++`, so a SQL `-- comment` or a YAML `---`
undercounted the diff. The implementer fixed it, committed, `head_moved` true;
the gates re-ran clean on the new head; the lens withdrew its own finding on
the evidence. That is REVIEW ⇄ REBUT closing the loop against a real defect
rather than a planted one, which is what Appendix L could not show.

**Three are still open** and they are the expensive three: `EXHAUSTED` when the
post-rebuttal re-run is red, a rebuttal that claims a fix and does neither, and
a critic *confirming* a plausible-but-wrong finding. All three are failure
paths, and a green run cannot exercise them — which is the argument for a task
chosen to fail rather than for waiting.

**GATE ⇄ REPAIR did not fire, for the fourth time.** Four live tasks, four
greens on attempt one. This is no longer an accident to be waited out: an agent
with `Bash` runs every gate it can reach before committing, so the bullet above
is the standing behaviour and not a sampling artifact. Repair's domain is the
core gates the agent cannot run — `scope`, `committed`, `census` — and testing
it means a task that trips one of those, not a fifth hope.

**And the run measured two things nothing had.** The agent's `uv run pytest`
took four `403`s from the proxy and cost three turns (item 10, closed). And
five tests in this repo's own suite failed inside a cell while passing on the
host, so the baseline every gate result is subtracted from was carrying five
failures for reasons unrelated to any task (closed by PR #16). Both were
invisible to every unit test and to three prior live runs; both cost money on
the first task that reached PACKAGE.
