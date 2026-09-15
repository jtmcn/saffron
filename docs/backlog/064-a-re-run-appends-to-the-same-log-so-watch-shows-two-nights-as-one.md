---
id: 64
title: A re-run appends to the same log, so `watch` shows two nights as one
status: done
tier: 3
closed: 2026-09-14
specs: [SA-0081]
prs: [248]
commits: []
cites: []
related: []
---

## Problem

**Tier 3.** Measured 2026-09-04 while reading `SA-0051`'s second run with the
verb built two specs earlier.

The batch tree keys a task directory by spec id — `~/.saffron/batches/v0/<SPEC-ID>` —
and `EventLog` appends. A spec driven twice therefore writes both runs into one
`events.jsonl`, in order, with nothing between them. `saffron watch SA-0051`
opened on this line:

```
PLAN: rejected, $1.80 spent — plan's own estimate of 650 changed lines exceeds
the feature ceiling of 600
```

which belonged to the *previous* attempt, not the one being watched. The run
being read had been accepted at 300 lines and was in its repair turn.

**Not the same gap as the no-rotation ceiling.** `EventLog`'s own `ponytail:`
names one file per task with no rotation, and that is about size. This is about
*identity*: two runs of one spec are two different nights, and nothing in the
file says where the first ends. An operator diagnosing a re-run reads the
failure of a run that no longer exists and draws a conclusion about the one
that does — which is worse than a file that is merely large.

**It is also how a stale log reads as a live one.** A spec that was driven last
week and is being driven now shows last week's `READY_FOR_REVIEW` and pull
request URL above today's preflight. `--no-follow` on a task that has not
started yet prints the previous run in full and looks current.

**Not** one directory per run. The task directory's name is what `saffron
watch SA-0051` resolves, what `patch.diff` and `plan.json` live beside, and
what the batch index links to; making it run-scoped changes four things to fix
one, and `plan.json` being overwritten by a re-run is the same defect with the
same fix.

## Done looks like

a run boundary in the log that `describe` renders — the
run id is already minted before the first event is written, so a marker
carrying it costs nothing to produce — and `watch` defaulting to the newest
run, with the whole file reachable behind a flag. The cheap half is the marker;
the flag can wait for someone to want it.

## Record

**Status: merged, 2026-09-14 — `SA-0081`, PR #248, stacked on
`SA-0080`, in stack #251.** Two things below are out of date. The run id is *not* minted before the
first event: the ledger mints run and task ids inside `run_one_cell`, after
`Ceilings` and the cell's first `Preflight` are logged. And the two "runs" are two
**tasks**, since a run is a repo's slice of a batch. The marker exists anyway:
`Ceilings` is the first event `run_task` writes, so the spec keys the boundary
on it.
