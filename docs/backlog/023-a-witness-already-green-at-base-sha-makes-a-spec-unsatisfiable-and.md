---
id: 23
title: A witness already green at `base_sha` makes a spec unsatisfiable, and nothing says so
status: done
tier: 3
specs: [SA-0005, SA-0011, SA-0084, SA-0085]
prs: [250]
commits: []
cites: []
related: [18]
---

## Problem

**Status:** merged, 2026-09-14 — `SA-0085`, PR #250, stacked on
`SA-0084`, in stack #251. It names the witness before the first turn
and does not stop the task: the attempts are still paid for. Found by review of `SA-0011`. The `watch()` line asked for below is now an
event: it goes on `Baseline`, because `criteria` skips at baseline and nothing
else there reads a witness.

`saffron/gates/core/criteria.py` reports `witness-green-at-base` (`:100`) for a
non-`preserves` witness that already passed at base. It is blocking, and no
repair turn can fix it: the agent's only routes are renaming or deleting the
pre-existing test, and `census` and `integrity` both block those. So an
operator authoring error — naming a witness that already passes — burns
`max_attempts × budget_usd` with nothing to show, the same corpse `DESIGN.md:379`
records for item 18 (`SA-0005`, $5.34, dead at turn 61).

It cannot be caught at intake, because it needs the suite. But the baseline
suite already holds the answer: after `baseline = _suite([])`
(`saffron/cell/session.py:724`), any non-`preserves` witness appearing in the
baseline's `collected` union is a spec that cannot pass, before a single repair
attempt is spent finding that out the expensive way.

**Done looks like** one `watch()` line there naming those witnesses, turning
four dead attempts into a legible operator message on the first unattended
night.
