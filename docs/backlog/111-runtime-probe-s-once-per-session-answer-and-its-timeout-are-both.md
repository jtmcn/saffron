---
id: 111
title: '`runtime.probe()`''s once-per-session answer and its timeout are both untested'
status: done
tier: 3
filed: 2026-09-12
closed: 2026-09-14
specs: [SA-0079]
prs: [245]
commits: []
cites: []
related: [116]
---

## Problem

**Tier 3.** Found reviewing `SA-0077` (PR #232), 2026-09-12. Two lines of
`probe()` survive deletion with the suite green: the memo that asks the runtime
once per process, and the 10-second `timeout_s` on `--version` — the review's
mutant removing it survived. Measured by the same review: with the timeout, a
runtime that hangs on `--version` reports absent after 10.0s.
The memo is a note in the spec, not a criterion. Unverified: whether an
installed runtime whose service is stopped still reports present —
`container --version` looks client-side, and the spec put it out of scope. The
same review found `probe()`'s docstring and `pytest_runtest_setup`'s running
well past what this repo keeps comments to.

## Done looks like

a witness for each — a stub runtime that counts its own
invocations across two probes, and one that sleeps past a timeout patched small
— each killed by deleting the line it names.

## Record

**Status: merged, 2026-09-14 — `SA-0079`, PR #245, in stack #251.** The docstring hand fix below also owes `probe()`'s garbled "starts a
process that is not there once per test". A runtime that forks outliving the
timeout is item 116.
