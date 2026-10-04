---
id: SA-0201
title: A plan turn the provider served nothing ends NOT_IMPLEMENTED and exits 1, as if the task had failed
type: bug
priority: 2
depends_on: [SA-0199]
estimated_lines: 243
estimate_measured: true
touches:
  - saffron/phases/implement.py
  - saffron/cell/session.py
  - saffron/cli.py
  - saffron/batch.py
  - tests/test_implement.py
  - tests/test_session.py
  - tests/test_cli.py
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
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/report/**
  - saffron/task.py
  - saffron/events.py
  - saffron/record/**
  - saffron/gates/**
  - saffron/agents/**
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/cell/runtimes/**
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/phases/package.py
budget_usd: 22
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A turn whose result event ends `api_error` and counts zero on all four
      token fields says, on the `AttemptResult` its `AgentFailed` carries,
      that the provider served it nothing. The witness feeds `run_agent`
      SA-0152's first result event verbatim, which says so. It then feeds
      that event with each of `input_tokens`, `output_tokens`,
      `cache_read_input_tokens` and `cache_creation_input_tokens` set to 1,
      each of the four set to null, all four absent, and the terminal reason
      `completed`. None of those ten says so.
    witness: tests/test_implement.py::test_a_turn_the_provider_served_no_token_is_told_apart_from_one_it_served
    wrong_versions:
      - A count that is absent or null read as zero, so a runner that sent no usage reads as served nothing.
      - A check of `input_tokens` and `output_tokens` alone, so a turn that read only from the cache reads as served nothing.
      - A check that ignores the terminal reason, so a zero-token `completed` result reads as served nothing.
      - A check on `num_turns` being zero instead of the counts, which SA-0152's own event fails at 1.
      - A check on `total_cost_usd` being zero instead of the counts, so a turn that read tokens at $0.00 reads as served nothing.
  - claim: >-
      When the plan turn's first call fails and the provider served it
      nothing, the task ends `PROVIDER_UNREACHABLE`. The returned outcome and
      the ledger's task row both say so, the run row reads `COMPLETE`, the
      spend is $0.00, and no second turn runs. The same failure on a
      `rejected` window still ends `RATE_LIMITED`, in the outcome and the row.
    witness: tests/test_session.py::test_a_plan_turn_the_provider_served_nothing_ends_provider_unreachable
    wrong_versions:
      - The ledger row set to the new state while the returned outcome still says `NOT_IMPLEMENTED`.
      - The served-nothing check made before the rejected-window check, so a closed window ends `PROVIDER_UNREACHABLE`.
      - The run row left open for the new state, so it does not read `COMPLETE`.
  - claim: >-
      Of the plan turn's first call, its two re-prompts and an implement
      turn, only the first call can end the task `PROVIDER_UNREACHABLE`. The
      witness drives five cases with no commits. That first call served
      nothing ends `PROVIDER_UNREACHABLE`. That first
      call failing `api_error` at $0.00 with tokens served ends
      `NOT_IMPLEMENTED`. A schema re-prompt served nothing after a completed
      first call ends `NOT_IMPLEMENTED`, and so does a scope re-prompt served
      nothing after a first call whose proposal was refused. An implement turn served nothing
      after a completed plan turn ends `NOT_IMPLEMENTED` and logs that it
      ended without finishing. Each case checks the outcome, the task row
      and the number of turns run.
    witness: tests/test_session.py::test_a_turn_that_fails_after_a_completed_turn_keeps_not_implemented
    wrong_versions:
      - A failed plan re-prompt that keeps its served-nothing fact, so it ends `PROVIDER_UNREACHABLE` after a completed turn.
      - An implement turn served nothing that also ends `PROVIDER_UNREACHABLE`.
      - A plan-turn check on `api_error` at $0.00 instead of the served-nothing fact.
      - The first call's completion recorded just before the schema re-prompt, so a failed scope re-prompt ends `PROVIDER_UNREACHABLE`.
  - claim: >-
      `saffron cell` exits 2 when its task ends `PROVIDER_UNREACHABLE`, and
      still exits 1 when it ends `NOT_IMPLEMENTED`.
    witness: tests/test_cli.py::test_a_provider_that_served_nothing_exits_2_and_a_task_that_failed_exits_1
    mutant:
      file: saffron/cli.py
      find: '"PROVIDER_UNREACHABLE": 2,'
      replace: '"PROVIDER_UNREACHABLE": 1,'
    wrong_versions:
      - The state left out of the exit map, so it takes the default 1.
      - '`NOT_IMPLEMENTED` mapped to 2 as well.'
  - claim: >-
      In `saffron batch`, a task that ends `PROVIDER_UNREACHABLE` counts
      toward the breaker as `PREFLIGHT_FAILED` does, and is not offered
      again. Two in a row end the night `INFRASTRUCTURE` before a third task
      starts.
    witness: tests/test_batch.py::test_a_provider_that_served_nothing_counts_toward_the_breaker
    mutant:
      file: saffron/batch.py
      find: 'if outcome.state in ABORT_STATES:'
      replace: 'if outcome.state in ABORT_STATES - {"PROVIDER_UNREACHABLE"}:'
    wrong_versions:
      - The breaker's abort set left without the state, so two in a row drain the night.
      - The stack batch's re-offer applied to a plain batch too, so the same spec starts twice.
  - claim: >-
      In a stack batch, a task that ends `PROVIDER_UNREACHABLE` is not a miss.
      The same spec is offered again at once, on the same predecessor, with
      no wait, and nothing that depends on it is refused. It still counts
      toward the breaker, and a success after it resets the count. So the
      breaker bounds the re-offers: two in a row end the night
      `INFRASTRUCTURE`, and the spec is not offered a third time. The count
      goes through the breaker's own abort set. With that set patched to
      leave the state out, the same spec runs a third time and the night
      drains. The witness drives all three. In the first order, two specs each end
      `PROVIDER_UNREACHABLE` once and then reach review, and the night drains.
      In the second, one spec ends `PROVIDER_UNREACHABLE` twice with a third
      run queued that would reach review.
    witness: tests/test_batch.py::test_a_stack_batch_offers_a_provider_that_served_nothing_again_until_the_breaker
    mutant:
      file: saffron/batch.py
      find: 'if outcome.state in ABORT_STATES:'
      replace: 'if outcome.state in ABORT_STATES - {"PROVIDER_UNREACHABLE"}:'
    wrong_versions:
      - The state counted as a miss, as the first draft of this spec had it, so its dependent is refused and it never runs again.
      - The state re-offered on a fresh predecessor, the spec it ran on taken for a layer.
      - The state re-offered at the back of the queue, so a later spec runs first and becomes its predecessor.
      - The state routed through the `RATE_LIMITED` wait, so the batch sleeps for a reset time it was never given.
      - The state re-offered but not counted, so a run of them never reaches the breaker.
      - The breaker's abort set left without the state.
      - The re-offer counted in its own branch beside the `RATE_LIMITED` one, outside the abort-set test, so the declared mutant cannot reach it.
---

## Context

Backlog item **b-031ac2**, filed from the spec loop's run 26. It cites
`DESIGN.md` §4.3 and §5.1. Every line number below was read at `0fecec0c`.

**What happened.** `SA-0152`'s first cell passed preflight from both
networks. Its plan turn then logged ten `api_retry` events and the text "API
Error: Connection refused". Its result event, in
`~/.saffron/batches/v0/SA-0152/events.jsonl`, reads `success`, `api_error`,
`is_error` true, `num_turns` 1, `total_cost_usd` 0.0, and zero on all four
token fields. The ledger holds task 211 `NOT_IMPLEMENTED` with one attempt,
`success`/`api_error`, 1 turn, $0.00. The cell exited 1. The re-run went
green and reached #650.

**Measured across this host.** Every result event in
`~/.saffron/batches/` ending `api_error` was read. Three count zero on all
four token fields: the first cells of `SA-0152`, `SA-0193` and `SA-0195`.
Each was a plan turn after ten `api_retry` events, and each ended
`NOT_IMPLEMENTED`. The other three served tokens or carried none. `SA-0121`
and `SA-0133` each counted over two hundred thousand. `SA-0057`'s event carries no
counts, so all four read null. So `num_turns` cannot tell an unserved turn apart,
and `total_cost_usd` cannot either.

**Where the fact lives.** The runner copies the four counts onto the result
event and nulls one the SDK did not send (`images/agent_runner.py:57-65`,
`:131-146`). The host keeps that event whole with `result.update(event)`
(`saffron/phases/implement.py:291`).
It builds the `AttemptResult` from it and raises `AgentFailed` carrying it
when the turn failed (`saffron/phases/implement.py:385-421`).
`AttemptResult` has no field for the counts (`saffron/phases/implement.py:84-105`).

**How the plan turn fails today.** The plan checkpoint's first call sends
`implement.PLAN_PROMPT` with no session to resume
(`saffron/cell/session.py:511-513`). Its two re-prompts resume
it after a completed first call (`saffron/cell/session.py:542-549`,
`:575-582`). On `AgentFailed` it re-raises with the cost summed
(`saffron/cell/session.py:611-618`). `_drive_cell`, which `run_one_cell`
wraps (`saffron/cell/session.py:1785`), catches that, sets
`NOT_IMPLEMENTED` and finishes the run `COMPLETE`
(`saffron/cell/session.py:2149-2169`). The CLI maps an unmapped state to 1
(`saffron/cli.py:488`).

**The rate-limit guard comes first.** Every turn goes through
`stop_on_rejected` (`saffron/cell/session.py:2045`). It turns a failed turn on
a `rejected` window into `RateLimited` before any phase sees the
`AgentFailed` (`saffron/cell/session.py:164-185`). `_drive_cell` ends that
`RATE_LIMITED` (`saffron/cell/session.py:3066-3094`).

**What a later turn does today.** An implement turn that fails is kept as
an attempt (`saffron/cell/session.py:2236-2246`). With no commits and no
bound cut, it logs `ended_without_finishing`
(`saffron/cell/session.py:2387-2399`) and ends `NOT_IMPLEMENTED`
(`saffron/cell/session.py:2417-2440`). Salvage, repair, notes, review and
rebuttal turns each have their own failure path (`saffron/cell/session.py:2324`,
`:2504`, `:2574`, `saffron/phases/review.py:263`, `saffron/phases/rebut.py:210`).
This spec changes none of them.

**What `PREFLIGHT_FAILED` gets.** `_drive_cell` sets it and finishes the
run `COMPLETE` (`saffron/cell/session.py:1990-2001`). The CLI exits 2
(`saffron/cli.py:87`). The breaker counts it as an abort
(`saffron/batch.py:57-61`, `:309-318`). In a stack batch it is not a layer
(`saffron/batch.py:360-364`). It is recorded as a miss, so its dependents
are refused, and it is not offered again (`saffron/batch.py:726-737`). The
scheduler re-queues it (`saffron/scheduler.py:109-117`).

**What `RATE_LIMITED` gets in a stack batch.** `_drive` waits for the reset
time (`saffron/batch.py:299-306`). It then drops the spec from the started
set, so it can run again (`saffron/batch.py:307`). That branch neither counts nor resets the
breaker. The wrapper keeps the spec queued without a miss, so it runs again
on the same predecessor (`saffron/batch.py:726-729`). `_drive` takes the
stack batch's mark from `sleep`: `run_batch` passes none
(`saffron/batch.py:107-109`), and `run_stack_batch` defaults it
(`saffron/batch.py:409`).

**Already true at your base.** This spec's own pull request made
`PROVIDER_UNREACHABLE` a terminal state in `ontology/factory.ttl`. It
rendered `CONTEXT.md` and the shapes from it. It added the state to
`ledger.TaskState`, to `scheduler.REQUEUE_STATES` beside `RATE_LIMITED`,
and to `report/index.py`'s `_STATE_RANK` at level 2. `DESIGN.md` §3.3,
§4.2.1, §5.1.1 and §6 name it. Nothing sets it yet.

## Problem

A plan turn the provider served nothing is not the task failing, and the
cell must say so. Make these changes.

1. **The fact.** Give `AttemptResult` a boolean field, false by default,
   that says the provider served the turn nothing. `run_agent` sets it true
   only when the result's terminal reason is `api_error` and all four
   counts are present and zero. A null or absent count leaves it false.
2. **The state.** At `_drive_cell`'s plan-turn catch, a failed attempt
   carrying that fact ends the task `PROVIDER_UNREACHABLE`. Any other ends
   it `NOT_IMPLEMENTED` as today. Keep the phase line, the
   reported spend and the `COMPLETE` run row exactly as today.
3. **Only the first call.** A plan re-prompt follows a completed call. So in
   `plan_checkpoint`'s catch, clear the fact when the first call had
   returned. Leave every later turn's failure path alone.
4. **The exit code.** Add the state to the CLI's exit map with 2, beside
   `PREFLIGHT_FAILED`, `GATE_ERROR` and `RATE_LIMITED`.
5. **The breaker.** Add the state to `batch.ABORT_STATES`, and change its
   comment's count from three to four. Update the set literal that
   `tests/test_batch.py:507` pins. A plain batch then treats it as it
   treats `PREFLIGHT_FAILED`.
6. **The stack batch's re-offer.** In a stack batch the state is not a
   miss. Keep it queued in the wrapper, as `RATE_LIMITED` is kept, so it
   runs again on the same predecessor. In `_drive` the count goes through
   the existing `ABORT_STATES` membership test (`saffron/batch.py:309`),
   unchanged. The only new line there drops the spec from the started set
   when `sleep` is set, after that test, with no wait. Leave the
   `RATE_LIMITED` branch as it is. The breaker is the only bound on the
   re-offers, so the count must rise on each one.

## Out of scope

- **The scheduler, the ledger, the morning queue and the vocabulary.** They
  name the state at your base already, and they are forbidden here.
- **A watch line or `TaskOutcome` event for the new state.** The plan
  turn's phase line still names `api_error` and $0.00.
- **A turn after the plan turn's first call.** Any later turn served
  nothing keeps the state it ends in today. Criterion 3 drives the plan
  re-prompt and the implement turn. The salvage, repair, notes, review
  and rebuttal turns are left undriven, since this change reaches none of them.
- **A credential that is missing.** It returns `api_error`, by
  `saffron/phases/implement.py:404-407`'s note, which says nothing of its
  token counts. No event log on this host holds one, so whether it ends
  `PROVIDER_UNREACHABLE` or `NOT_IMPLEMENTED` is unmeasured. Either is
  acceptable here.

## Notes for the agent

**Your base.** This spec stacks on `SA-0199`, which follows `SA-0198` and
`SA-0197`. Those edit `session.py`, `cli.py` and their tests too, so read
each file at your base before you edit it.

**Edit or new.** The field, the plan-turn branch and the re-prompt rule are
new code. So criteria 1 to 3 declare a witness and no mutant. Criterion 4's
mutant pins the exit map entry the change writes. Its spelling is close to
forced, and if it does not match, `witness` names it and counts nothing.
Criteria 5 and 6 share a mutant on the breaker's existing membership test.

**Witnesses red at base.** Criteria 1 to 3 build or read the new field, so
they fail at base without it. Each also observes behaviour only the change
produces: the fact itself, and a first plan call that ends
`PROVIDER_UNREACHABLE`. Criteria 4 to 6 fail at base on behaviour.

**Criterion 1's witness.** Use the module's `_stream` fake with
`returncode=1` and SA-0152's result event as a dict. Copy it from the
Context above, with `session_id` `488a9976-3135-4e7d-8435-b4d793fc1f82` and
`structured_output` null. Read the field off `raised.value.attempt`. One
plain `def` drives all eleven cases.

**Criteria 2 and 3's witnesses.** Use `_stub_the_runtime` and `_drive`.
Script each failing turn as `implement.AgentFailed("api_error",
attempt=...)`, an `AttemptResult` with `success`, `api_error`, `is_error`
true, cost 0.0 and the field set. For criterion 2's second half, add
`rate_limit_status="rejected"` and a `rate_limit_resets_at`, and drive it
under a fresh `tmp_path` subdirectory. For criterion 3, call
`_stub_the_runtime(monkeypatch, commits=0)` per case, each under its own
subdirectory. The schema re-prompt case scripts `_turn("not the schema", cost=0.0)`
first. The scope re-prompt case scripts a proposal already inside
`touches` first, `_block(_PROPOSAL | {"proposed_touches": ["src/x.py"]})`
at cost 0.0, as `test_a_refused_proposal_is_reprompted_and_a_plan_can_follow`
does. The implement case scripts `_turn(_block(_PLAN), cost=0.0)` first.
Both completed first turns cost $0.00, so a check on spend cannot pass.

**Criterion 4's witness.** Copy the shape of
`test_the_exit_code_distinguishes_the_terminal_states` in
`tests/test_cli.py`, which runs without a `push_unpackaged_work` patch.
Script `run_one_cell` to return the two states in turn, and assert `[2, 1]`.

**Two comments in `batch.py` go stale.** The started-set comment says
only a rate-limited spec is taken back out (`saffron/batch.py:215`).
`_is_layer`'s docstring calls anything else a miss
(`saffron/batch.py:360-363`). Update each in one line to name the new state.

**Criterion 5's witness.** Copy `test_two_consecutive_aborts_fire_the_breaker`.
Three candidates, and a `FakeRunner` scripting two `PROVIDER_UNREACHABLE`
outcomes. Assert `INFRASTRUCTURE` and that the runner saw the first two
candidates once each.

**Criterion 6's witness.** Copy the shape of
`test_a_rate_limit_in_a_stack_batch_neither_counts_toward_the_breaker_nor_resets_it`.
Use `RateLimitScript`, an `AdvancingClock` passed as both `clock` and
`sleep`, and `_raise_on_real_sleep`. The first order is `TE-0`, `TE-1`,
`TE-2` depending on `TE-1`, then `TE-3`. `TE-1` and `TE-3` each end
`PROVIDER_UNREACHABLE` and then reach review. The others reach review.
Assert `DRAINED`, no refused line, an empty `clock.sleeps`, and these calls
in order: `(TE-0, None)`, `(TE-1, TE-0)` twice, `(TE-2, TE-1)`,
`(TE-3, TE-2)` twice. The second order is `TE-5` then `TE-6`. `TE-5`
scripts two `PROVIDER_UNREACHABLE` steps and then a review. Assert
`INFRASTRUCTURE`, an empty `sleeps`, and calls `(TE-5, None)` twice only.
Last, monkeypatch `batch.ABORT_STATES` to leave the state out and run a
third order with the same three steps. Assert `DRAINED` and three calls.
A small local runner helper keeps the three orders short.

**Measured on a prototype, 2026-10-03.** All six witnesses were written
against `0fecec0c` with this pull request's hand edits, and passed.
Criterion 6 was rewritten at `ed501943`, after review moved the stack batch
off the miss. Criteria 3 and 6 gained a case at `dc8facfe`. Each
fails with the four source files reverted. Each wrong version listed above
was applied to the prototype and failed its own criterion's witness. The
four test modules passed whole, and `ruff` passed.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence over
25 words. Keep each docstring within ten lines.

**Size.** `saffron/cell/**` is in `elevate_on`, so `size` blocks. The
prototype counted 969 changed tokens by `size_gate`, against the `bug`
ceiling of 1300. `estimated_lines` is those tokens over four. Keep comments
to one or two lines, and the tests close to the shapes above.
