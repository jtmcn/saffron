---
id: b-910cef
title: "The queue's open pull request refusal blocks every child of an open stack, so a second batch cannot run"
status: open
tier: 2
filed: 2026-10-09
specs: []
prs: [780]
commits: []
cites: [§4.2.1]
related: [b-e0e1cf, b-883f74]
---

## Problem

Found in the spec loop's run 32.

`SA-0233`'s PACKAGE seed failed, and batch 20 refused nine specs that
reached it. The operator asked for a second batch over those nine and
`SA-0251`. The queue refused all ten against the stack's own open pull
requests. A plain queue admitted only `SA-0235` and `SA-0251`, and
`--stack` admitted none.

`open_pr_refusal` exempts only the candidate's ancestor branches by
`depends_on` (`saffron/scheduler.py:688-713`). A stack batch cuts every
layer from its predecessor, so each later spec's tree holds every layer's
changes. Its `touches` overlap pull requests it does not name as parents.
The ten specs moved to the next loop.

## Done looks like

A batch can run specs whose parents sit in an open stack. The exemption reads
the stack's recorded chain, not `depends_on` alone. A test queues a child of
an open three-layer stack whose `touches` overlap the bottom layer.

## Record

- 2026-10-09: filed from the spec loop's run 32.
