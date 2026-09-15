---
id: 18
title: A spec's ceilings were declarations with no reader, and turn exhaustion is total loss
status: done
tier: null
closed: 2026-08-25
specs: [SA-0007, SA-0009, SA-0018, SA-0054]
prs: []
commits: []
cites: [§2.1]
related: [4, 9, 17]
---

## Problem

Found by running `SA-0005`, which is the only way it could have been found: it
is invisible to every unit test and to four green live runs.

**Two of three ceilings did nothing.** `cli.py` built `CellSpec` with
`budget_usd=args.budget` and `max_attempts=args.max_attempts`, whose argparse
defaults made *not given* and *given the default* the same value — so a spec's
own `budget_usd` and `max_attempts` were parsed, validated, and discarded.
`max_turns` was not on `Spec` at all: hardcoded 60, unsettable, unprintable.
This is the third declaration-with-no-reader in two days, after
`Policy.elevate_on` and `GateDeclaration.blocking` (item 17). **The pattern is
worth more than any of the three instances**: a field that parses and validates
and changes nothing is indistinguishable from one that works, and the repo has
now produced four of them.

**And the ceiling that fired was the one nobody could see.** `SA-0005` died at
turn 61 with $5.34 of a declared $12 spent — stopped by the bound its author
could not raise, holding more than half the budget it *could* declare.

**Turn exhaustion discards everything.** An idle or wall kill leaves commits
behind (item 4). `error_max_turns` fires with the worktree full, the cell is
torn down, and the run exports nothing: 61 turns of correct work, $7.50, zero
commits. `implement.md` said *"Commit your work"* — singular, at the end.

**And a fifth, found the same day by `SA-0005` (#21).** `cli.py` never passed
`risk=spec.risk` into `CellSpec`, and `package.py` never passed the effective
tier or the advisory set to the PR body or the queue line — a value computed,
carried out on `CellOutcome`, and read by nobody. `SA-0007` closes it.

**What made it worth more than a sixth instance: the tests.** Every test of the
new behaviour called the renderer directly with hand-supplied values, so the
suite was green about a function that works and silent about whether anything
calls it. That is the shape all five share — the declaration end is tested, the
reading end does not exist, and no test spans the two. **A test that constructs
the argument it then asserts on cannot detect a caller that never passes it.**

**And the spec is what made it unfixable in place.** `SA-0005`'s `touches` did
not include `cli.py` or `package.py`, so the implementer could not have closed
the gap without failing `scope`, and one of the three findings was dropped as
unanchorable for the same reason — it named a file the diff could not contain.
Both lenses confirmed the blocker after the rebuttal, the first recorded
disagreement this pipeline has produced (item 9), and the adjudication is on
#21: **the fault was the spec's, not the implementer's.** A spec whose
acceptance criteria reach outside its own `touches` is unsatisfiable by
construction, and nothing in intake checks for it.

**And `SA-0016`'s criterion-path refusal, built to catch exactly this at
intake, does not fire on `SA-0005` — measured, not reasoned about:**

```
uv run python -c "
from pathlib import Path
from saffron.intake import load_spec
from saffron.scheduler import _unmatched_criterion_path
spec, _ = load_spec(Path('.saffron/specs/SA-0005-size-wiring.md'))
print(_unmatched_criterion_path(spec), len(spec.acceptance_criteria))"
None 7
```

Seven criteria parse in full — `SA-0014` already fixed the truncation that
would explain a `None` here — and still none of them trips the refusal,
because none of the seven names a path at all, backticked or bare. They name
behaviour: "the PR body header and the queue line report" the effective tier,
"`size` runs in `_suite`". The paths that behaviour lives in are `cli.py` and
`package.py`, exactly the ones this item already names as outside `touches`.
A refusal keyed on path tokens cannot see a criterion that reaches outside
`touches` by naming behaviour instead of a file, and no widening of the token
rule changes that: resolving "the queue line" to a file is a symbol index,
which is language-aware, and core knows nothing about languages (§2.1) — the
check cannot live in the scan. `SA-0018` closes the gap from the other side
instead: a door at the plan checkpoint an IMPLEMENT attempt can propose scope
through, reaching `SCOPE_REVIEW` with the paths and the root cause, so a spec
shaped like `SA-0005` stops there instead of at a fourth exhausted attempt.

**Still open, deliberately:** `error_max_turns` is not resumable. A bound that
resumes is not a bound, and committing per step removes most of the loss — if a
run exhausts turns *with* its commits landing, that is the evidence for
reopening this, and the honest shape then is a repair-loop state rather than a
retry.

## Record

**Status:** **done**, 2026-08-25 — the item's own closure paragraph is below.

**Closed, 2026-08-25.** The flags default to `None` and stay overrides, the
spec governs otherwise, `max_turns` joins `Spec`, all three print with their
source on the way in, and a turn ceiling names itself in the failure instead of
reading as `exited 1`. `implement.md` asks for a commit per coherent step and
says why, with the measurement.
