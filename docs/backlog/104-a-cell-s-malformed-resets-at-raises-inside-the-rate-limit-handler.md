---
id: 104
title: A cell's malformed `resets_at` raises inside the rate-limit handler
status: done
tier: 2
closed: 2026-09-13
specs: [SA-0076]
prs: [230]
commits: []
cites: [§4.2.1]
related: []
---

## Problem

**Tier 2.** Found reviewing `SA-0070` (PR #221), 2026-09-12. `SA-0070` made
`events._when` return `"unknown"` for a `resets_at` it cannot read — a string,
a list, an integer past a timestamp, `NaN` — because `rate_limit` events
carrying them reach the renderer from a live cell. Its twin,
`saffron/phases/implement.py:when` (`:172`), still calls `time.localtime`
unguarded, and `saffron/cell/session.py:1843` calls it inside the
`except RateLimited` handler on `stopped.resets_at`: the cell's own
`rate_limit.get("resets_at")`, guarded only by truthiness. Measured by the
review: a rejected rate limit with `resets_at="soon"` raises `TypeError` there.
What that does past the handler is not verified; a raise out of
`run_one_cell` reaches the batch loop as an abort (§4.2.1) where a provider
ceiling should have been `RATE_LIMITED`. `phases/**` was forbidden to
`SA-0070`.

## Done looks like

one function rather than two — `implement.when` replaced
by `events._when`, or guarded the same way — with a witness that drives a
rejected rate limit carrying a malformed `resets_at` through the session and
asserts `RATE_LIMITED`.

## Record

**Status: `READY_FOR_REVIEW`, 2026-09-12 — `SA-0076`, PR #230 in stack #233.**
`implement.when` is deleted and `events.when` is the one formatter. A review
commit added the first test pinning its output to local time: before it, a
formatter that always returned `"unknown"`, or used `gmtime`, passed the whole
suite. The "not verified"
below is now measured, through `run_one_cell` with `tests/test_session.py`'s
stubs. It is worse than an abort. All four values raise out of the session:
`TypeError` for a string or a list, `OverflowError` for `10**20`, `ValueError`
for NaN. Each leaves the run row `RUNNING`, because the raise is inside `except
RateLimited` and its sibling `except BaseException` never closes the row. The
ledger keeps a run that reads as still going.

Merged 2026-09-13, PR #230.
