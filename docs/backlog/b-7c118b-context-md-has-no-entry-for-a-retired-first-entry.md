---
id: b-7c118b
title: '`CONTEXT.md` has no entry for a `retired_first` entry, the field SA-0350 adds'
status: done
closed: 2026-11-07
tier: 2
by_hand: true
filed: 2026-11-07
specs: [SA-0350]
prs: [1042]
commits: []
cites: [§4.2.1]
related: [b-e7898b]
---

## Problem

Found 2026-11-07, writing `SA-0350`.

`SA-0350` adds `retired_first` to a spec. Each entry is a spec id that
must be retired to `done/` at the spec's base before its cell runs. The
queue scan and `saffron cell` refuse the spec while one is not.
`CONTEXT.md` has no word for such an entry. So nothing constrains what
the next spec calls it.

`CONTEXT.md` is `protected`, and `SA-0350` forbids it. The entry lands by
hand.

## Done looks like

A **Retired-first entry** in `CONTEXT.md`, beside **Consumed name**. It
says an entry is a spec id that must sit in `done/` at the spec's base. A
`MERGED` task, a waiting task or a place in the stack order does not
count. It says the queue scan refuses the spec under the `depends_on`
kind, and so does `saffron cell`, naming each id not retired. Its
`_Avoid_` line names "parent" (that is a `depends_on` entry). It lands
after `SA-0350` merges.

## Record

- 2026-11-07: filed with `SA-0350`.
- 2026-11-07: the entry landed by hand in #1042, beside `SA-0350`.
