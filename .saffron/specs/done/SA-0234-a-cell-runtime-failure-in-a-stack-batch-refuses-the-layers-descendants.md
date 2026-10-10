---
id: SA-0234
title: A cell runtime failure in a stack batch marks the layer missed, so the batch refuses its descendants
type: bug
priority: 2
depends_on: [SA-0226]
estimated_lines: 163
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
  - saffron/spec_review.py
  - saffron/follow_up.py
  - saffron/end_review.py
  - saffron/scheduler.py
  - saffron/reconcile.py
  - saffron/intake.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 16
max_attempts: 3
max_turns: 110
risk: standard
acceptance:
  - claim: >-
      In a stack batch, a spec of the order whose `review` or `runner`
      raised `CellRuntimeError` is not a miss. It is offered again at once,
      on the same predecessor, and a spec that depends on it is not refused.
      A `review` that raised it still records its round routed `error`. A
      `RuntimeError` that is not a `CellRuntimeError` is still a miss from
      either seat, and its dependent is refused. The witness drives each
      seat with each of the two exceptions, and the batch drains.
    witness: tests/test_batch.py::test_a_cell_runtime_failure_in_a_stack_batch_is_offered_again_not_missed
    wrong_versions:
      - The class checked is `RuntimeError`, the base of `CellRuntimeError`, so every raise from either seat is offered again.
      - The `review` seat still records a miss, so its dependent is refused.
      - The `runner` seat still records a miss, so its dependent is refused.
      - The spec stays queued but the loop still counts it as started, so its dependent runs next on the wrong predecessor.
      - The spec is kept out of the misses but taken out of the queue, so its dependent runs on the wrong predecessor.
      - A `CellRuntimeError` from `review` records no spec review round.
  - claim: >-
      A follow-up whose `review` or `runner` raised `CellRuntimeError` is
      offered again at once, on the same predecessor. A follow-up whose
      `review` or `runner` raised a `RuntimeError` that is not one is not
      offered again. The one whose review raised it is listed unrun. The
      witness drives all four.
    witness: tests/test_batch.py::test_a_follow_ups_cell_runtime_failure_is_offered_again
    wrong_versions:
      - The loop offers a spec again after any raise, so a follow-up that raised `RuntimeError` runs twice.
      - The class checked is `RuntimeError`, so a follow-up that raised a plain one runs twice.
      - The follow-ups' pass offers nothing again, because only the order's misses changed.
      - The loop never offers a raising spec again, in either pass.
  - claim: >-
      Each re-offer counts toward the breaker. A spec whose `review`, or
      whose `runner`, raises `CellRuntimeError` twice in a row ends the
      stack batch `INFRASTRUCTURE` after two calls. Its dependent is neither
      refused nor reviewed. A plain batch passes no `sleep`, and never
      offers a spec whose `runner` raised `CellRuntimeError` again. The
      witness drives both seats in a stack batch, and the plain batch.
    witness: tests/test_batch.py::test_a_cell_runtime_failure_is_offered_again_only_until_the_breaker
    wrong_versions:
      - The wrapper calls `runner` again in place on a `CellRuntimeError`, so the breaker never sees the first raise.
      - The wrapper calls `review` again in place on a `CellRuntimeError`, so the breaker never sees the first raise.
      - A `CellRuntimeError` is not counted as an abort, so the re-offers never reach the breaker.
      - The re-offer ignores `sleep`, so a plain batch starts the raising spec twice.
      - The `runner` seat still records a miss, so the dependent is refused.
      - The `review` seat still records a miss, so the dependent is refused.
---

## Context

Backlog item **b-60a399**, which cites `DESIGN.md` §4.4 and §7. It was
measured in batch 13, in stage 2 of the delegate-loop plan. Every line
number below was read at `958db033`. Your base also carries `SA-0226`,
which edits the same function, so the lines shift.

