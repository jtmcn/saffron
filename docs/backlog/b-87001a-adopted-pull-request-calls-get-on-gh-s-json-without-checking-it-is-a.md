---
id: b-87001a
title: "_adopted_pull_request calls .get on gh's JSON without checking it is an object, so adopt exits 2 where it should refuse"
status: open
tier: 3
filed: 2026-10-25
specs: []
prs: []
commits: []
cites: []
related: [b-619b7d]
---

## Problem

Found in the spec loop's run 48, by #961's Spec seat, and confirmed by
the delegate.

`_adopted_pull_request` in `saffron/cli.py` parses `gh pr view`'s stdout
and calls `info.get(...)` at once. JSON that parses to `null` or a list
raises `AttributeError`, and `saffron adopt` exits 2. Its docstring says it
returns `None` when `gh` prints no usable JSON, so the caller refuses with
exit 1.

## Done looks like

A non-object payload returns `None`, and a test drives `null` and a
list.

## Record

- 2026-10-25: filed from the spec loop's run 48.
