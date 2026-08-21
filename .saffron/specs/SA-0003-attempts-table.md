---
id: SA-0003
title: An attempt's identity is recorded nowhere, so no question about one is answerable
type: feature
priority: 1
touches:
  - saffron/ledger.py
  - saffron/cell/session.py
  - tests/test_ledger.py
  - tests/test_session.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
budget_usd: 6
max_attempts: 4
risk: elevated
---

## Context
`DESIGN.md` §4.1 declares an `attempts` table:

```sql
attempts (attempt_id, task_id, phase, n, session_id, model, started_at,
          ended_at, subtype, terminal_reason, num_turns, cost_usd_est)
```

`saffron/ledger.py` does not implement it. `saffron/cell/session.py` therefore
prints `session_id`, `num_turns`, `terminal_reason` and each turn's cost to the
watch line and drops them, and every gate result from the repair loop is written
against the same `attempt_id` (the task's own id, per the documented convention).

## Problem
Nothing records what an attempt was. Three consequences, all of which §4.1 and
§5.4 assume are answerable:

- "Which attempt produced this failure?" cannot be asked at all — every attempt's
  gate results collapse onto one id.
- A crashed session's cost is reconciled in memory and then forgotten, so
  `spent_usd_est` exists on no row and a budget cannot be audited after the fact.
- §8's flywheel asks which gate was the sole failure on a rejected task. With one
  `attempt_id` per task the question has no join to stand on.

## Acceptance criteria
- [ ] An `attempts` table exists with the columns §4.1 declares
- [ ] `Ledger` gains a way to open an attempt and a way to close it with its
      outcome — `subtype`, `terminal_reason`, `num_turns`, `cost_usd_est`
- [ ] `run_one_cell` opens an attempt per agent turn and closes it with the
      turn's real result, including on the failed-turn path
- [ ] Gate results from the repair loop are recorded against the attempt that
      produced them, not against the task
- [ ] The baseline suite still hangs off `run_id`, not an attempt — it has no
      agent, no session and no cost (§4.1)
- [ ] `gate_results` still satisfies "exactly one of `attempt_id` and `run_id` is
      set"; the existing constraint must not be weakened to make this pass
- [ ] A test asserts a two-attempt task records two distinct attempts, and that
      each attempt's gate results are attributable to it
- [ ] Every existing ledger and session test still passes unchanged

## Out of scope
`tasks.spent_usd_est`. Summing an attempt's costs onto its task is a separate
question and depends on whether a resumed session reports per-turn or
whole-session cost, which is not yet known. Do not add that column and do not
guess at that behaviour.

The `phase` column may be recorded as a literal string; there is no phase
enumeration to reach for and inventing one is not this task.

## Notes for the agent
`saffron/ledger.py` is a single-file SQLite DAO — read it fully before editing;
its schema is created in one place and its tests assert against real rows.
`saffron/cell/session.py`'s `run_one_cell` is long: the agent turns are the plan
checkpoint, the implement turn and each repair turn.

The existing tests are the specification for everything you are not changing. If
one of them fails, that is the answer, not an obstacle.
