---
id: SA-0053
title: a running cell writes its whole log to disk, and only the terminal that started it can read it
type: feature
priority: 1
depends_on: []
touches:
  - saffron/watch.py
  - tests/test_watch.py
  - saffron/cli.py
  - tests/test_cli.py
forbidden:
  - DESIGN.md
  - CONTEXT.md
  - .saffron/**
  - saffron/events.py
  - saffron/cell/**
  - saffron/phases/**
  - saffron/gates/**
  - saffron/report/**
  - saffron/ledger.py
  - saffron/scheduler.py
  - saffron/preflight.py
  - saffron/reconcile.py
  - saffron/replay.py
budget_usd: 8
max_attempts: 3
max_turns: 70
risk: standard
acceptance:
  - claim: >-
      A task's log renders as the same lines its terminal printed, through the
      existing describe function rather than a second formatter. The whole
      point is that a watcher and the attended terminal agree; two renderers
      would drift, and the golden fixture that pins the terminal's output would
      only cover one of them.
    witness: tests/test_watch.py::test_a_log_renders_as_the_lines_its_terminal_printed
  - claim: >-
      The default view drops exactly two shapes, both identified by the agent
      payload's own type rather than by the text it renders to: the periodic
      system event whose subtype is the running thinking-token estimate, and
      the bare tool result. Measured on one live task: 630 and 71 of 878
      lines, which is 80 percent of the log. A watcher that prints all of it
      is one an operator stops reading, which is the failure this spec exists
      to prevent rather than a matter of taste.
    witness: tests/test_watch.py::test_the_default_view_drops_the_token_counter_and_bare_acknowledgements
  - claim: >-
      The agent's rate-limit line is kept. It is six lines in that same log and
      it is the operator's first warning that a night is about to die of a
      provider ceiling — the one agent line least safe to hide. A filter that
      drops it has confused the rarest signal for the commonest noise.
    witness: tests/test_watch.py::test_the_rate_limit_line_is_signal_and_is_kept
  - claim: >-
      The agent's own prose is never filtered, whatever it happens to say. A
      free-text message renders as the agent's tag followed by the text
      itself, so it shares a prefix space with every telemetry shape — an
      agent remarking that a rate limit looks wrong must not be filtered as
      the rate-limit line it is about.
    witness: tests/test_watch.py::test_the_agents_own_words_are_never_filtered
  - claim: >-
      Everything is still reachable, because the dropped lines are the record
      of what the agent actually did and a diagnosis needs them. The filter is
      a default, never a deletion.
    witness: tests/test_watch.py::test_the_unfiltered_view_keeps_every_line
  - claim: >-
      Following a growing log emits only what arrived since the last poll. A
      watcher that re-rendered the file each time would repeat every line it
      had already printed, which is the one behaviour that makes a follower
      useless. The poll interval is injected, so the test neither waits nor
      sleeps.
    witness: tests/test_watch.py::test_following_emits_only_events_that_arrived_since_the_last_poll
  - claim: >-
      A log caught mid-write loses the partial line and keeps every whole one.
      This is a live file being appended by another process, so a reader
      arriving between the write and its flush is the normal case rather than
      the corrupt one — and the existing reader already draws that
      distinction. The witness proves the follower inherits it rather than
      reimplementing it.
    witness: tests/test_watch.py::test_a_partial_final_line_is_dropped_and_the_whole_ones_survive
  - claim: >-
      Naming a task with no directory says which directory it looked in and
      exits 1. Driven through the command itself, not only the module: the
      whole content of the decision is which exit code an operator sees, and a
      module-level test leaves the handler deletable — with it gone the outer
      catch-all returns 2 instead, and every test still passes.
    witness: tests/test_cli.py::test_watch_exits_one_and_names_the_directory_for_an_unknown_task
  - claim: >-
      Both flags reach the follower. Without this the unfiltered flag and the
      poll interval can be dropped from the call entirely and the suite stays
      green, which makes the flags decoration rather than wiring.
    witness: tests/test_cli.py::test_watch_passes_its_flags_through_to_the_follower
  - claim: >-
      The command resolves its task directory from the same batch-tree root
      the rest of the CLI already computes, rather than rebuilding the path
      from its own idea of where the tree lives. Two spellings of one location
      is how a watcher comes to read a directory nothing writes.
    witness: tests/test_cli.py::test_watch_reads_the_batch_tree_the_cli_already_computes
---

## Context

Every mechanism this needs already shipped. `SA-0029` built the event log and
`SA-0030`/`SA-0031` moved 64 call sites onto it, so a running cell already
writes its whole life to `events.jsonl` — one JSON object per line, **flushed
on every append**, deliberately: that method's own docstring says a disk-full
night must not render as a night in which nothing happened.

`describe` already turns any event into the exact line the attended terminal
prints — its docstring says so, and a golden fixture pins it. `read_log`
already drops a truncated final line per-line rather than discarding the file.

What is missing is a verb. `saffron` has four subcommands — `replay`, `cell`,
`queue`, `reconcile` — and none of them reads a log back.

## Problem

- **A task can only be watched by the terminal that launched it.** The log is
  live on disk and nothing offers it to a second reader.
- **A finished task's log can only be read as raw JSON.** The renderer exists
  and has no caller outside the running supervisor.
- **The raw log is unreadable at operator speed.** Measured on one live task:
  850 events, of which 681 are the agent's token counter and bare tool
  acknowledgements.

## Out of scope

**Detecting that a task has finished.** A follower here runs until it is
interrupted, the way `tail -f` does. The teardown event is not a reliable end
marker — it is emitted on the teardown path, and a killed cell reaches no such
path — so a watcher that stopped on it would report a crashed task as a
finished one. Ending on a real terminal state is worth doing once something
records one; it is not worth guessing now.

**Rendering a night rather than a task.** The batch index is
`saffron/report/**`, which is `forbidden`. This reads one task's log.

**Changing what any event says.** `saffron/events.py` is `forbidden`:
`describe`, `read_log` and the event kinds are reused exactly as they are. If
a line reads badly, that is a finding to report rather than a formatter to
fork — a second renderer is the one outcome this spec must not produce.

**Following a task that has not started.** The directory appears when the
supervisor first writes to it. Waiting for it to exist is a different feature
from reading it.

## Notes for the agent

**Filter on the agent payload's own `type`, never on the rendered line.** The
noise is two shapes inside one event kind, so filtering by kind would drop the
agent's real work with them — but filtering by rendered text is worse, and this
is the sentence a previous attempt got wrong. `_describe_agent_event` renders a
free-text message as `agent:` followed by the text itself, so *any* prefix match
on the rendered line collides with whatever the agent happens to say. The
discriminators are in the payload: the periodic system event carrying the
thinking-token estimate as its subtype, and the tool result. Both are exact
matches on fields, not prefixes on prose.

**The rate-limit line is signal.** It renders with a leading `agent: rate limit`
and it is tempting to read as telemetry; it is the provider ceiling announcing
itself, six lines against the token counter's 630, and hiding it is how a night
dies of `RATE_LIMITED` with nothing on screen to say so.

**Injected, so the tests neither sleep nor wait.** The poll interval is a
parameter with a real default bound as a keyword — the shape this repo uses for
the queue scan's `gh` and for PACKAGE's runner. A follower whose loop calls
the clock directly cannot be tested without making the suite slow, and a slow
test is one that gets marked and skipped.

**The follower's stop condition is the seam to get right.** It runs until
interrupted, so a test needs the loop to be finite without pretending the
production loop is. Give the poll a way to say "stop" that the real default
never says, rather than counting iterations inside the loop body.

**The subcommand is thin on purpose.** `saffron/cli.py` gains a parser block
and a dispatch line; everything with behaviour goes in the new module so it can
be tested without argparse. The batch-tree root is already computed once in
`main` — read it from there rather than adding a second computation, which is
what the last witness pins.

**A new module, and the name is free.** Two comments in the codebase mention a
`watch(...)` call site historically; no function or module by that name exists
today. Confirm that before naming anything, because the comments read as though
one does.

**Exit `1` for a task directory that is not there, and this spec is choosing
it rather than inheriting it.** The `0`/`1`/`2` vocabulary belongs to running a
task — reviewable, did not make it, infrastructure failed — and watching is not
running one. `2` would claim infrastructure failed when the real cause is a
mistyped spec id, and `0` would make a typo look like a task that has not
started. Say so in a comment beside the return.

**No new test may carry the `cell` marker.** `pyproject.toml` sets
`addopts = "-m 'not cell'"` and the `tests` gate passes the same argv to
`--collect-only`, so a cell-marked witness is never collected at head,
`criteria` reports `witness-not-collected`, and the attempt is spent on a test
that was correct. Nothing here needs a container: every witness writes a log
file and reads it back.

**Write the fixtures as real event objects, not hand-typed JSON.** Constructing
the kinds and appending them through the existing log writer is what makes the
test prove the round trip. A hand-written JSON fixture proves the parser reads
what the test author imagined the writer emits.
