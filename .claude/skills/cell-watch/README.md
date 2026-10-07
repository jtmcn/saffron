# cell-watch

A Claude Code mod that follows a Saffron task through its `events.jsonl`. It
reads each event's `kind` field, so no pattern over rendered lines decides a
milestone. For an operator at the prompt, it does the work of the spec loop's
Monitor over `tail -F | grep`. The model cannot start it, so an unattended
loop still uses the Monitor.

## Use

- `/cell-watch` follows the newest task log under `~/.saffron/batches/v0`, so
  it moves to each next spec of a batch by itself.
- `/cell-watch SA-NNNN` follows one task.
- `--pane` opens a pane of the task's lines.
- `--quiet` keeps the status line and toasts and submits no prompt.
- `/cell-watch stop` ends the watch.

The status line reads `SA-0222 · IMPLEMENT #1 · $6.26/$26.00`.

## What wakes the session

The mod submits one prompt for each milestone below.

- A baseline fail outside `prose`. One set of failing gates wakes once per
  session, because a stacked batch hands one base to every cell.
- A baseline gate that aborted.
- A `budget_usd` ceiling that stops the task.
- A `Terminal` event.
- A `TaskOutcome`, with spend against budget, and the reopening time of a rate
  limit.

The log is not the process. Wait for the cell's exit notice before
`driver.py record`.

A detail field mixes host and cell text. The mod strips its control
characters and caps it at 500 characters before any toast or prompt, as
`describe` does.

## Check it

```
claude plugin validate .claude/skills/cell-watch
claude plugin test .claude/skills/cell-watch
```

The mod API is early access, and it moves between Claude Code releases. This
copy was written against Claude Code 2.1.293.
