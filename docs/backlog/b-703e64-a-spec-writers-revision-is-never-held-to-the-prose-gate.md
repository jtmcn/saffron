---
id: b-703e64
title: A stack batch's spec writer revises a spec the prose gate never reads, so the finish that writes it back goes red
status: open
tier: 1
filed: 2026-10-13
specs: [SA-0286]
prs: [867]
commits: []
cites: [§4.2, §5.4]
related: []
---

## Problem

Found in the spec loop's run 37, batch 29.

The batch's spec review ran three rounds on `SA-0286`, and its writer revised
the spec twice. The revision lives only in the ledger's `spec_texts`. The tree
kept the queued text, and the cell's worktree carried it. Preflight said so:
the host judged one text and the agent could read another.

After the end review, the finish wrote that revision back into the tree as
commit `55c118b3`. Re-verification then reported 13 new failures and the
finish escalated, so nothing was linked. The suite passed on the host at that
commit, 4405 tests. The revised text alone carried 12 new `prose` hits: em
dashes, semicolons and sentences over 25 words. No step held the writer's
text to the gate before the finish committed it.

## Done looks like

A revision the spec writer returns is run through the `prose` gate before the
batch accepts it. A hit sends it back to the writer, or the batch keeps the
last text that passed. The finish's write-back of a revision then cannot be
the commit that turns re-verification red.
The follow-up writer's spec meets the same gate, and the queue's own checks,
before the finish commits it.

## Record

- 2026-10-13: filed from the spec loop's run 37. The queued `SA-0286` text
  was retired to `done/`, since the task's `spec_sha` is that text's.
- 2026-10-14: recurred in the spec loop's run 38, batch 30. The follow-up
  writer turned an end-review concern into `SA-0292`. The spec carried 21
  `prose` hits, the queue refused it on its own text, and a criterion named a
  path outside its `touches`. Re-verification reported 24 new failures and the
  finish escalated. Review fixed the concern with one comment on #872.
