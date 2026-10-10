---
id: b-ff3141
title: "A draft's revision prompt says the text replaces the file at its path, and no file is there"
status: open
tier: 3
filed: 2026-10-09
specs: []
prs: [782]
commits: []
cites: []
related: [b-98a3be]
---

## Problem

Found by #782's Spec seat in the spec loop's run 32.

`saffron draft` reuses `_stack_revise` for its revision. That prompt says the
text "replaces the file at that path" (`saffron/cli.py:1040`). A draft writes
its spec into the tree only after the chain ends, so no file is there while it
runs. `SA-0229` scoped only the review's sentence and left this one.

## Done looks like

A draft's revision prompt says what the revision replaces, the recorded text,
and a test reads the sentence as a literal.

## Record

- 2026-10-09: filed from the spec loop's run 32.
