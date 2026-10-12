---
id: b-54fee5
title: "`_GLOB_CHARS` is spelled in `saffron/scheduler.py` and `saffron/agents/context.py`"
status: open
tier: 3
filed: 2026-10-11
specs: []
prs: []
commits: []
cites: []
related: [b-f8fa24]
---

## Problem

Found by the Standards seat on #809 (`SA-0259`), in the spec loop's run 34.

`saffron/scheduler.py:272` defines `_GLOB_CHARS = frozenset("*?[")`.
`SA-0259` added the same line to `saffron/agents/context.py`, to skip a
`touches` component that holds a glob. The spec forbade `scheduler.py`, so
the cell could not import one from the other. Importing the scheduler's
private name into `agents/context` would also point the dependency the
wrong way.

Two copies can drift. One module would then call a component a glob while
the other reads it as a literal path.

## Done looks like

One module owns the set of glob characters, and the other imports it. No
second definition remains under `saffron/`.

## Record

- 2026-10-11: filed from the spec loop's run 34 (#809).
