---
id: SA-0261
title: A start that fails preflight in a stack batch marks the layer missed, so the batch refuses its descendants
type: bug
priority: 2
depends_on: []
estimated_lines: 126
estimate_measured: true
touches:
  - saffron/batch.py
  - tests/test_batch.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - CLAUDE.md
  - README.md
  - pyproject.toml
  - uv.lock
  - .saffron/**
  - .claude/**
  - ontology/**
  - tests/ontology/**
  - docs/**
  - harness/**
  - records/**
  - hooks/**
  - images/**
  - saffron/agents/**
  - saffron/record/**
  - saffron/view/**
  - saffron/gates/**
  - saffron/cell/**
  - saffron/cli.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/preflight.py
  - saffron/spec_review.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/intake.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 24
max_attempts: 3
max_turns: 140
risk: standard
acceptance:
  - claim: >-
      In a stack batch, a spec of the order whose task returns
      `PREFLIGHT_FAILED` is not a miss. It runs again at once, on the same
      predecessor, with no second spec review, and a spec that depends on it
      is not refused. A task that returns `GATE_ERROR` is still a miss, and
      its dependent is refused. The witness drives both states in one
      batch, and the batch drains.
    witness: tests/test_batch.py::test_a_preflight_failure_in_a_stack_batch_is_offered_again_not_missed
    wrong_versions:
      - The wrapper keeps the spec queued but the loop still counts it as started, so its dependent runs next on the wrong predecessor.
      - The loop offers the spec again but the wrapper still records a miss, so its dependent is refused.
      - Every state in `ABORT_STATES` is kept queued and offered again, so a `GATE_ERROR` task runs twice and its dependent is not refused.
      - The re-offer takes the spec out of `reviewed`, so it is reviewed a second time.
  - claim: >-
      A follow-up whose task returns `PREFLIGHT_FAILED` runs again at once,
      on the same predecessor. A follow-up whose task returns `GATE_ERROR`
      runs once, and the next follow-up runs on the last layer. No
      follow-up is listed unrun. The witness drives both states.
    witness: tests/test_batch.py::test_a_follow_ups_preflight_failure_is_offered_again
    wrong_versions:
      - The wrapper keeps the spec queued but the loop still counts it as started, so the follow-up runs once.
      - The wrapper calls `runner` again in place for a spec of the order only, so a follow-up runs once.
      - The loop also offers a `GATE_ERROR` spec again, so a follow-up that returned it runs twice.
  - claim: >-
      Each re-offer counts toward the breaker. A spec of the order whose
      task returns `PREFLIGHT_FAILED` twice in a row ends the stack batch
      `INFRASTRUCTURE` after two `runner` calls and one review. Its
      dependent is neither refused nor reviewed. A plain batch passes no
      `sleep`, and never offers a spec whose task returned
      `PREFLIGHT_FAILED` again. The witness drives the stack batch and the
      plain batch.
    witness: tests/test_batch.py::test_a_preflight_failure_is_offered_again_only_until_the_breaker
    wrong_versions:
      - The wrapper calls `runner` again in place on `PREFLIGHT_FAILED`, so the breaker never sees the first outcome.
      - A stack batch's `PREFLIGHT_FAILED` is not counted as an abort, so the re-offers never reach the breaker.
      - The re-offer ignores `sleep`, so a plain batch starts the spec twice.
      - The loop offers the spec again but the wrapper still records a miss, so the dependent is refused.
---

## Context

Backlog item **b-032c61**, which cites `DESIGN.md` §4.2.1 and §5.1.1. It
was found by the first review of `SA-0244` on 2026-10-07. Every line number
below was read at `0a5e3e5c`.

**The two returns.** `run_one_cell` returns a `CellOutcome` in
`PREFLIGHT_FAILED` for two causes. A baseline that aborts sets the run's
preflight `FAILED` and the task `PREFLIGHT_FAILED`
(`saffron/cell/session.py:2072-2084`). An N1 refusal raises
`preflight.PreflightFailed`, which is caught and turned into the same
return (`saffron/cell/session.py:3290-3300`, from `SA-0244`). Both write
the same `FAILED` preflight and the same task state. A baseline abort also
records its gate results (`saffron/cell/session.py:2054-2055`), but no
field names the cause. The batch reads only the returned state, so it
treats both alike.

**How the outcome becomes a miss today.** `run_stack_batch` wraps each spec
in `wrapped` (`saffron/batch.py:525`). After `runner` returns, it keeps a
spec queued only for a `CellOutcome` in `RATE_LIMITED` or
`PROVIDER_UNREACHABLE` (`saffron/batch.py:745-751`). Any other result takes
the spec out of `remaining` and, unless it is a layer or a follow-up, adds
it to `missed` (`saffron/batch.py:752-757`). `resolve_prefix` then refuses
each spec whose `depends_on` reaches a missed one
(`saffron/batch.py:513-523`).

**What the loop does with the outcome.** `_drive` counts
`PREFLIGHT_FAILED` as an abort, since it is in `ABORT_STATES`
(`saffron/batch.py:62-64`, `:316-317`). It takes a spec back out of
`started` only for `PROVIDER_UNREACHABLE` with `sleep` set
(`saffron/batch.py:327-330`). So `_drive` never offers a
`PREFLIGHT_FAILED` spec again that pass, since it stays in `started`
(`:225`, `:254`). Two aborts in a row (`_BREAKER_THRESHOLD`, `saffron/batch.py:68`) stop the batch
before the next spec, as `INFRASTRUCTURE` (`:248-249`).

**The precedent, `SA-0234`.** A `CellRuntimeError` raised by `review` or
`runner` is not a miss (`saffron/batch.py:579`, `:741`). `_drive` adds it
to `consecutive_aborts` (`saffron/batch.py:281`). With `sleep` set, it then
takes the spec back out of `started` (`:286-289`). The
`PROVIDER_UNREACHABLE` branch does the same for its outcome (b-031ac2). `run_stack_batch` always passes `sleep`
to both of its passes (`saffron/batch.py:423`, `:778`, `:824`). Before
`SA-0244`, an N1 refusal raised out of the cell's start, and
`PreflightFailed` subclasses `CellRuntimeError` (`saffron/preflight.py:55`).
So a stack batch offered it again. `SA-0244` made it a returned outcome,
and the stack batch now misses it.

**The plain batch already does the right thing.** `saffron batch` without
`--stack` calls `run_batch` with no `sleep` (`saffron/cli.py:1942-1952`).
So `_drive` offers no spec again that night, whether it raised
`CellRuntimeError` or returned `PROVIDER_UNREACHABLE` or `PREFLIGHT_FAILED`.
A plain batch has no `missed`. Each rescan refuses a dependent whose parent
is `PREFLIGHT_FAILED` afresh, through its last branch,
`depends_on {dep} is {states[-1]}` (`saffron/scheduler.py:641`). The
parent re-queues the next night, since `PREFLIGHT_FAILED` is in `REQUEUE_STATES`
(`saffron/scheduler.py:111-120`). Nothing about that path is terminal for
the dependent, so this spec leaves it as it is.

## Problem

Treat a `PREFLIGHT_FAILED` outcome in a stack batch as `SA-0234` treats a
`CellRuntimeError`.

1. **The wrapper.** Add `PREFLIGHT_FAILED` to the tuple that holds
   `RATE_LIMITED` and `PROVIDER_UNREACHABLE` (`saffron/batch.py:745-751`). The spec
   stays in `remaining` and out of `missed`, so it runs again against the
   same `pred`.
2. **The re-offer in `_drive`.** With `sleep` set, take a `PREFLIGHT_FAILED`
   spec back out of `started`, as the `PROVIDER_UNREACHABLE` branch does
   (`saffron/batch.py:327-330`). Keep the abort count before it, so the
   breaker is the only bound, in both passes.
3. **Two comments go stale.** One names the states taken back out of
   the started set, `RATE_LIMITED` and `PROVIDER_UNREACHABLE`
   (`saffron/batch.py:217-218`). The `_is_layer` docstring names
   what `wrapped` keeps queued (`saffron/batch.py:375-377`). Correct each
   in place.

## Out of scope

- **Telling the two causes apart.** No new state, no new reason field, and
  no read of the run's preflight column. The breaker bounds both.
- **The plain batch.** `run_batch` keeps its behaviour, for the reason above.
- **A new stop reason or log line.** A batch the breaker stops already
  reads `INFRASTRUCTURE`. `missed` is local to one call
  (`saffron/batch.py:461`), so no later batch inherits it.
- **`GATE_ERROR`.** It stays a miss, as ADR 7 says.
- **`DESIGN.md` §4.2.1 and ADR 7.** Their sentences on what a stack batch
  offers again are hand edits in this spec's pull request.

## Notes for the agent

**Edit, no mutant.** The change adds one state to an existing tuple and
widens one existing condition. No text at base fixes the spelling of
either, so each criterion declares a witness and no mutant. The `witness`
gate reports `skip` for all three. Do not run the wrong versions yourself.

**Every witness fails at base.** At base the first `PREFLIGHT_FAILED` is a
miss and is never offered again. Its dependent is refused, and a lone
follow-up runs once. The tests import nothing the change adds.

**One helper drives all three.** Subclass `StackDoubles` with a queue of
states per spec id. Each `runner` call pops that spec's next queued state
and returns it, recording the call as `StackDoubles` does. An empty queue
falls back to `READY_FOR_REVIEW`. `StackDoubles.runner` already returns
the state its row names, so the subclass need only set it before the call.
Run each stack batch with `review` and `mint` from the doubles,
`sleep=_fail_sleep` and a budget of 100.

**Criterion 1.** The order is `TE-0`, `TE-1`, `TE-2` on `TE-1`, `TE-3`,
`TE-4` on `TE-3`, and `TE-5`. `TE-1` returns `PREFLIGHT_FAILED` once, and
`TE-3` returns `GATE_ERROR` once. A success sits between the two, so the
breaker never fires. Assert `DRAINED`. Assert these review calls, as
`(spec, predecessor)`: `TE-0` and none, `TE-1` on `TE-0`, `TE-2` on `TE-1`,
`TE-3` on `TE-2`, `TE-5` on `TE-2`. Assert these runner calls: `TE-0` and
none, `TE-1` on `TE-0` twice, `TE-2` on `TE-1`, `TE-3` on `TE-2`, `TE-5`
on `TE-2`. Assert the refused lines are exactly `TE-4` reaching `TE-3`.

**Criterion 2.** Order `TE-7` alone, with `end_review` and `follow_ups`
from the doubles. The follow-ups are `TE-8`, `TE-9` and `TE-10`, in that
order. `TE-8` returns `PREFLIGHT_FAILED` once, and `TE-9` returns
`GATE_ERROR` once. A follow-up is never taken out of `remaining`
(`saffron/batch.py:752-753`), and its pass rescans `follow_up_candidates`, a fixed list (`:816`).
So only the loop decides whether `TE-9` runs
again. Assert `DRAINED`. Assert these runner calls: `TE-7` and none, `TE-8`
on `TE-7` twice, `TE-9` on `TE-8` once, `TE-10` on `TE-8`. Assert no line
names a follow-up unrun.

**Criterion 3.** One stack batch, then one plain batch. The stack batch is
`TE-21`, then `TE-22` on `TE-21`. `TE-21` returns `PREFLIGHT_FAILED`
twice, then `READY_FOR_REVIEW`. The third entry is what tells a counted
re-offer from an uncounted one. Assert `INFRASTRUCTURE`, one review call
and two runner calls, both `TE-21` and none, and no refused line. Then run
`run_batch` over `TE-41` and `TE-42` with a `FakeRunner`. Its first entry
is `PREFLIGHT_FAILED` and its second `READY_FOR_REVIEW`. Pass `rescan`
returning the same two candidates. Assert `DRAINED` and runner calls
`TE-41` then `TE-42`.

**What the witnesses leave undriven.** The two causes reach `wrapped` as
one state, so the witnesses drive the state, not a cause. A
`PREFLIGHT_FAILED` that `mint` or `revise` could produce does not exist:
neither returns a `CellOutcome`. A re-offer runs the same minted task
again, as the `PROVIDER_UNREACHABLE` and `CellRuntimeError` re-offers do.

**Measured on a prototype, 2026-10-10.** The change and all three
witnesses were written against `0a5e3e5c` and passed. Each failed with
`saffron/batch.py` reverted to base. Each wrong version listed above was
applied as an edit, and each failed its own criterion's witness. The whole
of `tests/test_batch.py` passed, and `ruff` passed. The diff measured 502
changed tokens by `size_gate`, against the `bug` ceiling of 1300.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words. Keep each docstring within ten lines.
