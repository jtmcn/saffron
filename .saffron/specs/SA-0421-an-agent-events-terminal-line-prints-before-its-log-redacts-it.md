---
id: SA-0421
title: "An `Agent` event's terminal line prints before its log redacts it, so the cell's token reaches the batch log file"
type: bug
priority: 2
estimated_lines: 15
estimate_measured: true
touches:
  - saffron/events.py
  - saffron/cell/session.py
  - saffron/task.py
  - tests/test_credentials.py
  - tests/test_task.py
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
  - saffron/credentials.py
  - saffron/cli.py
  - saffron/commit_review.py
  - saffron/end_review.py
  - saffron/spec_review.py
  - saffron/phases/**
  - saffron/gates/**
  - saffron/agents/**
  - tests/test_events.py
  - tests/test_session.py
  - tests/test_package.py
  - tests/test_queued_specs.py
  - tests/test_scheduler.py
budget_usd: 48
max_attempts: 3
max_turns: 260
acceptance:
  - claim: >-
      `session._default_emit` prints each `Agent` event as its log redacted
      it, with the token that log holds, in every field `describe` renders.
      The witness emits five events through a log handed the cell's token.
      A parsed `text` event carries the token and a GitHub token. A raw
      line carries the token and an AWS access key id. A `detail` carries
      the token and an Anthropic API key. Two raw lines start the token, and
      then a GitHub token, ten characters before `describe`'s 160-character
      cut. No printed line holds the token, its first ten characters, any of
      the three shapes or `ghp_`. Each line equals `describe` of the event
      the log read back. Handed `None`, the log prints the token and still
      redacts the three shapes. A log whose `events.jsonl` is a directory refuses
      every write and still prints each line redacted. A clean `text` event
      over `BOUND_CHARS` prints the line `describe` gives the event as
      emitted, while the log stores it bounded.
    witness: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
    positive_case: >-
      Handed the token, every line names its redacted kinds in its
      `(redacted: ...)` suffix, the cell's own token in the first four.
      Handed `None`, the token's first ten characters print in the same
      four lines.
    wrong_versions:
      - "`_default_emit` prints `describe(event)` before the log redacts it, as at base."
      - "`EventLog.append` returns the event after the size bound, so a clean event over `BOUND_CHARS` prints as `agent: (bounded, ...)`."
      - "`EventLog.append` returns the event as it was handed when its write is refused."
      - "`_default_emit` passes the line `describe` rendered through `credentials.redact`, so a credential cut at 160 characters keeps its first ten."
      - "`_default_emit` prints a copy redacted with no token, so the token prints."
      - "`_default_emit` redacts `line` and `detail` and prints a parsed `event` dict as it came."
    covers:
      - set: the fields `describe` renders for an `Agent` event
        members:
          - member: a parsed `event` dict
            driven_by: "`_default_emit` redacts `line` and `detail` and prints a parsed `event` dict as it came."
          - member: a raw `line`
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
          - member: a host-authored `detail`
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
      - set: the credentials an event carries
        members:
          - member: the cell's own token
            driven_by: "`_default_emit` prints a copy redacted with no token, so the token prints."
          - member: "a listed shape: a GitHub token, an AWS access key id or an Anthropic API key"
            driven_by: "`_default_emit` prints `describe(event)` before the log redacts it, as at base."
      - set: where a credential sits against the 160-character cut
        members:
          - member: inside the cut
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
          - member: straddling the cut
            driven_by: "`_default_emit` passes the line `describe` rendered through `credentials.redact`, so a credential cut at 160 characters keeps its first ten."
      - set: the token the log holds
        members:
          - member: a token
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
          - member: "`None`"
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
      - set: the log's write
        members:
          - member: written
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
          - member: refused
            driven_by: "`EventLog.append` returns the event as it was handed when its write is refused."
      - set: the event's size against `BOUND_CHARS`
        members:
          - member: under the bound
            driven_by: tests/test_credentials.py::test_the_default_emitters_line_carries_no_credential
          - member: over the bound
            driven_by: "`EventLog.append` returns the event after the size bound, so a clean event over `BOUND_CHARS` prints as `agent: (bounded, ...)`."
  - claim: >-
      The `emit` `run_task` builds when handed none prints each `Agent`
      event as its log redacted it, with the token `run_task` was handed, in
      every field `describe` renders. The witness has the `run_one_cell`
      double emit the same five events the first criterion names. Handed the
      token, no printed `agent:` line holds the token, its first ten
      characters, any of the three shapes or `ghp_`. The printed `agent:`
      lines equal `describe` of each `Agent` event the task's own
      `events.jsonl` holds, in order. Handed `None`, the token prints and
      the three shapes are still redacted.
    witness: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
    positive_case: >-
      Handed the token, every `agent:` line names its redacted kinds, the
      cell's own token in the first four. Handed `None`, the token's first
      ten characters print in the same four lines.
    wrong_versions:
      - "`run_task`'s `emit` prints `describe(event)` before the log redacts it, as at base."
      - "`run_task`'s `emit` passes the line `describe` rendered through `credentials.redact`, so a credential cut at 160 characters keeps its first ten."
      - "`run_task`'s `emit` prints a copy redacted with no token, so the token prints."
      - "`run_task`'s `emit` redacts `line` and `detail` and prints a parsed `event` dict as it came."
    covers:
      - set: the fields `describe` renders for an `Agent` event
        members:
          - member: a parsed `event` dict
            driven_by: "`run_task`'s `emit` redacts `line` and `detail` and prints a parsed `event` dict as it came."
          - member: a raw `line`
            driven_by: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
          - member: a host-authored `detail`
            driven_by: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
      - set: the credentials an event carries
        members:
          - member: the cell's own token
            driven_by: "`run_task`'s `emit` prints a copy redacted with no token, so the token prints."
          - member: "a listed shape: a GitHub token, an AWS access key id or an Anthropic API key"
            driven_by: "`run_task`'s `emit` prints `describe(event)` before the log redacts it, as at base."
      - set: where a credential sits against the 160-character cut
        members:
          - member: inside the cut
            driven_by: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
          - member: straddling the cut
            driven_by: "`run_task`'s `emit` passes the line `describe` rendered through `credentials.redact`, so a credential cut at 160 characters keeps its first ten."
      - set: the token `run_task` is handed
        members:
          - member: a token
            driven_by: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
          - member: "`None`"
            driven_by: tests/test_task.py::test_run_tasks_default_emit_prints_no_credential
  - claim: >-
      A cell driven through `run_one_cell`'s default `emit` still prints the
      lines its `events.jsonl` replays.
    witness: tests/test_events.py::test_events_jsonl_reproduces_what_the_terminal_printed
    preserves: true
  - claim: >-
      `run_task`'s `emit` still warns once when its log refuses the first
      write, and the log holds only the events the cell emitted.
    witness: tests/test_task.py::test_a_log_that_failed_on_its_first_write_still_warns
    preserves: true
---

## Context

Backlog item **b-0f5493**, filed from `SA-0417`'s first spec review. It
cites `DESIGN.md` §5.7. Every line below was read at `e7b70e7e`.

**What the log redacts.** `EventLog.append` redacts an `Agent` event's
`event`, `line` and `detail` (`saffron/events.py:479-501`). It uses
`redact_nested` and `redact` with the token the log was built with. It then bounds
an oversized `event` dict (`saffron/events.py:502-512`) and writes the line.
It returns nothing, and on a refused write it sets `failed`
(`saffron/events.py:520-524`).

**What the terminal prints.** Two emitters print before they append.

- `session._default_emit` prints `describe(event)`, then calls
  `log.append(event)` (`saffron/cell/session.py:128-139`). `cli.py`'s
  `_spec_session_emit` builds it for every spec review, spec writer, end
  review and follow-up writer (`saffron/cli.py:1370-1375`). `run_one_cell`
  builds it when handed no `emit` (`saffron/cell/session.py:1163-1165`).
- Handed no `emit`, `run_task` builds a closure. It prints
  `describe(event)`, then appends the event (`saffron/task.py:803-810`). Every
  `run_task` caller in `cli.py` hands it no `emit`, so `saffron cell` and
  `saffron batch` both print through it. It hands that closure to
  `run_one_cell` (`saffron/task.py:963-972`).

`describe` renders an `Agent` event's raw `line` and `detail` as they
came, cut to 160 and 500 characters (`saffron/events.py:909-922`).
`_describe_agent_event` renders a parsed `text` the same way, cut to 160
(`saffron/events.py:763-769`). Under `launchd`, stdout goes to
`~/.saffron/batch.out.log` (`docs/host/dev.saffron.batch.plist:58-59`). So
the cell's own token and every listed shape reach a host file.

**Who overrides `append` today.** Two test doubles in `tests/test_task.py`
subclass `EventLog` and return nothing from `append`: `_FailFirst`
(`tests/test_task.py:625-639`) and `_FailAfterTwo` (`:674-689`).

**The settled scope.** The operator settled these. Each emitter redacts an
event with the token its log holds before it prints the line. The printed
line and the appended line come from one redaction, so the two cannot
disagree.

## Problem

An `Agent` event's terminal line carries the credentials its log line
redacts. Make these changes.

1. **`EventLog.append` returns what it redacted.** It returns the event as
   redacted, before the size bound. It returns that event on a refused
   write too. Annotate the return as `Event`. A non-`Agent` event comes back
   as it was handed.
2. **`_default_emit` prints what `append` returns.** Append first, and print
   `describe` of the returned event.
3. **`run_task`'s `emit` prints what `append` returns.** Append first, and
   print `describe` of the returned event. The refused-write warning still
   prints once, after the line, and is never appended.
4. **The two doubles return an event.** On a refusal, `_FailFirst.append`
   and `_FailAfterTwo.append` return the event they were handed. Otherwise
   each returns what `super().append` returns.

**Before the bound, not after.** A clean event over `BOUND_CHARS` prints
today as `describe` renders its own dict. Returning the bounded event
would print `agent: (bounded, ...)` instead. This spec keeps that line
as it is.

## Out of scope

- **The three print-only defaults this spec was asked to weigh.** Each is the default
  of a function whose one production caller hands its own `emit`.
  `plan_checkpoint` (`saffron/cell/session.py:651`) and `repair_loop`
  (`:864`) are each called once, by `_drive_cell`
  (`saffron/cell/session.py:2653-2662`, `:3206-3212`). `_resolve_stacked_on`
  (`saffron/task.py:507`) is called once, by `run_task`
  (`saffron/task.py:835-845`), and emits no `Agent` event.
- **PACKAGE's two default emitters.** Each prints before it appends
  (`saffron/phases/package.py:687-697`, `:1167-1177`). `package.py`
  constructs no `Agent` event and calls no agent, and `append` redacts
  only an `Agent` event. So redacting first would print the same lines.
- **The spec sessions' token.** `_spec_session_emit` builds its log with no
  token (`saffron/cli.py:1375`). After this change those lines redact the
  shapes and print the token. `cli.py` is forbidden here.
- **`saffron review` and `saffron draft`.** `commit_review` hands its lenses
  a print-only `emit` (`saffron/commit_review.py:295`). `saffron draft`
  builds its agent with no `emit` (`saffron/cli.py:1700-1704`), and
  `run_spec_writer` calls it with none (`saffron/spec_review.py:745`). So
  `run_agent`'s own print-only default prints (`saffron/phases/implement.py:242`).
  Neither command has a log to redact through.
- **Every other event kind.** `describe` renders `detail` on `Preflight`,
  a rejected plan and others. `append` redacts none of them, and their
  lines stay as they are.
- **A hand edit in this spec's pull request.** `DESIGN.md` §5.7's last
  sentence before "Model-authored text" becomes false. The caller replaces
  "So is each event's terminal line, printed to stdout and under `launchd`
  to the batch log file." with this text.

  > An `Agent` event's terminal line is printed from the event its log
  > redacted. So stdout, and under `launchd` the batch log file, carry what
  > `events.jsonl` carries. A spec session's log holds no token, so its
  > lines redact the shapes alone. A print-only emitter prints its lines
  > as they came, `saffron draft`'s and `saffron review`'s among them. Every
  > other event kind's line is printed as it is written.

## Notes for the agent

**Edit or new.** Each criterion edits existing code, and no mutant on the
ref pins one. `append`'s redaction lines exist at your base and survive the
change, but a mutant there falsifies the log as much as the line. The
emitters' new spelling is yours, so no `find` written now pins it. Each
witness stands alone, and `witness` reports `skip` for both. The two `preserves` witnesses exist at
your base and pass there. The second one uses `_FailFirst`, so step 4 keeps
it green.

**`tests/test_credentials.py`.** Build each credential from pieces, as the
module's helpers do (`_github_token`, `_aws_key`, `_api_key`). Use a token
longer than eight characters that matches no shape, since the literal
check ignores a shorter one (`saffron/credentials.py:32-35`). Import
`_default_emit`, `EventLog` and `describe` inside the test body. Read
`capsys` after each log's events, so each half sees its own lines.

**`tests/test_task.py`.** The module-level driver at
`tests/test_task.py:46-122` takes `events` and `token`. Its double emits
each event through the `emit` it is handed. Pass `state="NOT_IMPLEMENTED"`, so no PACKAGE path
prints. Give each half its own `spec_id`, `task_id` and `out_dir`. Keep
only the printed lines that start with `agent: `, since the closure also
prints the task's `ceilings:` line.

**Shapes.** Each witness drives three of the five listed shapes, one per
field. `append`'s own per-shape test,
`test_every_shape_package_refuses_is_redacted_from_the_log`, drives every
shape through the same redaction, the OAuth token and the private key
block included.

**The `prose` gate.** `append`'s docstring is ten lines at your base
(`saffron/events.py:468-477`). A sentence added there pushes it past the
limit, so fold the return into its first sentence. Each new docstring
sentence stays within 25 words.

**Size.** A prototype at `e7b70e7e` measured 59 changed tokens outside the
test paths with `size_gate`, and `estimated_lines` is that over four. It
held all four steps and both new witnesses. Each new witness failed with
the source reverted. Every wrong version listed above failed its witness
there.
