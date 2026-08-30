---
id: SA-0018
title: a feature spec whose touches cannot satisfy its criteria has nothing to do but burn
type: feature
priority: 2
depends_on:
  - SA-0016
touches:
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/agents/artifacts.py
  - saffron/agents/prompts/implement.md
  - docs/BACKLOG.md
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_artifacts.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/gates/**
  - saffron/scheduler.py
  - saffron/report/**
budget_usd: 16
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`SA-0016` built §4.2.1's criterion-path refusal and named its corpse: item 18,
`SA-0005`, $5.34 dead at turn 61. That refusal is built and correct, and it
does not fire on `SA-0005`. It cannot. Measured against every spec on disk,
the refusal returns nothing for `SA-0005`, and the reason is not truncation —
`SA-0014` fixed that, and the criteria parse to seven full texts:

```
uv run python -c "
from pathlib import Path
from saffron.intake import load_spec
from saffron.scheduler import _unmatched_criterion_path
spec, _ = load_spec(Path('.saffron/specs/SA-0005-size-wiring.md'))
print(_unmatched_criterion_path(spec), len(spec.acceptance_criteria))"
None 7
```

`SA-0005`'s acceptance criteria name **no path at all** — not backticked, not
bare. They name behaviour: "the PR body header and the queue line report" the
effective tier, "`size` runs in `_suite`". The paths that behaviour lives in
are `cli.py` and `package.py`, and item 18's adjudication is that neither was
in `touches`, so "the implementer could not have closed the gap without
failing `scope`", and one of the three findings was dropped as unanchorable
for the same reason. **The fault was the spec's.** A refusal keyed on path
tokens cannot see a criterion that reaches outside `touches` by naming
behaviour, and no widening of the token rule changes that.

## Problem
- **The one repo-agnostic way to catch this before a cell does not exist.**
  Resolving "the queue line" to a file means a symbol index, which is
  language-aware, and core knows nothing about languages (§2.1). The check
  cannot live in the scan.
- **So it must be caught inside the cell, and there the door is marked
  bugs only.** §5.2 is titled "Phase 1 — DIAGNOSE (bugs only)": an agent that
  discovers its `touches` cannot satisfy its criteria has no state to stop in.
  A bug proposes scope and reaches `SCOPE_REVIEW` for a one-click ratification;
  a feature spec has one move, which is to keep going until a ceiling stops it.
  That is what turn 61 was.

## Acceptance criteria
- [ ] An IMPLEMENT attempt can end by proposing scope instead of a diff: the
      task reaches `SCOPE_REVIEW` carrying the proposed `touches` and a
      one-paragraph root cause, from a `feature` spec as well as a bug
- [ ] The proposal is extracted and hashed the moment it is produced and never
      re-read from the workspace, the same rule every other control artifact
      follows — a file left in the workspace is a claim, not a record
- [ ] A proposal naming no path outside the spec's declared `touches` is
      refused rather than recorded, and the attempt continues; without that it
      is an escape hatch from any spec the agent finds hard
- [ ] The recorded proposal includes the task's own spec path, or the
      ratification's first commit fails `scope` on every task that uses it
- [ ] An attempt that proposes scope spends no further turns: the proposal is
      the end of the attempt, not a note it carries while continuing
- [ ] `docs/BACKLOG.md` records under item 18 that the criterion-path refusal
      does not fire on `SA-0005`, and why — the measurement above, not a
      reasoned restatement of it
- [ ] Every new test runs with no network and no cell

## Out of scope
**Widening the criterion-path refusal.** `SA-0016`'s rule stays exactly as
built; `saffron/scheduler.py` is forbidden here. A symbol index that resolves
behaviour to a file is language-aware and belongs in a target repo's
`.saffron/`, never in core (§2.1) — if it is ever built it is a declared gate,
not a scan.

**Editing `SA-0016`'s spec text.** An edit moves its `spec_sha`, and a spec
that is done at one sha is queued again at another (§4.1) — correcting a
merged spec's prose would re-run it. The correction belongs in the backlog,
which is why it is a criterion above. `.saffron/**` is forbidden.

**The morning queue's rendering of a `SCOPE_REVIEW` item and its one-click
ratification.** `saffron/report/**` is forbidden and `saffron queue` is
`SA-0017`. The ledger is authoritative until that PR merges, so this spec ends
when the state and its artifact are recorded.

## Notes for the agent
**The state already exists; the door does not.** `SCOPE_REVIEW` is in §3.3's
terminal states that reach you, it is first in the morning queue's ordering,
and `scheduler.DONE_STATES` already treats it as done with the spec. Nothing
writes it. Read §5.2 for the ratification contract before adding a second
producer of it — in particular that ratified scope is recorded in the ledger
and written into the spec file **on the task's own branch as its first
commit**, never to a remote `main`.

**A proposal is not a plan and not a rebuttal.** The two existing extraction
turns are the shape to copy, not to reuse: this one produces a path list and a
root cause, and its validation is that the list reaches outside `touches`.
Reusing the plan artifact for it would make a rejected plan and an unsatisfiable
spec the same event, and they say different things.

**The test that would have failed.** `SA-0005`'s own criteria, run through
whatever this spec builds, must reach `SCOPE_REVIEW` naming `cli.py` — a test
whose fixture is a spec you wrote to be obviously under-scoped proves the happy
path and nothing about item 18. Item 18 is the fixture.

**A test that constructs the value it then asserts on proves nothing about the
caller** — the defect that shipped `SA-0005` green, and the one the critic
caught in `SA-0007`. Drive this through the phase, not by handing a fake
proposal to a recorder.

Commit after each coherent step. Uncommitted work dies with the cell.
