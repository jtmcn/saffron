---
id: b-e0044f
title: "The finishing layer queues a follow-up spec whose cell already ran, and judges the writer's drafts with `prose`, so it escalates"
status: done
tier: 2
filed: 2026-10-27
closed: 2026-10-30
specs: [SA-0327]
prs: [996]
commits: []
cites: [§5.7]
related: [b-fdbedc, b-781ea4]
---

## Problem

Found in the spec loop's run 49, by `saffron finish 58`.

The finish drafted `SA-0323` and `SA-0324`. `SA-0323`'s cell ran and reached
`READY_FOR_REVIEW` as #982. `SA-0324` was refused for two citations. The
finishing layer, `341fee6e`, then added both spec files to `.saffron/specs/`.
Its suite reported `red suite, 40 new failures`, so nothing was pushed or linked.

The delegate counted the 40 by hand. 39 are `prose` hits in the two drafts, 23
and 16. The writer never checks a draft against `prose`. The last one is
`test_queued_specs.py`, which fails `SA-0323` because its fix is already in the
tree. A spec whose cell ran belongs in `done/`, not the queue.

## Done looks like

The finishing layer retires a follow-up whose cell ran, and its suite does not
fail on a draft's prose. A finish that drafts a spec reaches its push.

## Record

- 2026-10-27: filed from the spec loop's run 49.
- 2026-10-30: done in #996 (`SA-0327`), from the spec loop's run 50.
