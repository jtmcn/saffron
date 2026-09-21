---
id: b-d1d634
title: The spec writer's caller learns a split only when the whole draft is done
status: open
tier: 3
filed: 2026-09-20
by_hand: true
specs: []
prs: []
commits: []
cites: []
related: [b-ea1d13, b-b69bb6, 157]
---

## Problem

Filed 2026-09-20 from the review of #392, which closed b-ea1d13. That item
asked step 1 of `.claude/agents/spec-writer.md` to report the size estimate
and the split decision before drafting. #392 narrowed it to report ordering:
a split now leads the writer's final report and names each child.

The narrowing rests on one claim in b-ea1d13's `## Record`. It reads "A
subagent reports once, when it finishes, so no estimate can reach the caller
before the drafting". That rules out a second output mid-run. It does not rule
out an early return. Step 1 can end the invocation on a split, report the
parent and the children it would write, and stop. The caller then dispatches
one writer per child, which is what the item asked for.

The Record's second claim does not hold. It reads "Children carry `depends_on`
the parent, so they cannot be written before it exists". A child names its
parent by id, and `records new-id` gives that id before any file. Nothing in
the queue reads the parent's file to resolve a child's `depends_on`.

`SA-0113` measured the draft at 35.7 minutes and the first review at 6.2. A
caller told at minute two dispatches the children beside the parent. That is
the cost b-ea1d13 was filed against, and it stands.

## Done looks like

Step 1 ends the writer's invocation on a split. The report names the parent
and each child it would write, and no spec file lands in that run. The caller
dispatches one writer per child. An estimate under the ceiling changes
nothing about the current flow.

The other close is the operator rejecting the split-and-stop shape, with the
reason in one line here.

## Record

- 2026-09-20: filed from the review of #392. `by_hand` because the file is the
  writer agent's own instruction surface, which is why b-ea1d13 carries the
  same flag.
