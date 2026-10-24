---
id: b-25634b
title: "`saffron finish` restates `saffron batch`'s stack adapter wiring line for line"
status: open
tier: 3
filed: 2026-10-23
specs: []
prs: [944]
commits: []
cites: [§4.2.1]
related: [b-8a0c9a]
---

## Problem

Found by the Standards seat on #944 (`SA-0305`), in the spec loop's run 46.

`_finish` in `saffron/cli.py` builds every stack adapter `_batch` builds.
That set holds the runner, the graded-heads end review and the shared commit
cache. It also holds the spec review, cite, revise, mint, the base check,
follow-ups, the open pull request reader and the finish. Two comments are
copied word for word. The spec
asked for that copy. CLAUDE.md names two copies of the task driver as what
let the unattended path stop recording its ceilings.

## Done looks like

One helper in `saffron/cli.py` builds the stack adapters from the pinned
base, the repo, the ledger, the batch tree, the writer cap and the slug.
`_batch` and `_finish` both call it.

## Record

- 2026-10-23: filed from the spec loop's run 46.
