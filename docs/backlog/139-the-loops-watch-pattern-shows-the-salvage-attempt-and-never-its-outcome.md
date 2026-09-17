---
id: 139
title: The loop's watch pattern shows a salvage starting and never whether it recovered anything
status: done
tier: 3
filed: 2026-09-16
closed: 2026-09-16
by_hand: false
specs: []
prs: [277, 287]
commits: []
cites: [§4.3]
related: [67]
---

## Problem

**Tier 3.** Observed on 2026-09-16 watching `SA-0088`'s cell.

`driver.py pattern` builds the Monitor's `grep -E`, and `WATCH_PREFIXES` carries
`IMPLEMENT`, `GATE`, `REVIEW`, `REBUT`, `PACKAGE`, `gates:`, `baseline:`,
`ceilings:`, `teardown`, `rate limit`, `cell:`, `PLAN` and `budget:` — but not
`SALVAGE`.

So the watcher saw

```
IMPLEMENT: cut off at the turn ceiling with nothing committed — spending one turn to salvage it
```

and then nothing. The line that says whether the salvage worked —

```
SALVAGE: recovered 1 commit(s), $7.96 spent
```

— never reached the Monitor. Whether the cell has anything left to gate is
exactly the question the first line raises, and the answer is invisible without
tailing the log by hand.

Item 67's `budget:` and `PLAN` were added for the same reason after run 2.

**Two more, found reviewing the fix.** `SCOPE:` and `REPAIR:` are printed
(`saffron/events.py`) and were never in the set either — so a scope refusal and
a whole repair turn were invisible to the watcher, not just the salvage
outcome. Nothing held the two lists together, which is why the set could drift
three members out of date without anyone noticing. `saffron/events.py`'s
`LineLabel` is the closed set of progress-line prefixes, and is what the check
below should read — the same way `watch_pattern` reads the ontology's terminal
states rather than copying them.

## Done looks like

`SALVAGE` in `WATCH_PREFIXES`, and a check that every line the CLI prints at the
start of a phase has its outcome line in the same set.

## Record

**Filed 2026-09-16** from the spec loop's run of that day (stack #285).

**2026-09-16, a fix is open as PR #287.** `SALVAGE` is in `WATCH_PREFIXES`. It stays `open` until that merges.

**2026-09-16, done.** PR #287 merged (`1f64a99`). `SALVAGE`, `SCOPE` and
`REPAIR` are in `WATCH_PREFIXES` (`driver.py:57-63`), and a test holds that
list to `LineLabel`. Closed 2026-09-16 on review of the backlog: #287 wrote this record's "stays `open` until that merges" line itself, so the line could only land by the merge that should have closed it.
