---
id: b-f5ceaf
title: '`CONTEXT.md` has no entry for a removed name, the `removes` entry SA-0290 adds'
status: open
tier: 2
by_hand: true
filed: 2026-10-12
specs: [SA-0290]
prs: []
commits: []
cites: [§4.2.1]
related: [b-e773d9]
---

## Problem

Found 2026-10-12, writing `SA-0290`.

`SA-0290` adds `removes` to a spec. Each entry is a `path` or `path:name`
the spec deletes. The queue scan then refuses a candidate that clashes
on one. `CONTEXT.md` defines **Consumed name** for a `consumes`
entry, and nothing for this one. So nothing constrains what the next spec
calls it.

`CONTEXT.md` is `protected`, and `SA-0290` forbids it. The entry lands by
hand.

## Done looks like

A **Removed name** entry in `CONTEXT.md`, beside **Consumed name**. It
says an entry is a repo-relative path, or `path:name` for a name the spec
deletes or renames. It says the queue scan refuses a candidate that
clashes with another spec on one. The other names it in its body, claims or
`consumes`, and no `depends_on` path joins them. A removed bare path also
matches a `consumes` entry under that path. The other is a candidate,
or its task waits to land. A waiting partner holds the candidate, and of
two candidates the later id is held. Its `_Avoid_` line names "deletion" and
"breaking change". It lands after `SA-0290` merges.

## Record

- 2026-10-12: filed with `SA-0290`.
