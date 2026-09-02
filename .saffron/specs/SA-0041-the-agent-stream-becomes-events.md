---
id: SA-0041
title: the agent stream and its supervisor still speak prose, and Agent.event is always None
type: refactor
priority: 1
depends_on:
  - SA-0030
touches:
  - saffron/phases/implement.py
  - saffron/phases/review.py
  - saffron/phases/rebut.py
  - saffron/cell/session.py
  - tests/test_implement.py
  - tests/test_review.py
  - tests/test_rebut.py
  - tests/test_agent_runner.py
  - tests/test_session.py
  - tests/test_events.py
  - docs/BACKLOG.md
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - tests/fixtures/watch-golden.txt
  - saffron/phases/package.py
  - saffron/cli.py
  - saffron/ledger.py
  - saffron/cell/runtime.py
  - saffron/cell/worktree.py
  - saffron/cell/proxy.py
  - saffron/report/**
  - saffron/gates/**
  - saffron/events.py
  - images/**
acceptance:
  - claim: >-
      Every `watch(...)` in `saffron/phases/implement.py`,
      `saffron/phases/review.py` and `saffron/phases/rebut.py` is an
      `emit(<Event>)`, and none of those three carries a `watch` parameter.
    witness: tests/test_events.py::test_no_phase_this_spec_owns_still_takes_a_watch
  - claim: >-
      Both `_phase_watch` constructions in `saffron/cell/session.py` are gone,
      and the adapter with them. It exists only for these three phases —
      `saffron/phases/package.py` is called from `saffron/cli.py`, never from
      the supervisor — so nothing else keeps it alive.
    witness: tests/test_events.py::test_the_supervisor_no_longer_adapts_events_to_prose
  - claim: >-
      `Agent.event` carries the parsed cell event dict again. `SA-0030`'s
      adapter is handed a string `_consume` already rendered, so every per-turn
      line lands in `Agent.detail` as prose and `Agent.event` is permanently
      `None` — the inverse of what `events.Agent` documents. Emitting at the
      call site is the only place the dict still exists.
    witness: tests/test_events.py::test_a_driven_agent_turn_logs_the_event_not_its_rendering
  - claim: >-
      `implement._describe` is deleted, not left delegating, and its behaviour
      is served by `events.describe`. `SA-0040`'s parity test keeps its node id
      and has its body rewritten against `events.describe` — `census` fails any
      test collected at base and absent at head and has no `touches` override,
      so deleting it is an unrepairable gate failure, and keeping `_describe`
      alive to satisfy it leaves this criterion silently unmet.
    witness: tests/test_events.py::test_the_duplicated_agent_renderer_still_matches_its_original
    preserves: true
  - claim: >-
      The `agent: (raw)` path survives exactly: a line that is not JSON came
      from a process sharing the runner's stdout inside an untrusted cell, and
      is shown, truncated, and never parsed as an event.
    witness: tests/test_implement.py::test_a_raw_line_is_shown_and_never_read_as_an_event
  - claim: >-
      An unknown cell event kind reaches the log and the terminal without
      raising.
    witness: tests/test_events.py::test_an_unknown_cell_event_kind_does_not_raise
  - claim: >-
      No `watch=` remains in any test file this spec owns. The parent required
      this of all seven; `SA-0042` claims the three it owns.
    witness: tests/test_events.py::test_no_test_this_spec_owns_still_passes_a_watch
  - claim: >-
      The terminal output does not change, asserted against
      `tests/fixtures/watch-golden.txt` line for line.
    witness: tests/test_events.py::test_watch_output_matches_the_golden_fixture
    preserves: true
  - claim: >-
      `run_one_cell` stays callable with no `emit` argument and still prints.
    witness: tests/test_events.py::test_run_one_cell_with_no_emit_argument_still_prints
    preserves: true
budget_usd: 14
max_attempts: 4
max_turns: 120
risk: elevated
---

## Context
`SA-0031` tried to migrate all four phase modules, `saffron/cli.py` and the
supervisor's hand-offs in one spec. It died at 141 turns of 140 and $19.17 of
an $18.00 budget with six commits and red gates, and pushed no branch. Its
exported patch is in the batch tree; this spec does not inherit it.

This is the first of two children. Measured against `saffron/SA-0030`'s head,
2026-09-01: `implement.py` **5** `watch(...)` call sites, `review.py` **1**,
`rebut.py` **1** — seven. `saffron/cell/session.py` hands those three a
string-taking callable at **8** keyword sites and builds `_phase_watch` twice,
at the `plan_checkpoint` and `_drive_cell` constructions.

**The adapter dies here, not in the sibling.** It exists only for these three
phases: `package.py` is called from `cli.py`, outside `run_one_cell`, and never
receives the supervisor's adapter at all.

## Problem
- **`Agent.event` is always `None`.** `SA-0030`'s contract lens raised it and it
  is correct. `_phase_watch` receives a string `implement._consume` has already
  rendered with `_describe`, so the structured record `events.Agent` documents
  is flattened to prose before the host ever sees it. The dict cannot be
  recovered downstream; it has to be emitted where it still exists.
- **Two renderers exist for one thing.** `implement._describe` renders the
  cell's events and `events.describe` renders the host's. `SA-0040` proved they
  agree today over eleven shapes; nothing keeps them agreeing.
- **The adapter is a seam with no owner.** It exists so `SA-0030` could land
  without touching four more files.

## Out of scope
**`saffron/phases/package.py` and `saffron/cli.py`.** Both are `forbidden` and
both are `SA-0042`'s. PACKAGE's eight call sites cannot reach the log until
`cli.py` builds the fan-out — `package()` runs outside `run_one_cell` — so they
ship together, and neither belongs here.

**Changing any message.** If a line reads badly it reads exactly that way
afterwards. The golden fixture is the point.

**Any new event kind.** `SA-0040` proved the nine cover all 64 families;
`events.py` is `forbidden`. A call site that does not fit is a finding for the
pull request body.

## Notes for the agent
**The golden fixture is `forbidden`.** If it does not match, the migration is
wrong — `SA-0024` makes editing it a gate failure rather than a broken promise.
The harness in `tests/test_session.py` is fair game; the recording is not.

**Every criterion above names a witness, and the `criteria` gate checks it.**
A witness must not exist, or must be failing, at `base_sha`, and must pass at
head — except the two marked `preserves`, which must be green at both. Write
the test first; that is the gate's own contract, not a style preference.

**`tests/test_session.py` carries `agent_says`**, added by `SA-0030`'s review
round so a test can observe the supervisor handing the adapter over. It is what
`test_the_supervisor_hands_the_adapter_to_the_agent_it_calls` uses; when the
adapter goes, that test becomes the witness for its replacement rather than
being deleted.

**`tests/test_agent_runner.py` is `cell`-marked, and nothing automatic will
check it.** `addopts = "-m 'not cell'"` excludes it from `make check`, from the
`tests` gate, and from the `criteria` gate's collection — so a witness inside it
could never be collected and would block every attempt, which is why this is a
note and not a criterion. Its one `watch=` site calls `implement.run_agent`
with the signature this spec removes. Migrate it, run
`uv run pytest -m cell tests/test_agent_runner.py` by hand, and say in the pull
request body that you did.

Commit after each coherent step. Uncommitted work dies with the cell.
