---
id: b-835bfb
title: A host listener that starts between two cells is caught only at the next cell's preflight, after its image build
status: open
tier: 3
filed: 2026-10-03
specs: [SA-0198]
prs: []
commits: []
cites: [§5.1]
related: [b-2dc561]
---

## Problem

Found in the spec loop's run 27.

Colima started on the operator's host at 14:10, between `SA-0197`'s cell and
`SA-0198`'s. Its `limactl hostagent` listened on `*:53`. `SA-0198`'s preflight
found DNS answering from inside a cell at `10.88.0.1:53` and `10.0.0.105:53`.
It refused with exit 2, after the proxy started and the image built.

Nothing was spent, but the delegate learned of it only from the exit. In a
batch, every later task would fail the same probe. The probe runs per cell,
and the spec loop's `next` checks nothing about the host.

## Done looks like

`driver.py next` runs the same host probe preflight runs, and names the
process before a cell starts. A batch runs it once between tasks, before the
image build.

## Record

- 2026-10-03: filed from the spec loop's run 27.
