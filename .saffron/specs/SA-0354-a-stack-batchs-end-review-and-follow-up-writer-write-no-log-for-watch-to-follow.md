---
id: SA-0354
title: A stack batch's end review and follow-up writer write no log, so `saffron watch` shows nothing at the end of a night
type: feature
priority: 2
depends_on: [SA-0339]
estimated_lines: 96
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
  - saffron/end_review.py
  - saffron/follow_up.py
  - saffron/spec_review.py
  - saffron/qualify.py
  - saffron/finish.py
  - saffron/commit_review.py
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
  - tests/test_end_review.py
  - tests/test_follow_up.py
  - tests/test_scheduler.py
  - tests/test_queued_specs.py
budget_usd: 28
max_attempts: 3
max_turns: 130
risk: standard
acceptance:
  - claim: >-
      Both end-of-night adapters a stack batch builds write every event
      their agent emits to an `events.jsonl` directly under `out_dir`.
      `_stack_end_review` hands `end_review.run_end_review` an `emit` whose
      directory is `<batch key>.end-review`. The agent that
      `_stack_follow_ups` binds for its writer has an `emit` whose directory
      is `<batch key>.follow-ups`. A second end review or follow-up pass for
      the same batch key appends to the same log, so the export that each
      pass deletes takes no line of it. `watch.follow_every_task` over
      `out_dir` then yields each event prefixed with that directory's name.
      Each event still prints on stdout as `describe` renders it. The
      witness drives the end review through `review.run_lens` for the join
      lens and each of `end_review.END_LENSES`, so the `emit` reaches the
      agent the way a lens hands it over. It runs one end review and one
      follow-up pass for batch `7`, then a second of each for `7`, then one
      of each for `8`. Every agent call emits one event. The witness asserts
      the follower's exact twelve lines and the twelve printed lines, in
      order.
    witness: tests/test_cli.py::test_a_stack_batchs_end_review_and_follow_up_writer_reach_the_follower_by_batch
    wrong_versions:
      - "`_stack_follow_ups` given a log and `_stack_end_review` left on `run_end_review`'s print default."
      - "`_stack_end_review` given a log and `_stack_follow_ups`'s writer left on `run_agent`'s print default."
      - "The end review's `emit` bound into its `partial(implement.run_agent, ...)` rather than passed to `run_end_review`, which `run_lens` overrides with its own `emit` keyword."
      - "A log written inside the export directory, `out_dir / \"end-review\" / <batch key>` or `out_dir / \"follow-ups\" / <batch key>`, which the follower never lists and each pass deletes."
      - The log file removed or truncated each time an adapter builds its `emit`, so the second pass for batch `7` loses the first pass's lines.
      - Both adapters writing to one directory, such as the follow-up writer logging under `.end-review`.
      - One directory per kind with no batch key in its name, such as `out_dir / "end-review-log"`.
      - "Each event routed to `out_dir / event.spec_id`, the way `_record_events` routes a fact, which names the directory `end-review-7` or `follow-up-SY-1`."
      - The follow-up writer's directory named for the origin layer's spec id rather than the batch key.
      - An emit that appends to the log and prints nothing, which drops the session from the batch's own stdout.
      - Rendered `describe` lines written to the file in place of events, which `read_log_since` cannot parse.
  - claim: >-
      `saffron batch --stack` still builds `_stack_end_review` and
      `_stack_follow_ups` with `main`'s own `out_dir`, the root `saffron
      watch` with no spec id follows, as it does today. The witness asserts
      both builds' `out_dir` under a `--home` it names.
    witness: tests/test_cli.py::test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer
    preserves: true
    wrong_versions:
      - "`_batch` builds `_stack_end_review` with an `out_dir` other than `main`'s, such as `out_dir / \"end-review\"`."
  - claim: >-
      `saffron finish <batch id>` still builds `_stack_end_review` and
      `_stack_follow_ups` with `main`'s own `out_dir`, the same root, as it
      does today. The witness asserts both builds' `out_dir` under a
      `--home` it names.
    witness: tests/test_cli.py::test_saffron_finish_runs_a_deferred_stack_batchs_tail_on_its_own_id_at_its_pinned_base
    preserves: true
    wrong_versions:
      - "`_finish` builds `_stack_end_review` with an `out_dir` other than `main`'s, such as `out_dir / \"finish\"`."
---

## Context

