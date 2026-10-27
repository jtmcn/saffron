---
id: b-bc8343
title: The glossary names no review commit and no commit review, the read SA-0326 adds
status: open
tier: 2
by_hand: true
filed: 2026-10-27
specs: [SA-0326]
prs: []
commits: []
cites: [§4.1, §5.7, §6.1]
related: [b-549012]
---

## Problem

Found 2026-10-27, writing `SA-0326`.

`SA-0326` adds `saffron review <task id>`. It reads one task's review commits
with the two end-review lenses, and charges each turn as an attempt labelled
`COMMIT_REVIEW`. `CONTEXT.md` defines no **Review commit**, though `DESIGN.md`
§6.1 uses the words. Its **End-review lens** entry says each lens reads
one layer in the end review, which this command makes false. Its **Phase** entry
names SPEC_REVIEW and SPEC_WRITING as the labels outside the cell pipeline, and
not this one.

`CONTEXT.md` is `protected` and generated from `ontology/factory.ttl`, and
`SA-0326` forbids both. So the entries land by hand.

## Done looks like

A **Review commit** entry: a commit pushed onto a task's branch after PACKAGE,
read by no in-cell lens. A **Commit review** entry: the two end-review lenses
reading one task's review commits, from its packaged head to its pull
request's head at origin. The **End-review lens** entry names that second
reader. The **Phase** entry adds COMMIT_REVIEW beside SPEC_REVIEW and
SPEC_WRITING. `DESIGN.md` §6.1 gains a paragraph beside `saffron regate`'s, naming the
command, its range and its three exit codes. The stack page's attempt table
(`saffron/report/stack.py:136-155`) gains a COMMIT_REVIEW row, which a cell
can land. All of it lands after `SA-0326` merges.

## Record

- 2026-10-27: filed with `SA-0326`.
