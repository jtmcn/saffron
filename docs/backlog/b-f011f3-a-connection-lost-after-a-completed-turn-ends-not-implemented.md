---
id: b-f011f3
title: A connection lost after a completed turn still ends the task `NOT_IMPLEMENTED`
status: open
tier: 2
filed: 2026-11-04
specs: []
prs: []
commits: []
cites: [§4.3]
related: [b-031ac2]
---

## Problem

Found by the spec loop's run 53, in `SA-0333`'s first cell.

The cell lost its API connection mid-IMPLEMENT, after the plan was accepted.
It ended `NOT_IMPLEMENTED` at $4.81 with no commits, and the batch then
refused `SA-0330` for its parent.

b-031ac2 fixed this for a session that completed no turn. A session that
completed turns first still reads as a task that did not implement. A
`NOT_IMPLEMENTED` row is decided, so the batch will not rerun it at the same
`spec_sha`.

## Done looks like

A lost connection ends the task in a state that decided nothing about
the spec, whatever turns came first, so a later batch reruns it.

## Record

- 2026-11-04: filed from the spec loop's run 53.
