---
id: b-54ad4f
title: "No gate checks that a comment's citation of `CONTEXT.md`, an ADR or a criterion names something that exists"
status: open
tier: 2
filed: 2026-10-12
specs: []
prs: []
commits: []
cites: [§5.4]
related: []
---

## Problem

Found by the Standards seat on #844 and #845, in the spec loop's run 35.

On #844 five comments cited "ADR 7, criterion N". ADR 7 numbers no
criteria. On #845 three comments cited `CONTEXT.md` notes about
`ready_task` that `CONTEXT.md` does not hold. One cited an `Attempt` entry
that says the opposite. The critic raised none of them, and the review
commits rewrote all of them.

## Done looks like

- A `terms` or `prose` rule resolves each citation of a `CONTEXT.md`
  entry, an ADR criterion or a `DESIGN.md` section against the tree at head.
- An unresolved citation is a gate failure that names the comment.

## Record

- 2026-10-12: filed from the spec loop's run 35 (#844, #845).