**What happened.** `SA-0206`'s spec review raised `CellRuntimeError:
seeding the worktree failed`. Git in the cell got "Permission denied" on a
loose object (b-6ac0cd). The batch marked `SA-0206` missed, and the log
read "SA-0207 refused reaches SA-0206". A cell runtime failure says the
host broke, not the spec. CLAUDE.md's `error` ≠ `fail` rule draws the same
line for gates.

**The error type.** `CellRuntimeError` is the cell runtime's own error, a
subclass of `RuntimeError` (`saffron/cell/runtime.py:35-36`). The seed in
`prepare_worktree` (`saffron/cell/worktree.py:41`) raises it when the seed
exits nonzero (`:106-109`). The stack batch's review runs in a layer cell
(`saffron/cli.py:956`), so the raise reaches `review`.
`saffron/finish.py:19` already imports the type from that module.

**How a raise becomes a miss today.** `run_stack_batch` wraps each spec in
`wrapped` (`saffron/batch.py:519`). When `review` raises, it records a
round routed `error` and sets the task `GATE_ERROR`. For a spec of the
order it then adds the spec to `missed` and takes it out of `remaining`,
and re-raises (`saffron/batch.py:561-575`). When `runner` raises it does
the same, with no round (`saffron/batch.py:729-735`). `resolve_prefix`
refuses each spec whose `depends_on` reaches a missed one
(`saffron/batch.py:507-518`). A follow-up is never added to `missed`, by
the `is_follow_up` test at both sites.

**What the loop does with the raise.** The general handler in `_drive`
(`saffron/batch.py:183`) counts it as an abort (`:268`, `:280`). It prints
"raised" with the type and text, and attaches any run the call minted
(`:283-284`). The spec stays in `started`, so `_drive` never offers it
again that pass (`saffron/batch.py:224`, `:253`). Two aborts in a row
(`_BREAKER_THRESHOLD`, `saffron/batch.py:67`) stop the batch before the
next spec, as `INFRASTRUCTURE` (`:247-248`). The order's pass rescans with
`resolve_prefix` (`saffron/batch.py:761`). The follow-ups' pass rescans
the fixed list (`:807`).

**The precedent, b-031ac2.** A `CellOutcome` in `RATE_LIMITED` or
`PROVIDER_UNREACHABLE` keeps `original` in `remaining`
(`saffron/batch.py:736-742`). For `PROVIDER_UNREACHABLE`, `_drive` counts
the abort and then takes the spec out of `started` when `sleep` is set
(`saffron/batch.py:310-325`). So it runs again at once, on the same
predecessor, and the breaker bounds it. `run_stack_batch` always passes
`sleep` (`saffron/batch.py:417`, `:769`, `:815`). `run_batch` passes it
only from its own caller, and `saffron batch` passes none
(`saffron/cli.py:1761-1771`).

## Problem

Treat a `CellRuntimeError` from a stack batch's `review` or `runner` as the
`PROVIDER_UNREACHABLE` precedent treats its outcome.

1. **The two raise sites in `wrapped`.** For a `CellRuntimeError`, leave
   the spec out of `missed` and keep `original` in `remaining`. Any other
   exception takes today's path. The `review` site records its `error`
   round and sets `GATE_ERROR` whatever the exception's type.
2. **The re-offer in `_drive`.** Its handler counts the raise first. Then,
   for a `CellRuntimeError` with `sleep` set, it takes the spec out of
   `started`. `sleep` is the stack batch's mark, as in the
   `PROVIDER_UNREACHABLE` branch. The breaker is then the only bound, in
   both passes.
3. **Four comments go stale.** The `started` comment names the states
   taken back out (`saffron/batch.py:216-218`). The `mint` comment says a
   raise from `review` or `runner` is a miss (`saffron/batch.py:529`). The
   `review` comment says a raise from `review` is a miss
   (`saffron/batch.py:559-560`). The `_is_layer` docstring names only the
   two outcomes kept queued (`saffron/batch.py:370-371`). Correct each in
   one or two lines.

## Out of scope

- **`mint` and `revise`.** In the order's pass, a raise from either stays a
  miss, whatever its type (`saffron/batch.py:530-536`, `:688-694`). In the
  follow-ups' pass, change 2 offers a follow-up again after any
  `CellRuntimeError`, the writer's included. A follow-up is never a miss.
- **Any exception outside `CellRuntimeError`.** Its path stays as it is.
- **A new state, stop reason or log line.** The "raised" line already names
  the type. A batch the breaker stops reads `INFRASTRUCTURE`. `missed` is
  local to one call (`saffron/batch.py:455`), so no later batch inherits it.
- **`DESIGN.md` §4.2.1 and ADR 7.** Their sentences on misses are hand
  edits in this spec's pull request.

## Notes for the agent

**Edit, no mutant.** The change adds a type test to two existing
conditions and one new branch. No text at base fixes its spelling, so each
criterion declares a witness and no mutant. The `witness` gate reports
`skip` for all three. Do not run the wrong versions yourself.

**Every witness fails at base.** At base the first raise is a miss. Its
dependent is refused, and nothing is offered again. Import
`CellRuntimeError` from `saffron.cell.runtime` in the tests, which exists
at base.

**One helper drives all three.** Subclass `StackDoubles` with a table keyed
by `(seat, spec id)`, where the seat is `review` or `runner`. Each call
first pops and raises that key's next queued exception, recording the call
as `StackDoubles` does. Otherwise it falls back to `StackDoubles`. Run
each batch with `sleep=_fail_sleep` and a budget of 100.

**Criterion 1.** The order is `TE-1`, `TE-2` on `TE-1`, `TE-3` on `TE-2`,
`TE-5` on `TE-3`, `TE-4`, `TE-6`, and `TE-7` on `TE-6`. `TE-1`'s review
raises `CellRuntimeError` once, and `TE-2`'s runner once. `TE-3`'s review
raises `RuntimeError`, and `TE-6`'s runner. A success sits between each
raise, so the breaker never fires. Assert `DRAINED`. Assert these review
calls, as `(spec, predecessor)`: `TE-1` and none twice, `TE-2` on `TE-1`,
`TE-3` on `TE-2`, `TE-4` on `TE-2`, `TE-6` on `TE-4`. Assert these runner
calls: `TE-1` and none, `TE-2` on `TE-1` twice, `TE-4` on `TE-2`, `TE-6`
on `TE-4`. Assert the refused lines are exactly `TE-5` reaching `TE-3` and
`TE-7` reaching `TE-6`. Assert `TE-1`'s task routes read `error`, then
`run`, with `_task_routes`.

**Criterion 2.** Order `TE-13` alone, with `end_review` and `follow_ups`
from the doubles. The follow-ups are `TE-8`, `TE-9`, `TE-10`, `TE-12` and
`TE-11`, in that order. `TE-8`'s review raises `CellRuntimeError` once,
and `TE-9`'s runner once. `TE-10`'s runner raises `RuntimeError`, and
`TE-11`'s review. `TE-12` sits between those two, so the breaker never
fires. Assert `DRAINED`. Assert these review calls: `TE-13` and none,
`TE-8` on `TE-13` twice, `TE-9` on `TE-8`, `TE-10` on `TE-9`, `TE-12` on
`TE-9`, `TE-11` on `TE-12`. Assert these runner calls: `TE-13` and none,
`TE-8` on `TE-13`, `TE-9` on `TE-8` twice, `TE-10` on `TE-9`, `TE-12` on
`TE-9`. Assert the line `follow-ups unrun  TE-11`.

**Criterion 3.** Two stack batches, then one plain batch. The first is
`TE-21`, then `TE-22` on `TE-21`, with `TE-21`'s runner raising
`CellRuntimeError` twice. The second is `TE-31` and `TE-32` the same way,
with `TE-31`'s review raising it twice. For each, assert `INFRASTRUCTURE`,
two calls of the raising seat for the first spec, no refused line, and no
review call for the dependent. Then run `run_batch` over `TE-41` and
`TE-42` with a `FakeRunner`. Its first entry is a `CellRuntimeError`, and
its second reaches review. Pass `rescan` returning the same two
candidates. Assert `DRAINED` and runner calls `TE-41` then `TE-42`.

**What the witnesses leave undriven.** A `CellRuntimeError` from `mint` or
`revise` in the order's pass stays a miss. No criterion claims it. An
exception that is not a `RuntimeError` at all keeps today's path, and the
witnesses drive the closer complement, a plain `RuntimeError`.

**Measured on a prototype, 2026-10-07.** The change and all three
witnesses were written against `958db033` and passed. Each failed with
`saffron/batch.py` reverted to base. Each wrong version listed above was
applied as an edit, and each failed its own criterion's witness. The whole
of `tests/test_batch.py` passed, and `ruff` passed. The diff measured 652
changed tokens by `size_gate`, against the `bug` ceiling of 1300.

**The `prose` gate** reads every new comment and docstring. Write none with
an em dash, a semicolon, a contraction, the perfect tense or a sentence
over 25 words. Keep each docstring within ten lines.
