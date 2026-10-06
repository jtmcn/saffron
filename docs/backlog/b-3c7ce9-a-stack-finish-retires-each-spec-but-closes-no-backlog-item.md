---
id: b-3c7ce9
title: "A stack finish retires each layer's spec but closes no backlog item, so this repo's suite goes red on every finish"
status: open
tier: 1
filed: 2026-10-05
specs: []
prs: []
commits: []
cites: [§4.4]
related: [b-b0cd68]
---

## Problem

Measured in stage 2 of the delegate-loop plan, in batches 13 and 14.

`commit_finish` in `saffron/finish.py` moves each layer's spec into
`.saffron/specs/done/` (`saffron/finish.py:159`). It edits no backlog record.
The records check then reports "open, but SA-NNNN is in done/" for each
retired spec whose origin item is still open (`tests/records/check.py:496`).
`test_the_backlog_records_hold` in `tests/records/test_records_integrity.py`
fails on it, so this repo's suite goes red on every finish.

Batch 13's finishing commit `f9ae5547` moved `SA-0205` and `SA-0208` and
nothing else, with 0 insertions. Batch 14's `002afbc7` did the same. Both
finishes escalated "red suite, 3 new failures" and linked nothing. Pytest on
`f9ae5547` gave 1 failed, that test, and 3679 passed.

b-b0cd68 made retirement keep the spec tests green. It left the records
check out.

## Done looks like

A stack finish on this repo goes green. Either the finishing commit closes
each retired spec's origin item in the same commit, or the finish retires
nothing. A test drives a finish over a layer whose spec cites an open item
and reads the records check back clean.

## Record

- 2026-10-05: filed from stage 2 of the delegate-loop plan (the first live stack batches, batches 13 and 14).
