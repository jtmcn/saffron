---
id: b-1b05be
title: "The deferred finish grades each layer's critic findings at PACKAGE's head, so it re-raises what review commits fixed"
status: done
tier: 2
filed: 2026-10-25
closed: 2026-10-27
specs: [SA-0320]
prs: [976]
commits: []
cites: [§5.7]
related: [b-781ea4, b-cc87b1]
---

## Problem

Found in the spec loop's run 48.

`saffron finish 53`, `54` and `55` each read the in-cell critic's findings
at the head PACKAGE pushed. Review commits had already fixed most of them.
Five of the eight findings the three finishes reported named a head below
the reviewed one. Four of those five were already fixed, and the spec
answered the fifth. Each one went to the writer as a follow-up draft and
was pooled.

`finish/53/findings.json` names `3df11823`, while #961's head was
`a0ec477e`. `finish/54` names `9a39daa9` beside `78f1453b`, and `finish/55`
names `ce276ec7` beside `872215b4`.

## Done looks like

The finish reads each finding at the layer's pushed head. It drops one
that a later commit on the layer changed before the writer sees it.

## Record

- 2026-10-25: filed from the spec loop's run 48.
- 2026-10-27: done by `SA-0320` in #976, from the spec loop's run 49.
