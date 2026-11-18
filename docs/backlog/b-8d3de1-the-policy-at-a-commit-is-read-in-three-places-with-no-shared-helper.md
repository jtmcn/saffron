---
id: b-8d3de1
title: The policy at a commit is read in three places with no shared helper
status: open
tier: 3
filed: 2026-11-18
closed:
specs: []
prs: []
commits: []
cites: []
related: [b-e9153f]
---

## Problem

Found in the spec loop's run 79, on #1261 (`SA-0411`). The stack mint now
reads `.saffron/policy.yaml` at the pinned base with `file_at` and parses
it (`saffron/cli.py:1615`). That is the third copy of one read, after
`saffron/task.py:903` and `saffron/spec_citations.py:403`. Each spells the
path, the absent-file case and the parse on its own.

A shared helper belongs in `saffron/repos/policy.py` or
`saffron/repos/mirror.py`. Both were forbidden to `SA-0411`.

## Done looks like

One function returns the parsed policy at a commit, or `None` when the
file is absent. All three call sites use it, and a test drives the absent
and the unparseable case through it.
