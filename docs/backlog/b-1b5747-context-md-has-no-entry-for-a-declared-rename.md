---
id: b-1b5747
title: '`CONTEXT.md` has no entry for a `renames` entry, the field SA-0387 adds'
status: done
tier: 2
by_hand: true
filed: 2026-11-13
closed: 2026-11-14
specs: []
prs: [1198]
commits: []
cites: [§5.4]
related: [b-f30189]
---

## Problem

Found 2026-11-13, writing `SA-0387`.

`SA-0387` adds `renames` to a spec. Each entry maps an old collected
test name to its new one, and `census` accepts the pair when the head
carried it out. `CONTEXT.md` has no word for such an entry. So nothing
constrains what the next spec calls it.

`CONTEXT.md` is `protected`, and `SA-0387` forbids it. The entry lands by
hand.

## Done looks like

A **Declared rename** entry in `CONTEXT.md`, beside **Removed name**. It
says an entry maps an old collected test name to a new one, each opaque.
It says `census` accepts a pair only when the old name is absent at head.
The new name must also be collected at head and absent at base. It says a
new name not collected at head fails `census` as `rename-not-collected`.
Its `_Avoid_` line names "removed name" (that is a `removes` entry). It
lands after `SA-0387` merges.

## Record

- 2026-11-13: filed with `SA-0387`.
- 2026-11-14: done by hand in #1198, the spec loop's run 69 pull request,
  which sits on #1196.
