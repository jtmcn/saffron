---
id: b-5288d7
title: Three modules each split a `consumes` or `removes` entry at its colon
status: open
tier: 3
filed: 2026-10-20
specs: []
prs: [919]
commits: []
cites: [§4.2.1]
related: [b-e773d9]
---

## Problem

Found by the Standards seat on #919, in the spec loop's run 45.

`saffron/intake.py`'s validator, `saffron/repos/mirror.py`'s
`unresolved_consumes` and `saffron/scheduler.py`'s `_entry_subject` each
call `partition(":")` on an entry. `_entry_subject` first decided a bare
path by comparing the subject to the path, so `a.py:a.py` read as bare.
Review fixed that instance. The three readers can still drift apart.
`SA-0290` could not share one, since its spec forbade `saffron/repos/`.

## Done looks like

One function in `saffron/intake.py` splits an entry into its path, its
name and whether it named one. All three modules call it.

## Record

- 2026-10-20: filed from the spec loop's run 45.
