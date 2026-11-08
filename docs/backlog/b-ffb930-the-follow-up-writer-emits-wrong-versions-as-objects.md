---
id: b-ffb930
title: "The follow-up writer emits `wrong_versions` as objects, so its first draft never parses"
status: open
tier: 2
filed: 2026-11-06
specs: [SA-0353]
prs: []
commits: []
cites: [§3]
related: [b-4a9207, b-01c53d]
---

## Problem

Found by `saffron finish 67`, in the spec loop's run 54.

The end review raised one real concern on #1024: `routed.py`'s first line
still said one `RefsRecord` per mirror. The writer's first draft of
`SA-0338` failed to parse. Each of its four `wrong_versions` entries was an
object, not a string. The second draft failed the finishing suite's `prose`
gate on six hits, and the finding was pooled. The delegate fixed the line by
hand.

## Done looks like

The writer's output is checked against `Spec`'s schema and the `prose` gate
inside its own session, before the finish reads it.

## Record

- 2026-11-06: filed from the spec loop's run 54.
