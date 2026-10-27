---
id: b-781ea4
title: The finish's follow-up drafts fail to parse on a list item that starts with a backtick, so every finding is pooled
status: open
tier: 2
filed: 2026-10-24
specs: []
prs: []
commits: []
cites: [§4.2.1]
related: [b-cc87b1]
---

## Problem

Found in the spec loop's run 47, in `saffron finish 51`.

The end review raised three findings on `SA-0314`. The writer drafted a follow-up for each.
Two drafts failed with "spec frontmatter is not valid YAML", at a list item that opens
with a backtick. The third declared `type: test`, and the finish pooled it as neither bug
nor feature. The finish spent $20.66 and filed nothing.

`~/.saffron/run47/finish.log` holds the three `pooled` lines.

## Done looks like

A drafted follow-up whose frontmatter does not parse is sent back to the writer once,
with the parse error. The writer's prompt names the two types a follow-up can declare.

## Record

- 2026-10-24: filed from the spec loop's run 47.
- 2026-10-25: recurred in the spec loop's run 48. `saffron finish 55` pooled one
  draft with "spec has no YAML frontmatter block".
- 2026-10-27: recurred twice in `saffron finish 58`, in the spec loop's run 49. Two drafts had no frontmatter block, for `saffron/qualify.py` and `tests/ontology/test_vocabulary_agrees_with_context.py`, so both findings were pooled.
