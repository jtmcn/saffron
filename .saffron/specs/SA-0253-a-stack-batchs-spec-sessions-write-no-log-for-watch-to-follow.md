---
id: SA-0253
title: A stack batch's spec review and spec writer write no log, so `saffron watch` shows nothing while they run
type: bug
priority: 2
depends_on: [SA-0245]
estimated_lines: 81
estimate_measured: true
touches:
  - saffron/cli.py
  - tests/test_cli.py
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
  - saffron/watch.py
  - saffron/events.py
  - saffron/batch.py
  - saffron/spec_review.py
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/task.py
  - saffron/ledger.py
  - saffron/repos/**
  - saffron/phases/**
  - saffron/cell/**
  - saffron/gates/**
  - saffron/record/**
  - saffron/report/**
  - tests/test_watch.py
  - tests/test_batch.py
  - tests/test_sigterm.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 14
max_attempts: 3
max_turns: 100
acceptance:
  - claim: >-
      Both spec session adapters a stack batch builds, `_stack_review` and
      `_stack_revise`, write every event their agent emits to an
      `events.jsonl` directly under `out_dir`. The review's directory is
      `<spec id>.spec-review` and the writer's is `<spec id>.spec-write`,
      named for the candidate whatever the layer. A later round of either
      appends to the same log, so the next round's export deletes no line
      of it. `watch.follow_every_task` over `out_dir` then yields each event
      prefixed with that directory's name. Each event still prints on the
      batch's stdout as `describe` renders it, as it does today. The
      witness drives both adapters through the follower. It runs two
      review rounds and two writer rounds of one spec, each with and
      without a spec text, plus a second spec's review on a layer. The
      writer's second round runs on a layer too. Every agent call emits
      two events. The witness asserts the follower's exact ten lines and
      the ten printed lines, in order.
    witness: tests/test_cli.py::test_a_stack_batchs_spec_sessions_reach_the_follower_by_phase_across_rounds
    wrong_versions:
      - "`_stack_review` given a log and `_stack_revise` left on `run_agent`'s print default."
      - "`_stack_revise` given a log and `_stack_review` left on `run_agent`'s print default."
      - A log written inside the export directory, `out_dir / "spec-review" / <spec id>`, which the follower never lists and each round deletes.
      - The export moved into the log's own directory, so the second review round deletes the first round's lines.
      - The log file removed or truncated at the start of each session.
      - Both adapters writing to one directory, such as the writer logging under `.spec-review`.
      - One directory per phase with no spec id in its name, such as `out_dir / "spec-review"`.
      - The directory named for the layer's spec when a layer is given, for either adapter.
      - An emit that appends to the log and prints nothing, which drops the session from the batch's own log.
      - Rendered `describe` lines written to the file in place of events, which `read_log_since` cannot parse.
  - claim: >-
      `_stack_review` still exports `.saffron/` at the pinned base into
      `out_dir / "spec-review" / <spec id>` and mounts that as the gates
      directory, as it does today.
    witness: tests/test_cli.py::test_a_spec_review_fills_cores_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head
    preserves: true
  - claim: >-
      `_stack_revise` still exports `.saffron/` at the pinned base into
      `out_dir / "spec-write" / <spec id>` and mounts that as the gates
      directory, as it does today.
    witness: tests/test_cli.py::test_a_spec_revision_fills_cores_writer_prompt_from_its_base_policy_in_a_cell_at_its_predecessors_head
    preserves: true
---

## Context

Backlog item **b-4e1b6d**, which cites `DESIGN.md` §4.3. The event log is
§4.7. `b-2d09de` gave `saffron watch` its form with no spec id
(`SA-0197`). All line numbers below are at `958db033`.

**The spec review.** `_stack_review` builds the stack batch's review
adapter (`saffron/cli.py:897`). Each call hands `export_saffron_dir`
the destination `out_dir / "spec-review" / candidate.spec.id`
(`saffron/cli.py:919-921`). Its `agent = partial(` binds
`implement.run_agent` to a spec id and a timeout, with no `emit`
(`saffron/cli.py:951-955`).

**The spec writer.** `_stack_revise` builds the revision adapter the same
way (`saffron/cli.py:971`). It exports into `out_dir / "spec-write" / <spec
id>` (`saffron/cli.py:1005-1007`). Its agent is the same `partial` with no
`emit` (`saffron/cli.py:1035-1039`). `_batch` builds both with `main`'s
`out_dir` (`saffron/cli.py:1685-1686`). For a batch that is
`<home>/batches/v0` (`saffron/cli.py:235-236`).

**Where the events go now.** `run_agent`'s `emit` defaults to
`print(describe(event))` (`saffron/phases/implement.py:266`). Neither
`run_spec_review` nor `run_spec_writer` passes an `emit` in its
`first = agent(` and `got = agent(` calls
(`saffron/spec_review.py:358`, `:401`, `:676`, `:719`). So every event of
both sessions reaches the batch's stdout and no file.

**What the follower reads.** `follow_every_task` lists `root` on every
poll. It reads `<root>/<child>/events.jsonl` for each directory one level
down (`saffron/watch.py:236`, `:258-266`). It prefixes each line with the
directory's name (`saffron/watch.py:266`). A directory that joins after the
start reads from offset 0 (`saffron/watch.py:260`). `saffron watch` with no
spec id runs `for line in follow_every_task(` over `out_dir`
(`saffron/cli.py:1950`). The directory
`out_dir / "spec-review"` holds no `events.jsonl`, so it renders nothing.

**The export deletes its destination.** `export_saffron_dir` calls
`shutil.rmtree(dest, ignore_errors=True)` before it writes
(`saffron/repos/mirror.py:196`). Each review or revision round calls it
again for the same spec. A stack batch calls `review` per round
(`saffron/batch.py:562`) and `revise` per revision (`saffron/batch.py:688`).

**How a task writes its log.** `EventLog(task_dir)` appends one flushed
line per event to `task_dir / "events.jsonl"`. It creates the directory on
the first write and never raises (`saffron/events.py:404-447`). When no
`emit` is passed, `run_task` binds one that prints `describe(event)` when
it is not empty and then appends (`saffron/task.py:473-491`).

## Problem

During the first live `saffron batch --stack` on 2026-10-05, `saffron
watch` printed nothing for several minutes. `SA-0208`'s spec review wrote
377 agent lines to the batch's stdout in that time. No log existed for the
follower to read. The spec-writing session has the same shape.

Give each of the two adapters an `emit` that prints each event as today
and appends it to an `EventLog`. The review's log directory is `out_dir /
f"{candidate.spec.id}.spec-review"`. The writer's is `out_dir /
f"{candidate.spec.id}.spec-write"`. A followed line then reads
`SA-0208.spec-review agent: ...`, which names the spec and the phase.

**Why these names.**

- Directly under `out_dir`, so `follow_every_task` lists them.
- Outside `out_dir / "spec-review" / <spec id>`, which each round deletes.
- Apart from `out_dir / <spec id>`, the task's own log. `follow` opens
  that log at its newest `Ceilings`, through `_since_newest_task`
  (`saffron/watch.py:118-133`, `:215-216`).
  A spec session writes no `Ceilings`, so its lines would fall inside the
  span of whichever task ran before it.
- In name order each sorts right after its task's directory, so one
  spec's lines sit together in a poll.
- `cell-watch` skips each directory that fails `SPEC.test(spec)`, and
  `SPEC` is `^SA-\d+$` (`.claude/skills/cell-watch/hooks/register.tsx:15`,
  `:38`). Its follow mode then never picks a spec session as the newest
  task.

## Out of scope

- **The follow-up writer.** `_stack_follow_ups` binds its writer's
  `implement.run_agent` to `spec_id=f"follow-up-{origin.spec_id}"`, with no
  `emit` (`saffron/cli.py:1151-1155`). It runs after the end review, for a
  spec no queue holds yet. It stays
  print only.
- **The end review's lenses.** `_stack_end_review` binds its
  `implement.run_agent` with no `emit` either (`saffron/cli.py:690-694`). It stays print only.
- **The cell's own lines.** `layer_cell` passes `print(detail)` as its
  cell up and cell down notes (`saffron/end_review.py:610`, `:639`). They are not agent events
  and stay out of the log.
- **`saffron/watch.py`.** The follower reads any directory as it stands.
  Its docstrings say "task directory", and they stay as they are.
- **A warning on a failed write.** `run_task` prints a warning holding
  `refused a write` on its log's first failure (`saffron/task.py:486-491`).
  The new emit needs none.
- **`DESIGN.md` §4.7.** Its first sentence says each spec has one
  `events.jsonl`. The operator edits it by hand.

## Notes for the agent

**An edit with no mutant.** The change binds a new `emit` in two existing
`partial` calls. No text there forces its spelling, so criterion 1 declares
a witness and no mutant, and `witness` reports `skip` for it. Criteria 2
and 3 name tests that pass now.

**One helper.** Write one function in `saffron/cli.py` that takes a log
directory and returns the emit. Both adapters call it once per call of
their own callable, with the candidate's spec id. Import `EventLog`,
`Event` and `describe` from `saffron.events`, the module that defines
them. Leave each adapter's export path, prompt and timeout as they are.

**The witness.** Add it to `tests/test_cli.py` beside
`test_a_review_reads_a_recorded_text_and_a_revision_starts_from_the_queued_file`.
Reuse `_spec_session_rig` with `".saffron/specs/SY-1-x.md"`, so a writer
handed `None` finds a queued file. Import `watch` and `Agent` inside the
test body.

- Fake `implement.run_agent` with the keyword `emit` defaulting to a
  module-level `def` that prints `describe(event)`. That is
  `run_agent`'s own default, so at base the fake prints and writes no log.
- Each fake call records its spec id. It emits two `Agent` text events,
  `call <n>a` then `call <n>b`, where `<n>` counts calls from 1. It
  returns `rate_limit_status="rejected"`, as the rig's first test does, so
  each session makes one call.
- Create `rig.out_dir`, then build both adapters. Drive
  `watch.follow_every_task(rig.out_dir, sleep=...)` to its end with a
  `sleep` that counts its calls.
- The first sleep runs `review(SY-1, None)`, then `revise(SY-1, None, None,
  "rt")`, then `review(SY-1, None, spec_text="revised\n")`. The second runs
  `revise(SY-1, SY-7, "given\n", "rt")`, then `review(SY-2, SY-7)`. Both
  return `True`, and the third returns `False`.
- Assert the calls' spec ids are `SY-1` four times, then `SY-2`.
- Assert the follower's list exactly. It is `SY-1.spec-review` with calls
  1 and 3, then `SY-1.spec-write` with call 2, from the second poll. Then
  `SY-1.spec-write` with call 4 and `SY-2.spec-review` with call 5, from
  the third. Each call gives its `a` line, then its `b` line.
- Read `capsys` and keep the lines that start with `agent: `. Assert they
  are calls 1 to 5, `a` then `b` each, in call order.

A prototype of this change passed the witness and the two `preserves`
tests. `tests/test_cli.py`, `tests/test_batch.py` and `tests/test_watch.py`
passed on it in full. With the source at base the witness failed on an
empty follower list. Each wrong version under criterion 1 failed it
(measured 2026-10-07 on the host).

Commit after the witness passes.
