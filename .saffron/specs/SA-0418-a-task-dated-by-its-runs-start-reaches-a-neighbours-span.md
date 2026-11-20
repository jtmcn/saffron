---
id: SA-0418
title: "The projection dates a task by its run's start, so a batch's later cells reach their own span rarely and three chains break on a neighbour's span"
type: bug
priority: 2
estimated_lines: 71
estimate_measured: true
history:
  command: python -m saffron.cli --home "$SAFFRON_HISTORY_HOME" chains
  batches: true
touches:
  - saffron/projection.py
  - tests/test_projection.py
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
  - docs/**
  - images/**
  - harness/**
  - records/**
  - hooks/**
  - saffron/chain_walk.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/events.py
  - saffron/task.py
  - saffron/cell/**
  - saffron/gates/**
  - tests/test_chain_walk.py
  - tests/test_history_run.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 24
max_attempts: 3
max_turns: 120
acceptance:
  - claim: >-
      A task is tied to the span that holds the start of its last cell
      attempt. A cell attempt is any attempt outside the phases
      `SPEC_REVIEW`, `SPEC_WRITING` and `COMMIT_REVIEW`. This witness drives
      the last two, and criterion 2's drives `SPEC_REVIEW`. The witness writes
      one log with four spans and three merged tasks. Task A's run row
      predates every span. A's gated `IMPLEMENTING` attempt lies in span 0.
      A reaches `run_task` again under its own id, and its last cell attempt
      is an ungated `REVIEWING` one. It starts in the very second of span
      1's `Ceilings`, which carries a fraction of a second. A also has a
      spec writing attempt inside span 2. Task B's
      run row and its spec review lie inside span 1, and so does B's first
      cell attempt, an ungated `REPAIRING` one in the middle of span 1. B's
      other cell attempts lie in span 2. The gated one is `IMPLEMENTING`,
      and the last, an ungated `REBUTTING` one, starts in the second before
      span 3 starts. B also
      has a commit review attempt inside span 3. Task C, the last in the
      log, has a run row one second after span 3's `Ceilings` and a cell
      attempt a day later. Each span's plan and export lines match the
      stored files in a pattern the other spans lack. So A states both
      edges, B states only its diff-to-plan edge, and C states only its
      pull-request-to-diff edge. Q4 reaches A's pull request alone.
    witness: tests/test_projection.py::test_a_task_is_tied_to_the_span_its_last_cell_attempt_starts_in
    wrong_versions:
      - Each task is tied by its run's `started_at`, as at base.
      - Each task is tied by its first cell attempt, so a re-queued task keeps its first span.
      - Each task is tied by its last gated attempt, falling back to its last cell attempt.
      - Every cell attempt of a task claims the span it lies in, and the task is tied to the span of its last one.
      - Each task is tied by its first attempt in any phase.
      - Each task is tied by its last attempt in any phase.
      - A later spec writing session counts as a cell attempt.
      - A commit review session counts as a cell attempt.
      - A span holds an instant only after its start second, so an attempt in the `Ceilings` second falls to the span before.
      - A span holds an instant up to and including its end, so the second of the next `Ceilings` lies in two spans.
      - A span starts at the raw `Ceilings` timestamp, unfloored.
      - The task is tied to the span whose `Ceilings` is nearest its instant, before or after.
      - The last span in a log ends an hour after its `Ceilings`.
    covers:
      - set: phases outside the cell
        members:
          - member: "`SPEC_WRITING`, A's attempt inside span 2"
            driven_by: A later spec writing session counts as a cell attempt.
          - member: "`COMMIT_REVIEW`, B's attempt inside span 3"
            driven_by: A commit review session counts as a cell attempt.
      - set: a span's edges
        members:
          - member: an attempt in the start second of its own span
            driven_by: A span holds an instant only after its start second, so an attempt in the `Ceilings` second falls to the span before.
          - member: an attempt in the start second of the next span
            driven_by: A span holds an instant up to and including its end, so the second of the next `Ceilings` lies in two spans.
          - member: a `Ceilings` timestamp with a fraction
            driven_by: A span starts at the raw `Ceilings` timestamp, unfloored.
          - member: an attempt in the last second before the next span
            driven_by: The task is tied to the span whose `Ceilings` is nearest its instant, before or after.
          - member: the last span, open at its end
            driven_by: The last span in a log ends an hour after its `Ceilings`.
      - set: where a task's run row lies
        members:
          - member: before every span, task A
            driven_by: Each task is tied by its run's `started_at`, as at base.
          - member: inside the span before its own, task B
            driven_by: Each task is tied by its run's `started_at`, as at base.
          - member: inside its own span, task C
            driven_by: tests/test_projection.py::test_a_task_is_tied_to_the_span_its_last_cell_attempt_starts_in
      - set: steps after the first
        members:
          - member: a task's second span, A's re-queue
            driven_by: Each task is tied by its first cell attempt, so a re-queued task keeps its first span.
          - member: an ungated last cell attempt after a gated one, A
            driven_by: Each task is tied by its last gated attempt, falling back to its last cell attempt.
          - member: an earlier cell attempt inside another task's span, B's in span 1
            driven_by: Every cell attempt of a task claims the span it lies in, and the task is tied to the span of its last one.
          - member: the second task in a log, B
            driven_by: Each task is tied by its run's `started_at`, as at base.
          - member: a spec review in the span before its own, B
            driven_by: Each task is tied by its first attempt in any phase.
          - member: the last task in a log, C
            driven_by: The last span in a log ends an hour after its `Ceilings`.
  - claim: >-
      A task with no cell attempt is unattributable, and the span its other
      times land in stays its owner's. The witness writes one span, owned by
      merged task F. Task D's only attempt is a spec review inside that
      span. Task E has no attempt at all, and its run row lies inside the
      span. D and E are each left out as `unattributable`. F is kept, states
      both edges, and is the one pull request Q4 reaches.
    witness: tests/test_projection.py::test_a_task_with_no_cell_attempt_takes_no_span
    positive_case: >-
      F, in the same log and through the same graph, is kept with both its
      edges and reached by Q4.
    wrong_versions:
      - A spec review session counts as a cell attempt.
      - A task with no cell attempt is tied by its run's `started_at`.
      - A task with no cell attempt is tied by its first attempt in any phase.
    covers:
      - set: tasks with no cell attempt
        members:
          - member: a task whose only attempt is a spec review, D
            driven_by: A spec review session counts as a cell attempt.
          - member: a task with no attempt at all, E
            driven_by: A task with no cell attempt is tied by its run's `started_at`.
          - member: a spec review standing in for a missing cell attempt, D
            driven_by: A task with no cell attempt is tied by its first attempt in any phase.
  - claim: >-
      A span that two tasks' last cell attempts land in is no one's, and the
      next span in the log still goes to its own task. The witness writes two
      spans. Merged tasks G and H each end their cell in span 0. Merged task
      J has its run row and a spec review inside span 0, and its cell in
      span 1. G and H are each left out as `unattributable`. J is kept and
      states span 1's edges, its pull-request-to-diff edge alone.
    witness: tests/test_projection.py::test_a_span_two_tasks_claim_is_no_ones_and_the_next_span_is_still_owned
    positive_case: >-
      J, in the same log and through the same graph, is kept with span 1's
      edges.
    wrong_versions:
      - The first task to land in a span keeps it.
      - The last task to land in a span keeps it.
      - A span claimed twice leaves every task of that log unattributed.
      - Each task is tied by its run's `started_at`, as at base.
    covers:
      - set: tasks in a span claimed twice
        members:
          - member: the first claimant, G
            driven_by: The first task to land in a span keeps it.
          - member: the second claimant, H
            driven_by: The last task to land in a span keeps it.
      - set: the span after a collision
        members:
          - member: J's own span, after the collided one
            driven_by: A span claimed twice leaves every task of that log unattributed.
          - member: J's run row inside the collided span
            driven_by: Each task is tied by its run's `started_at`, as at base.
  - claim: >-
      An instant in a second that two spans' floors share is still
      unattributable, and a ledger time still reads as UTC with the host zone set to `JST-9`. In
      case (j), one task's last cell attempt lies in the shared second and
      its sibling's predates both spans. In case (a), two tasks' last cell
      attempts land in the second of two spans.
    witness: tests/test_projection.py::test_tasks_that_match_their_spans_in_count_but_not_time_are_unattributable
    preserves: true
    wrong_versions:
      - An instant in a second two spans' floors share is still tied to the later span.
      - A ledger time is parsed in the host's local zone.
      - A span two tasks land in goes to one of them.
---

## Context

Backlog item **b-952c34**, with item 170, b-946f03 and b-60d804. It cites
`DESIGN.md` §4.1, and Appendix T states the rule the projection serves.
Every line below was read at `4e58acde`. This spec's base changes no file
it cites. Its commits add this spec and one backlog record. They edit
another backlog record, the priority order and the queue smoke test in
`tests/test_scheduler.py`.

**The rule today.** `materialize` hands `_attribute` each task's run
`started_at` (`saffron/projection.py:334-339`). `_attribute` ties a task to
the one span whose `[start, end)` holds that second
(`saffron/projection.py:225-249`). A span starts at its `Ceilings` second,
floored (`saffron/projection.py:205`). A span claimed by two tasks goes to
neither (`:245`). An instant in a second that two spans' floors share is
no one's (`:236`). An instant later in such a span still lands in the
later span, since the earlier one is empty (`:207`). The module docstring states the same rule
(`saffron/projection.py:19-22`), and so does `_run_start_epoch`'s
(`:217-222`).

**Why a run's start misses.** `run_task` emits `Ceilings` before it calls
`run_one_cell` (`saffron/task.py:817`, `:963`). Inside the cell, `_drive_cell`
wraps every turn's agent so that each turn opens an attempt
(`saffron/cell/session.py:2637`). The wrapper opens it under the task's own
state (`saffron/cell/session.py:288-312`, `saffron/ledger.py:1700-1707`).
A spec session names its own phase instead.
`SPEC_REVIEW` comes from `saffron/batch.py:800` and `saffron/draft.py:203`.
`SPEC_WRITING` comes from `saffron/batch.py:909-910`,
`saffron/follow_up.py:326` and `saffron/draft.py:232`. A commit review opens
`COMMIT_REVIEW` (`saffron/commit_review.py:174`). `saffron/task.py:1132-1134`
already sets the two spec phases apart as spend outside the cell. A stack
batch mints the run row first (`saffron/cli.py:1622`, `saffron/batch.py:706`).
It then reviews the spec (`saffron/batch.py:800`) and only then starts the
cell. So the run's start lands in the previous task's span, or before the
log's first span.

**One task can own several spans.** The queue scan hands a task in
`REQUEUE_STATES` back under its own id (`saffron/scheduler.py:164-172`,
`:1347-1350`). A stack batch passes that id to `run_task`
(`saffron/cli.py:946`). Each call that gets past its first refusals
(`saffron/task.py:771-793`) emits a fresh `Ceilings` (`:817`). On the home ledger,
`SA-0380` task 423 wrote ten spans in one log. Its last span holds its
last export.

**Measured over a copy of the home ledger**, taken 2026-11-20, with the
batch tree at `~/.saffron/batches/v0`.

| rule | compared | breaks | unattributable |
| --- | --- | --- | --- |
| run start, at base | 143 | 3 | 187 |
| first cell attempt, else run start | 294 | 2 | 36 |
| last cell attempt | 294 | 0 | 36 |

Under the base rule, all three breaks are misattributions. `SA-0415` task
462 has its run row inside span 1, the span of task 461's second call to
`run_task`. 462's own span is span 2. `SA-0245` task 274 and
`SA-0277` task 308 fall the same way into the span before their own. Under
the first cell attempt, tasks 422 (`SA-0378`) and 423 (`SA-0380`) break.
Each reached `run_task` more than once and is tied to its first span,
whose export a later call replaced. Under the last cell attempt the same
294 tasks compare and none breaks. The record's own tally kept 178 when
it dated each task by its first attempt in any phase.

## Problem

The projection ties a task to the span holding its run's start. A batch
writes that row before the cell starts, so half of merged history is left
out. Three tasks it does keep land on another task's span. Make these
changes.

1. **Date each task by its last cell attempt.** Read each task's last
   attempt `started_at` outside the three phases above, from the ledger
   `materialize` already holds. Hand that instant to `_attribute` in place
   of the run's `started_at`. A task with no such attempt has no instant,
   and `_attribute` leaves it unattributable.
2. **Keep the rest of the rule.** A span's `[start, end)` is unchanged,
   with floored starts and an open last span. A span two tasks' instants
   land in stays no one's. An instant in a second that two spans'
   floors share stays no one's. A ledger time parses as UTC.
3. **Say the new rule where the old one is said.** The module docstring,
   `_attribute`'s docstring and `_run_start_epoch`'s docstring each name a
   run's start. Name the last cell attempt instead.
4. **Date the fixture's attempts.** `build` in `tests/test_projection.py`
   opens its gated attempt at the wall clock. Every attempt `build` opens
   needs a time inside its own task's span, so each existing test keeps its
   meaning. Rework cases (a) and (j) of
   `test_tasks_that_match_their_spans_in_count_but_not_time_are_unattributable`
   so their tasks' cell attempts, rather than their run rows, decide them.
   In (a), each task's last cell attempt lies in the second span, at its own
   run row's second. In (j), the first task's attempt lies in second N. Its
   sibling's attempt lies at its own run row, a day before both spans. With
   both attempts in N, the collision rule alone would decide (j), and a
   deleted floor guard would pass it.

## Out of scope

- **`SA-0013` task 8**, and every other task with no `events.jsonl`. No log
  can tie it, so it stays `unattributable`. Item 170 decides whether such
  tasks are migrated or abandoned.
- **A log with no `Ceilings`.** Twenty merged tasks have one. Nineteen stay
  `unattributable`, and `SA-0063` task 59 is left out first as
  `spec_unusable`. With the 17 that have no log, they make the 36.
- **Nine old `ORPHANED` tasks with no attempt.** The base rule kept them by
  their run's start. They leave the graph, and none is merged, so the
  comparison is unchanged. Any other task with no cell attempt is
  unattributable too, such as a `PREFLIGHT_FAILED` or `SPEC_WITHHELD` one.
  On the ledger copy no such task was kept at base, so only the nine
  leave.
- **A span no task's last cell attempt lands in.** Take a task whose own
  `Ceilings` never reached its log. Its last cell attempt lies in a
  neighbour's span. Where the neighbour's own attempt lands there too, the
  span goes to neither. Where it lands in no task's span, the stray task
  takes it. Three causes leave a span that empty. One is a neighbour whose
  own `Ceilings` is missing and which has no cell attempt. Another is an
  earlier span of a re-queued neighbour. The last is a call that stopped at
  preflight (`saffron/cell/session.py:2566`) before the attempt wrapper
  (`:2637`).
- **The `v0.5` phase.** A ledger migration backfills one attempt per
  legacy gate result in phase `v0.5`, started at migration time
  (`saffron/ledger.py:519-526`). The rule reads it as a cell attempt. The
  ledger copy holds no such row, so no witness drives it.
- **The `REPLAY` phase.** `saffron/replay.py:88` opens it for v0 replays,
  and no replayed spec writes a `Ceilings`.
- **Appendix T's answer.** The rule's rerun over the kept tasks is
  recorded by hand in b-946f03 after this lands.

## Notes for the agent

**Edit or new.** Each criterion edits `_attribute` and its caller, whose
spelling is new at your base. Criterion 1's witness has a mutant on the
ref, in a line of `_spans` the change leaves alone
(`saffron/projection.py:205`). Criteria 2 and 3 have none, and `witness`
reports `skip` for each. The `preserves` witness exists at your base and
passes there. It passes again
once cases (a) and (j) carry their own attempts.

**Phases.** The new witnesses use the phases a cell records:
`IMPLEMENTING` for a gated attempt, `REVIEWING` or `REBUTTING` for a later
ungated one.

**The fixture.** `T` takes no attempt times today, and `build` opens one
attempt only when `gate_result` is set (`tests/test_projection.py:184-197`).
Give `T` a list of `(phase, started_at)` attempts. Open one attempt in
phase `IMPLEMENT` in the task's own `Ceilings` second when the list is
absent. That one attempt carries the gate result when `gate_result` is set,
so no extra attempt appears. `tests/test_projection.py:341-342` pins the
attempt numbers `[1, 1, 2]` and two phases. Record a gate result on a cell
attempt, never on a spec session. With an attempts list, the gate result
goes on its `IMPLEMENT` or `IMPLEMENTING` attempt, never on the list's
last attempt by default. Criterion 1's A ends on an ungated attempt. Write each time as
the ledger's own text, `%Y-%m-%d %H:%M:%S` in UTC.
`tests/test_chain_walk.py` builds through the same helper and must pass
unedited.

**Writing a log by hand.** `build` writes one span per `T` in list order.
Criteria 1 to 3 need spans no `T` owns, such as A's first span. Build those
tasks with `no_ceilings=True` and write the spec's whole `events.jsonl`
afterwards, in time order. `_spans` cuts the log by position and dates each
span by its `Ceilings`.

**What each witness observes.** Read the graph's edges, never only
`kept`. A plan line matching the stored `plan.json` states the
diff-to-plan edge, and an export line matching `patch.diff` states the
pull-request-to-diff edge (`saffron/projection.py:412-421`, `:468-469`).
Give every span in a witness log a pairing no other span has. A task on a
neighbour's span then shows the wrong edges. Compare every task's edges in
one assertion, so a failure names each task that moved. Q4 reaches a pull request
only with both edges and a gated attempt (`ontology/queries/Q4-derivation-chain.rq`).

**Times.** Set each run row away from its own span unless the criterion
says otherwise. A run row at the span's `Ceilings` passes the base rule,
so a witness built that way stays green with the source reverted.

**The `prose` gate.** A docstring line you rewrite is judged as new text.
The module docstring's paragraph at `saffron/projection.py:19-22` holds an
em-dash and a sentence over 25 words. `_run_start_epoch`'s docstring at
`:218-220` holds an em-dash too. Each rewrite takes neither, and nor does
`_attribute`'s docstring. Name the last cell attempt in the date helper's
docstring. The prototype failed `make check` until each sentence was cut
short.

**Imports.** Import `saffron.projection` inside each test body, as the
file's docstring asks (`tests/test_projection.py:3-6`).

**Size.** A prototype at `4e58acde` measured 283 changed tokens outside
the test paths with `size_gate`, and 830 under them. `estimated_lines` is
the first over four. Each new witness failed with `saffron/projection.py`
reverted, and each wrong version above failed its witness there. The
`history` command took 72 seconds over a copy of the home ledger on the
host. It printed 294 compared, 0 breaks and 36 unattributable.