Backlog item **b-e7b6a2**, which cites `DESIGN.md` §4.7. `SA-0253` (#821)
did the same for a stack batch's spec review and spec writer, and named
these two sessions out of its scope. ADR 7 is the stack batch. All line
numbers below are at `c8e8f6e6`, SA-0339's packaged head.

**Other work on these files.** `SA-0338` and `SA-0339` are queued and
touch `saffron/cli.py`, and `SA-0338` touches `tests/test_cli.py`. Spec
pull requests #1042 (`SA-0350`) and #1043 (`SA-0352`) are open and also
touch `saffron/cli.py`. Any of them can move the `saffron/cli.py` lines
cited here. None of the four specs names `_stack_end_review` or
`_stack_follow_ups`.

**The end review.** `_stack_end_review` builds the stack batch's
`end_review` callable (`saffron/cli.py:940`). Each call exports `.saffron/`
into `out_dir / "end-review" / batch_key` (`saffron/cli.py:954-956`). Its
agent is `stop_on_rejected(partial(implement.run_agent, ...))` with the spec
id `end-review-<batch key>` and no `emit` (`saffron/cli.py:960-966`). Its
call to `end_review.run_end_review` passes no `emit`
(`saffron/cli.py:977-991`). So `run_end_review` keeps its default,
`print(describe(event))` (`saffron/end_review.py:698`). It threads that
`emit` to the join lens and to each layer's lenses
(`saffron/end_review.py:730`, `:747`, `:524`, `:470`, `:404`, `:651`).
`review.run_lens` passes it to the agent as a keyword on every call
(`saffron/phases/review.py:321`). A keyword given at the call wins over one
bound in a `partial`. So an `emit` bound into the agent's `partial` never
reaches a lens.

**The follow-up writer.** `_stack_follow_ups` builds the `follow_ups`
callable (`saffron/cli.py:1674`). Each call exports into
`out_dir / "follow-ups" / batch_key` (`saffron/cli.py:1706-1708`). Its
`write` binds `partial(implement.run_agent, ...)` with the spec id
`follow-up-<origin spec id>` and no `emit` (`saffron/cli.py:1747-1751`).
It hands that agent to `spec_review.run_spec_writer`
(`saffron/cli.py:1760`), which calls it with no `emit`
(`saffron/spec_review.py:676`). So `run_agent`'s default prints each event
(`saffron/phases/implement.py:250`) and no file holds it. The `emit=print`
handed to `follow_up.write_follow_ups` takes progress strings, not events
(`saffron/cli.py:1804`, `saffron/follow_up.py:240`).

**Both commands.** `_batch` builds `_stack_end_review` and
`_stack_follow_ups` with `main`'s `out_dir` when the batch is not deferred
(`saffron/cli.py:2389-2391`, `:2415-2422`). `_finish` builds both with the
same `out_dir` (`saffron/cli.py:2661-2663`, `:2674-2681`). Neither command takes
`--out`, so for either that is `<home>/batches/v0`
(`saffron/cli.py:344-345`). `saffron watch` with no spec id runs
`follow_every_task` over that same `out_dir` (`saffron/cli.py:429`,
`:3121-3128`).

**What the follower reads.** `follow_every_task` lists `root` on every
poll and reads `<root>/<child>/events.jsonl` for each directory one level
down. It prefixes each line with the directory's name. A directory that
joins after the start reads from offset 0 (`saffron/watch.py:254-268`).
`read_log_since` returns nothing for a directory with no `events.jsonl`
(`saffron/events.py:709-713`).

**The export deletes its destination.** `export_saffron_dir` calls
`shutil.rmtree(dest, ignore_errors=True)` before it writes
(`saffron/repos/mirror.py:220`).

**The helper `SA-0253` left.** `_spec_session_emit(log_dir)` returns
`partial(_default_emit, log=EventLog(log_dir))` (`saffron/cli.py:1259-1263`).
`_default_emit` prints `describe(event)` when it is not empty, then
appends the event (`saffron/cell/session.py:125-136`). `EventLog` creates
its directory on the first write (`saffron/events.py:556`).

## Problem

A stack night's end runs the end review's lenses and then the follow-up
writer. Both print their events to the batch's stdout alone. `saffron
watch` follows the batch tree, so it shows nothing for the last stretch of
a night. Before #821 the spec sessions looked the same.

Give `_stack_end_review` an `emit` to hand `run_end_review`, and give the
follow-up writer's agent one too. Each prints as today and appends to an
`EventLog`. The end review's directory is `out_dir /
f"{batch_key}.end-review"`, and the follow-up writer's is `out_dir /
f"{batch_key}.follow-ups"`. A followed line then reads `7.end-review agent:
...`, which names the batch and the session kind.

**Why these names.** They follow `SA-0253`'s rule. Each export directory's
two parts, `end-review/<batch key>` and `follow-ups/<batch key>`, become
one directory, `<batch key>.<kind>`, directly under `out_dir`.

- Directly under `out_dir`, so `follow_every_task` lists them.
- Outside the export, which each pass deletes.
- One directory per kind per batch, since both sessions belong to the
  batch rather than to one spec. Every lens of one end review shares a
  log, and so does every follow-up spec one pass writes.
- `cell-watch` skips each directory that fails `^SA-\d+$`
  (`.claude/skills/cell-watch/hooks/register.tsx:15`, `:38`). So its
  follow mode never picks either directory as the newest task.

## Out of scope

- **Which lens or layer a line belongs to.** The prefix names the batch
  and the kind. One end review runs its join lens, then each layer's
  lenses in a loop, one session at a time (`saffron/end_review.py:716-749`,
  `:382-406`). So their lines do not interleave.
- **`saffron draft`'s writer.** `_draft_adapters`' `write` binds its agent
  with no `emit` (`saffron/cli.py:1566-1570`). It is an attended command
  and stays print only.
- **`saffron review`'s lenses** (`saffron/commit_review.py:259`). That
  command is attended too.
- **Progress strings.** `write_follow_ups` prints its own lines through
  `emit=print`. `layer_cell` prints the cell up and cell down lines
  (`saffron/end_review.py:800`, `:819`, `:831`). Neither is an agent event,
  and both stay out of the log.
- **`saffron/watch.py`.** The follower reads any directory as it stands.
- **`DESIGN.md` §4.7.** It is protected. The spec pull request carries the
  hand edit the notes name.

## Notes for the agent

**An edit with no mutant.** The change passes a new `emit` in two existing
calls. No text there forces its spelling, so criterion 1 declares a
witness and no mutant, and `witness` reports `skip` for it. Criteria 2 and
3 name tests that pass now.

**The change.** Reuse `_spec_session_emit` for both, and widen its
docstring to say so. Pass the end review's `emit` to `run_end_review`
itself, never into the agent's `partial`, for the reason the Context gives.
Bind the follow-up writer's `emit` in its existing `partial`, as
`_stack_review` does. Leave each adapter's export path, prompt, spec id and
timeout as they are.

**The witness.** Add it to `tests/test_cli.py` right after
`test_a_stack_batchs_spec_sessions_reach_the_follower_by_phase_across_rounds`.
Import `watch` and `Agent` inside the test body.

- Reuse `_spec_session_rig(tmp_path, monkeypatch)` for the mirror, the
  checkout and the cell fakes. Create `rig.out_dir`. Build a `Ledger` at
  `tmp_path / "ledger.db"` and `upsert_repo` it at the pinned url, so the
  follow-up adapter resolves a repo id.
- Fake `implement.run_agent` as the neighbouring test does, with `emit`
  defaulting to `_default_spec_session_emit`. Each call records its spec
  id and emits one `Agent` text event, `call <n>`, where `<n>` counts calls
  from 1. It returns `rate_limit_status="rejected"`.
- Fake `end_review.run_end_review` with a keyword `emit` that also
  defaults to `_default_spec_session_emit`. For each lens in `("join",
  *end_review.END_LENSES)` it calls `review.run_lens` with the `agent` and
  `emit` it was given, inside `pytest.raises(session.RateLimited)`, since
  `stop_on_rejected` raises on a rejected call. It returns an empty
  `StackReview`.
- Fake `follow_up.write_follow_ups` to call its `write` once, with
  `_follow_up_group("k-top", "src/a.py", ["one"])`. Patch `cli.writer_left`
  to return a float. Hand each follow-up pass a `StackReview` whose one
  layer is `k-top`, with `fields` naming `SY-1` at `rig.base_sha`.
- Drive `watch.follow_every_task(rig.out_dir, sleep=...)` to its end. The
  first sleep runs the end review and the follow-ups for `"7"`. The second
  runs both for `"7"` again, then both for `"8"`. Both return `True`, and
  the third returns `False`.
- Assert the spec ids: `end-review-7` three times, `follow-up-SY-1`, the
  same four again, then `end-review-8` three times and `follow-up-SY-1`.
- Assert the follower's list exactly. It is `7.end-review` calls 1 to 3
  and `7.follow-ups` call 4 from the second poll. From the third it is
  `7.end-review` calls 5 to 7, `7.follow-ups` call 8, `8.end-review` calls
  9 to 11 and `8.follow-ups` call 12.
- Read `capsys` and keep the lines that start with `agent: `. Assert they
  are calls 1 to 12 in call order.

**The two `preserves` witnesses.** Neither asserts the end review's
`out_dir` today, and the finish test asserts neither build's. Extend them.

- In `test_a_stack_batch_holds_the_writer_share_and_passes_its_follow_up_writer`,
  also patch `cli._stack_end_review` with a fake that records its keywords
  and returns a callable. Assert its one build's `out_dir` is
  `home1 / "batches" / "v0"`, beside the follow-up build's existing
  assertion.
- In `test_saffron_finish_runs_a_deferred_stack_batchs_tail_on_its_own_id_at_its_pinned_base`,
  assert `review_kwargs["out_dir"]` and `follow_ups_kwargs["out_dir"]` are
  `fixture.out_dir`.

A prototype of this change passed the witness and both extended tests.
`tests/test_cli.py`, `tests/test_batch.py` and `tests/test_watch.py` passed
on it in full. With the source at base the witness failed on an empty
follower list, and the extended tests still passed. Each wrong version
under the three criteria failed its witness (measured 2026-11-07 on the
host).

**For the operator, not the cell.** The spec pull request adds one
sentence to `DESIGN.md` §4.7, after the sentence that names
`SA-NNNN.spec-review`. It reads: "Its end review and follow-up writer log
in `<batch id>.end-review` and `<batch id>.follow-ups`, one each per batch
(`SA-0354`)."

Commit after the witness passes.
