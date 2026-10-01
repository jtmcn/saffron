---
id: b-3590be
title: A revised spec of the order refused on an open pull request gets no task state
status: open
tier: 3
filed: 2026-10-01
specs: [SA-0162]
prs: [626]
commits: []
cites: [§4.2.1]
related: [b-df59f8]
---

## Problem

Found by #626's Spec seat, 2026-10-01.

`_revised_spec_refusal`'s caller sets no task state on a gate 0 refusal.
The escalate path sets `SPEC_WITHHELD`. The task stays in whatever state
minting and review left it, and the spec says nothing about it.

## Done looks like

A refused revised spec ends in a named state, and a test asserts it.

## Record

- 2026-10-01: filed from #626's review seats.
