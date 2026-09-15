---
id: 95
title: A night that dies resolving its queue leaves no row to say it ever started
status: done
tier: 1
closed: 2026-09-12
specs: [SA-0065, SA-0066]
prs: [212]
commits: []
cites: []
related: [26, 46]
---

## Problem

**Tier 1 — honesty.** `SA-0065` (merged 2026-09-10) made `discover_specs` refuse
a spec directory that is absent or is not a directory, so the silent empty queue
item **26** describes now stops the night instead of draining it. Found by the
review round on that task's own pull request: the refusal is visible in exactly
one place, and it is not the audit trail.

Traced rather than assumed. `_batch` calls `_resolve_queue` inside its
`readiness.ok` branch (`saffron/cli.py:715`), and `run_batch` — the call whose own
comment says it "is what makes the batch row close `INFRASTRUCTURE` and exist at
all" — is not reached until line 735. A `SpecError` from discovery therefore
propagates past it to the catch-all at `saffron/cli.py:172`, which wraps every
subcommand, prints one line, and returns `2`. Correct exit code, and **no batch
row, no `PREFLIGHT_FAILED`, no task row: nothing in `~/.saffron/ledger.db` records
that a night began.**

That lands the report in the one place item **46** already says is fragile: the
batch's stdout is the night's only human-readable account, and under launchd
without `PYTHONUNBUFFERED=1` SIGTERM discards it. So the failure mode `SA-0065`
was written to make visible is visible on a terminal nobody is watching and
invisible everywhere the morning looks.

Not the same as item 26 and not closed by it: 26 was that nothing *refused* the
directory. This is that the refusal is unrecorded.

## Done looks like

an aborted resolution closing a batch row the way a failed readiness check already does — the state exists and `run_batch` already writes it
for the readiness path, so this is about reaching it, not inventing it. The
narrower version, if the row is judged wrong: `_batch` catching `SpecError` around
`_resolve_queue` and routing it through the same `INFRASTRUCTURE` stop the
readiness failure takes, rather than letting it reach a catch-all that cannot know
a night was in progress.

## Record

**Status:** **done** — `SA-0066`, PR #212, merged 2026-09-12.
