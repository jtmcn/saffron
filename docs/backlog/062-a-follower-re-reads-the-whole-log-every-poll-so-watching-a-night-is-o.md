---
id: 62
title: A follower re-reads the whole log every poll, so watching a night is O(n²)
status: done
tier: 3
specs: [SA-0053, SA-0080]
prs: [119, 247]
commits: []
cites: []
related: []
---

## Problem

**Status: merged, 2026-09-14 — `SA-0080`, PR #247, in stack #251.** It added `read_log_since` beside `read_log` rather than giving
`read_log` an offset, so "done looks like" below is met by a sibling. The follower
assumes an append-only log: a truncated or replaced file stalls it and then loses
events, so whoever lifts `EventLog`'s rotation `ponytail:` owns the follower's reset.

**Tier 3.** Measured 2026-09-04 while reviewing `SA-0053` (PR #119), and named
in a `ponytail:` beside the call.

`watch.follow` calls `read_log` once per poll and slices past what it has
already seen. `read_log` has no offset — it reads and parses the entire file —
so following costs O(n²) over a night. Measured: **5.7s for one `read_log`** on
a 37 MB / 160k-line log, past which the default 1s interval falls permanently
behind and pegs a core re-parsing what it already rendered. `events.py`'s own
`ponytail:` names "tens of MB a night" as the ceiling, so this is inside the
range the log is designed for.

**Done looks like** `read_log` taking a byte offset and returning the position
it stopped at, with `follow` holding that between polls. The truncated-final-
line tolerance has to survive it: a partial line at the offset boundary must
leave the offset *before* it, or the next poll resumes mid-object and drops
every line after.

**Not** having the follower parse the file itself. A second parser beside
`read_log` is the same defect as a second renderer beside `describe`, which is
the thing `SA-0053` was written to avoid.
